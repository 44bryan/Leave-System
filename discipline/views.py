from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q, F
from django.urls import reverse
from django.urls import reverse
from datetime import date

from accounts.models import Employee
from .models import DisciplineRecord


def _notify_discipline_hierarchy(record, issuer_user, issuer_name, short_reason):
    """Notify the full management hierarchy when a discipline notice is formally issued."""
    from notifications.utils import notify
    action_label = record.get_action_type_display()
    detail_url   = reverse('discipline:detail', kwargs={'pk': record.pk})
    target       = record.employee
    notified     = {issuer_user.pk}  # never re-notify the issuer

    def _send(user, title, message):
        if user and user.pk not in notified:
            notified.add(user.pk)
            notify(user, title=title, message=message, notification_type='discipline', url=detail_url)

    # 1. Employee
    _send(target.user,
          f'Discipline Notice: {action_label}',
          f'A {action_label} has been issued to you by {issuer_name}. Reason: {short_reason}. Contact HR if you have questions.')

    # 2. Supervisor / Line Manager
    if target.supervisor:
        _send(target.supervisor.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} has issued a {action_label} to your subordinate {target.get_full_name()}. Reason: {short_reason}.')

    # 3. Unit Head
    if target.unit_head:
        _send(target.unit_head.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} has issued a {action_label} to {target.get_full_name()} in your unit. Reason: {short_reason}.')

    # 4. Nurse Superintendent
    if target.nurse_superintendent:
        _send(target.nurse_superintendent.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} has issued a {action_label} to {target.get_full_name()}. Reason: {short_reason}.')

    # 5. HR staff
    for hr in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
        _send(hr.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} issued a {action_label} to {target.get_full_name()}. Reason: {short_reason}.')

    # 6. Admin Director(s)
    for ad in Employee.objects.filter(role='admin_director', is_active=True).select_related('user'):
        _send(ad.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} issued a {action_label} to {target.get_full_name()}. Reason: {short_reason}.')

    # 7. CEO
    for ceo in Employee.objects.filter(role='ceo', is_active=True).select_related('user'):
        _send(ceo.user,
              f'Discipline Issued — {target.get_full_name()}',
              f'{issuer_name} issued a {action_label} to {target.get_full_name()}. Reason: {short_reason}.')


def _process_pending_dismissals():
    """Deactivate Django User accounts of dismissed employees past their 14-day window."""
    try:
        from datetime import timedelta
        cutoff = date.today() - timedelta(days=14)
        from accounts.models import Employee as _Emp
        pending = _Emp.objects.filter(
            dismissal_date__lte=cutoff,
            user__is_active=True,
        ).select_related('user')
        for emp in pending:
            emp.user.is_active = False
            emp.user.save(update_fields=['is_active'])
    except Exception:
        pass


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


# ── Permission helpers ──────────────────────────────────────────────────────

def can_issue_formally(emp, is_super):
    """HR, Admin Director, CEO, and Superuser can formally issue discipline notices."""
    if is_super:
        return True
    if emp is None:
        return False
    return emp.is_hr() or emp.role == 'admin_director' or emp.is_ceo()


def is_proposal_only_role(emp):
    """Manager, Unit Head, Finance Director, and Nurse Superintendent can only submit verbal-warning proposals to HR."""
    if emp is None:
        return False
    return emp.role in ('manager', 'unit_head', 'finance_director', 'nurse_superintendent')


def can_access_issue_form(emp, is_super):
    """Any role that may use the issue/propose form."""
    if is_super:
        return True
    if emp is None:
        return False
    return (
        emp.is_hr()
        or emp.role == 'admin_director'
        or emp.is_ceo()
        or is_proposal_only_role(emp)
    )


def can_view_discipline(emp, is_super):
    """HR, Admin Director, CEO, Manager, Unit Head, Finance Director, and Superuser can view records."""
    if is_super:
        return True
    if emp is None:
        return False
    return (
        emp.is_hr()
        or emp.role == 'admin_director'
        or emp.is_ceo()
        or is_proposal_only_role(emp)
    )


def is_hr_or_above(emp, is_super):
    if is_super:
        return True
    if emp is None:
        return False
    return emp.is_hr() or emp.role == 'admin_director'


