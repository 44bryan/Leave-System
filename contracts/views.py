from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from collections import defaultdict

from accounts.models import Employee, Department
from .models import Contract, ContractNotification


def _is_hr_or_above(user):
    """HR, superuser, or director — can VIEW contracts."""
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_director() or user.is_superuser
    except Exception:
        return user.is_superuser


def _can_manage_contracts(user):
    """Only HR and superuser can ISSUE / RENEW / TERMINATE contracts."""
    try:
        emp = user.employee
        return emp.is_hr() or user.is_superuser
    except Exception:
        return user.is_superuser


def _get_employee(request):
    try:
        return request.user.employee
    except Exception:
        return None


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

    unread_count = emp.contract_notifications.filter(is_read=False).count()
    notifications = emp.contract_notifications.all()[:10]

    seniority_ladder = [
        ("Probationary Period", 0,  "#6b7a8d"),
        ("Class 1",             1,  "#0284c7"),
        ("Class 2",             3,  "#0891b2"),
        ("Class 3",             5,  "#059669"),
        ("Class 4",             8,  "#d97706"),
        ("Senior Staff",        12, "#dc2626"),
        ("Senior Executive",    17, "#7c3aed"),
        ("Principal Executive", 22, "#4c1d95"),
    ]

    return render(request, 'contracts/my_contract.html', {
        'contract': contract,
        'employee': emp,
        'notifications': notifications,
        'unread_count': unread_count,
        'seniority_ladder': seniority_ladder,
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

    filter_type = request.GET.get('type', '')
    filter_status = request.GET.get('status', '')
    filter_expiring = request.GET.get('expiring', '')

    contracts = Contract.objects.select_related('employee', 'employee__user', 'employee__department').all()

    if filter_type:
        contracts = contracts.filter(contract_type=filter_type)
    if filter_status:
        contracts = contracts.filter(status=filter_status)

    # Convert to list so we can apply computed-property filters
    contracts = list(contracts)
    if filter_expiring == '30':
        contracts = [c for c in contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 30]
    elif filter_expiring == '60':
        contracts = [c for c in contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 60]

    # Summary counts
    all_contracts = Contract.objects.all()
    total = all_contracts.count()
    active_cdd = all_contracts.filter(contract_type='CDD', status='active').count()
    active_cdi = all_contracts.filter(contract_type='CDI', status='active').count()
    expiring_soon = [c for c in Contract.objects.filter(contract_type='CDD', status='active') if c.is_expiring_soon]

    return render(request, 'contracts/contract_list.html', {
        'contracts': contracts,
        'total': total,
        'active_cdd': active_cdd,
        'active_cdi': active_cdi,
        'expiring_soon_count': len(expiring_soon),
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_expiring': filter_expiring,
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

        if not emp_id or not contract_type or not start_date:
            messages.error(request, "Employee, contract type, and start date are required.")
            return render(request, 'contracts/issue_contract.html', {
                'employees': employees, 'today': today,
            })

        if contract_type == 'CDD' and not end_date:
            messages.error(request, "End date is required for CDD (fixed-term) contracts.")
            return render(request, 'contracts/issue_contract.html', {
                'employees': employees, 'today': today,
            })

        emp = get_object_or_404(Employee, pk=emp_id)

        # Mark any existing active contract as renewed (if this is a renewal)
        existing = emp.contracts.filter(status='active').first()

        contract = Contract.objects.create(
            employee=emp,
            contract_type=contract_type,
            start_date=start_date,
            end_date=end_date,
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
        notify(
            emp.user,
            title='Contract Issued',
            message=(
                f"A {contract.get_contract_type_display()} contract has been issued to you, "
                f"effective {contract.start_date.strftime('%d %b %Y')}."
                + (f" End date: {contract.end_date.strftime('%d %b %Y')}." if contract.end_date else " This is a permanent contract.")
                + " Please visit the HR Office to sign and collect your contract document."
            ),
            notification_type='contract_issued',
            url='/contracts/my-contract/',
        )

        messages.success(request, f"Contract issued for {emp.get_full_name()}.")
        return redirect('contracts:detail', pk=contract.pk)

    return render(request, 'contracts/issue_contract.html', {
        'employees': employees,
        'today': today,
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

        if contract_type == 'CDD' and not new_end:
            messages.error(request, "End date is required for CDD renewal.")
            return redirect('contracts:detail', pk=pk)

        # Mark old contract as renewed
        old_contract.status = 'renewed'
        old_contract.save()

        # Create new contract
        new_contract = Contract.objects.create(
            employee=old_contract.employee,
            contract_type=contract_type,
            start_date=new_start,
            end_date=new_end,
            notes=notes,
            status='active',
            created_by=request.user,
            renewed_from=old_contract,
        )

        # Notify employee (ContractNotification + main bell)
        renewal_msg = (
            f"Your contract has been renewed. "
            f"New contract type: {new_contract.get_contract_type_display()}. "
            f"Start date: {new_contract.start_date.strftime('%d %b %Y')}."
            + (f" End date: {new_contract.end_date.strftime('%d %b %Y')}." if new_contract.end_date else " This is a permanent contract (CDI).")
        )
        ContractNotification.objects.create(
            employee=old_contract.employee,
            contract=new_contract,
            notification_type='renewed',
            message=renewal_msg,
        )
        from notifications.utils import notify
        notify(
            old_contract.employee.user,
            title='Contract Renewed',
            message=renewal_msg,
            notification_type='contract_renewed',
            url=f'/contracts/{new_contract.pk}/',
        )

        messages.success(
            request,
            f"Contract renewed for {old_contract.employee.get_full_name()}. Employee has been notified."
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

        termination_msg = (
            f"Your contract has been terminated"
            + (f" for the following reason: {reason}" if reason else "")
            + ". Please contact HR for further information."
        )
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
            url=f'/contracts/{contract.pk}/',
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
    total_staff   = len(all_employees)

    # ── Expiry urgency buckets ────────────────────────────────────────────────
    expiring_30  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 0 < c.days_remaining <= 30], key=lambda c: c.days_remaining)
    expiring_60  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 30 < c.days_remaining <= 60], key=lambda c: c.days_remaining)
    expiring_90  = sorted([c for c in all_contracts if c.contract_type == 'CDD' and c.days_remaining is not None and 60 < c.days_remaining <= 90], key=lambda c: c.days_remaining)
    already_expired = Contract.objects.filter(
        contract_type='CDD', status='active', end_date__lt=today
    ).select_related('employee', 'employee__user', 'employee__department').order_by('end_date')

    # ── Seniority distribution ────────────────────────────────────────────────
    seniority_buckets = [
        ("Probationary Period", 0,  1,  "#6b7a8d"),
        ("Class 1",             1,  3,  "#0284c7"),
        ("Class 2",             3,  5,  "#0891b2"),
        ("Class 3",             5,  8,  "#059669"),
        ("Class 4",             8,  12, "#d97706"),
        ("Senior Staff",        12, 17, "#dc2626"),
        ("Senior Executive",    17, 22, "#7c3aed"),
        ("Principal Executive", 22, 999,"#4c1d95"),
    ]
    seniority_dist = []
    for label, min_yr, max_yr, color in seniority_buckets:
        count = sum(1 for c in all_contracts if min_yr <= c.years_of_service < max_yr)
        seniority_dist.append({
            'label': label, 'count': count, 'color': color,
            'pct': round((count / total_active * 100) if total_active else 0),
            'min_yr': min_yr,
        })

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
    dept_map = defaultdict(lambda: {'CDI': 0, 'CDD': 0, 'total': 0})
    for c in all_contracts:
        dept_name = str(c.employee.department) if c.employee.department else 'No Department'
        dept_map[dept_name][c.contract_type] += 1
        dept_map[dept_name]['total'] += 1
    dept_breakdown = sorted(
        [{'dept': k, **v} for k, v in dept_map.items()],
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
        'expiring_30': expiring_30,
        'expiring_60': expiring_60,
        'expiring_90': expiring_90,
        'already_expired': already_expired,
        'seniority_dist': seniority_dist,
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
