from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import date

from accounts.models import Employee
from .models import DisciplineRecord


@login_required
def my_discipline_notices(request):
    """Employee's personal discipline record — visible only to the employee themselves."""
    emp = get_employee(request)
    if not emp:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    notices = DisciplineRecord.objects.filter(employee=emp).select_related(
        'issued_by'
    ).order_by('-date_issued')

    return render(request, 'discipline/my_notices.html', {
        'notices': notices,
        'employee': emp,
    })


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


def can_issue_discipline(emp, is_super):
    """HR, Admin Director, and Superuser can issue all types. Manager can issue limited types."""
    if is_super:
        return True
    if emp is None:
        return False
    return emp.is_hr() or emp.is_director() or emp.is_manager()


def is_hr_or_above(emp, is_super):
    if is_super:
        return True
    if emp is None:
        return False
    return emp.is_hr() or emp.is_director()


# Types a manager is allowed to issue
MANAGER_ALLOWED_TYPES = ['verbal_warning', 'written_caution']


@login_required
def issue_discipline(request):
    emp = get_employee(request)
    is_super = request.user.is_superuser

    if not can_issue_discipline(emp, is_super):
        messages.error(request, "You do not have permission to issue discipline notices.")
        return redirect('dashboard:home')

    is_manager_only = (emp and emp.is_manager() and not emp.is_hr() and not emp.is_director() and not is_super)

    # Determine which employees this issuer can see
    if is_super or (emp and (emp.is_hr() or emp.is_director())):
        employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    elif emp and emp.is_manager():
        employees = emp.subordinates.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    else:
        employees = Employee.objects.none()

    # Action types available to this issuer
    all_types = DisciplineRecord.ACTION_CHOICES
    if is_manager_only:
        available_types = [(k, v) for k, v in all_types if k in MANAGER_ALLOWED_TYPES]
    else:
        available_types = all_types

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        action_type = request.POST.get('action_type')
        reason = request.POST.get('reason', '').strip()
        notes = request.POST.get('notes', '').strip()
        suspension_start = request.POST.get('suspension_start') or None
        document = request.FILES.get('document')

        # Validate
        errors = []
        if not employee_id:
            errors.append("Please select an employee.")
        if not action_type:
            errors.append("Please select a discipline type.")
        if not reason:
            errors.append("Reason is required.")
        if is_manager_only and action_type not in MANAGER_ALLOWED_TYPES:
            errors.append("You are not authorised to issue this type of discipline notice.")
        if action_type == 'suspension' and not suspension_start:
            errors.append("Please provide the suspension start date.")

        if errors:
            for e in errors:
                messages.error(request, e)
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
            )
            if action_type == 'suspension' and suspension_start:
                record.suspension_start = suspension_start
            if document:
                record.document = document

            record.save()

            # Notify the employee via the main notification system
            from notifications.utils import notify
            issuer_name = request.user.get_full_name() or request.user.username
            notify(
                target_employee.user,
                title=f'Discipline Notice: {record.get_action_type_display()}',
                message=(
                    f"A {record.get_action_type_display()} has been issued to you by {issuer_name}. "
                    f"Reason: {reason}. "
                    f"Please review the notice and contact HR if you have any questions."
                ),
                notification_type='discipline',
                url=f'/discipline/{record.pk}/',
            )

            messages.success(
                request,
                f"{record.get_action_type_display()} issued to {target_employee.get_full_name()} successfully."
            )

            # Notify HR/Admin for dismissal
            if action_type == 'dismissal':
                messages.warning(
                    request,
                    f"DISMISSAL issued for {target_employee.get_full_name()}. "
                    f"HR and Admin must manually deactivate this employee's account."
                )

            return redirect('discipline:detail', pk=record.pk)

    from accounts.models import Department
    departments = Department.objects.all().order_by('name')

    return render(request, 'discipline/issue_form.html', {
        'employees': employees,
        'available_types': available_types,
        'is_manager_only': is_manager_only,
        'departments': departments,
    })


@login_required
def discipline_list(request):
    emp = get_employee(request)
    is_super = request.user.is_superuser

    # Filter records by role
    if is_super or (emp and (emp.is_hr() or emp.is_director())):
        records = DisciplineRecord.objects.select_related(
            'employee__user', 'employee__department', 'issued_by'
        ).all()
    elif emp and emp.is_manager():
        records = DisciplineRecord.objects.filter(
            employee__supervisor=emp
        ).select_related('employee__user', 'employee__department', 'issued_by')
    elif emp:
        records = DisciplineRecord.objects.filter(
            employee=emp
        ).select_related('employee__user', 'issued_by')
    else:
        records = DisciplineRecord.objects.none()

    # Filters
    type_filter = request.GET.get('type', '')
    if type_filter:
        records = records.filter(action_type=type_filter)

    dept_filter = request.GET.get('dept', '')
    if dept_filter and (is_super or (emp and (emp.is_hr() or emp.is_director()))):
        records = records.filter(employee__department_id=dept_filter)

    from accounts.models import Department
    departments = Department.objects.all()

    # Dismissal alert (HR/Admin/Superuser only)
    dismissal_alert = []
    if is_super or (emp and (emp.is_hr() or emp.is_director())):
        dismissal_alert = DisciplineRecord.objects.filter(
            action_type='dismissal'
        ).select_related('employee__user').order_by('-date_issued')[:10]

    return render(request, 'discipline/list.html', {
        'records': records,
        'type_filter': type_filter,
        'dept_filter': dept_filter,
        'departments': departments,
        'action_types': DisciplineRecord.ACTION_CHOICES,
        'dismissal_alert': dismissal_alert,
        'is_privileged': is_super or (emp and (emp.is_hr() or emp.is_director())),
    })


@login_required
def discipline_detail(request, pk):
    emp = get_employee(request)
    is_super = request.user.is_superuser

    record = get_object_or_404(
        DisciplineRecord.objects.select_related('employee__user', 'employee__department', 'issued_by'),
        pk=pk
    )

    # Access control
    if is_super or (emp and (emp.is_hr() or emp.is_director())):
        pass  # full access
    elif emp and emp.is_manager():
        if record.employee.supervisor != emp:
            messages.error(request, "Access denied.")
            return redirect('discipline:list')
    elif emp:
        if record.employee != emp:
            messages.error(request, "Access denied.")
            return redirect('dashboard:home')
    else:
        return redirect('dashboard:home')

    return render(request, 'discipline/detail.html', {'record': record})


@login_required
def discipline_stats(request):
    """Standalone stats page — HR, Admin Director, Superuser only."""
    emp = get_employee(request)
    is_super = request.user.is_superuser

    if not is_hr_or_above(emp, is_super):
        return redirect('dashboard:home')

    today = date.today()
    all_records = DisciplineRecord.objects.select_related('employee__user', 'employee__department')

    type_filter = request.GET.get('type', '')
    if type_filter:
        filtered = all_records.filter(action_type=type_filter)
    else:
        filtered = all_records

    warned_employees = Employee.objects.filter(
        discipline_records__action_type__in=['verbal_warning', 'written_caution', 'final_warning']
    ).distinct().select_related('user', 'department')

    suspended_employees = Employee.objects.filter(
        discipline_records__action_type='suspension',
        discipline_records__suspension_end__gte=today,
    ).distinct().select_related('user', 'department')

    dismissed_employees = Employee.objects.filter(
        discipline_records__action_type='dismissal'
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
