from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q
from datetime import date, timedelta
from accounts.models import Employee, Department
from leaves.models import LeaveRequest, LeaveBalance, LeaveType


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


def _build_contract_analytics(today, year):
    """Return contract analytics context dict — shared by admin, HR, and director dashboards."""
    from contracts.models import Contract as _Contract
    from collections import defaultdict as _dd

    _all_active = list(
        _Contract.objects.filter(status='active')
        .select_related('employee', 'employee__user', 'employee__department')
    )
    _active_cdd    = [c for c in _all_active if c.contract_type == 'CDD']
    _active_cdi    = [c for c in _all_active if c.contract_type == 'CDI']
    _active_intern = [c for c in _all_active if c.contract_type == 'INTERN']
    _active_wacs   = [c for c in _all_active if c.contract_type == 'WACS']

    contracts_expired_active = sorted(
        [c for c in _active_cdd if c.is_expired], key=lambda c: c.end_date
    )
    contracts_expiring_30 = sorted(
        [c for c in _active_cdd if c.days_remaining is not None and 0 < c.days_remaining <= 30],
        key=lambda c: c.days_remaining
    )
    contracts_expiring_60 = sorted(
        [c for c in _active_cdd if c.days_remaining is not None and 30 < c.days_remaining <= 60],
        key=lambda c: c.days_remaining
    )
    contracts_expiring_90 = sorted(
        [c for c in _active_cdd if c.days_remaining is not None and 60 < c.days_remaining <= 90],
        key=lambda c: c.days_remaining
    )

    _all_emp = list(Employee.objects.filter(is_active=True).select_related('user', 'department'))
    contracts_near_retirement = sorted(
        [e for e in _all_emp if e.is_near_retirement()],
        key=lambda e: (e.years_to_retirement() or 99)
    )

    _ct_total = len(_all_active)

    # Staff category distribution — numeric system (1–12 with optional letter suffixes)
    import re as _re

    def _cat_num(cat):
        m = _re.match(r'^(\d+)', cat or '')
        return int(m.group(1)) if m else 0

    _cat_qs = (
        Employee.objects.filter(is_active=True, staff_category__gt='')
        .values('staff_category')
        .annotate(count=Count('id'))
    )
    staff_category_detail = sorted(
        [{'cat': row['staff_category'], 'count': row['count'],
          'color': '#0284c7' if _cat_num(row['staff_category']) <= 6 else '#7c3aed'}
         for row in _cat_qs],
        key=lambda x: (_cat_num(x['cat']), x['cat'])
    )
    _total_categorised = sum(x['count'] for x in staff_category_detail)

    def _pct(n):
        return round(n / _total_categorised * 100) if _total_categorised else 0

    _lower = sum(x['count'] for x in staff_category_detail if 1 <= _cat_num(x['cat']) <= 6)
    _upper = sum(x['count'] for x in staff_category_detail if 7 <= _cat_num(x['cat']) <= 12)
    staff_category_groups = [
        {'label': 'Category 1–6', 'count': _lower, 'pct': _pct(_lower), 'color': '#0284c7'},
        {'label': 'Category 7–12', 'count': _upper, 'pct': _pct(_upper), 'color': '#7c3aed'},
    ]
    _dept_map = _dd(lambda: _dd(int))
    for c in _all_active:
        dn = str(c.employee.department) if c.employee.department else 'No Department'
        _dept_map[dn][c.contract_type] += 1
        _dept_map[dn]['total'] += 1
    contract_dept_breakdown = sorted(
        [{'dept': k, 'CDI': v.get('CDI', 0), 'CDD': v.get('CDD', 0),
          'INTERN': v.get('INTERN', 0), 'WACS': v.get('WACS', 0),
          'total': v.get('total', 0)} for k, v in _dept_map.items()],
        key=lambda x: -x['total']
    )
    contract_long_service = sorted(_active_cdi, key=lambda c: -c.years_of_service)[:8]
    contract_recent_activity = list(
        _Contract.objects.select_related('employee', 'employee__user', 'created_by').order_by('-created_at')[:10]
    )
    contract_issued_year = _Contract.objects.filter(created_at__year=year).count()
    contract_renewed_year = _Contract.objects.filter(status='renewed', updated_at__year=year).count()
    contract_terminated_year = _Contract.objects.filter(status='terminated', updated_at__year=year).count()

    return {
        'contracts_expired_active': contracts_expired_active,
        'contracts_expiring_30': contracts_expiring_30,
        'contracts_expiring_60': contracts_expiring_60,
        'contracts_expiring_90': contracts_expiring_90,
        'contracts_near_retirement': contracts_near_retirement,
        'contract_total_active': _ct_total,
        'contract_total_cdi': len(_active_cdi),
        'contract_total_cdd': len(_active_cdd),
        'contract_total_intern': len(_active_intern),
        'contract_total_wacs': len(_active_wacs),
        'staff_category_groups': staff_category_groups,
        'staff_category_detail': staff_category_detail,
        'contract_dept_breakdown': contract_dept_breakdown,
        'contract_long_service': contract_long_service,
        'contract_recent_activity': contract_recent_activity,
        'contract_issued_year': contract_issued_year,
        'contract_renewed_year': contract_renewed_year,
        'contract_terminated_year': contract_terminated_year,
    }