# ── Views ───────────────────────────────────────────────────────────────────

@login_required
def my_discipline_notices(request):
    """Employee's personal discipline record — shows only formally-issued (non-proposal) records."""
    emp = get_employee(request)
    if not emp:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    notices = DisciplineRecord.objects.filter(
        employee=emp, is_proposal=False
    ).select_related('issued_by').order_by('-date_issued')

    return render(request, 'discipline/my_notices.html', {
        'notices': notices,
        'employee': emp,
    })


@login_required
def issue_discipline(request):
    emp = get_employee(request)
    is_super = request.user.is_superuser

    if not can_access_issue_form(emp, is_super):
        messages.error(request, "You do not have permission to issue or propose discipline notices.")
        return redirect('dashboard:home')

    # Classify issuer
    _formal = can_issue_formally(emp, is_super)
    _proposal_only = is_proposal_only_role(emp)
    # CEO and Admin Director can choose formal or proposal
    _can_choose = emp and emp.role in ('admin_director', 'ceo') and not is_super

    # Determine which employees this issuer can see
    if is_super or (emp and (emp.is_hr() or emp.role == 'admin_director' or emp.is_ceo())):
        employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    elif emp and emp.is_manager():
        employees = emp.subordinates.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    elif emp and emp.role == 'unit_head':
        employees = emp.unit_head_of.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    elif emp and emp.role == 'finance_director':
        employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    else:
        employees = Employee.objects.none()

    # Pre-fill support (from Step 4 "Issue Final Discipline" on detail page)
    prefill_employee = request.GET.get('prefill_employee', '')
    prefill_type = request.GET.get('prefill_type', '')
    # These are populated on POST error so the form restores its previous state
    posted_action_type = ''
    posted_suspension_start = ''
    posted_suspension_end = ''
    posted_reason = ''

    # Available action types
    all_types = DisciplineRecord.ACTION_CHOICES
    if _proposal_only:
        available_types = [(k, v) for k, v in all_types if k == 'verbal_warning']
    else:
        available_types = all_types

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        action_type = request.POST.get('action_type')
        reason = request.POST.get('reason', '').strip()
        notes = request.POST.get('notes', '').strip()
        suspension_start = request.POST.get('suspension_start') or None
        suspension_end = request.POST.get('suspension_end') or None
        document = request.FILES.get('document')
        proposal_note = request.POST.get('proposal_note', '').strip()
        submit_as_proposal = request.POST.get('submit_as_proposal') == '1'

        # Determine if this submission becomes a proposal
        if _proposal_only:
            is_prop = True
        elif _can_choose:
            is_prop = submit_as_proposal
        else:
            is_prop = False  # HR / superuser always formal

        # Validate
        errors = []
        if not employee_id:
            errors.append("Please select an employee.")
        if not action_type:
            errors.append("Please select a discipline type.")
        if not reason:
            errors.append("Reason is required.")
        if _proposal_only and action_type != 'verbal_warning':
            errors.append("You may only propose a Verbal Warning. Other discipline types must go through HR.")
        if action_type == 'suspension' and not is_prop:
            if not suspension_start:
                errors.append("Please provide the suspension start date.")
            if not suspension_end:
                errors.append("Please provide the suspension end date.")

        if errors:
            for e in errors:
                messages.error(request, e)
            # Restore posted values so the form doesn't reset on error
            posted_action_type = action_type or ''
            posted_suspension_start = suspension_start or ''
            posted_suspension_end = suspension_end or ''
            posted_reason = reason
        else:
            try:
                target_employee = employees.get(pk=employee_id)
            except Employee.DoesNotExist:
                messages.error(request, "Invalid employee selected.")
                return redirect('discipline:issue')

            record = DisciplineRecord(
                employee=target_employee,
                action_type=action_type,
                issued_by=request.user,
                reason=reason,
                notes=notes,
                is_proposal=is_prop,
                proposal_note=proposal_note,
            )
            if action_type == 'suspension' and suspension_start:
                record.suspension_start = suspension_start
            if action_type == 'suspension' and suspension_end:
                record.suspension_end = suspension_end
            if document:
                record.document = document
            # Directly issued by HR/CEO/Director — mark review chain complete immediately
            if not is_prop:
                record.hr_proposed_sanction = 'no_further_action'
                record.director_proposed_sanction = 'no_further_action'

            record.save()

            from notifications.utils import notify
            issuer_name = request.user.get_full_name() or request.user.username

            if is_prop:
                # Notify HR staff of the proposal
                hr_staff = Employee.objects.filter(role='hr', is_active=True).select_related('user')
                for hr_emp in hr_staff:
                    notify(
                        hr_emp.user,
                        title=f'Discipline Proposal: {record.get_action_type_display()} — {target_employee.get_full_name()}',
                        message=(
                            f"{issuer_name} has submitted a {record.get_action_type_display()} proposal "
                            f"for {target_employee.get_full_name()}. "
                            f"Please review and formally execute if appropriate."
                        ),
                        notification_type='discipline',
                        url=reverse('discipline:detail', kwargs={'pk': record.pk}),
                    )
                from dashboard.models import AuditLog
                AuditLog.log(
                    request, AuditLog.ACTION_DISCIPLINE,
                    f'Discipline proposal ({record.get_action_type_display()}) submitted for '
                    f'{target_employee.get_full_name()}. Forwarded to HR for execution.',
                    target_user=target_employee.user,
                )
                messages.success(
                    request,
                    f"Proposal submitted. HR has been notified to review and formally execute the "
                    f"{record.get_action_type_display()} for {target_employee.get_full_name()}."
                )
            else:
                # Formal notice — notify full hierarchy
                _notify_discipline_hierarchy(record, request.user, issuer_name, reason[:120])

                if action_type == 'dismissal':
                    from datetime import timedelta
                    target_employee.dismissal_date = date.today()
                    target_employee.save(update_fields=['dismissal_date'])
                    messages.warning(
                        request,
                        f"DISMISSAL issued for {target_employee.get_full_name()}. "
                        f"HR and Admin must manually deactivate this employee's account."
                    )

                from dashboard.models import AuditLog
                AuditLog.log(
                    request, AuditLog.ACTION_DISCIPLINE,
                    f'{record.get_action_type_display()} formally issued to '
                    f'{target_employee.get_full_name()}. Reason: {reason[:100]}.',
                    target_user=target_employee.user,
                )
                messages.success(
                    request,
                    f"{record.get_action_type_display()} issued to {target_employee.get_full_name()} successfully."
                )

            return redirect('discipline:detail', pk=record.pk)

    from accounts.models import Department
    departments = Department.objects.all().order_by('name')

    return render(request, 'discipline/issue_form.html', {
        'employees': employees,
        'available_types': available_types,
        'is_proposal_only': _proposal_only,
        'can_choose': _can_choose,
        'is_formal_only': _formal and not _can_choose,
        'departments': departments,
        'prefill_employee': prefill_employee,
        'prefill_type': prefill_type or posted_action_type,
        'posted_suspension_start': posted_suspension_start,
        'posted_suspension_end': posted_suspension_end,
        'posted_reason': posted_reason,
    })


