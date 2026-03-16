from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from datetime import date
from .models import LeaveRequest, LeaveBalance, LeaveType
from .forms import LeaveRequestForm, ApprovalForm
from accounts.models import Employee
from notifications.utils import notify


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


@login_required
def submit_leave(request):
    employee = get_employee(request)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    # Get or create balance
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': 18}
    )

    form = LeaveRequestForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = employee

        # Validate balance (only for deductible leave types)
        if leave.leave_type.is_deductible and leave.total_days > balance.remaining_days:
            messages.error(request, f"Insufficient leave balance. You have {balance.remaining_days} days remaining.")
        else:
            # Check for overlapping requests
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['pending', 'manager_approved', 'hr_approved', 'approved'],
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date,
            )
            if overlapping.exists():
                messages.error(request, "You already have a leave request for overlapping dates.")
            else:
                leave.save()
                messages.success(request, f"Leave request submitted successfully for {leave.total_days} day(s). Awaiting manager approval.")
                # Notify the employee's supervisor
                if employee.supervisor:
                    notify(
                        employee.supervisor.user,
                        f'New Leave Request — {employee.get_full_name()}',
                        f'{employee.get_full_name()} has submitted a {leave.leave_type} request '
                        f'for {leave.total_days} day(s) ({leave.start_date} → {leave.end_date}). Awaiting your approval.',
                        notification_type='leave_submitted',
                        url=reverse('leaves:manager_action', kwargs={'pk': leave.pk}),
                    )
                return redirect('leaves:my_requests')

    import json
    leave_types = LeaveType.objects.filter(is_active=True).values('id', 'is_deductible')
    deductible_map = json.dumps({str(lt['id']): lt['is_deductible'] for lt in leave_types})

    return render(request, 'leaves/request_form.html', {
        'form': form,
        'balance': balance,
        'deductible_map': deductible_map,
    })


@login_required
def my_requests(request):
    employee = get_employee(request)
    if not employee:
        return redirect('dashboard:home')

    requests = LeaveRequest.objects.filter(employee=employee).select_related('leave_type', 'manager_action_by__user', 'hr_action_by__user')
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': 18}
    )

    return render(request, 'leaves/my_requests.html', {
        'leave_requests': requests,
        'balance': balance,
    })


@login_required
def cancel_request(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=employee)
    if leave.can_cancel():
        leave.status = LeaveRequest.STATUS_CANCELLED
        leave.save()
        messages.success(request, "Leave request cancelled.")
    else:
        messages.error(request, "This request cannot be cancelled.")
    return redirect('leaves:my_requests')


@login_required
def manager_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_manager():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    if request.user.is_superuser:
        pending = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_PENDING
        ).select_related('employee__user', 'employee__department', 'leave_type')
    else:
        pending = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_PENDING,
            employee__supervisor=employee
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

    # If already actioned, show a clear message instead of crashing
    if leave.status != LeaveRequest.STATUS_PENDING:
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
            return redirect('leaves:manager_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Manager Review',
        'action_type': 'manager',
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
            return redirect('leaves:hr_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'HR Final Review',
        'action_type': 'hr',
    })


@login_required
def director_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_director():
        messages.error(request, "Access denied. Administration Director only.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_HR_APPROVED
    ).select_related('employee__user', 'employee__department', 'leave_type', 'manager_action_by__user', 'hr_action_by__user')

    return render(request, 'leaves/director_approvals.html', {
        'pending_requests': pending,
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
                leave.status = LeaveRequest.STATUS_APPROVED
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
            return redirect('leaves:director_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Administration Director — Final Review',
        'action_type': 'director',
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
def print_leave(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk)

    if leave.status != LeaveRequest.STATUS_APPROVED:
        messages.error(request, "Only fully approved leave requests can be printed.")
        return redirect('leaves:detail', pk=pk)

    can_view = (
        leave.employee == employee or
        request.user.is_superuser or
        (employee and employee.is_hr()) or
        (employee and employee.is_director())
    )
    if not can_view:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    return render(request, 'leaves/leave_print.html', {'leave': leave})


@login_required
def all_leaves_hr(request):
    """HR/Director view of all leave requests"""
    employee = get_employee(request)
    if not employee or (not employee.is_hr() and not employee.is_director() and not employee.is_ceo()):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    status_filter = request.GET.get('status', '')
    dept_filter = request.GET.get('dept', '')
    year_filter = request.GET.get('year', str(date.today().year))

    qs = LeaveRequest.objects.select_related(
        'employee__user', 'employee__department', 'leave_type'
    ).filter(start_date__year=year_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)
    if dept_filter:
        qs = qs.filter(employee__department_id=dept_filter)

    from accounts.models import Department
    departments = Department.objects.all()

    return render(request, 'leaves/all_leaves.html', {
        'leave_requests': qs,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
        'year_filter': year_filter,
        'departments': departments,
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
        defaults={'total_entitlement': 18}
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
    """Superuser-only: correct total_days, status, and add a note on any leave request."""
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

    valid_statuses = dict(LeaveRequest.STATUS_CHOICES).keys()
    update_fields = {'total_days': new_days}

    if new_status and new_status in valid_statuses:
        update_fields['status'] = new_status

    if admin_note:
        existing = leave.director_remarks or ''
        separator = '\n' if existing else ''
        update_fields['director_remarks'] = f"{existing}{separator}[Admin correction] {admin_note}"

    # Use queryset .update() to bypass save() so total_days is NOT recalculated from dates
    LeaveRequest.objects.filter(pk=pk).update(**update_fields)

    messages.success(
        request,
        f"Leave #{pk} corrected: {new_days} days"
        + (f", status → {new_status}" if 'status' in update_fields else "")
        + "."
    )
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
    if not request.user.is_superuser:
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