def admin_dashboard(request):
    from django.contrib.auth.models import User
    from django.contrib.admin.models import LogEntry
    from discipline.models import DisciplineRecord
    from datetime import datetime
    today = date.today()
    year = today.year

    # ── Own employee self-service data (admin may also be an employee) ──
    admin_employee = get_employee(request)
    my_balance = None
    my_recent_requests = []
    my_pending_count = 0
    my_on_leave = None
    my_active_suspension = None
    my_is_birthday = False
    if admin_employee:
        my_balance, _ = LeaveBalance.objects.get_or_create(
            employee=admin_employee, year=today.year,
            defaults={'total_entitlement': 18}
        )
        my_recent_requests = admin_employee.leave_requests.all()[:5]
        my_pending_count = admin_employee.leave_requests.filter(
            status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved']
        ).count()
        my_on_leave = admin_employee.leave_requests.filter(
            status='approved', start_date__lte=today, end_date__gte=today
        ).first()
        my_active_suspension = DisciplineRecord.objects.filter(
            employee=admin_employee,
            action_type='suspension',
            suspension_start__lte=today,
            suspension_end__gte=today,
        ).first()
        my_is_birthday = (
            admin_employee.date_of_birth is not None
            and admin_employee.date_of_birth.month == today.month
            and admin_employee.date_of_birth.day == today.day
        )

    # ── System counts ──
    total_employees = Employee.objects.filter(is_active=True).count()
    total_departments = Department.objects.count()
    total_users = User.objects.count()
    approved_year = LeaveRequest.objects.filter(status='approved', start_date__year=year).count()
    rejected_year = LeaveRequest.objects.filter(
        status__in=['rejected_manager', 'rejected_hr', 'rejected_director'],
        start_date__year=year
    ).count()
    pending_manager = LeaveRequest.objects.filter(status='pending').count()
    pending_hr = LeaveRequest.objects.filter(status='manager_approved').count()
    pending_director = LeaveRequest.objects.filter(status='hr_approved').count()
    pending_all = pending_manager + pending_hr + pending_director

    # ── Role breakdown ──
    role_counts = {
        'Employees': Employee.objects.filter(role='employee').count(),
        'Managers': Employee.objects.filter(role='manager').count(),
        'HR Admins': Employee.objects.filter(role='hr').count(),
        'Directors': Employee.objects.filter(role='admin_director').count(),
    }

    # ── Recent admin log entries ──
    try:
        recent_logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:15]
    except Exception:
        recent_logs = []

    # ── Departments with employee counts ──
    departments = Department.objects.annotate(emp_count=Count('employee'))

    # ── Recently added employees ──
    recent_employees = Employee.objects.select_related('user', 'department').order_by('-user__date_joined')[:8]

    # ── Discipline stats ──
    discipline_warned = DisciplineRecord.objects.filter(
        action_type__in=['verbal_warning', 'written_caution', 'final_warning']
    ).values('employee').distinct().count()
    discipline_suspended = DisciplineRecord.objects.filter(
        action_type='suspension', suspension_end__gte=today,
    ).count()
    discipline_dismissed = DisciplineRecord.objects.filter(
        action_type='dismissal'
    ).values('employee').distinct().count()
    dismissal_alert = DisciplineRecord.objects.filter(
        action_type='dismissal'
    ).select_related('employee__user').order_by('-date_issued')[:10]

    # ── Currently on leave ──
    on_leave_now = LeaveRequest.objects.filter(
        status='approved', start_date__lte=today, end_date__gte=today
    ).select_related('employee__user', 'employee__department', 'leave_type')

    # ── Pending approvals at each stage ──
    pending_hr_requests = LeaveRequest.objects.filter(
        status='manager_approved'
    ).select_related('employee__user', 'leave_type', 'manager_action_by__user')[:10]

    awaiting_director = LeaveRequest.objects.filter(
        status='hr_approved'
    ).select_related('employee__user', 'employee__department', 'leave_type', 'hr_action_by__user')[:10]

    # ── Monthly chart ──
    monthly_data = []
    month_labels = []
    for m in range(1, 13):
        count = LeaveRequest.objects.filter(
            status='approved', start_date__year=year, start_date__month=m
        ).count()
        monthly_data.append(count)
        month_labels.append(datetime(year, m, 1).strftime('%b'))

    # ── Department leave activity ──
    dept_stats = Department.objects.annotate(
        total_requests=Count(
            'employee__leave_requests',
            filter=Q(employee__leave_requests__start_date__year=year)
        ),
        approved_requests=Count(
            'employee__leave_requests',
            filter=Q(
                employee__leave_requests__status='approved',
                employee__leave_requests__start_date__year=year
            )
        )
    )

    # ── Low leave balance ──
    all_balances = LeaveBalance.objects.filter(year=year).select_related('employee__user', 'employee__department')
    low_balance = [b for b in all_balances if b.remaining_days <= 3]

    # ── Contract analytics ──────────────────────────────────────────────────
    _contract_ctx = _build_contract_analytics(today, year)

    return render(request, 'dashboard/admin_dashboard.html', {
        'employee': admin_employee,
        'balance': my_balance,
        'my_recent_requests': my_recent_requests,
        'my_pending_count': my_pending_count,
        'on_leave': my_on_leave,
        'active_suspension': my_active_suspension,
        'is_own_birthday': my_is_birthday,
        'today': today,
        'total_employees': total_employees,
        'total_departments': total_departments,
        'total_users': total_users,
        'approved_year': approved_year,
        'rejected_year': rejected_year,
        'pending_manager': pending_manager,
        'pending_hr': pending_hr,
        'pending_director': pending_director,
        'pending_all': pending_all,
        'role_counts': role_counts,
        'recent_logs': recent_logs,
        'departments': departments,
        'recent_employees': recent_employees,
        'year': year,
        'discipline_warned': discipline_warned,
        'discipline_suspended': discipline_suspended,
        'discipline_dismissed': discipline_dismissed,
        'dismissal_alert': dismissal_alert,
        'on_leave_now': on_leave_now,
        'pending_hr_requests': pending_hr_requests,
        'awaiting_director': awaiting_director,
        'monthly_data': monthly_data,
        'month_labels': month_labels,
        'dept_stats': dept_stats,
        'low_balance': low_balance,
        **_contract_ctx,
    })