@login_required
def execute_proposal(request, pk):
    """HR formally executes a discipline proposal — makes it a real notice visible to the employee."""
    emp = get_employee(request)
    is_super = request.user.is_superuser

    if not (is_super or (emp and emp.is_hr())):
        messages.error(request, "Only HR can formally execute discipline proposals.")
        return redirect('discipline:list')

    record = get_object_or_404(DisciplineRecord, pk=pk, is_proposal=True)

    if request.method == 'POST':
        suspension_start = request.POST.get('suspension_start') or None
        suspension_end = request.POST.get('suspension_end') or None

        if record.action_type == 'suspension' and not record.suspension_start and not suspension_start:
            messages.error(request, "Please provide the suspension start date to execute this notice.")
            return redirect('discipline:detail', pk=pk)

        if suspension_start and not record.suspension_start:
            record.suspension_start = suspension_start
        if suspension_end and not record.suspension_end:
            record.suspension_end = suspension_end

        record.is_proposal = False
        record.issued_by = request.user  # HR becomes the formal issuer
        record.date_issued = date.today()
        # If HR is executing without a prior HR review step, mark HR review complete
        if not record.hr_proposed_sanction:
            record.hr_proposed_sanction = 'no_further_action'
        record.save()

        if record.action_type == 'dismissal':
            from datetime import timedelta
            record.employee.dismissal_date = date.today()
            record.employee.save(update_fields=['dismissal_date'])

        issuer_name = request.user.get_full_name() or request.user.username
        _notify_discipline_hierarchy(record, request.user, issuer_name, record.reason[:120])

        from dashboard.models import AuditLog
        AuditLog.log(
            request, AuditLog.ACTION_DISCIPLINE,
            f'Discipline proposal executed: {record.get_action_type_display()} formally issued to '
            f'{record.employee.get_full_name()} on {date.today().strftime("%d %b %Y")}.',
            target_user=record.employee.user,
        )
        messages.success(
            request,
            f"Proposal executed. {record.get_action_type_display()} formally issued to "
            f"{record.employee.get_full_name()} on {date.today().strftime('%d %b %Y')}."
        )

    return redirect('discipline:detail', pk=pk)


