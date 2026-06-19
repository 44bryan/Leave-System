from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from datetime import date
from collections import defaultdict

from accounts.models import Employee, Department
from .models import Contract, ContractNotification


def _is_hr_or_above(user):
    """HR, superuser, director, or CEO — can VIEW contracts."""
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_director() or emp.is_ceo() or user.is_superuser
    except Exception:
        return user.is_superuser


def _can_manage_contracts(user):
    """HR, CEO, and superuser can ISSUE / RENEW / TERMINATE contracts."""
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_ceo() or user.is_superuser
    except Exception:
        return user.is_superuser


def _get_employee(request):
    try:
        return request.user.employee
    except Exception:
        return None


def _contract_issue_message(contract):
    """Return a tailored notification title + message for a newly issued contract."""
    start_d = _parse_date(contract.start_date)
    end_d   = _parse_date(contract.end_date)
    issued_on = contract.created_at.strftime('%d %b %Y') if contract.created_at else (start_d.strftime('%d %b %Y') if start_d else '—')
    start = start_d.strftime('%d %b %Y') if start_d else '—'
    end   = end_d.strftime('%d %b %Y') if end_d else None
    ct    = contract.contract_type

    collect_notice = (
        f" Your physical contract document is ready for collection at the HR Office "
        f"as of {issued_on}. Please pass by the HR Office at your earliest convenience "
        f"to sign and collect your copy."
    )

    if ct == 'INTERN':
        title = 'Internship Contract Issued'
        msg = (
            f"An Internship Contract has been issued to you, effective {start}."
            + (f" Your internship ends on {end}." if end else "")
            + collect_notice
        )
    elif ct == 'WACS':
        title = 'Residents Contract Issued'
        msg = (
            f"A Residents contract has been issued to you, effective {start}."
            + (f" Programme end date: {end}." if end else "")
            + collect_notice
        )
    elif ct == 'CDI':
        title = 'Permanent Contract (CDI) Issued'
        msg = (
            f"A Permanent (CDI) contract has been issued to you, effective {start}. "
            "This is an open-ended employment contract with no fixed end date."
            + collect_notice
        )
    else:  # CDD
        title = 'Fixed-Term Contract (CDD) Issued'
        msg = (
            f"A Fixed-Term (CDD) contract has been issued to you, effective {start}."
            + (f" Contract end date: {end}." if end else "")
            + collect_notice
        )
    return title, msg


def _parse_date(d):
    """Accept a date object or a string in various formats and return a date object."""
    if d is None:
        return None
    if not d:
        return None
    if isinstance(d, str):
        from datetime import datetime as _dt
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y',
                    '%m-%d-%Y', '%Y/%m/%d', '%d.%m.%Y', '%d %m %Y'):
            try:
                return _dt.strptime(d.strip()[:10], fmt).date()
            except ValueError:
                continue
        return None
    return d


def _contract_renewal_message(new_contract):
    """Return a tailored renewal/extension message for a contract."""
    start_d = _parse_date(new_contract.start_date)
    end_d   = _parse_date(new_contract.end_date)
    start = start_d.strftime('%d %b %Y') if start_d else '—'
    end   = end_d.strftime('%d %b %Y') if end_d else None
    ct    = new_contract.contract_type

    collect_notice = (
        " A new physical contract document is ready for collection at the HR Office. "
        "Please pass by the HR Office at your earliest convenience to sign and collect your copy."
    )

    if ct == 'INTERN':
        msg = (
            f"Your Internship Contract has been extended, effective {start}."
            + (f" New end date: {end}." if end else "")
            + collect_notice
        )
    elif ct == 'WACS':
        msg = (
            f"Your WACS Residency Programme contract has been extended, effective {start}."
            + (f" New programme end date: {end}." if end else "")
            + collect_notice
        )
    elif ct == 'CDI':
        msg = (
            f"Your contract has been renewed as a Permanent (CDI) contract, effective {start}. "
            "This is an open-ended employment contract."
            + collect_notice
        )
    else:  # CDD
        msg = (
            f"Your Fixed-Term (CDD) contract has been renewed, effective {start}."
            + (f" New end date: {end}." if end else "")
            + collect_notice
        )
    return msg