def _send_birthday_notifications():
    """Send a Happy Birthday notification to every employee whose birthday is today.
    Only fires once per year — checked by looking for an existing birthday notification
    sent today for that employee.
    """
    try:
        from accounts.models import Employee as _Emp
        from notifications.utils import notify
        from notifications.models import Notification

        today = date.today()
        birthday_employees = _Emp.objects.filter(
            is_active=True,
            date_of_birth__isnull=False,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        ).select_related('user')

        for emp in birthday_employees:
            # Skip if already sent today
            already_sent = Notification.objects.filter(
                recipient=emp.user,
                notification_type='birthday',
                created_at__date=today,
            ).exists()
            if already_sent:
                continue

            age = today.year - emp.date_of_birth.year
            notify(
                emp.user,
                title='🎂 Happy Birthday!',
                message=(
                    f"Wishing you a very Happy Birthday, {emp.user.first_name or emp.get_full_name()}! "
                    f"On behalf of the entire Magrabi ICO Cameroon Eye Institute family, "
                    f"we hope your {age}{'st' if age == 1 else 'nd' if age == 2 else 'rd' if age == 3 else 'th'} birthday is filled with joy and wonderful memories. "
                    f"Thank you for your dedication and hard work. "
                    f"Have a fantastic day! 🎉"
                ),
                notification_type='birthday',
                url='/accounts/profile/',
            )
    except Exception:
        pass


def _process_expired_interns():
    """Deactivate intern/WACS accounts whose contract end_date has passed and contract is not renewed/extended."""
    try:
        from contracts.models import Contract as _Contract
        expired_contracts = _Contract.objects.filter(
            contract_type__in=['INTERN', 'WACS'],
            status='active',
            end_date__lt=date.today(),
        ).select_related('employee', 'employee__user')
        for contract in expired_contracts:
            contract.status = 'expired'
            contract.save(update_fields=['status'])
            emp = contract.employee
            if emp.user.is_active:
                emp.user.is_active = False
                emp.user.save(update_fields=['is_active'])
    except Exception:
        pass


@login_required
def home(request):
    _process_expired_interns()
    _send_birthday_notifications()
    # After a full factory reset the admin password is 'admin' — force change immediately
    if request.user.is_superuser and request.user.check_password('admin'):
        from django.contrib import messages
        messages.warning(
            request,
            "Your password is the default 'admin'. Please change it now before continuing."
        )
        return redirect('accounts:change_password')

    if request.user.is_superuser:
        return admin_dashboard(request)

    employee = get_employee(request)
    if not employee:
        return render(request, 'dashboard/no_profile.html')

    if employee.is_director():
        return director_dashboard(request, employee)
    elif employee.is_ceo():
        return director_dashboard(request, employee)
    elif employee.is_hr():
        return hr_dashboard(request, employee)
    elif employee.is_manager():
        return manager_dashboard(request, employee)
    elif employee.is_unit_head():
        return unit_head_dashboard(request, employee)
    else:
        return employee_dashboard(request, employee)


def employee_dashboard(request, employee):
    from discipline.models import DisciplineRecord
    today = date.today()
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    recent_requests = employee.leave_requests.all()[:5]
    pending_count = employee.leave_requests.filter(
        status__in=['pending', 'manager_approved', 'hr_approved']
    ).count()

    # Is currently on leave?
    on_leave = employee.leave_requests.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).first()

    # Discipline notices for this employee
    discipline_notices = DisciplineRecord.objects.filter(
        employee=employee
    ).order_by('-date_issued')
    active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()

    is_own_birthday = (
        employee.date_of_birth is not None
        and employee.date_of_birth.month == today.month
        and employee.date_of_birth.day == today.day
    )

    return render(request, 'dashboard/employee_dashboard.html', {
        'employee': employee,
        'balance': balance,
        'recent_requests': recent_requests,
        'pending_count': pending_count,
        'on_leave': on_leave,
        'today': today,
        'discipline_notices': discipline_notices,
        'active_suspension': active_suspension,
        'is_own_birthday': is_own_birthday,
    })


