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


def admin_dashboard(request):
    from django.contrib.auth.models import User
    from django.contrib.admin.models import LogEntry
    today = date.today()
    year = today.year

    total_employees = Employee.objects.filter(is_active=True).count()
    total_departments = Department.objects.count()
    total_users = User.objects.count()
    total_requests_year = LeaveRequest.objects.filter(start_date__year=year).count()
    approved_year = LeaveRequest.objects.filter(status='approved', start_date__year=year).count()
    pending_all = LeaveRequest.objects.filter(
        status__in=['pending', 'manager_approved', 'hr_approved']
    ).count()

    # Role breakdown
    role_counts = {
        'Employees': Employee.objects.filter(role='employee').count(),
        'Managers': Employee.objects.filter(role='manager').count(),
        'HR Admins': Employee.objects.filter(role='hr').count(),
        'Directors': Employee.objects.filter(role='admin_director').count(),
    }

    # Recent admin log entries
    try:
        recent_logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:15]
    except Exception:
        recent_logs = []

    # Departments with employee counts
    departments = Department.objects.annotate(emp_count=Count('employee'))

    # Recently added employees
    recent_employees = Employee.objects.select_related('user', 'department').order_by('-user__date_joined')[:8]

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_employees': total_employees,
        'total_departments': total_departments,
        'total_users': total_users,
        'total_requests_year': total_requests_year,
        'approved_year': approved_year,
        'pending_all': pending_all,
        'role_counts': role_counts,
        'recent_logs': recent_logs,
        'departments': departments,
        'recent_employees': recent_employees,
        'year': year,
    })


@login_required
def home(request):
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
    elif employee.is_hr():
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
        status__in=['pending', 'manager_approved', 'hr_approved']
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


def director_dashboard(request, employee):
    today = date.today()
    year = today.year

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

    return render(request, 'dashboard/director_dashboard.html', {
        'employee': employee,
        'total_employees': total_employees,
        'pending_director': pending_director,
        'approved_year': approved_year,
        'rejected_year': rejected_year,
        'on_leave_now': on_leave_now,
        'awaiting_director': awaiting_director,
        'monthly_data': monthly_data,
        'month_labels': month_labels,
        'year': year,
    })


def hr_dashboard(request, employee):
    today = date.today()
    year = today.year

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

    return render(request, 'dashboard/hr_dashboard.html', {
        'employee': employee,
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
    })


@login_required
def leave_tracker(request):
    """HR leave balance tracker for all employees"""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not emp.is_director()):
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
        'years': range(2023, date.today().year + 2),
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
    Soft reset: deletes all leave requests, balances, and leave types
    but keeps all user accounts, employee profiles, and departments.
    """
    from django.contrib import messages
    from django.db import transaction

    if request.method != 'POST':
        return redirect('dashboard:admin_settings')

    confirm = request.POST.get('confirm_text', '').strip()
    if confirm != 'RESET LEAVE DATA':
        messages.error(request, "Confirmation text did not match. Reset cancelled.")
        return redirect('dashboard:admin_settings')

    with transaction.atomic():
        LeaveRequest.objects.all().delete()
        LeaveBalance.objects.all().delete()

    messages.success(
        request,
        "Soft reset complete. All leave requests and balances have been cleared. "
        "User accounts, employee profiles, departments, and leave types are intact."
    )
    return redirect('dashboard:admin_settings')