def _contract_termination_message(contract, reason=''):
    """Return a tailored termination message for a contract."""
    ct = contract.contract_type
    label_map = {
        'CDI': 'Permanent (CDI)',
        'CDD': 'Fixed-Term (CDD)',
        'INTERN': 'Internship',
        'WACS': 'WACS Residency',
    }
    label = label_map.get(ct, contract.get_contract_type_display())
    msg = (
        f"Your {label} contract has been terminated"
        + (f" for the following reason: {reason}" if reason else "")
        + ". Please contact HR for further information."
    )
    return msg


# ── Employee views ───────────────────────────────────────────────────────────

@login_required
def my_contract(request):
    emp = _get_employee(request)
    if not emp:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    # Get the most recent active contract (or the latest one)
    contract = (
        emp.contracts.filter(status='active').first()
        or emp.contracts.first()
    )

    all_contracts = emp.contracts.order_by('-start_date', '-created_at')
    unread_count = emp.contract_notifications.filter(is_read=False).count()
    notifications = emp.contract_notifications.all()[:10]

    return render(request, 'contracts/my_contract.html', {
        'contract': contract,
        'employee': emp,
        'all_contracts': all_contracts,
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def my_notifications(request):
    emp = _get_employee(request)
    if not emp:
        return redirect('dashboard:home')

    # Mark all as read
    emp.contract_notifications.filter(is_read=False).update(is_read=True)
    notifications = emp.contract_notifications.all()

    return render(request, 'contracts/notifications.html', {
        'notifications': notifications,
        'employee': emp,
    })


# ── HR / Admin views ─────────────────────────────────────────────────────────

@login_required
def contract_list(request):
    if not _is_hr_or_above(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    from django.db.models import Q, Value
    from django.db.models.functions import Concat
    filter_type = request.GET.get('type', '')
    filter_status = request.GET.get('status', '')
    filter_expiring = request.GET.get('expiring', '')
    filter_dept = request.GET.get('dept', '')
    filter_emp  = request.GET.get('employee', '')
    filter_q    = request.GET.get('q', '').strip()

    contracts = Contract.objects.select_related('employee', 'employee__user', 'employee__department').annotate(
        emp_full_name=Concat('employee__user__first_name', Value(' '), 'employee__user__last_name')
    )

    if filter_q:
        contracts = contracts.filter(
            Q(emp_full_name__icontains=filter_q) |
            Q(employee__user__first_name__icontains=filter_q) |
            Q(employee__user__last_name__icontains=filter_q) |
            Q(employee__employee_id__icontains=filter_q)
        )
    if filter_type:
        contracts = contracts.filter(contract_type=filter_type)
    if filter_status:
        contracts = contracts.filter(status=filter_status)
    if filter_dept:
        contracts = contracts.filter(employee__department_id=filter_dept)
    if filter_emp:
        contracts = contracts.filter(employee_id=filter_emp)

    # Chronological order — most recent contracts first
    contracts = contracts.order_by('-start_date', '-created_at')

    # Convert to list so we can apply computed-property filters
    contracts = list(contracts)
    if filter_expiring == '30':
        contracts = [c for c in contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 30]
    elif filter_expiring == '60':
        contracts = [c for c in contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 60]

    # Summary counts — distinct employees (so a person with 3 renewals counts as 1)
    all_active = Contract.objects.filter(status='active')
    total         = all_active.values('employee').distinct().count()
    active_cdi    = all_active.filter(contract_type='CDI'   ).values('employee').distinct().count()
    active_cdd    = all_active.filter(contract_type='CDD'   ).values('employee').distinct().count()
    active_intern = all_active.filter(contract_type='INTERN').values('employee').distinct().count()
    active_wacs   = all_active.filter(contract_type='WACS'  ).values('employee').distinct().count()
    expiring_soon = [c for c in Contract.objects.filter(contract_type='CDD', status='active') if c.is_expiring_soon]

    from accounts.models import Department as _Dept, Employee as _Emp
    all_departments = _Dept.objects.order_by('name')
    all_employees   = _Emp.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')

    return render(request, 'contracts/contract_list.html', {
        'contracts': contracts,
        'total': total,
        'active_cdi': active_cdi,
        'active_cdd': active_cdd,
        'active_intern': active_intern,
        'active_wacs': active_wacs,
        'expiring_soon_count': len(expiring_soon),
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_expiring': filter_expiring,
        'filter_dept': filter_dept,
        'filter_emp': filter_emp,
        'filter_q': filter_q,
        'all_departments': all_departments,
        'all_employees': all_employees,
    })


@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    # Employees can only view their own contract
    if not _is_hr_or_above(request.user):
        emp = _get_employee(request)
        if not emp or contract.employee != emp:
            messages.error(request, "Access denied.")
            return redirect('contracts:my_contract')

    # Only show OLDER contracts (true history — no forward links creating circular navigation)
    renewal_history = Contract.objects.filter(
        employee=contract.employee,
        start_date__lte=contract.start_date,
    ).exclude(pk=contract.pk).order_by('-start_date')

    return render(request, 'contracts/contract_detail.html', {
        'contract': contract,
        'renewal_history': renewal_history,
    })


@login_required
def issue_contract(request):
    if not _can_manage_contracts(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    today = date.today()

    if request.method == 'POST':
        emp_id = request.POST.get('employee')
        contract_type = request.POST.get('contract_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        notes = request.POST.get('notes', '')
        internship_type = request.POST.get('internship_type', '') if contract_type == 'INTERN' else ''
        working_dept_id = request.POST.get('working_department', '') if contract_type in ('INTERN', 'WACS') else ''

        if not emp_id or not contract_type or not start_date:
            messages.error(request, "Employee, contract type, and start date are required.")
            return render(request, 'contracts/issue_contract.html', {
                'employees': employees, 'today': today,
                'all_departments': __import__('accounts.models', fromlist=['Department']).Department.objects.order_by('name'),
            })

        parsed_start = _parse_date(start_date)
        if not parsed_start:
            messages.error(request, "Invalid start date. Use DD/MM/YYYY or YYYY-MM-DD.")
            return render(request, 'contracts/issue_contract.html', {
                'employees': employees, 'today': today,
                'all_departments': __import__('accounts.models', fromlist=['Department']).Department.objects.order_by('name'),
            })

        parsed_end = None
        if end_date:
            parsed_end = _parse_date(end_date)
            if not parsed_end:
                messages.error(request, "Invalid end date. Use DD/MM/YYYY or YYYY-MM-DD.")
                return render(request, 'contracts/issue_contract.html', {
                    'employees': employees, 'today': today,
                    'all_departments': __import__('accounts.models', fromlist=['Department']).Department.objects.order_by('name'),
                })

        if contract_type in ('CDD', 'INTERN', 'WACS') and not parsed_end:
            label = {'CDD': 'Fixed-Term (CDD)', 'INTERN': 'Internship', 'WACS': 'WACS Residency'}[contract_type]
            messages.error(request, f"End date is required for {label} contracts.")
            return render(request, 'contracts/issue_contract.html', {
                'employees': employees, 'today': today,
                'all_departments': __import__('accounts.models', fromlist=['Department']).Department.objects.order_by('name'),
            })

        emp = get_object_or_404(Employee, pk=emp_id)

        # Mark any existing active contract as renewed (if this is a renewal)
        existing = emp.contracts.filter(status='active').first()

        contract = Contract.objects.create(
            employee=emp,
            contract_type=contract_type,
            internship_type=internship_type,
            working_department_id=working_dept_id or None,
            start_date=parsed_start,
            end_date=parsed_end,
            notes=notes,
            status='active',
            created_by=request.user,
            renewed_from=existing,
        )

        if existing:
            existing.status = 'renewed'
            existing.save()

        # Notify employee via main notification system
        from notifications.utils import notify
        _title, _msg = _contract_issue_message(contract)
        notify(
            emp.user,
            title=_title,
            message=_msg,
            notification_type='contract_issued',
            url=reverse('contracts:my_contract'),
        )

        messages.success(request, f"Contract issued for {emp.get_full_name()}.")
        try:
            from dashboard.models import AuditLog
            AuditLog.log(
                request, AuditLog.ACTION_CONTRACT,
                f"Issued contract ({contract.contract_type}) for {emp.get_full_name()} "
                f"({contract.start_date} → {contract.end_date or 'open-ended'})",
                target_user=emp.user,
            )
        except Exception:
            pass
        return redirect('contracts:detail', pk=contract.pk)

    preselect_employee_pk = request.GET.get('employee')
    preselect_employee = None
    if preselect_employee_pk:
        try:
            preselect_employee = employees.get(pk=preselect_employee_pk)
        except Employee.DoesNotExist:
            pass

    from accounts.models import Department as _Dept
    return render(request, 'contracts/issue_contract.html', {
        'employees': employees,
        'today': today,
        'preselect_employee': preselect_employee,
        'all_departments': _Dept.objects.order_by('name'),
    })


@login_required
def renew_contract(request, pk):
    if not _can_manage_contracts(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    old_contract = get_object_or_404(Contract, pk=pk)

    if request.method == 'POST':
        new_start = request.POST.get('start_date')
        new_end = request.POST.get('end_date') or None
        contract_type = request.POST.get('contract_type', old_contract.contract_type)
        notes = request.POST.get('notes', '')

        if not new_start:
            messages.error(request, "New start date is required.")
            return redirect('contracts:detail', pk=pk)

        if contract_type in ('CDD', 'INTERN', 'WACS') and not new_end:
            messages.error(request, "End date is required for this contract type renewal.")
            return redirect('contracts:detail', pk=pk)

        # Mark old contract as renewed
        old_contract.status = 'renewed'
        old_contract.save()

        # Pass internship_type for INTERN contracts
        internship_type = request.POST.get('internship_type', '') if contract_type == 'INTERN' else ''

        # Create new contract
        new_contract = Contract.objects.create(
            employee=old_contract.employee,
            contract_type=contract_type,
            internship_type=internship_type,
            start_date=new_start,
            end_date=new_end,
            notes=notes,
            status='active',
            created_by=request.user,
            renewed_from=old_contract,
        )

        # Notify employee (ContractNotification + main bell)
        renewal_msg = _contract_renewal_message(new_contract)
        is_extended = contract_type in ('INTERN', 'WACS')
        ContractNotification.objects.create(
            employee=old_contract.employee,
            contract=new_contract,
            notification_type='renewed',
            message=renewal_msg,
        )
        from notifications.utils import notify
        notify(
            old_contract.employee.user,
            title='Contract Extended' if is_extended else 'Contract Renewed',
            message=renewal_msg,
            notification_type='contract_renewed',
            url=reverse('contracts:detail', kwargs={'pk': new_contract.pk}),
        )

        action_word = "extended" if is_extended else "renewed"
        messages.success(
            request,
            f"Contract {action_word} for {old_contract.employee.get_full_name()}. Employee has been notified."
        )
        return redirect('contracts:detail', pk=new_contract.pk)

    return redirect('contracts:detail', pk=pk)


@login_required
def terminate_contract(request, pk):
    if not _can_manage_contracts(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    contract = get_object_or_404(Contract, pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        contract.status = 'terminated'
        contract.save()

        termination_msg = _contract_termination_message(contract, reason)
        ContractNotification.objects.create(
            employee=contract.employee,
            contract=contract,
            notification_type='terminated',
            message=termination_msg,
        )
        from notifications.utils import notify
        notify(
            contract.employee.user,
            title='Contract Terminated',
            message=termination_msg,
            notification_type='contract_terminated',
            url=reverse('contracts:my_contract'),
        )

        messages.success(
            request,
            f"Contract terminated for {contract.employee.get_full_name()}. Employee has been notified."
        )
        return redirect('contracts:list')

    return redirect('contracts:detail', pk=pk)


@login_required
def contract_stats(request):
    if not _is_hr_or_above(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    today = date.today()

    # ── All active contracts ──────────────────────────────────────────────────
    all_contracts = list(
        Contract.objects.filter(status='active')
        .select_related('employee', 'employee__user', 'employee__department')
        .order_by('start_date')
    )
    all_employees = list(Employee.objects.filter(is_active=True).select_related('user', 'department'))

    total_active  = len(all_contracts)
    total_cdi     = sum(1 for c in all_contracts if c.contract_type == 'CDI')
    total_cdd     = sum(1 for c in all_contracts if c.contract_type == 'CDD')
    total_intern  = sum(1 for c in all_contracts if c.contract_type == 'INTERN')
    total_wacs    = sum(1 for c in all_contracts if c.contract_type == 'WACS')
    total_staff   = len(all_employees)

    # ── Expiry urgency buckets ────────────────────────────────────────────────
    expiring_30  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 30], key=lambda c: c.days_remaining)
    expiring_60  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 30 < c.days_remaining <= 60], key=lambda c: c.days_remaining)
    expiring_90  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 60 < c.days_remaining <= 90], key=lambda c: c.days_remaining)
    already_expired = Contract.objects.filter(
        contract_type='CDD', status='active', end_date__lt=today
    ).select_related('employee', 'employee__user', 'employee__department').order_by('end_date')

    # ── Years of service distribution (all active employees with any contract) ─
    service_ranges = [
        ("<1 year",   0, 1),
        ("1–3 years", 1, 3),
        ("3–5 years", 3, 5),
        ("5–10 years",5, 10),
        ("10–15 yrs", 10, 15),
        ("15–20 yrs", 15, 20),
        ("20+ years", 20, 999),
    ]
    service_dist = []
    for label, lo, hi in service_ranges:
        count = sum(1 for c in all_contracts if lo <= c.years_of_service < hi)
        service_dist.append({
            'label': label, 'count': count,
            'pct': round((count / total_active * 100) if total_active else 0),
        })

    # ── Age & retirement ─────────────────────────────────────────────────────
    near_retirement = [e for e in all_employees if e.is_near_retirement()]
    ages = [e.age() for e in all_employees if e.age() is not None]
    avg_age = round(sum(ages) / len(ages)) if ages else None

    age_ranges = [
        ("<25",  0, 25),
        ("25–34",25, 35),
        ("35–44",35, 45),
        ("45–54",45, 55),
        ("55–59",55, 60),
        ("60+",  60, 200),
    ]
    age_dist = []
    for label, lo, hi in age_ranges:
        count = sum(1 for a in ages if lo <= a < hi)
        age_dist.append({
            'label': label, 'count': count,
            'pct': round((count / len(ages) * 100) if ages else 0),
            'danger': lo >= 55,
        })

    # ── Department breakdown ──────────────────────────────────────────────────
    dept_map = defaultdict(lambda: defaultdict(int))
    for c in all_contracts:
        dept_name = str(c.employee.department) if c.employee.department else 'No Department'
        dept_map[dept_name][c.contract_type] += 1
        dept_map[dept_name]['total'] += 1
    dept_breakdown = sorted(
        [{'dept': k, 'CDI': v.get('CDI', 0), 'CDD': v.get('CDD', 0),
          'INTERN': v.get('INTERN', 0), 'WACS': v.get('WACS', 0),
          'total': v.get('total', 0)} for k, v in dept_map.items()],
        key=lambda x: -x['total']
    )

    # ── Long-service leaders ──────────────────────────────────────────────────
    long_service = sorted(
        [c for c in all_contracts if c.contract_type == 'CDI'],
        key=lambda c: -c.years_of_service
    )[:10]

    # ── Recent contract activity ──────────────────────────────────────────────
    recent_activity = Contract.objects.select_related(
        'employee', 'employee__user', 'created_by'
    ).order_by('-created_at')[:15]

    # ── Terminations this year ────────────────────────────────────────────────
    terminated_year = Contract.objects.filter(
        status='terminated', updated_at__year=today.year
    ).count()
    renewed_year = Contract.objects.filter(
        status='renewed', updated_at__year=today.year
    ).count()
    issued_year = Contract.objects.filter(
        created_at__year=today.year
    ).count()

    return render(request, 'contracts/stats.html', {
        'today': today,
        'total_staff': total_staff,
        'total_active': total_active,
        'total_cdi': total_cdi,
        'total_cdd': total_cdd,
        'total_intern': total_intern,
        'total_wacs': total_wacs,
        'expiring_30': expiring_30,
        'expiring_60': expiring_60,
        'expiring_90': expiring_90,
        'already_expired': already_expired,
        'service_dist': service_dist,
        'near_retirement': near_retirement,
        'avg_age': avg_age,
        'age_dist': age_dist,
        'dept_breakdown': dept_breakdown,
        'long_service': long_service,
        'recent_activity': recent_activity,
        'terminated_year': terminated_year,
        'renewed_year': renewed_year,
        'issued_year': issued_year,
    })


@login_required
def bulk_issue_contract(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. System admin only.")
        return redirect('dashboard:home')

    from accounts.models import Department as _Dept
    employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')
    departments = _Dept.objects.order_by('name')
    today = date.today()

    if request.method == 'POST':
        emp_ids = request.POST.getlist('employees')
        contract_type = request.POST.get('contract_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        notes = request.POST.get('notes', '')
        internship_type = request.POST.get('internship_type', '') if contract_type == 'INTERN' else ''
        working_dept_id = request.POST.get('working_department', '') if contract_type in ('INTERN', 'WACS') else ''

        if not emp_ids:
            messages.error(request, "Please select at least one employee.")
            return render(request, 'contracts/bulk_issue_contract.html', {
                'employees': employees, 'departments': departments, 'today': today,
            })

        if not contract_type or not start_date:
            messages.error(request, "Contract type and start date are required.")
            return render(request, 'contracts/bulk_issue_contract.html', {
                'employees': employees, 'departments': departments, 'today': today,
            })

        parsed_start = _parse_date(start_date)
        if not parsed_start:
            messages.error(request, "Invalid start date.")
            return render(request, 'contracts/bulk_issue_contract.html', {
                'employees': employees, 'departments': departments, 'today': today,
            })

        parsed_end = None
        if end_date:
            parsed_end = _parse_date(end_date)

        if contract_type in ('CDD', 'INTERN', 'WACS') and not parsed_end:
            label = {'CDD': 'Fixed-Term (CDD)', 'INTERN': 'Internship', 'WACS': 'WACS Residency'}[contract_type]
            messages.error(request, f"End date is required for {label} contracts.")
            return render(request, 'contracts/bulk_issue_contract.html', {
                'employees': employees, 'departments': departments, 'today': today,
            })

        from notifications.utils import notify
        created_count = 0
        for emp_id in emp_ids:
            try:
                emp = Employee.objects.get(pk=emp_id)
            except Employee.DoesNotExist:
                continue

            existing = emp.contracts.filter(status='active').first()
            contract = Contract.objects.create(
                employee=emp,
                contract_type=contract_type,
                internship_type=internship_type,
                working_department_id=working_dept_id or None,
                start_date=parsed_start,
                end_date=parsed_end,
                notes=notes,
                status='active',
                created_by=request.user,
                renewed_from=existing,
            )
            if existing:
                existing.status = 'renewed'
                existing.save()

            _title, _msg = _contract_issue_message(contract)
            notify(
                emp.user,
                title=_title,
                message=_msg,
                notification_type='contract_issued',
                url=reverse('contracts:my_contract'),
            )
            created_count += 1

        messages.success(request, f"{created_count} contract{'s' if created_count != 1 else ''} issued successfully. All employees have been notified.")
        return redirect('contracts:list')

    return render(request, 'contracts/bulk_issue_contract.html', {
        'employees': employees,
        'departments': departments,
        'today': today,
    })


@login_required
def bulk_renew_contracts(request):
    """Bulk-renew expired (or expiring) fixed-term contracts by a chosen duration."""
    if not _can_manage_contracts(request.user):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    from dateutil.relativedelta import relativedelta
    from accounts.models import Department as _Dept

    DURATION_CHOICES = [
        ('1m',  '1 Month'),
        ('2m',  '2 Months'),
        ('3m',  '3 Months'),
        ('6m',  '6 Months'),
        ('1y',  '1 Year'),
        ('2y',  '2 Years'),
    ]

    def _apply_duration(dt, code):
        mapping = {
            '1m': relativedelta(months=1),
            '2m': relativedelta(months=2),
            '3m': relativedelta(months=3),
            '6m': relativedelta(months=6),
            '1y': relativedelta(years=1),
            '2y': relativedelta(years=2),
        }
        return dt + mapping[code]

    filter_type   = request.GET.get('type', '')
    filter_status = request.GET.get('status', 'expired')
    filter_dept   = request.GET.get('dept', '')
    filter_q      = request.GET.get('q', '').strip()

    from django.db.models import Q, Value
    from django.db.models.functions import Concat
    today = date.today()

    qs = Contract.objects.select_related(
        'employee', 'employee__user', 'employee__department'
    ).filter(contract_type__in=('CDD', 'INTERN', 'WACS')).annotate(
        emp_full_name=Concat('employee__user__first_name', Value(' '), 'employee__user__last_name')
    )

    if filter_type:
        qs = qs.filter(contract_type=filter_type)
    if filter_dept:
        qs = qs.filter(employee__department_id=filter_dept)
    if filter_q:
        qs = qs.filter(
            Q(emp_full_name__icontains=filter_q) |
            Q(employee__user__first_name__icontains=filter_q) |
            Q(employee__user__last_name__icontains=filter_q) |
            Q(employee__employee_id__icontains=filter_q)
        )

    # 'expired': DB-status='expired' OR (active but end_date already passed)
    if filter_status == 'expired':
        qs = qs.filter(
            Q(status='expired') |
            Q(status='active', end_date__lt=today)
        )
    elif filter_status == 'expiring':
        # Still active, end_date in the future
        qs = qs.filter(status='active', end_date__gte=today)
    else:
        # 'active' or anything else — show all active (not terminated/renewed)
        qs = qs.exclude(status__in=('terminated', 'renewed'))

    contracts = list(qs.order_by('end_date', 'employee__user__last_name'))
    all_departments = _Dept.objects.order_by('name')

    if request.method == 'POST':
        contract_ids = request.POST.getlist('contracts')
        duration_code = request.POST.get('duration', '1m')

        if not contract_ids:
            messages.error(request, "Please select at least one contract to renew.")
        elif duration_code not in dict(DURATION_CHOICES):
            messages.error(request, "Invalid duration selected.")
        else:
            from notifications.utils import notify
            renewed_count = 0
            for cid in contract_ids:
                try:
                    old_c = Contract.objects.get(pk=cid)
                except Contract.DoesNotExist:
                    continue
                if not old_c.end_date:
                    continue

                # New contract starts day after old end, ends old_end + duration
                new_start = old_c.end_date + relativedelta(days=1)
                new_end   = _apply_duration(old_c.end_date, duration_code)

                old_c.status = 'renewed'
                old_c.save()

                new_c = Contract.objects.create(
                    employee=old_c.employee,
                    contract_type=old_c.contract_type,
                    internship_type=old_c.internship_type,
                    working_department=old_c.working_department,
                    start_date=new_start,
                    end_date=new_end,
                    notes=old_c.notes,
                    status='active',
                    created_by=request.user,
                    renewed_from=old_c,
                )

                renewal_msg = _contract_renewal_message(new_c)
                ContractNotification.objects.create(
                    employee=old_c.employee,
                    contract=new_c,
                    notification_type='renewed',
                    message=renewal_msg,
                )
                notify(
                    old_c.employee.user,
                    title='Contract Extended',
                    message=renewal_msg,
                    notification_type='contract_renewed',
                    url=reverse('contracts:detail', kwargs={'pk': new_c.pk}),
                )
                try:
                    from dashboard.models import AuditLog
                    AuditLog.log(
                        request, AuditLog.ACTION_CONTRACT,
                        f"Bulk-renewed contract ({new_c.contract_type}) for {old_c.employee.get_full_name()} "
                        f"→ {new_c.start_date} to {new_c.end_date}",
                        target_user=old_c.employee.user,
                    )
                except Exception:
                    pass
                renewed_count += 1

            if renewed_count:
                messages.success(
                    request,
                    f"{renewed_count} contract{'s' if renewed_count != 1 else ''} renewed successfully. "
                    "All employees have been notified."
                )
                return redirect('contracts:list')

    return render(request, 'contracts/bulk_renew_contracts.html', {
        'contracts': contracts,
        'duration_choices': DURATION_CHOICES,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_dept': filter_dept,
        'filter_q': filter_q,
        'all_departments': all_departments,
        'today': today,
    })


@login_required
def delete_contract(request, pk):
    """Permanently delete a contract record — superuser only."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. System admin only.")
        return redirect('dashboard:home')

    contract = get_object_or_404(Contract, pk=pk)

    if request.method == 'POST':
        emp_name = contract.employee.get_full_name()
        ct_display = contract.get_contract_type_display()
        start = contract.start_date
        employee_pk = contract.employee.pk
        contract.delete()
        messages.success(request, f"Contract ({ct_display}, {start}) for {emp_name} has been permanently deleted.")
        try:
            from dashboard.models import AuditLog
            AuditLog.log(
                request, AuditLog.ACTION_CONTRACT,
                f"Permanently deleted contract ({ct_display}, {start}) for {emp_name}",
            )
        except Exception:
            pass
        return redirect('contracts:list')

    return redirect('contracts:detail', pk=pk)


@login_required
def contract_pdf(request, pk):
    """Download a contract as a PDF letter."""
    contract = get_object_or_404(Contract, pk=pk)
    emp = contract.employee

    # Only the employee themselves, HR, directors, CEO, or superuser can download
    try:
        requester = request.user.employee
        allowed = (
            requester == emp or
            requester.is_hr() or
            requester.is_director() or
            requester.is_ceo() or
            request.user.is_superuser
        )
    except Exception:
        allowed = request.user.is_superuser

    if not allowed:
        messages.error(request, "You do not have permission to download this contract.")
        return redirect('contracts:list')

    from .pdf_utils import generate_contract_pdf
    buf = generate_contract_pdf(contract)
    safe_name = emp.employee_id + "_contract.pdf"
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
    return response
