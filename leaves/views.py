from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from datetime import date
from .models import LeaveRequest, LeaveBalance, LeaveType
from .forms import LeaveRequestForm, ApprovalForm
from .seniority import seniority_entitlement
from accounts.models import Employee
from notifications.utils import notify


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


def _save_drawn_signature(employee, b64_data):
    """Decode a base64 PNG from the signature pad and save to employee.signature + signature_b64."""
    import base64
    from django.core.files.base import ContentFile
    if not b64_data or not b64_data.startswith('data:image/png;base64,'):
        return
    try:
        raw = base64.b64decode(b64_data.split(',', 1)[1])
        if employee.signature:
            try:
                employee.signature.delete(save=False)
            except Exception:
                pass
        fname = f"{employee.employee_id}_sig.png"
        employee.signature.save(fname, ContentFile(raw), save=False)
        # Also store b64 in DB so it survives Railway redeploys (ephemeral filesystem)
        employee.signature_b64 = b64_data
        employee.save(update_fields=['signature', 'signature_b64'])
    except Exception:
        pass


@login_required
def submit_leave(request):
    employee = get_employee(request)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    # Block suspended employees from applying for leave
    from datetime import date as _date
    from discipline.models import DisciplineRecord
    today = _date.today()
    active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()
    if active_suspension:
        messages.error(request, f"You cannot apply for leave while suspended (until {active_suspension.suspension_end.strftime('%d %B %Y')}).")
        return redirect('dashboard:home')

    # Get or create balance
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': seniority_entitlement(employee)}
    )

    # Build backup employee list: ALL active staff (not just same dept), excluding self
    today_date = date.today()
    all_employees = Employee.objects.filter(
        is_active=True,
    ).exclude(pk=employee.pk).select_related('user', 'department')

    on_leave_pks = set(
        LeaveRequest.objects.filter(
            status='approved',
            employee__in=all_employees,
            start_date__lte=today_date,
            end_date__gte=today_date,
        ).values_list('employee_id', flat=True)
    )

    backup_choices = [
        {'id': e.pk, 'name': e.get_full_name(), 'dept': str(e.department or ''), 'unavailable': e.pk in on_leave_pks}
        for e in all_employees.order_by('user__last_name', 'user__first_name')
    ]

    form = LeaveRequestForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = employee

        # Backup employee — required
        backup_id = request.POST.get('backup_employee')
        if not backup_id:
            messages.error(request, "Please select a back-up employee to cover you during your leave.")
            return render(request, 'leaves/request_form.html', {
                'form': form, 'balance': balance, 'backup_choices': backup_choices,
                'leave_types': LeaveType.objects.filter(is_active=True),
            })
        try:
            leave.backup_employee = Employee.objects.get(pk=backup_id)
        except Employee.DoesNotExist:
            messages.error(request, "Selected back-up employee not found.")
            return render(request, 'leaves/request_form.html', {
                'form': form, 'balance': balance, 'backup_choices': backup_choices,
                'leave_types': LeaveType.objects.filter(is_active=True),
            })

        # Validate balance (only for deductible leave types)
        if leave.leave_type.is_deductible and leave.total_days > balance.remaining_days:
            messages.error(request, f"Insufficient leave balance. You have {balance.remaining_days} days remaining.")
        else:
            # Check for overlapping requests
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved', 'approved'],
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date,
            )
            if overlapping.exists():
                messages.error(request, "You already have a leave request for overlapping dates.")
            else:
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                if sig_b64 and sig_b64.startswith('data:image/'):
                    leave.employee_sig_b64 = sig_b64
                elif employee.signature_b64:
                    leave.employee_sig_b64 = employee.signature_b64
                leave.save()
                if employee.is_intern() or employee.is_wacs_resident():
                    # Interns and WACS residents skip manager — go directly to HR
                    role_label = 'Intern' if employee.is_intern() else 'WACS Resident'
                    leave.status = LeaveRequest.STATUS_MANAGER_APPROVED
                    leave.save(update_fields=['status'])
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Sent directly to HR for review.")
                    for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
                        notify(
                            hr_emp.user,
                            f'{role_label} Leave Request — {employee.get_full_name()}',
                            f'{employee.get_full_name()} ({role_label}) has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). '
                            f'No manager approval required — awaiting your HR review.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                        )
                elif employee.role in ('admin_director', 'medical_director') or employee.reports_to_ceo:
                    # Admin Director, Medical Director, or any staff flagged reports_to_ceo — CEO sole approver
                    role_labels = {'admin_director': 'Administration Director', 'medical_director': 'Medical Director'}
                    role_label = role_labels.get(employee.role, 'Staff')
                    leave.status = LeaveRequest.STATUS_HR_APPROVED
                    leave.save(update_fields=['status'])
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Sent directly to the CEO for approval.")
                    for ceo_emp in Employee.objects.filter(role='ceo', is_active=True).select_related('user'):
                        notify(
                            ceo_emp.user,
                            f'{role_label} Leave — Awaiting Your Approval',
                            f'{employee.get_full_name()} ({role_label}) has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). Awaiting your approval.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:ceo_action', kwargs={'pk': leave.pk}),
                        )
                elif employee.is_hr():
                    # HR staff — skip all intermediate steps; Admin Director approves directly
                    leave.status = LeaveRequest.STATUS_HR_APPROVED
                    leave.save(update_fields=['status'])
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Sent directly to Administration Director for approval.")
                    for dir_emp in Employee.objects.filter(role__in=('admin_director', 'finance_director'), is_active=True).select_related('user'):
                        notify(
                            dir_emp.user,
                            f'HR Staff Leave — Awaiting Your Approval — {employee.get_full_name()}',
                            f'{employee.get_full_name()} (HR) has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). '
                            f'No intermediate approvals required — awaiting your decision.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:director_action', kwargs={'pk': leave.pk}),
                        )
                elif employee.reports_to_hr:
                    # Reports directly to HR — HR is the FINAL approver, no Director step
                    leave.status = LeaveRequest.STATUS_MANAGER_APPROVED
                    leave.save(update_fields=['status'])
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Sent to HR for final approval.")
                    for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
                        notify(
                            hr_emp.user,
                            f'Leave Request (HR Final) — {employee.get_full_name()}',
                            f'{employee.get_full_name()} has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). '
                            f'You are the final approver — no Director step required.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:hr_action', kwargs={'pk': leave.pk}),
                        )
                elif employee.reports_to_director:
                    # Reports directly to Director — skip unit head and manager; goes to HR then Director
                    leave.status = LeaveRequest.STATUS_MANAGER_APPROVED
                    leave.save(update_fields=['status'])
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Sent directly to HR for review.")
                    for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
                        notify(
                            hr_emp.user,
                            f'Leave Request (Direct Report) — {employee.get_full_name()}',
                            f'{employee.get_full_name()} has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). '
                            f'No unit head or manager approval required — awaiting your HR review.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:hr_action', kwargs={'pk': leave.pk}),
                        )
                elif employee.unit_head:
                    # Has unit head — notify unit head first
                    messages.success(request, f"Leave request submitted for {leave.total_days} day(s). Awaiting Unit Head approval.")
                    notify(
                        employee.unit_head.user,
                        f'New Leave Request — {employee.get_full_name()}',
                        f'{employee.get_full_name()} has submitted a {leave.leave_type} request '
                        f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). Awaiting your Unit Head approval.',
                        notification_type='leave_submitted',
                        url=reverse('leaves:unit_head_action', kwargs={'pk': leave.pk}),
                    )
                else:
                    # No unit head — notify supervisor (line manager) directly
                    messages.success(request, f"Leave request submitted successfully for {leave.total_days} day(s). Awaiting manager approval.")
                    if employee.supervisor:
                        notify(
                            employee.supervisor.user,
                            f'New Leave Request — {employee.get_full_name()}',
                            f'{employee.get_full_name()} has submitted a {leave.leave_type} request '
                            f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). Awaiting your approval.',
                            notification_type='leave_submitted',
                            url=reverse('leaves:manager_action', kwargs={'pk': leave.pk}),
                        )
                try:
                    from dashboard.models import AuditLog
                    AuditLog.log(
                        request, AuditLog.ACTION_LEAVE_SUBMIT,
                        f"Submitted {leave.leave_type} leave request for {leave.total_days} day(s) "
                        f"({leave.start_date} → {leave.end_date})",
                    )
                except Exception:
                    pass
                return redirect('leaves:my_requests')

    import json
    leave_types = LeaveType.objects.filter(is_active=True).values('id', 'is_deductible')
    deductible_map = json.dumps({str(lt['id']): lt['is_deductible'] for lt in leave_types})

    return render(request, 'leaves/request_form.html', {
        'form': form,
        'balance': balance,
        'deductible_map': deductible_map,
        'backup_choices': backup_choices,
        'employee': employee,
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def my_requests(request):
    employee = get_employee(request)
    if not employee:
        return redirect('dashboard:home')

    current_year = date.today().year
    year_filter = int(request.GET.get('year', current_year))
    status_filter = request.GET.get('status', '')

    qs = LeaveRequest.objects.filter(
        employee=employee,
        start_date__year=year_filter,
    ).select_related('leave_type', 'manager_action_by__user', 'hr_action_by__user')

    if status_filter:
        qs = qs.filter(status=status_filter)

    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=current_year,
        defaults={'total_entitlement': seniority_entitlement(employee, current_year)}
    )

    return render(request, 'leaves/my_requests.html', {
        'leave_requests': qs,
        'balance': balance,
        'year_filter': year_filter,
        'status_filter': status_filter,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'years': range(2000, current_year + 11),
    })


@login_required
def cancel_request(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=employee)
    if leave.can_cancel():
        leave.status = LeaveRequest.STATUS_CANCELLED
        leave.save()
        messages.success(request, "Leave request cancelled.")

        # Notify unit head and/or line manager so they know not to act on it
        notif_title = f'Leave Request Cancelled — {employee.get_full_name()}'
        notif_msg = (
            f'{employee.get_full_name()} has cancelled their {leave.leave_type} leave request '
            f'({leave.start_date} → {leave.end_date}). No further action is needed.'
        )
        detail_url = reverse('leaves:detail', kwargs={'pk': leave.pk})
        recipients = set()
        if leave.employee.unit_head:
            recipients.add(leave.employee.unit_head.user)
        if leave.employee.supervisor:
            recipients.add(leave.employee.supervisor.user)
        for recipient in recipients:
            notify(recipient, notif_title, notif_msg,
                   notification_type='leave_cancelled', url=detail_url)
    else:
        messages.error(request, "This request cannot be cancelled.")
    return redirect('leaves:my_requests')


@login_required
def unit_head_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_unit_head():
        messages.error(request, "Access denied. Unit Head role required.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_PENDING,
        employee__unit_head=employee,
    ).select_related('employee__user', 'employee__department', 'leave_type')

    return render(request, 'leaves/unit_head_approvals.html', {
        'pending_requests': pending,
    })


@login_required
def unit_head_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_unit_head():
        messages.error(request, "Access denied. Unit Head role required.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.employee.unit_head != employee and not request.user.is_superuser:
        messages.error(request, "You are not the Unit Head for this employee.")
        return redirect('leaves:unit_head_approvals')

    if leave.status != LeaveRequest.STATUS_PENDING:
        messages.warning(request, f"Leave request #{pk} is no longer pending (status: {leave.get_status_display()}).")
        return redirect('leaves:unit_head_approvals')

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.unit_head_action_by = employee
            leave.unit_head_action_date = timezone.now()
            leave.unit_head_remarks = remarks
            if action == 'approve':
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                leave.unit_head_sig_b64 = sig_b64 if sig_b64.startswith('data:image/') else (employee.signature_b64 or '')
                leave.status = LeaveRequest.STATUS_UNIT_HEAD_APPROVED
                leave.save()
                messages.success(request, "Leave approved. Forwarded to Line Manager.")
                notify(
                    leave.employee.user,
                    'Leave Request — Unit Head Approved',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'has been approved by your Unit Head and is now awaiting your Line Manager.',
                    notification_type='leave_manager_approved',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
                if leave.employee.supervisor:
                    notify(
                        leave.employee.supervisor.user,
                        f'Leave Awaiting Your Approval — {leave.employee.get_full_name()}',
                        f'{leave.employee.get_full_name()} ({leave.employee.department or "No dept"}) '
                        f'has a {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                        f'{leave.total_days} day(s)) approved by Unit Head, pending your review.',
                        notification_type='leave_submitted',
                        url=reverse('leaves:manager_action', kwargs={'pk': leave.pk}),
                    )
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_UNIT_HEAD
                leave.save()
                messages.warning(request, f"Leave request #{pk} rejected.")
                notify(
                    leave.employee.user,
                    'Leave Request — Rejected by Unit Head',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'was rejected by your Unit Head.'
                    + (f' Remarks: {remarks}' if remarks else ''),
                    notification_type='leave_rejected',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            return redirect('leaves:unit_head_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Unit Head Review',
        'action_type': 'unit_head',
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def manager_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_manager():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    if request.user.is_superuser:
        pending = LeaveRequest.objects.filter(
            status__in=[LeaveRequest.STATUS_PENDING, LeaveRequest.STATUS_UNIT_HEAD_APPROVED]
        ).select_related('employee__user', 'employee__department', 'leave_type')
    else:
        # Show 'pending' leaves from employees WITHOUT a unit_head (direct reports)
        # and 'unit_head_approved' from employees WITH a unit_head (both supervised by this manager)
        pending = LeaveRequest.objects.filter(
            employee__supervisor=employee
        ).filter(
            Q(status=LeaveRequest.STATUS_PENDING, employee__unit_head__isnull=True) |
            Q(status=LeaveRequest.STATUS_UNIT_HEAD_APPROVED)
        ).select_related('employee__user', 'employee__department', 'leave_type')

    return render(request, 'leaves/manager_approvals.html', {
        'pending_requests': pending,
    })


@login_required
def manager_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_manager():
        messages.error(request, "Access denied. Manager role required.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk)

    # Check supervisor authority (superuser bypasses this)
    if not request.user.is_superuser and leave.employee.supervisor != employee:
        messages.error(request, "You are not the supervisor for this employee.")
        return redirect('leaves:manager_approvals')

    # Accept both 'pending' (no unit_head employees) and 'unit_head_approved' (has unit_head)
    valid_statuses = [LeaveRequest.STATUS_PENDING, LeaveRequest.STATUS_UNIT_HEAD_APPROVED]
    if leave.status not in valid_statuses:
        messages.warning(
            request,
            f"Leave request #{pk} is no longer pending "
            f"(current status: {leave.get_status_display()}). No action taken."
        )
        return redirect('leaves:manager_approvals')

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.manager_action_by = employee
            leave.manager_action_date = timezone.now()
            leave.manager_remarks = remarks
            if action == 'approve':
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                leave.manager_sig_b64 = sig_b64 if sig_b64.startswith('data:image/') else (employee.signature_b64 or '')
                leave.status = LeaveRequest.STATUS_MANAGER_APPROVED
                messages.success(request, "Leave request approved. Forwarded to HR for review.")
                notify(
                    leave.employee.user,
                    'Leave Request — Manager Approved',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'has been approved by your manager and is now awaiting HR review.',
                    notification_type='leave_manager_approved',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
                # Notify all HR admins that a leave is awaiting their review
                from accounts.models import Employee as _Emp
                for hr_emp in _Emp.objects.filter(role='hr', is_active=True).select_related('user'):
                    notify(
                        hr_emp.user,
                        f'Leave Awaiting HR Review — {leave.employee.get_full_name()}',
                        f'{leave.employee.get_full_name()} ({leave.employee.department or "No dept"}) '
                        f'has a {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                        f'{leave.total_days} day(s)) pending your review.',
                        notification_type='leave_submitted',
                        url=reverse('leaves:hr_action', kwargs={'pk': leave.pk}),
                    )
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_MANAGER
                messages.warning(request, f"Leave request #{pk} has been rejected.")
                notify(
                    leave.employee.user,
                    'Leave Request — Rejected by Manager',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'was rejected by your manager.'
                    + (f' Remarks: {remarks}' if remarks else ''),
                    notification_type='leave_rejected',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            leave.save()
            try:
                from dashboard.models import AuditLog
                audit_action = AuditLog.ACTION_LEAVE_APPROVE if action == 'approve' else AuditLog.ACTION_LEAVE_REJECT
                AuditLog.log(
                    request, audit_action,
                    f"Manager {'approved' if action == 'approve' else 'rejected'} leave request "
                    f"for {leave.employee.get_full_name()} ({leave.leave_type}, {leave.start_date} → {leave.end_date})",
                    target_user=leave.employee.user,
                )
            except Exception:
                pass
            return redirect('leaves:manager_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Manager Review',
        'action_type': 'manager',
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def hr_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_hr():
        messages.error(request, "Access denied. HR Admin only.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_MANAGER_APPROVED
    ).select_related('employee__user', 'employee__department', 'leave_type', 'manager_action_by__user')

    return render(request, 'leaves/hr_approvals.html', {
        'pending_requests': pending,
    })


@login_required
def hr_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_hr():
        messages.error(request, "Access denied. HR Admin role required.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.status != LeaveRequest.STATUS_MANAGER_APPROVED:
        messages.warning(
            request,
            f"Leave request #{pk} is not awaiting HR approval "
            f"(current status: {leave.get_status_display()}). No action taken."
        )
        return redirect('leaves:hr_approvals')

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.hr_action_by = employee
            leave.hr_action_date = timezone.now()
            leave.hr_remarks = remarks
            if action == 'approve':
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                hr_sig = sig_b64 if sig_b64.startswith('data:image/') else (employee.signature_b64 or '')
                leave.hr_sig_b64 = hr_sig
                if leave.employee.reports_to_hr:
                    # HR is the FINAL approver — approve directly, no Director step
                    now = timezone.now()
                    if not leave.unit_head_action_by:
                        leave.unit_head_action_by = employee
                        leave.unit_head_action_date = now
                        leave.unit_head_remarks = 'Direct report to HR — approved by HR'
                        leave.unit_head_sig_b64 = hr_sig
                    if not leave.manager_action_by:
                        leave.manager_action_by = employee
                        leave.manager_action_date = now
                        leave.manager_remarks = 'Direct report to HR — approved by HR'
                        leave.manager_sig_b64 = hr_sig
                    # Also fill director slot so PDF is complete
                    leave.director_action_by = employee
                    leave.director_action_date = now
                    leave.director_remarks = 'Final approval by HR (reports directly to HR)'
                    leave.director_sig_b64 = hr_sig
                    leave.status = LeaveRequest.STATUS_APPROVED
                    messages.success(request, "Leave request FULLY APPROVED by HR (final approver).")
                    notify(
                        leave.employee.user,
                        'Leave Request — Fully Approved by HR',
                        f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                        f'{leave.total_days} day(s)) has been fully approved by HR.',
                        notification_type='leave_approved',
                        url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                    )
                else:
                    leave.status = LeaveRequest.STATUS_HR_APPROVED
                    messages.success(request, "Leave request approved by HR. Forwarded to Administration Director.")
                    notify(
                        leave.employee.user,
                        'Leave Request — HR Approved',
                        f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                        f'has been approved by HR and is now awaiting the Administration Director\'s final decision.',
                        notification_type='leave_hr_approved',
                        url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                    )
                    # Notify Admin Director and Finance Director
                    from accounts.models import Employee as _Emp
                    for dir_emp in _Emp.objects.filter(role__in=('admin_director', 'finance_director'), is_active=True).select_related('user'):
                        notify(
                            dir_emp.user,
                            f'Leave Awaiting Your Approval — {leave.employee.get_full_name()}',
                            f'{leave.employee.get_full_name()} ({leave.employee.department or "No dept"}) '
                            f'has a {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                            f'{leave.total_days} day(s)) awaiting your final decision.',
                            notification_type='leave_hr_approved',
                            url=reverse('leaves:director_action', kwargs={'pk': leave.pk}),
                        )
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_HR
                messages.warning(request, f"Leave request #{pk} has been rejected by HR.")
                notify(
                    leave.employee.user,
                    'Leave Request — Rejected by HR',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'was rejected by HR.'
                    + (f' Remarks: {remarks}' if remarks else ''),
                    notification_type='leave_rejected',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            leave.save()
            try:
                from dashboard.models import AuditLog
                audit_action = AuditLog.ACTION_LEAVE_APPROVE if action == 'approve' else AuditLog.ACTION_LEAVE_REJECT
                AuditLog.log(
                    request, audit_action,
                    f"HR {'approved' if action == 'approve' else 'rejected'} leave request "
                    f"for {leave.employee.get_full_name()} ({leave.leave_type}, {leave.start_date} → {leave.end_date})",
                    target_user=leave.employee.user,
                )
            except Exception:
                pass
            return redirect('leaves:hr_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'HR Final Review',
        'action_type': 'hr',
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def director_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_director():
        messages.error(request, "Access denied. Administration Director only.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_HR_APPROVED
    ).exclude(
        # Admin Director, Medical Director, and reports_to_ceo go to CEO instead
        Q(employee__role__in=('admin_director', 'medical_director')) | Q(employee__reports_to_ceo=True)
    ).select_related('employee__user', 'employee__department', 'leave_type', 'manager_action_by__user', 'hr_action_by__user')

    # Check if admin director is on leave (finance director may be covering)
    from datetime import date as _date
    today = _date.today()
    admin_directors = Employee.objects.filter(role='admin_director', is_active=True)
    admin_dir_on_leave = any(
        req for ad in admin_directors
        for req in ad.leave_requests.filter(status='approved', start_date__lte=today, end_date__gte=today)
    )

    return render(request, 'leaves/director_approvals.html', {
        'pending_requests': pending,
        'employee': employee,
        'admin_dir_on_leave': admin_dir_on_leave,
    })


@login_required
def director_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_director():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.status != LeaveRequest.STATUS_HR_APPROVED:
        messages.warning(
            request,
            f"Leave request #{pk} is not awaiting Director approval "
            f"(current status: {leave.get_status_display()}). No action taken."
        )
        return redirect('leaves:director_approvals')

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.director_action_by = employee
            leave.director_action_date = timezone.now()
            leave.director_remarks = remarks
            if action == 'approve':
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                dir_sig = sig_b64 if sig_b64.startswith('data:image/') else (employee.signature_b64 or '')
                leave.director_sig_b64 = dir_sig
                leave.status = LeaveRequest.STATUS_APPROVED
                # Auto-fill bypassed approval slots for direct reports and HR staff
                applicant = leave.employee
                now = timezone.now()
                if applicant.reports_to_director or applicant.is_hr():
                    if not leave.unit_head_action_by:
                        leave.unit_head_action_by = employee
                        leave.unit_head_action_date = now
                        leave.unit_head_remarks = 'Direct report — approved by Administration Director'
                        leave.unit_head_sig_b64 = dir_sig
                    if not leave.manager_action_by:
                        leave.manager_action_by = employee
                        leave.manager_action_date = now
                        leave.manager_remarks = 'Direct report — approved by Administration Director'
                        leave.manager_sig_b64 = dir_sig
                    if applicant.is_hr() and not leave.hr_action_by:
                        leave.hr_action_by = employee
                        leave.hr_action_date = now
                        leave.hr_remarks = 'HR applicant — approved by Administration Director'
                        leave.hr_sig_b64 = dir_sig
                messages.success(request, "Leave request FULLY APPROVED by Administration Director.")
                notify(
                    leave.employee.user,
                    'Leave Request — Fully Approved',
                    f'Great news! Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                    f'{leave.total_days} day(s)) has been fully approved by the Administration Director.',
                    notification_type='leave_approved',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_DIRECTOR
                messages.warning(request, f"Leave request #{pk} has been rejected by Administration Director.")
                notify(
                    leave.employee.user,
                    'Leave Request — Rejected by Director',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'was rejected by the Administration Director.'
                    + (f' Remarks: {remarks}' if remarks else ''),
                    notification_type='leave_rejected',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            leave.save()
            try:
                from dashboard.models import AuditLog
                audit_action = AuditLog.ACTION_LEAVE_APPROVE if action == 'approve' else AuditLog.ACTION_LEAVE_REJECT
                AuditLog.log(
                    request, audit_action,
                    f"Director {'approved' if action == 'approve' else 'rejected'} leave request "
                    f"for {leave.employee.get_full_name()} ({leave.leave_type}, {leave.start_date} → {leave.end_date})",
                    target_user=leave.employee.user,
                )
            except Exception:
                pass
            return redirect('leaves:director_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Administration Director — Final Review',
        'action_type': 'director',
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def ceo_approvals(request):
    """CEO sees and approves Admin Director leave requests."""
    employee = get_employee(request)
    if not employee or not employee.is_ceo():
        messages.error(request, "Access denied. CEO only.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_HR_APPROVED,
    ).filter(
        Q(employee__role__in=('admin_director', 'medical_director')) | Q(employee__reports_to_ceo=True)
    ).select_related('employee__user', 'employee__department', 'leave_type')

    return render(request, 'leaves/ceo_approvals.html', {
        'pending_requests': pending,
        'employee': employee,
    })


@login_required
def ceo_action(request, pk):
    """CEO approves or rejects Admin Director leave."""
    employee = get_employee(request)
    if not employee or not employee.is_ceo():
        messages.error(request, "Access denied. CEO only.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk)

    applicant = leave.employee
    is_ceo_case = applicant.role in ('admin_director', 'medical_director') or applicant.reports_to_ceo
    if leave.status != LeaveRequest.STATUS_HR_APPROVED or not is_ceo_case:
        messages.warning(request, f"Leave request #{pk} is not awaiting CEO approval.")
        return redirect('leaves:ceo_approvals')

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            # Record CEO approval in the director slot (CEO is acting as final approver)
            leave.director_action_by = employee
            leave.director_action_date = timezone.now()
            leave.director_remarks = remarks
            if action == 'approve':
                sig_b64 = request.POST.get('signature_data', '')
                _save_drawn_signature(employee, sig_b64)
                ceo_sig = sig_b64 if sig_b64.startswith('data:image/') else (employee.signature_b64 or '')
                leave.director_sig_b64 = ceo_sig
                # Also fill all bypassed intermediate slots with CEO info
                now = timezone.now()
                leave.unit_head_action_by = employee
                leave.unit_head_action_date = now
                leave.unit_head_remarks = 'Approved by CEO (Administration Director leave)'
                leave.unit_head_sig_b64 = ceo_sig
                leave.manager_action_by = employee
                leave.manager_action_date = now
                leave.manager_remarks = 'Approved by CEO (Administration Director leave)'
                leave.manager_sig_b64 = ceo_sig
                leave.hr_action_by = employee
                leave.hr_action_date = now
                leave.hr_remarks = 'Approved by CEO'
                leave.hr_sig_b64 = ceo_sig
                leave.status = LeaveRequest.STATUS_APPROVED
                leave.save()
                messages.success(request, "Leave request FULLY APPROVED by CEO.")
                cover_note = ''
                if leave.employee.role == 'admin_director':
                    cover_note = ' Note: The Finance Director will cover your responsibilities during your absence.'
                elif leave.employee.role == 'medical_director':
                    cover_note = ' Please ensure your medical duties are covered during your absence.'
                notify(
                    leave.employee.user,
                    'Leave Request — Approved by CEO',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}, '
                    f'{leave.total_days} day(s)) has been approved by the CEO.' + cover_note,
                    notification_type='leave_approved',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_DIRECTOR
                leave.save()
                messages.warning(request, f"Leave request #{pk} rejected by CEO.")
                notify(
                    leave.employee.user,
                    'Leave Request — Rejected by CEO',
                    f'Your {leave.leave_type} request ({leave.start_date} → {leave.end_date}) '
                    f'was rejected by the CEO.'
                    + (f' Remarks: {remarks}' if remarks else ''),
                    notification_type='leave_rejected',
                    url=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
            try:
                from dashboard.models import AuditLog
                audit_action = AuditLog.ACTION_LEAVE_APPROVE if action == 'approve' else AuditLog.ACTION_LEAVE_REJECT
                AuditLog.log(
                    request, audit_action,
                    f"CEO {'approved' if action == 'approve' else 'rejected'} leave request "
                    f"for {leave.employee.get_full_name()} ({leave.leave_type}, {leave.start_date} → {leave.end_date})",
                    target_user=leave.employee.user,
                )
            except Exception:
                pass
            return redirect('leaves:ceo_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'CEO — Administration Director Leave Approval',
        'action_type': 'ceo',
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def leave_detail(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk)

    # Only owner, their manager, HR, Director, CEO, or Superuser can view
    can_view = (
        leave.employee == employee or
        request.user.is_superuser or
        (employee and employee.is_hr()) or
        (employee and employee.is_director()) or
        (employee and employee.is_ceo()) or
        (employee and employee.is_manager() and leave.employee.supervisor == employee)
    )
    if not can_view:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    return render(request, 'leaves/leave_detail.html', {'leave': leave})


@login_required
def leave_edit(request, pk):
    """Employee edits their own leave request — only while status is still pending."""
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.employee != employee:
        messages.error(request, "You can only edit your own leave requests.")
        return redirect('dashboard:home')
    if leave.status != LeaveRequest.STATUS_PENDING:
        messages.error(request, "This request can no longer be edited — it has already been reviewed.")
        return redirect('leaves:detail', pk=pk)

    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': seniority_entitlement(employee)}
    )

    dept_employees = Employee.objects.filter(
        department=employee.department, is_active=True,
    ).exclude(pk=employee.pk).select_related('user')
    on_leave_pks = set(
        LeaveRequest.objects.filter(
            status='approved',
            employee__in=dept_employees,
            start_date__lte=date.today(),
            end_date__gte=date.today(),
        ).values_list('employee_id', flat=True)
    )
    backup_choices = [
        {'id': e.pk, 'name': e.get_full_name(), 'unavailable': e.pk in on_leave_pks}
        for e in dept_employees
    ]

    form = LeaveRequestForm(request.POST or None, request.FILES or None, instance=leave)
    if request.method == 'POST' and form.is_valid():
        updated = form.save(commit=False)

        backup_id = request.POST.get('backup_employee')
        if backup_id:
            try:
                updated.backup_employee = Employee.objects.get(pk=backup_id)
            except Employee.DoesNotExist:
                pass

        if updated.leave_type.is_deductible and updated.total_days > balance.remaining_days + leave.total_days:
            messages.error(request, f"Insufficient leave balance.")
        else:
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved', 'approved'],
                start_date__lte=updated.end_date,
                end_date__gte=updated.start_date,
            ).exclude(pk=leave.pk)
            if overlapping.exists():
                messages.error(request, "You already have a leave request for overlapping dates.")
            else:
                updated.save()
                messages.success(request, "Leave request updated successfully.")

                # Notify unit head and line manager about the change
                notif_title = f'Leave Request Edited — {employee.get_full_name()}'
                notif_msg = (
                    f'{employee.get_full_name()} has edited their {updated.leave_type} leave request '
                    f'(now: {updated.start_date} → {updated.end_date}, {updated.total_days} day(s)). '
                    f'Please review the updated request before approving.'
                )
                detail_url = reverse('leaves:detail', kwargs={'pk': pk})
                recipients = set()
                if employee.unit_head:
                    recipients.add(employee.unit_head.user)
                if employee.supervisor:
                    recipients.add(employee.supervisor.user)
                for recipient in recipients:
                    notify(recipient, notif_title, notif_msg,
                           notification_type='leave_submitted', url=detail_url)
                return redirect('leaves:detail', pk=pk)

    import json
    leave_types = LeaveType.objects.filter(is_active=True).values('id', 'is_deductible')
    deductible_map = json.dumps({str(lt['id']): lt['is_deductible'] for lt in leave_types})

    return render(request, 'leaves/edit_form.html', {
        'form': form,
        'leave': leave,
        'balance': balance,
        'deductible_map': deductible_map,
        'backup_choices': backup_choices,
        'employee': employee,
        'current_sig_b64': employee.signature_b64 or '',
    })


@login_required
def pdf_leave(request, pk):
    """Download the official leave authorisation form as a filled PDF."""
    from django.http import HttpResponse
    from .pdf_utils import generate_leave_pdf

    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk)

    can_view = (
        leave.employee == employee or
        request.user.is_superuser or
        (employee and employee.is_hr()) or
        (employee and employee.is_director()) or
        (employee and employee.is_ceo()) or
        (employee and employee.is_manager() and leave.employee.supervisor == employee) or
        (employee and employee.is_unit_head() and leave.employee.unit_head == employee)
    )
    if not can_view:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    buf = generate_leave_pdf(leave)
    filename = f"leave_authorisation_{leave.employee.user.last_name}_{leave.start_date}.pdf"
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def print_leave(request, pk):
    """Redirect to the official PDF — the old HTML print view is retired."""
    return redirect('leaves:pdf_leave', pk=pk)


@login_required
def all_leaves_hr(request):
    """HR/Director view of all leave requests"""
    employee = get_employee(request)
    if not employee or (not employee.is_hr() and not employee.is_director() and not employee.is_ceo()):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    status_filter = request.GET.get('status', '')
    dept_filter   = request.GET.get('dept', '')
    emp_filter    = request.GET.get('employee', '')
    try:
        year_filter = int(request.GET.get('year', date.today().year))
    except (ValueError, TypeError):
        year_filter = date.today().year

    qs = LeaveRequest.objects.select_related(
        'employee__user', 'employee__department', 'leave_type'
    ).filter(start_date__year=year_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)
    if emp_filter:
        qs = qs.filter(employee_id=emp_filter)
    elif dept_filter:
        qs = qs.filter(employee__department_id=dept_filter)

    from accounts.models import Department
    departments = Department.objects.all()
    all_employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')

    return render(request, 'leaves/all_leaves.html', {
        'leave_requests': qs,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
        'emp_filter': emp_filter,
        'year_filter': year_filter,
        'departments': departments,
        'all_employees': all_employees,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'years': range(2000, date.today().year + 11),
    })


@login_required
def employee_leave_summary(request, pk):
    """Full leave summary for a specific employee — accessible to HR, Director, and the employee themselves."""
    from accounts.models import Employee as EmpModel
    viewer = get_employee(request)
    target = get_object_or_404(EmpModel, pk=pk)

    # Access: HR, Director, superuser, or the employee viewing their own summary
    if not (request.user.is_superuser or
            (viewer and (viewer.is_hr() or viewer.is_director())) or
            (viewer and viewer.pk == target.pk)):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    year = int(request.GET.get('year', date.today().year))
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=target, year=year,
        defaults={'total_entitlement': seniority_entitlement(target, year)}
    )

    all_requests = LeaveRequest.objects.filter(
        employee=target, start_date__year=year
    ).select_related('leave_type').order_by('-start_date')

    return render(request, 'leaves/employee_leave_summary.html', {
        'target': target,
        'balance': balance,
        'all_requests': all_requests,
        'year': year,
        'years': range(2000, date.today().year + 11),
    })


@login_required
def admin_override_leave(request, pk):
    """Superuser-only: cancel or revert any leave request back to pending."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if request.method != 'POST':
        return redirect('leaves:detail', pk=pk)

    leave = get_object_or_404(LeaveRequest, pk=pk)
    action = request.POST.get('admin_action')
    reason = request.POST.get('admin_reason', '').strip()

    if action == 'cancel':
        leave.status = LeaveRequest.STATUS_CANCELLED
        leave.director_remarks = f"[Admin cancelled] {reason}"
        leave.save()
        messages.success(request, f"Leave request #{pk} cancelled by admin. Balance restored automatically.")

    elif action == 'revert':
        # Send back to pending — clears all approval chain
        leave.status = LeaveRequest.STATUS_PENDING
        leave.manager_action_by = None
        leave.manager_action_date = None
        leave.manager_remarks = ''
        leave.hr_action_by = None
        leave.hr_action_date = None
        leave.hr_remarks = ''
        leave.director_action_by = None
        leave.director_action_date = None
        leave.director_remarks = f"[Admin reverted to pending] {reason}"
        leave.save()
        messages.success(request, f"Leave request #{pk} reverted to Pending. It must go through approval again.")

    return redirect('leaves:detail', pk=pk)


@login_required
def admin_edit_leave(request, pk):
    """Superuser-only: correct total_days, dates, status, and add a note on any leave request."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if request.method != 'POST':
        return redirect('leaves:detail', pk=pk)

    leave = get_object_or_404(LeaveRequest, pk=pk)

    try:
        new_days = int(request.POST.get('corrected_days', '').strip())
        if new_days < 0:
            raise ValueError
    except (ValueError, AttributeError):
        messages.error(request, "Invalid day count. Please enter a whole number ≥ 0.")
        return redirect('leaves:detail', pk=pk)

    new_status = request.POST.get('corrected_status', '').strip()
    admin_note = request.POST.get('correction_note', '').strip()
    new_start  = request.POST.get('corrected_start', '').strip()
    new_end    = request.POST.get('corrected_end', '').strip()

    valid_statuses = dict(LeaveRequest.STATUS_CHOICES).keys()
    update_fields = {'total_days': new_days}

    if new_status and new_status in valid_statuses:
        update_fields['status'] = new_status

    # Update dates if provided — validate first
    from datetime import datetime as _dt
    parsed_start = parsed_end = None
    if new_start:
        try:
            parsed_start = _dt.strptime(new_start, '%Y-%m-%d').date()
            update_fields['start_date'] = parsed_start
        except ValueError:
            messages.error(request, "Invalid start date format.")
            return redirect('leaves:detail', pk=pk)
    if new_end:
        try:
            parsed_end = _dt.strptime(new_end, '%Y-%m-%d').date()
            update_fields['end_date'] = parsed_end
        except ValueError:
            messages.error(request, "Invalid end date format.")
            return redirect('leaves:detail', pk=pk)

    if admin_note:
        existing = leave.director_remarks or ''
        separator = '\n' if existing else ''
        update_fields['director_remarks'] = f"{existing}{separator}[Admin correction] {admin_note}"

    # Use queryset .update() to bypass save() so total_days is NOT recalculated
    LeaveRequest.objects.filter(pk=pk).update(**update_fields)

    parts = [f"{new_days} days"]
    if 'start_date' in update_fields:
        parts.append(f"start → {new_start}")
    if 'end_date' in update_fields:
        parts.append(f"end → {new_end}")
    if 'status' in update_fields:
        parts.append(f"status → {new_status}")
    messages.success(request, f"Leave #{pk} corrected: {', '.join(parts)}.")
    return redirect('leaves:detail', pk=pk)


# ── Leave Type Management (superuser only) ──────────────────────────────────

DEFAULT_LEAVE_TYPES = [
    {'name': 'Annual Leave',               'is_deductible': True,  'color': 'primary',   'requires_document': False},
    {'name': 'Permission',                 'is_deductible': True,  'color': 'warning',   'requires_document': False},
    {'name': 'Permission for School Leave','is_deductible': True,  'color': 'info',      'requires_document': True},
    {'name': 'Sick Leave',                 'is_deductible': False, 'color': 'danger',    'requires_document': True},
    {'name': 'Maternity Leave',            'is_deductible': False, 'color': 'success',   'requires_document': True},
    {'name': 'Paternity Leave',            'is_deductible': False, 'color': 'success',   'requires_document': True},
    {'name': 'Marriage Leave',             'is_deductible': False, 'color': 'secondary', 'requires_document': False},
    {'name': 'Compassionate Leave',        'is_deductible': False, 'color': 'dark',      'requires_document': False},
    {'name': 'Study Leave',               'is_deductible': False, 'color': 'secondary', 'requires_document': False},
]


def seed_default_leave_types():
    """Create the default leave types if they don't already exist."""
    for lt in DEFAULT_LEAVE_TYPES:
        LeaveType.objects.get_or_create(name=lt['name'], defaults={
            'is_deductible':      lt['is_deductible'],
            'color':              lt['color'],
            'requires_document':  lt['requires_document'],
            'is_active':          True,
        })


@login_required
def leave_type_list(request):
    emp = get_employee(request)
    if not (request.user.is_superuser or (emp and (emp.is_hr() or emp.is_ceo()))):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    leave_types = LeaveType.objects.all()
    return render(request, 'leaves/leave_type_list.html', {'leave_types': leave_types})


@login_required
def leave_type_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_deductible = request.POST.get('is_deductible') == '1'
        requires_document = request.POST.get('requires_document') == '1'
        color = request.POST.get('color', 'primary').strip()
        is_active = request.POST.get('is_active') == '1'
        if not name:
            messages.error(request, "Leave type name is required.")
        elif LeaveType.objects.filter(name__iexact=name).exists():
            messages.error(request, f"A leave type named '{name}' already exists.")
        else:
            LeaveType.objects.create(
                name=name,
                is_deductible=is_deductible,
                requires_document=requires_document,
                color=color,
                is_active=is_active,
            )
            messages.success(request, f"Leave type '{name}' created.")
            return redirect('leaves:leave_type_list')
    _colors = [
        ('primary','Primary'),('secondary','Secondary'),('success','Success'),
        ('danger','Danger'),('warning','Warning'),('info','Info'),('dark','Dark'),
    ]
    return render(request, 'leaves/leave_type_form.html', {'action': 'Create', 'lt': None, 'colors': _colors})


@login_required
def leave_type_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    lt = get_object_or_404(LeaveType, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_deductible = request.POST.get('is_deductible') == '1'
        requires_document = request.POST.get('requires_document') == '1'
        color = request.POST.get('color', 'primary').strip()
        is_active = request.POST.get('is_active') == '1'
        if not name:
            messages.error(request, "Leave type name is required.")
        elif LeaveType.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            messages.error(request, f"A leave type named '{name}' already exists.")
        else:
            lt.name = name
            lt.is_deductible = is_deductible
            lt.requires_document = requires_document
            lt.color = color
            lt.is_active = is_active
            lt.save()
            messages.success(request, f"Leave type '{name}' updated.")
            return redirect('leaves:leave_type_list')
    _colors = [
        ('primary','Primary'),('secondary','Secondary'),('success','Success'),
        ('danger','Danger'),('warning','Warning'),('info','Info'),('dark','Dark'),
    ]
    return render(request, 'leaves/leave_type_form.html', {'action': 'Edit', 'lt': lt, 'colors': _colors})


@login_required
def leave_type_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    lt = get_object_or_404(LeaveType, pk=pk)
    if request.method == 'POST':
        name = lt.name
        try:
            lt.delete()
            messages.success(request, f"Leave type '{name}' deleted.")
        except Exception:
            messages.error(request, f"Cannot delete '{name}' — it is referenced by existing leave requests.")
    return redirect('leaves:leave_type_list')


@login_required
def restore_default_leave_types(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if request.method == 'POST':
        seed_default_leave_types()
        messages.success(request, "Default leave types restored (existing ones were not changed).")
    return redirect('leaves:leave_type_list')


@login_required
def backfill_signatures(request):
    """
    HR/superuser: copy each employee's current signature_b64 to any historical
    leave requests where the snapshot field is still empty.
    This repairs existing leaves after the b64 signature system was introduced.
    """
    employee = get_employee(request)
    if not employee or not (employee.is_hr() or request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        updated = 0
        for leave in LeaveRequest.objects.select_related(
            'employee', 'unit_head_action_by', 'manager_action_by',
            'hr_action_by', 'director_action_by'
        ):
            changed = False
            if not leave.employee_sig_b64 and leave.employee and leave.employee.signature_b64:
                leave.employee_sig_b64 = leave.employee.signature_b64
                changed = True
            if not leave.unit_head_sig_b64 and leave.unit_head_action_by and leave.unit_head_action_by.signature_b64:
                leave.unit_head_sig_b64 = leave.unit_head_action_by.signature_b64
                changed = True
            if not leave.manager_sig_b64 and leave.manager_action_by and leave.manager_action_by.signature_b64:
                leave.manager_sig_b64 = leave.manager_action_by.signature_b64
                changed = True
            if not leave.hr_sig_b64 and leave.hr_action_by and leave.hr_action_by.signature_b64:
                leave.hr_sig_b64 = leave.hr_action_by.signature_b64
                changed = True
            if not leave.director_sig_b64 and leave.director_action_by and leave.director_action_by.signature_b64:
                leave.director_sig_b64 = leave.director_action_by.signature_b64
                changed = True
            if changed:
                leave.save(update_fields=[
                    'employee_sig_b64', 'unit_head_sig_b64', 'manager_sig_b64',
                    'hr_sig_b64', 'director_sig_b64'
                ])
                updated += 1
        messages.success(request, f"Signatures synced to {updated} leave record(s).")
        return redirect('leaves:all_leaves')

    total = LeaveRequest.objects.count()
    missing = LeaveRequest.objects.filter(
        employee_sig_b64='', manager_sig_b64='', hr_sig_b64='', director_sig_b64=''
    ).count()
    return render(request, 'leaves/backfill_signatures.html', {
        'total': total,
        'missing': missing,
    })


@login_required
def set_leave_entitlement(request):
    """
    Superuser/HR: set a custom annual leave entitlement for a specific employee + year.
    Accessed via POST from the Leave Tracker modal.
    """
    employee = get_employee(request)
    if not (request.user.is_superuser or (employee and employee.is_hr())):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        emp_pk = request.POST.get('employee_id')
        year   = request.POST.get('year')
        days   = request.POST.get('total_entitlement')

        try:
            emp_pk = int(emp_pk)
            year   = int(year)
            days   = int(days)
            if days < 0 or days > 365:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Invalid entitlement value.")
            return redirect('dashboard:tracker')

        target = get_object_or_404(Employee, pk=emp_pk)
        balance, _ = LeaveBalance.objects.get_or_create(
            employee=target, year=year,
            defaults={'total_entitlement': days}
        )
        if balance.total_entitlement != days:
            balance.total_entitlement = days
            balance.save(update_fields=['total_entitlement'])
        messages.success(
            request,
            f"Leave entitlement for {target.get_full_name()} ({year}) set to {days} days."
        )

    return redirect(request.POST.get('next') or 'dashboard:tracker')