def manager_dashboard(request, employee):
    from django.db.models import Q
    from discipline.models import DisciplineRecord
    today = date.today()
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    my_recent_requests = employee.leave_requests.all()[:5]
    my_pending_count = employee.leave_requests.filter(
        status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved']
    ).count()
    my_on_leave = employee.leave_requests.filter(
        status='approved', start_date__lte=today, end_date__gte=today
    ).first()
    my_active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()
    my_is_birthday = (
        employee.date_of_birth is not None
        and employee.date_of_birth.month == today.month
        and employee.date_of_birth.day == today.day
    )

    # Show 'pending' for employees without unit_head + 'unit_head_approved' for those with unit_head
    pending_approvals = LeaveRequest.objects.filter(
        employee__supervisor=employee
    ).filter(
        Q(status='pending', employee__unit_head__isnull=True) |
        Q(status='unit_head_approved')
    ).select_related('employee__user', 'leave_type')

    subordinates = employee.subordinates.select_related('user').all()
    on_leave_today = LeaveRequest.objects.filter(
        status='approved',
        employee__supervisor=employee,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('employee__user', 'leave_type')

    return render(request, 'dashboard/manager_dashboard.html', {
        'employee': employee,
        'balance': balance,
        'my_recent_requests': my_recent_requests,
        'my_pending_count': my_pending_count,
        'on_leave': my_on_leave,
        'active_suspension': my_active_suspension,
        'is_own_birthday': my_is_birthday,
        'today': today,
        'pending_approvals': pending_approvals,
        'subordinates': subordinates,
        'on_leave_today': on_leave_today,
    })


def unit_head_dashboard(request, employee):
    from discipline.models import DisciplineRecord
    today = date.today()

    # ── own employee data (same as employee_dashboard) ────────────────────────
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    recent_requests = employee.leave_requests.all()[:5]
    pending_count = employee.leave_requests.filter(
        status__in=['pending', 'manager_approved', 'hr_approved']
    ).count()
    on_leave = employee.leave_requests.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).first()
    discipline_notices = DisciplineRecord.objects.filter(employee=employee).order_by('-date_issued')
    active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()
    is_own_birthday = (
        employee.date_of_birth is not None
        and employee.date_of_birth.month == today.month
        and employee.date_of_birth.day == today.day
    )

    # ── unit approval data ────────────────────────────────────────────────────
    pending_approvals = LeaveRequest.objects.filter(
        status='pending',
        employee__unit_head=employee,
    ).select_related('employee__user', 'leave_type')

    unit_members = Employee.objects.filter(unit_head=employee, is_active=True).select_related('user')
    unit_on_leave_today = LeaveRequest.objects.filter(
        status='approved',
        employee__unit_head=employee,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('employee__user', 'leave_type')

    return render(request, 'dashboard/unit_head_dashboard.html', {
        # employee self-service
        'employee': employee,
        'balance': balance,
        'recent_requests': recent_requests,
        'pending_count': pending_count,
        'on_leave': on_leave,
        'discipline_notices': discipline_notices,
        'active_suspension': active_suspension,
        'is_own_birthday': is_own_birthday,
        'today': today,
        # unit approval
        'pending_approvals': pending_approvals,
        'unit_members': unit_members,
        'unit_on_leave_today': unit_on_leave_today,
    })


def director_dashboard(request, employee):
    from discipline.models import DisciplineRecord
    today = date.today()
    year = today.year

    # ── Own employee self-service data ──
    my_balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    my_recent_requests = employee.leave_requests.all()[:5]
    my_pending_count = employee.leave_requests.filter(
        status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved']
    ).count()
    my_on_leave = employee.leave_requests.filter(
        status='approved', start_date__lte=today, end_date__gte=today
    ).first()
    my_active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()
    my_is_birthday = (
        employee.date_of_birth is not None
        and employee.date_of_birth.month == today.month
        and employee.date_of_birth.day == today.day
    )

    total_employees = Employee.objects.filter(is_active=True).count()
    pending_director = LeaveRequest.objects.filter(status='hr_approved').count()
    approved_year = LeaveRequest.objects.filter(status='approved', start_date__year=year).count()
    rejected_year = LeaveRequest.objects.filter(
        status__in=['rejected_manager', 'rejected_hr', 'rejected_director'],
        start_date__year=year
    ).count()

    on_leave_now = LeaveRequest.objects.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).select_related('employee__user', 'employee__department', 'leave_type')

    # Requests awaiting director sign-off
    awaiting_director = LeaveRequest.objects.filter(
        status='hr_approved'
    ).select_related('employee__user', 'employee__department', 'leave_type', 'manager_action_by__user', 'hr_action_by__user')[:10]

    monthly_data = []
    month_labels = []
    for m in range(1, 13):
        count = LeaveRequest.objects.filter(
            status='approved',
            start_date__year=year,
            start_date__month=m
        ).count()
        monthly_data.append(count)
        from datetime import datetime
        month_labels.append(datetime(year, m, 1).strftime('%b'))

    discipline_warned = DisciplineRecord.objects.filter(
        action_type__in=['verbal_warning', 'written_caution', 'final_warning']
    ).values('employee').distinct().count()
    discipline_suspended = DisciplineRecord.objects.filter(
        action_type='suspension',
        suspension_end__gte=today,
    ).count()
    discipline_dismissed = DisciplineRecord.objects.filter(
        action_type='dismissal'
    ).values('employee').distinct().count()

    _contract_ctx = _build_contract_analytics(today, year)

    return render(request, 'dashboard/director_dashboard.html', {
        'employee': employee,
        'balance': my_balance,
        'my_recent_requests': my_recent_requests,
        'my_pending_count': my_pending_count,
        'on_leave': my_on_leave,
        'active_suspension': my_active_suspension,
        'is_own_birthday': my_is_birthday,
        'today': today,
        'total_employees': total_employees,
        'pending_director': pending_director,
        'approved_year': approved_year,
        'rejected_year': rejected_year,
        'on_leave_now': on_leave_now,
        'awaiting_director': awaiting_director,
        'monthly_data': monthly_data,
        'month_labels': month_labels,
        'year': year,
        'discipline_warned': discipline_warned,
        'discipline_suspended': discipline_suspended,
        'discipline_dismissed': discipline_dismissed,
        **_contract_ctx,
    })