@login_required
def discipline_list(request):
    _process_pending_dismissals()
    emp = get_employee(request)
    is_super = request.user.is_superuser

    is_privileged = is_super or (emp and (emp.is_hr() or emp.role == 'admin_director' or emp.is_ceo()))
    is_submitter = emp and is_proposal_only_role(emp)

    if not (is_privileged or is_submitter):
        # Regular employees go to their personal notices
        return redirect('discipline:my_notices')

    # Build queryset
    if is_privileged:
        records = DisciplineRecord.objects.filter(is_proposal=False).select_related(
            'employee__user', 'employee__department', 'issued_by'
        )
        proposals = DisciplineRecord.objects.filter(is_proposal=True).select_related(
            'employee__user', 'employee__department', 'issued_by'
        )
    elif is_submitter:
        records = DisciplineRecord.objects.filter(
            issued_by=request.user, is_proposal=False
        ).select_related('employee__user', 'employee__department', 'issued_by')
        proposals = DisciplineRecord.objects.filter(
            issued_by=request.user, is_proposal=True
        ).select_related('employee__user', 'employee__department', 'issued_by')
    else:
        records = DisciplineRecord.objects.none()
        proposals = DisciplineRecord.objects.none()

    # Filters (apply to formal records only)
    type_filter = request.GET.get('type', '')
    if type_filter:
        records = records.filter(action_type=type_filter)

    dept_filter = request.GET.get('dept', '')
    if dept_filter and is_privileged:
        records = records.filter(employee__department_id=dept_filter)

    emp_filter = request.GET.get('employee', '')
    if emp_filter and is_privileged:
        records = records.filter(employee_id=emp_filter)

    name_filter = request.GET.get('name', '').strip()
    if name_filter and is_privileged:
        records = records.filter(
            Q(employee__user__first_name__icontains=name_filter) |
            Q(employee__user__last_name__icontains=name_filter)
        )

    from accounts.models import Department
    departments = Department.objects.all()

    # Dismissal alert (HR/Admin only)
    dismissal_alert = []
    if is_super or (emp and (emp.is_hr() or emp.role == 'admin_director')):
        dismissal_alert = DisciplineRecord.objects.filter(
            action_type='dismissal', is_proposal=False
        ).select_related('employee__user').order_by('-date_issued')[:10]

    all_employees = (
        Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
        if is_privileged else Employee.objects.none()
    )

    return render(request, 'discipline/list.html', {
        'records': records,
        'proposals': proposals,
        'type_filter': type_filter,
        'dept_filter': dept_filter,
        'emp_filter': emp_filter,
        'name_filter': name_filter,
        'departments': departments,
        'all_employees': all_employees,
        'action_types': DisciplineRecord.ACTION_CHOICES,
        'dismissal_alert': dismissal_alert,
        'is_privileged': is_privileged,
        'is_submitter': is_submitter,
    })


