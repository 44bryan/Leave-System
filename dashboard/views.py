from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from datetime import date, timedelta
from accounts.models import Employee, Department
from leaves.models import LeaveRequest, LeaveBalance, LeaveType


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


@login_required
def home(request):
    employee = get_employee(request)
    if not employee:
        return render(request, 'dashboard/no_profile.html')

    if employee.is_hr():
        return hr_dashboard(request, employee)
    elif employee.is_manager():
        return manager_dashboard(request, employee)
    else:
        return employee_dashboard(request, employee)


def employee_dashboard(request, employee):
    today = date.today()
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )
    recent_requests = employee.leave_requests.all()[:5]
    pending_count = employee.leave_requests.filter(
        status__in=['pending', 'manager_approved']
    ).count()

    # Is currently on leave?
    on_leave = employee.leave_requests.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).first()

    return render(request, 'dashboard/employee_dashboard.html', {
        'employee': employee,
        'balance': balance,
        'recent_requests': recent_requests,
        'pending_count': pending_count,
        'on_leave': on_leave,
        'today': today,
    })


def manager_dashboard(request, employee):
    today = date.today()
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=today.year,
        defaults={'total_entitlement': 18}
    )

    pending_approvals = LeaveRequest.objects.filter(
        status='pending',
        employee__supervisor=employee
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
        'pending_approvals': pending_approvals,
        'subordinates': subordinates,
        'on_leave_today': on_leave_today,
    })


def hr_dashboard(request, employee):
    today = date.today()
    year = today.year

    # Key stats
    total_employees = Employee.objects.filter(is_active=True).count()
    total_requests_year = LeaveRequest.objects.filter(start_date__year=year).count()
    pending_manager = LeaveRequest.objects.filter(status='pending').count()
    pending_hr = LeaveRequest.objects.filter(status='manager_approved').count()
    approved_year = LeaveRequest.objects.filter(status='approved', start_date__year=year).count()
    rejected_year = LeaveRequest.objects.filter(
        status__in=['rejected_manager', 'rejected_hr'],
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

    return render(request, 'dashboard/hr_dashboard.html', {
        'employee': employee,
        'total_employees': total_employees,
        'total_requests_year': total_requests_year,
        'pending_manager': pending_manager,
        'pending_hr': pending_hr,
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
    })


@login_required
def leave_tracker(request):
    """HR leave balance tracker for all employees"""
    emp = get_employee(request)
    if not emp or not emp.is_hr():
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
        'years': range(2023, date.today().year + 2),
        'departments': departments,
        'dept_filter': dept_filter,
    })