def hr_dashboard(request, employee):
    from discipline.models import DisciplineRecord
    today = date.today()
    year = today.year

    # ── Own employee self-service data ──
    my_balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    my_recent_requests = employee.leave_requests.all()[:5]
    my_pending_count = employee.leave_requests.filter(
        status__in=['pending', 'unit_head_approved', 'manager_approved', 'hr_approved']
    ).count()
    my_on_leave = employee.leave_requests.filter(
        status='approved', start_date__lte=today, end_date__gte=today
    ).first()
    my_active_suspension = DisciplineRecord.objects.filter(
        employee=employee,
        action_type='suspension',
        suspension_start__lte=today,
        suspension_end__gte=today,
    ).first()
    my_is_birthday = (
        employee.date_of_birth is not None
        and employee.date_of_birth.month == today.month
        and employee.date_of_birth.day == today.day
    )

    # Discipline stats
    discipline_warned = DisciplineRecord.objects.filter(
        action_type__in=['verbal_warning', 'written_caution', 'final_warning']
    ).values('employee').distinct().count()
    discipline_suspended = DisciplineRecord.objects.filter(
        action_type='suspension',
        suspension_end__gte=today,
    ).count()
    discipline_dismissed = DisciplineRecord.objects.filter(
        action_type='dismissal'
    ).values('employee').distinct().count()

    # Key stats
    total_employees = Employee.objects.filter(is_active=True).count()
    total_requests_year = LeaveRequest.objects.filter(start_date__year=year).count()
    pending_manager = LeaveRequest.objects.filter(status='pending').count()
    pending_hr = LeaveRequest.objects.filter(status='manager_approved').count()
    pending_director = LeaveRequest.objects.filter(status='hr_approved').count()
    approved_year = LeaveRequest.objects.filter(status='approved', start_date__year=year).count()
    rejected_year = LeaveRequest.objects.filter(
        status__in=['rejected_manager', 'rejected_hr', 'rejected_director'],
        start_date__year=year
    ).count()

    # Currently on leave
    on_leave_now = LeaveRequest.objects.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).select_related('employee__user', 'employee__department', 'leave_type')

    # Department breakdown
    dept_stats = Department.objects.annotate(
        total_requests=Count(
            'employee__leave_requests',
            filter=Q(employee__leave_requests__start_date__year=year)
        ),
        approved_requests=Count(
            'employee__leave_requests',
            filter=Q(
                employee__leave_requests__status='approved',
                employee__leave_requests__start_date__year=year
            )
        )
    )

    # Monthly trend (current year)
    monthly_data = []
    month_labels = []
    for m in range(1, 13):
        count = LeaveRequest.objects.filter(
            status='approved',
            start_date__year=year,
            start_date__month=m
        ).count()
        monthly_data.append(count)
        from datetime import datetime
        month_labels.append(datetime(year, m, 1).strftime('%b'))

    # Leave type breakdown
    type_stats = LeaveType.objects.annotate(
        total=Count(
            'leaverequest',
            filter=Q(leaverequest__start_date__year=year, leaverequest__status='approved')
        )
    ).filter(total__gt=0)

    # Recent requests
    recent_requests = LeaveRequest.objects.filter(
        status='manager_approved'
    ).select_related('employee__user', 'leave_type', 'manager_action_by__user')[:10]

    # Low balance employees
    all_balances = LeaveBalance.objects.filter(year=year).select_related('employee__user', 'employee__department')
    low_balance = []
    for b in all_balances:
        if b.remaining_days <= 3:
            low_balance.append(b)

    _contract_ctx = _build_contract_analytics(today, year)

    # Birthday data for HR dashboard
    from accounts.models import Employee as _EmpBday
    today_birthdays = list(
        _EmpBday.objects.filter(
            is_active=True,
            date_of_birth__isnull=False,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        ).select_related('user', 'department')
    )
    this_month_birthdays = sorted(
        _EmpBday.objects.filter(
            is_active=True,
            date_of_birth__isnull=False,
            date_of_birth__month=today.month,
        ).exclude(date_of_birth__day=today.day).select_related('user', 'department'),
        key=lambda e: e.date_of_birth.day
    )

    return render(request, 'dashboard/hr_dashboard.html', {
        'employee': employee,
        'balance': my_balance,
        'my_recent_requests': my_recent_requests,
        'my_pending_count': my_pending_count,
        'on_leave': my_on_leave,
        'active_suspension': my_active_suspension,
        'is_own_birthday': my_is_birthday,
        'today': today,
        'total_employees': total_employees,
        'total_requests_year': total_requests_year,
        'pending_manager': pending_manager,
        'pending_hr': pending_hr,
        'pending_director': pending_director,
        'approved_year': approved_year,
        'rejected_year': rejected_year,
        'on_leave_now': on_leave_now,
        'dept_stats': dept_stats,
        'monthly_data': monthly_data,
        'month_labels': month_labels,
        'type_stats': type_stats,
        'recent_requests': recent_requests,
        'low_balance': low_balance,
        'year': year,
        'discipline_warned': discipline_warned,
        'discipline_suspended': discipline_suspended,
        'discipline_dismissed': discipline_dismissed,
        'today_birthdays': today_birthdays,
        'this_month_birthdays': this_month_birthdays,
        **_contract_ctx,
    })