@login_required
def delete_discipline_record(request, pk):
    """Permanently delete a discipline record. Only superuser or admin_director."""
    emp = get_employee(request)
    is_super = request.user.is_superuser
    is_admin_dir = emp and emp.role == 'admin_director'

    if not (is_super or is_admin_dir):
        messages.error(request, "You do not have permission to delete discipline records.")
        return redirect('discipline:list')

    record = get_object_or_404(DisciplineRecord, pk=pk)

    if request.method == 'POST':
        employee = record.employee
        action_type = record.action_type

        if action_type == 'dismissal' and employee.dismissal_date:
            employee.dismissal_date = None
            employee.save(update_fields=['dismissal_date'])

        emp_name = employee.get_full_name()
        record_type = record.get_action_type_display()
        record.delete()

        messages.success(request, f"{record_type} record for {emp_name} has been permanently deleted.")
        return redirect('discipline:list')

    return redirect('discipline:detail', pk=pk)


@login_required
def discipline_detail(request, pk):
    emp = get_employee(request)
    is_super = request.user.is_superuser

    record = get_object_or_404(
        DisciplineRecord.objects.select_related('employee__user', 'employee__department', 'issued_by'),
        pk=pk
    )

    # Access control
    if is_super or (emp and (emp.is_hr() or emp.role == 'admin_director' or emp.is_ceo())):
        pass  # full access
    elif emp and is_proposal_only_role(emp):
        # Submitters can view: proposals they personally submitted OR their own personal notices
        if record.issued_by != request.user and record.employee != emp:
            messages.error(request, "Access denied.")
            return redirect('discipline:list')
    elif emp:
        # Regular employees see only their own formal notices
        if record.employee != emp or record.is_proposal:
            messages.error(request, "Access denied.")
            return redirect('dashboard:home')
    else:
        return redirect('dashboard:home')

    # Directly-issued records (by HR/CEO/Director) have both sanction fields set to sentinel
    is_direct_issue = (
        record.hr_proposed_sanction == 'no_further_action'
        and record.director_proposed_sanction == 'no_further_action'
        and not record.recommended_sanction
    )
    return render(request, 'discipline/detail.html', {'record': record, 'is_direct_issue': is_direct_issue})


@login_required
def propose_sanction(request, pk):
    """HR or Admin Director submits their proposed sanction on a discipline record."""
    if request.method != 'POST':
        return redirect('discipline:detail', pk=pk)

    emp = get_employee(request)
    is_super = request.user.is_superuser

    record = get_object_or_404(DisciplineRecord, pk=pk)

    role = request.POST.get('role')
    sanction = request.POST.get('proposed_sanction', '').strip()
    note = request.POST.get('proposed_note', '').strip()

    from notifications.utils import notify
    from accounts.models import Employee as _Emp

    if role == 'hr' and (is_super or (emp and emp.is_hr())):
        record.hr_proposed_sanction = sanction
        record.hr_proposed_note = note
        record.save()
        messages.success(request, "HR sanction review saved. You may now issue the formal discipline notice.")
    elif role == 'director' and (is_super or (emp and emp.role == 'admin_director')):
        record.director_proposed_sanction = sanction
        record.director_proposed_note = note
        record.save()
        messages.success(request, "Director proposed sanction saved.")
        hr_staff = _Emp.objects.filter(role='hr', is_active=True).select_related('user')
        for hr_emp in hr_staff:
            notify(
                hr_emp.user,
                title=f'Director Sanction Decision: {record.employee.get_full_name()}',
                message=(
                    f"The Administration Director has submitted their final sanction decision for {record.employee.get_full_name()}. "
                    f"Decision: {dict(record.RECOMMENDED_ACTION_CHOICES).get(record.director_proposed_sanction, record.director_proposed_sanction)}. "
                    f"Please review and take any necessary follow-up actions."
                ),
                notification_type='discipline',
                url=reverse('discipline:detail', kwargs={'pk': record.pk}),
            )
    else:
        messages.error(request, "You do not have permission to submit this proposal.")

    return redirect('discipline:detail', pk=pk)


