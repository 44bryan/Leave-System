
# ── Discipline Analytics Dashboard ───────────────────────────────────────────
@login_required
def discipline_analytics(request):
    import json
    from datetime import date
    from django.db.models import Count
    from discipline.models import DisciplineRecord
    from accounts.models import Department

    emp = request.user.employee
    if not (emp.is_hr() or emp.is_ceo() or request.user.is_superuser or emp.role == 'admin_director'):
        from django.contrib import messages as _msg
        _msg.error(request, "Access denied.")
        return redirect('dashboard:home')

    year    = int(request.GET.get('year', date.today().year))
    dept_pk = request.GET.get('dept', '')

    base_qs = DisciplineRecord.objects.filter(is_proposal=False, date_issued__year=year)
    if dept_pk:
        base_qs = base_qs.filter(employee__department__pk=dept_pk)

    # By action type
    by_type  = base_qs.values('action_type').annotate(count=Count('id')).order_by('-count')
    type_map = dict(DisciplineRecord.ACTION_CHOICES)
    type_labels = [type_map.get(r['action_type'], r['action_type']) for r in by_type]
    type_data   = [r['count'] for r in by_type]

    # Monthly trend
    monthly   = base_qs.values('date_issued__month').annotate(count=Count('id')).order_by('date_issued__month')
    mmap      = {r['date_issued__month']: r['count'] for r in monthly}
    mlabels   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    mdata     = [mmap.get(i, 0) for i in range(1, 13)]

    # By department
    by_dept     = base_qs.values('employee__department__name').annotate(count=Count('id')).order_by('-count')
    dept_labels = [r['employee__department__name'] or 'No Dept' for r in by_dept]
    dept_data   = [r['count'] for r in by_dept]

    # Top 5 employees
    top = (
        base_qs.values('employee__user__first_name', 'employee__user__last_name')
        .annotate(count=Count('id')).order_by('-count')[:5]
    )
    top_labels = [r['employee__user__first_name'] + ' ' + r['employee__user__last_name'] for r in top]
    top_data   = [r['count'] for r in top]

    # Severity counts
    sev = {r['action_type']: r['count'] for r in base_qs.values('action_type').annotate(count=Count('id'))}

    departments     = Department.objects.all().order_by('name')
    available_years = list(range(date.today().year, date.today().year - 5, -1))

    return render(request, 'dashboard/discipline_analytics.html', {
        'year': year, 'dept_pk': dept_pk,
        'departments': departments, 'available_years': available_years,
        'total':      base_qs.count(),
        'verbal':     sev.get('verbal_warning', 0),
        'caution':    sev.get('written_caution', 0),
        'final':      sev.get('final_warning', 0),
        'suspension': sev.get('suspension', 0),
        'dismissal':  sev.get('dismissal', 0),
        'system_count': base_qs.filter(is_system_generated=True).count(),
        'human_count':  base_qs.filter(is_system_generated=False).count(),
        'type_labels_json':    json.dumps(type_labels),
        'type_data_json':      json.dumps(type_data),
        'month_labels_json':   json.dumps(mlabels),
        'month_data_json':     json.dumps(mdata),
        'dept_labels_json':    json.dumps(dept_labels),
        'dept_data_json':      json.dumps(dept_data),
        'top_emp_labels_json': json.dumps(top_labels),
        'top_emp_data_json':   json.dumps(top_data),
    })


# ── Payroll Analytics Dashboard ───────────────────────────────────────────────
@login_required
def payroll_analytics(request):
    import json
    from datetime import date
    from django.db.models import Count
    from payroll.models import Payslip
    from accounts.models import Employee, Department

    emp = request.user.employee
    if not (emp.is_hr() or emp.is_ceo() or request.user.is_superuser):
        from django.contrib import messages as _msg
        _msg.error(request, "Access denied.")
        return redirect('dashboard:home')

    year      = int(request.GET.get('year', date.today().year))
    sel_month = int(request.GET.get('month', date.today().month))
    dept_pk   = request.GET.get('dept', '')

    active_qs = Employee.objects.filter(is_active=True)
    if dept_pk:
        active_qs = active_qs.filter(department__pk=dept_pk)
    total_active = active_qs.count()

    # Monthly coverage
    monthly_qs = Payslip.objects.filter(period_year=year).values('period_month').annotate(count=Count('id')).order_by('period_month')
    mmap        = {r['period_month']: r['count'] for r in monthly_qs}
    mlabels     = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    mdata       = [mmap.get(i, 0) for i in range(1, 13)]
    cov_pct     = [round(mmap.get(i, 0) / total_active * 100, 1) if total_active else 0 for i in range(1, 13)]

    # Dept coverage for selected month
    depts = Department.objects.all().order_by('name')
    dept_coverage = []
    for d in depts:
        ec = Employee.objects.filter(is_active=True, department=d).count()
        sc = Payslip.objects.filter(period_year=year, period_month=sel_month, employee__department=d, employee__is_active=True).count()
        dept_coverage.append({'dept': d.name, 'emp': ec, 'slips': sc, 'pct': round(sc / ec * 100, 1) if ec else 0})

    dcov_labels = [d['dept'] for d in dept_coverage]
    dcov_data   = [d['pct']  for d in dept_coverage]

    # Missing employees
    have_ids   = Payslip.objects.filter(period_year=year, period_month=sel_month).values_list('employee_id', flat=True)
    missing_qs = active_qs.exclude(pk__in=have_ids).select_related('user', 'department')

    month_slips   = Payslip.objects.filter(period_year=year, period_month=sel_month).count()
    sel_cov_pct   = round(month_slips / total_active * 100, 1) if total_active else 0
    month_name_map = {i: n for i, n in enumerate(mlabels, 1)}

    available_years = list(range(date.today().year, date.today().year - 5, -1))

    return render(request, 'dashboard/payroll_analytics.html', {
        'year': year, 'sel_month': sel_month,
        'sel_month_name': month_name_map.get(sel_month, ''),
        'dept_pk': dept_pk, 'departments': depts,
        'available_years': available_years,
        'month_choices': list(enumerate(mlabels, 1)),
        'total_active': total_active,
        'month_slips': month_slips,
        'month_coverage_pct': sel_cov_pct,
        'missing_count': missing_qs.count(),
        'missing_employees': missing_qs[:50],
        'dept_coverage': dept_coverage,
        'month_labels_json':    json.dumps(mlabels),
        'month_data_json':      json.dumps(mdata),
        'coverage_pct_json':    json.dumps(cov_pct),
        'dept_cov_labels_json': json.dumps(dcov_labels),
        'dept_cov_data_json':   json.dumps(dcov_data),
    })