@login_required
def retirement_dashboard(request):
    """HR-only: list of employees approaching retirement (within 3 years)."""
    emp = get_employee(request)
    is_super = request.user.is_superuser
    if not is_super and (not emp or not (emp.is_hr() or emp.is_director() or emp.is_ceo())):
        return redirect('dashboard:home')

    from accounts.models import Employee as _Emp
    today = date.today()
    retirement_age = 60

    # All active employees with DOB set
    all_employees = _Emp.objects.filter(
        is_active=True, date_of_birth__isnull=False
    ).select_related('user', 'department').order_by('date_of_birth')

    # Compute years to retirement and filter < 3 years
    near_retirement = []
    for e in all_employees:
        age = e.age()
        if age is None:
            continue
        ytr = retirement_age - age
        if 0 <= ytr <= 3:
            retirement_date = e.date_of_birth.replace(year=e.date_of_birth.year + retirement_age)
            near_retirement.append({
                'employee': e,
                'age': age,
                'years_to_retirement': ytr,
                'retirement_date': retirement_date,
                'months_remaining': max(0, (retirement_date.year - today.year) * 12 + (retirement_date.month - today.month)),
            })

    # Sort by soonest retirement first
    near_retirement.sort(key=lambda x: x['years_to_retirement'])

    return render(request, 'dashboard/retirement_dashboard.html', {
        'near_retirement': near_retirement,
        'total': len(near_retirement),
        'retirement_age': retirement_age,
    })


@login_required
def leave_tracker(request):
    """HR leave balance tracker for all employees"""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not emp.is_director() and not emp.is_ceo()):
        return redirect('dashboard:home')

    year = int(request.GET.get('year', date.today().year))
    dept_filter = request.GET.get('dept', '')

    employees = Employee.objects.filter(is_active=True).select_related('user', 'department')
    if dept_filter:
        employees = employees.filter(department_id=dept_filter)

    balances = []
    for employee in employees:
        balance, _ = LeaveBalance.objects.get_or_create(
            employee=employee, year=year,
            defaults={'total_entitlement': 18}
        )
        balances.append({
            'employee': employee,
            'balance': balance,
        })

    departments = Department.objects.all()

    return render(request, 'dashboard/leave_tracker.html', {
        'balances': balances,
        'year': year,
        'years': range(2000, date.today().year + 11),
        'departments': departments,
        'dept_filter': dept_filter,
    })


@login_required
def birthday_dashboard(request):
    """HR-only: staff birthdays organised by month, with current month highlighted."""
    emp = get_employee(request)
    is_super = request.user.is_superuser
    if not is_super and (not emp or not (emp.is_hr() or emp.is_director() or emp.is_ceo())):
        return redirect('dashboard:home')

    today = date.today()
    selected_month = int(request.GET.get('month', today.month))

    from accounts.models import Employee as _Emp
    from datetime import datetime

    month_name = datetime(today.year, selected_month, 1).strftime('%B')

    # All active employees with DOB
    all_employees = list(
        _Emp.objects.filter(is_active=True, date_of_birth__isnull=False)
        .select_related('user', 'department')
    )

    # Group by birth month
    months_data = []
    for m in range(1, 13):
        name = datetime(today.year, m, 1).strftime('%B')
        staff = sorted(
            [e for e in all_employees if e.date_of_birth.month == m],
            key=lambda e: e.date_of_birth.day
        )
        months_data.append({'month': m, 'name': name, 'staff': staff, 'count': len(staff)})

    # This month's birthdays, sorted by day
    this_month_staff = months_data[today.month - 1]['staff']

    # Today's birthdays
    todays_birthdays = [e for e in all_employees if e.date_of_birth.month == today.month and e.date_of_birth.day == today.day]

    # Selected month's birthdays
    selected_staff = months_data[selected_month - 1]['staff']

    return render(request, 'dashboard/birthday_dashboard.html', {
        'today': today,
        'months_data': months_data,
        'this_month_staff': this_month_staff,
        'todays_birthdays': todays_birthdays,
        'selected_month': selected_month,
        'selected_month_name': month_name,
        'selected_staff': selected_staff,
    })