@login_required
def discipline_stats(request):
    """Standalone stats page — HR, Admin Director, Superuser only."""
    emp = get_employee(request)
    is_super = request.user.is_superuser

    if not is_hr_or_above(emp, is_super) and not (emp and emp.is_ceo()):
        return redirect('dashboard:home')

    today = date.today()
    all_records = DisciplineRecord.objects.filter(is_proposal=False).select_related(
        'employee__user', 'employee__department'
    )

    type_filter = request.GET.get('type', '')
    if type_filter:
        filtered = all_records.filter(action_type=type_filter)
    else:
        filtered = all_records

    warned_employees = Employee.objects.filter(
        discipline_records__action_type__in=['verbal_warning', 'written_caution', 'final_warning'],
        discipline_records__is_proposal=False,
    ).distinct().select_related('user', 'department')

    suspended_employees = Employee.objects.filter(
        discipline_records__action_type='suspension',
        discipline_records__suspension_end__gte=today,
        discipline_records__is_proposal=False,
    ).distinct().select_related('user', 'department')

    dismissed_employees = Employee.objects.filter(
        discipline_records__action_type='dismissal',
        discipline_records__is_proposal=False,
    ).distinct().select_related('user', 'department')

    return render(request, 'discipline/stats.html', {
        'warned_employees': warned_employees,
        'suspended_employees': suspended_employees,
        'dismissed_employees': dismissed_employees,
        'warned_count': warned_employees.count(),
        'suspended_count': suspended_employees.count(),
        'dismissed_count': dismissed_employees.count(),
        'type_filter': type_filter,
        'action_types': DisciplineRecord.ACTION_CHOICES,
    })


@login_required
def direct_issue_discipline(request):
    """HR, Admin Director, CEO, Superuser: issue a discipline notice directly — no proposal step."""
    emp = get_employee(request)
    is_super = request.user.is_superuser

    allowed = is_super or (emp and (
        emp.is_hr() or emp.role == 'admin_director' or emp.is_ceo()
    ))
    if not allowed:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    employees = Employee.objects.filter(is_active=True).exclude(
        user=request.user
    ).select_related('user', 'department', 'supervisor', 'unit_head').order_by('user__last_name')

    posted = {}
    if request.method == 'POST':
        employee_id    = request.POST.get('employee')
        action_type    = request.POST.get('action_type', '').strip()
        reason         = request.POST.get('reason', '').strip()
        notes          = request.POST.get('notes', '').strip()
        suspension_start = request.POST.get('suspension_start') or None
        suspension_end   = request.POST.get('suspension_end') or None
        document       = request.FILES.get('document')

        posted = {
            'action_type': action_type,
            'reason': reason,
            'notes': notes,
            'suspension_start': suspension_start or '',
            'suspension_end': suspension_end or '',
        }

        errors = []
        if not employee_id:
            errors.append("Please select an employee.")
        if not action_type:
            errors.append("Please select a discipline type.")
        if not reason:
            errors.append("Reason is required.")
        if action_type == 'suspension':
            if not suspension_start:
                errors.append("Suspension start date is required.")
            if not suspension_end:
                errors.append("Suspension end date is required.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                target = employees.get(pk=employee_id)
            except Employee.DoesNotExist:
                messages.error(request, "Invalid employee selected.")
                return redirect('discipline:direct_issue')

            record = DisciplineRecord(
                employee=target,
                action_type=action_type,
                issued_by=request.user,
                reason=reason,
                notes=notes,
                is_proposal=False,
                hr_proposed_sanction='no_further_action',
                director_proposed_sanction='no_further_action',
            )
            if action_type == 'suspension' and suspension_start:
                record.suspension_start = suspension_start
            if action_type == 'suspension' and suspension_end:
                record.suspension_end = suspension_end
            if document:
                record.document = document
            record.save()

            if action_type == 'dismissal':
                target.dismissal_date = date.today()
                target.save(update_fields=['dismissal_date'])

            issuer_name = request.user.get_full_name() or request.user.username
            _notify_discipline_hierarchy(record, request.user, issuer_name, reason[:120])

            from dashboard.models import AuditLog
            AuditLog.log(
                request, AuditLog.ACTION_DISCIPLINE,
                f'{action_label} directly issued to {target.get_full_name()}. Reason: {reason[:100]}.',
                target_user=target.user,
            )

            messages.success(
                request,
                f'{action_label} successfully issued to {target.get_full_name()}.'
            )
            return redirect('discipline:detail', pk=record.pk)

    return render(request, 'discipline/direct_issue.html', {
        'employees': employees,
        'action_choices': DisciplineRecord.ACTION_CHOICES,
        'posted': posted,
    })