@login_required
def search(request):
    """Live search endpoint — returns JSON results for the topbar search."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    emp = get_employee(request)
    is_super = request.user.is_superuser
    is_privileged = is_super or (emp and (emp.is_hr() or emp.is_director()))

    results = []

    # ── Employees ──────────────────────────────────────────────
    if is_privileged:
        emp_qs = Employee.objects.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(employee_id__icontains=q) |
            Q(position__icontains=q) |
            Q(user__email__icontains=q)
        ).select_related('user', 'department')[:6]
    elif emp and emp.is_manager():
        emp_qs = emp.subordinates.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(employee_id__icontains=q)
        ).select_related('user', 'department')[:4]
    else:
        emp_qs = []

    for e in emp_qs:
        results.append({
            'type': 'employee',
            'icon': 'person',
            'title': e.get_full_name(),
            'subtitle': f"{e.employee_id} · {e.department or 'No dept'} · {e.get_role_display()}",
            'url': f"/accounts/employees/{e.pk}/edit/",
            'initials': (e.user.first_name[:1] + e.user.last_name[:1]).upper(),
        })

    # ── Leave Requests ─────────────────────────────────────────
    if is_privileged:
        lr_qs = LeaveRequest.objects.filter(
            Q(employee__user__first_name__icontains=q) |
            Q(employee__user__last_name__icontains=q) |
            Q(employee__employee_id__icontains=q) |
            Q(leave_type__name__icontains=q) |
            Q(reason__icontains=q)
        ).select_related('employee__user', 'leave_type')[:5]
    elif emp and emp.is_manager():
        lr_qs = LeaveRequest.objects.filter(
            Q(employee__supervisor=emp),
            Q(employee__user__first_name__icontains=q) |
            Q(employee__user__last_name__icontains=q) |
            Q(leave_type__name__icontains=q)
        ).select_related('employee__user', 'leave_type')[:4]
    elif emp:
        lr_qs = LeaveRequest.objects.filter(
            employee=emp
        ).filter(
            Q(leave_type__name__icontains=q) |
            Q(reason__icontains=q)
        ).select_related('leave_type')[:4]
    else:
        lr_qs = []

    status_labels = {
        'pending': 'Pending',
        'manager_approved': 'Pending HR',
        'hr_approved': 'Pending Director',
        'approved': 'Approved',
        'rejected_manager': 'Rejected',
        'rejected_hr': 'Rejected',
        'rejected_director': 'Rejected',
        'cancelled': 'Cancelled',
    }
    for lr in lr_qs:
        results.append({
            'type': 'leave',
            'icon': 'calendar-check',
            'title': f"{lr.employee.get_full_name()} — {lr.leave_type.name}",
            'subtitle': f"{lr.start_date} → {lr.end_date} · {status_labels.get(lr.status, lr.status)}",
            'url': f"/leaves/detail/{lr.pk}/",
            'initials': None,
        })

    # ── Departments ────────────────────────────────────────────
    if is_privileged:
        dept_qs = Department.objects.filter(
            Q(name__icontains=q) | Q(code__icontains=q)
        )[:3]
        for d in dept_qs:
            results.append({
                'type': 'department',
                'icon': 'building',
                'title': d.name,
                'subtitle': f"Code: {d.code}",
                'url': '/accounts/departments/',
                'initials': None,
            })

    return JsonResponse({'results': results, 'query': q})


# ─────────────────────────────────────────────────────────────
#  ADMIN SYSTEM SETTINGS
# ─────────────────────────────────────────────────────────────

def superuser_required_view(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.contrib import messages
            messages.error(request, "Access denied. Superuser only.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@superuser_required_view
def admin_settings(request):
    year = int(request.GET.get('year', date.today().year))
    employees = Employee.objects.filter(is_active=True).select_related('user', 'department')
    balances = []
    for emp in employees:
        bal, _ = LeaveBalance.objects.get_or_create(
            employee=emp, year=year,
            defaults={'total_entitlement': 18}
        )
        balances.append({'employee': emp, 'balance': bal})
    return render(request, 'dashboard/admin_settings.html', {
        'balances': balances,
        'year': year,
        'years': range(2000, date.today().year + 11),
    })


@superuser_required_view
def reset_leave_balances(request):
    """Reset total_entitlement to 18 for all active employees for the chosen year."""
    from django.contrib import messages
    if request.method != 'POST':
        return redirect('dashboard:admin_settings')
    year = int(request.POST.get('year', date.today().year))
    employees = Employee.objects.filter(is_active=True)
    count = 0
    for emp in employees:
        bal, created = LeaveBalance.objects.get_or_create(
            employee=emp, year=year,
            defaults={'total_entitlement': 18}
        )
        if not created:
            bal.total_entitlement = 18
            bal.save()
        count += 1
    messages.success(request, f"Leave balances reset to 18 days for {count} employees ({year}).")
    return redirect('dashboard:admin_settings')


@superuser_required_view
def carry_forward_leave(request):
    """Carry unused deductible leave from one year into the next as accumulated leave."""
    if request.method != 'POST':
        return redirect('dashboard:admin_settings')
    from_year = int(request.POST.get('from_year', date.today().year - 1))
    to_year = from_year + 1

    balances = LeaveBalance.objects.filter(year=from_year).select_related('employee')
    count = 0
    total_days = 0
    for bal in balances:
        carry = bal.remaining_days
        next_bal, created = LeaveBalance.objects.get_or_create(
            employee=bal.employee,
            year=to_year,
            defaults={'total_entitlement': 18, 'carried_forward': carry},
        )
        if not created:
            next_bal.carried_forward = carry
            next_bal.save()
        total_days += carry
        count += 1

    messages.success(
        request,
        f"Carry-forward complete: {count} employees — {total_days} days moved from {from_year} to {to_year}."
    )
    from django.urls import reverse
    return redirect(reverse('dashboard:admin_settings') + f'?year={to_year}')


@superuser_required_view
def export_data(request):
    """Export all key system data as a JSON file."""
    import json
    from django.core import serializers
    from django.contrib.auth.models import User

    # collect all models in dependency order
    datasets = {}

    users = User.objects.filter(is_superuser=False)
    datasets['users'] = json.loads(serializers.serialize('json', users))

    departments = Department.objects.all()
    datasets['departments'] = json.loads(serializers.serialize('json', departments))

    employees = Employee.objects.all()
    datasets['employees'] = json.loads(serializers.serialize('json', employees))

    leave_types = LeaveType.objects.all()
    datasets['leave_types'] = json.loads(serializers.serialize('json', leave_types))

    balances = LeaveBalance.objects.all()
    datasets['leave_balances'] = json.loads(serializers.serialize('json', balances))

    requests_qs = LeaveRequest.objects.all()
    datasets['leave_requests'] = json.loads(serializers.serialize('json', requests_qs))

    export = {
        'exported_at': date.today().isoformat(),
        'version': '1.0',
        'data': datasets,
    }

    payload = json.dumps(export, indent=2, default=str)
    response = HttpResponse(payload, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="leavedesk_backup_{date.today()}.json"'
    return response


@superuser_required_view
def import_data(request):
    """Import data from a previously exported JSON backup."""
    from django.contrib import messages
    from django.core import serializers
    from django.db import transaction

    if request.method != 'POST':
        return redirect('dashboard:admin_settings')

    uploaded = request.FILES.get('backup_file')
    if not uploaded:
        messages.error(request, "No file uploaded.")
        return redirect('dashboard:admin_settings')

    import json
    try:
        raw = uploaded.read().decode('utf-8')
        export = json.loads(raw)
        data = export.get('data', {})

        with transaction.atomic():
            # Restore in dependency order
            for section in ['users', 'departments', 'employees', 'leave_types', 'leave_balances', 'leave_requests']:
                records = data.get(section, [])
                if not records:
                    continue
                json_str = json.dumps(records)
                for obj in serializers.deserialize('json', json_str):
                    obj.save()

        messages.success(request, f"Backup from {export.get('exported_at', 'unknown date')} imported successfully.")
    except Exception as e:
        messages.error(request, f"Import failed: {e}")

    return redirect('dashboard:admin_settings')


@superuser_required_view
def reset_single_balance(request, pk):
    """Reset one employee's balance to 18 for the given year."""
    from django.contrib import messages
    from django.shortcuts import get_object_or_404
    if request.method != 'POST':
        return redirect('dashboard:admin_settings')
    employee = get_object_or_404(Employee, pk=pk)
    year = int(request.POST.get('year', date.today().year))
    bal, created = LeaveBalance.objects.get_or_create(
        employee=employee, year=year,
        defaults={'total_entitlement': 18}
    )
    if not created:
        bal.total_entitlement = 18
        bal.save()
    messages.success(request, f"Balance for {employee.get_full_name()} reset to 18 days ({year}).")
    return redirect(f"{request.META.get('HTTP_REFERER', '/dashboard/admin-settings/')}#balance-table")


@superuser_required_view
def adjust_entitlement(request, pk):
    """Set a custom total_entitlement for one employee for the given year."""
    from django.contrib import messages
    from django.shortcuts import get_object_or_404
    if request.method != 'POST':
        return redirect('dashboard:admin_settings')
    employee = get_object_or_404(Employee, pk=pk)
    year = int(request.POST.get('year', date.today().year))
    try:
        new_val = int(request.POST.get('entitlement', 18))
        if new_val < 0:
            raise ValueError
    except ValueError:
        messages.error(request, "Invalid entitlement value.")
        return redirect('dashboard:admin_settings')
    bal, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=year,
        defaults={'total_entitlement': new_val}
    )
    bal.total_entitlement = new_val
    bal.save()
    messages.success(request, f"Entitlement for {employee.get_full_name()} set to {new_val} days ({year}).")
    return redirect('dashboard:admin_settings')


@superuser_required_view
def factory_reset_full(request):
    """
    Full factory reset: wipes ALL data except the superuser account,
    resets admin username/password to 'admin'/'admin', and forces a
    password change on next login.
    """
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.db import transaction
    from django.contrib.auth import logout

    if request.method != 'POST':
        return redirect('dashboard:admin_settings')

    confirm = request.POST.get('confirm_text', '').strip()
    if confirm != 'RESET EVERYTHING':
        messages.error(request, "Confirmation text did not match. Reset cancelled.")
        return redirect('dashboard:admin_settings')

    with transaction.atomic():
        # Delete all leave data
        LeaveRequest.objects.all().delete()
        LeaveBalance.objects.all().delete()
        LeaveType.objects.all().delete()
        # Delete all employees and their non-superuser users
        Employee.objects.all().delete()
        Department.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # Reset the superuser account
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            admin.username = 'admin'
            admin.first_name = ''
            admin.last_name = ''
            admin.email = ''
            admin.set_password('admin')
            admin.save()

        # Re-seed default leave types
        from leaves.views import seed_default_leave_types
        seed_default_leave_types()

    # Force logout so they must log in with the new password
    logout(request)
    messages.success(
        request,
        "Full factory reset complete. Log in with username 'admin' and password 'admin'. "
        "You will be required to change your password immediately."
    )
    return redirect('accounts:login')


@superuser_required_view
def factory_reset_soft(request):
    """
    Soft reset: deletes all leave requests, balances, discipline records, and contract data
    but keeps all user accounts, employee profiles, and departments.
    """
    from django.contrib import messages
    from django.db import transaction
    from discipline.models import DisciplineRecord
    from contracts.models import Contract, ContractNotification
    from notifications.models import Notification

    if request.method != 'POST':
        return redirect('dashboard:admin_settings')

    confirm = request.POST.get('confirm_text', '').strip()
    if confirm != 'RESET LEAVE DATA':
        messages.error(request, "Confirmation text did not match. Reset cancelled.")
        return redirect('dashboard:admin_settings')

    with transaction.atomic():
        LeaveRequest.objects.all().delete()
        LeaveBalance.objects.all().delete()
        DisciplineRecord.objects.all().delete()
        ContractNotification.objects.all().delete()
        Contract.objects.all().delete()
        Notification.objects.all().delete()

    messages.success(
        request,
        "Soft reset complete. All leave requests, balances, discipline records, contracts, and notifications have been cleared. "
        "User accounts, employee profiles, departments, and leave types are intact."
    )
    return redirect('dashboard:admin_settings')


@superuser_required_view
def factory_reset_yearend(request):
    """
    Year-End Reset: clears only leave requests and leave balances.
    Keeps all employee profiles, departments, leave types, contracts,
    discipline records, and notifications intact.
    """
    from django.contrib import messages
    from django.db import transaction

    if request.method != 'POST':
        return redirect('dashboard:admin_settings')

    confirm = request.POST.get('confirm_text', '').strip()
    if confirm != 'NEW YEAR RESET':
        messages.error(request, "Confirmation text did not match. Reset cancelled.")
        return redirect('dashboard:admin_settings')

    with transaction.atomic():
        LeaveRequest.objects.all().delete()
        LeaveBalance.objects.all().delete()

    messages.success(
        request,
        "Year-End reset complete. All leave requests and balances have been cleared. "
        "Staff, contracts, discipline records, and notifications are untouched."
    )
    return redirect('dashboard:admin_settings')
