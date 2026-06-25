from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.models import Employee
from .models import AppraisalCycle, AppraisalRecord
from notifications.utils import notify


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


def _admin_director_on_leave():
    """Return True if ALL active admin directors have an active approved leave today."""
    from django.utils.timezone import now as _now
    today = _now().date()
    admin_directors = Employee.objects.filter(role='admin_director', is_active=True)
    if not admin_directors.exists():
        return True  # no admin director at all → fall back to finance director
    try:
        from leaves.models import LeaveRequest
        for emp in admin_directors:
            on_leave = LeaveRequest.objects.filter(
                employee=emp,
                status='approved',
                start_date__lte=today,
                end_date__gte=today,
            ).exists()
            if not on_leave:
                return False  # at least one admin director is available
    except Exception:
        return False
    return True  # all admin directors are on leave


def _notify_director(record):
    """Notify the correct director (admin director, or finance director if admin is on leave)."""
    if _admin_director_on_leave():
        recipients = Employee.objects.filter(role='finance_director', is_active=True)
        role_label = 'Finance Director'
    else:
        recipients = Employee.objects.filter(role='admin_director', is_active=True)
        role_label = 'Admin Director'
    for dir_emp in recipients:
        notify(
            dir_emp.user,
            f'Appraisal {role_label} Review — {record.employee.get_full_name()}',
            f'HR has reviewed the appraisal for {record.employee.get_full_name()}. Your comment is next.',
            notification_type='general',
            url=f'/appraisals/director/{record.pk}/',
        )


def _save_sig(record, field_name, b64_data):
    """Store a base64 signature on the record field."""
    if b64_data and b64_data.startswith('data:image/'):
        setattr(record, field_name, b64_data)


# ── HR: Initiate a new cycle ──────────────────────────────────────────────────

@login_required
def hr_initiate(request):
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    cycles = AppraisalCycle.objects.all()

    if request.method == 'POST':
        year      = request.POST.get('year', '').strip()
        trimester = request.POST.get('trimester', '').strip()
        title     = request.POST.get('title', '').strip()
        deadline_raw = request.POST.get('employee_deadline', '').strip()

        try:
            year      = int(year)
            trimester = int(trimester)
            if trimester not in (1, 2, 3):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Invalid year or trimester.")
            return redirect('appraisals:hr_initiate')

        if AppraisalCycle.objects.filter(year=year, trimester=trimester).exists():
            messages.error(request, "A cycle for that trimester/year already exists.")
            return redirect('appraisals:hr_initiate')

        from datetime import date as _date
        employee_deadline = None
        if deadline_raw:
            try:
                employee_deadline = _date.fromisoformat(deadline_raw)
            except ValueError:
                messages.error(request, "Invalid deadline date format.")
                return redirect('appraisals:hr_initiate')

        cycle = AppraisalCycle.objects.create(
            year=year, trimester=trimester,
            title=title or f"Trim {trimester} — {year}",
            initiated_by=request.user,
            employee_deadline=employee_deadline,
        )

        # Create one AppraisalRecord per active, non-superuser permanent/CDD staff
        # Interns and WACS residents are excluded from appraisals
        employees = Employee.objects.filter(
            is_active=True
        ).exclude(
            role__in=('intern', 'wacs_resident')
        ).select_related('user')
        created = 0
        for e in employees:
            if e.user.is_superuser:
                continue
            AppraisalRecord.objects.get_or_create(cycle=cycle, employee=e)
            notify(
                e.user,
                f'New Appraisal — {cycle}',
                f'Your appraisal form for {cycle} is now available. Please log in and complete your section.',
                notification_type='general',
                url=f'/appraisals/my/',
            )
            created += 1

        messages.success(request, f"Appraisal cycle '{cycle}' initiated for {created} employees.")
        return redirect('appraisals:hr_dashboard')

    from datetime import date
    return render(request, 'appraisals/hr_initiate.html', {
        'cycles': cycles,
        'current_year': date.today().year,
    })


@login_required
def hr_dashboard(request):
    emp = get_employee(request)
    is_privileged = (
        request.user.is_superuser or
        (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo()))
    )
    if not is_privileged:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    cycles = AppraisalCycle.objects.prefetch_related('records')
    return render(request, 'appraisals/hr_dashboard.html', {'cycles': cycles})


@login_required
def cycle_records(request, cycle_pk):
    emp = get_employee(request)
    is_privileged = (
        request.user.is_superuser or
        (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo()))
    )
    if not is_privileged:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    cycle   = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    records = cycle.records.select_related('employee__user', 'employee__department')
    is_ceo_view = request.GET.get('view') == 'ceo' or (emp and emp.is_ceo())
    return render(request, 'appraisals/cycle_records.html', {
        'cycle': cycle, 'records': records, 'is_ceo_view': is_ceo_view,
    })


@login_required
def hr_unlock_employee(request, record_pk):
    """HR opens an employee's overdue appraisal section so they can still submit."""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    record = get_object_or_404(AppraisalRecord, pk=record_pk)
    if record.status != AppraisalRecord.STATUS_EMPLOYEE:
        messages.error(request, "This appraisal is not awaiting the employee — nothing to unlock.")
        return redirect('appraisals:hr_deadline_missed')

    if request.method == 'POST':
        note = request.POST.get('note', '').strip()
        record.hr_unlocked    = True
        record.hr_unlock_note = note
        record.hr_unlocked_at = timezone.now()
        record.hr_unlocked_by = emp
        record.save(update_fields=['hr_unlocked', 'hr_unlock_note', 'hr_unlocked_at', 'hr_unlocked_by'])

        notify(
            record.employee.user,
            f'Appraisal Re-opened — {record.cycle}',
            f'HR has re-opened your appraisal for {record.cycle}. '
            f'Please log in immediately and complete your section.',
            notification_type='general',
            url='/appraisals/my/',
        )
        messages.success(request, f"Appraisal re-opened for {record.employee.get_full_name()}. They have been notified.")
        return redirect('appraisals:hr_deadline_missed')

    return render(request, 'appraisals/hr_unlock_confirm.html', {'record': record})


@login_required
def hr_deadline_missed(request):
    """HR view listing all employees who missed the deadline and haven't submitted."""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    from datetime import date
    today = date.today()

    # Records still at employee stage with a passed deadline
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_EMPLOYEE,
        cycle__employee_deadline__lt=today,
    ).select_related('employee__user', 'employee__department', 'cycle').order_by(
        'cycle__year', 'cycle__trimester', 'employee__user__last_name'
    )

    warnings_sent = request.session.pop('warnings_sent', None)
    return render(request, 'appraisals/hr_deadline_missed.html', {
        'records': records,
        'today': today,
        'warnings_sent': warnings_sent,
    })


@login_required
def send_appraisal_warnings_now(request):
    """HR triggers the appraisal warning letters immediately from the dashboard."""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if request.method != 'POST':
        return redirect('appraisals:hr_deadline_missed')

    from datetime import date
    from notifications.utils import notify as _notify

    today = date.today()
    missed = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_EMPLOYEE,
        hr_unlocked=False,
        warning_sent=False,
        cycle__employee_deadline__lt=today,
        cycle__is_distributed=False,
    ).select_related('employee__user', 'cycle')

    count = 0
    for record in missed:
        e = record.employee
        cycle = record.cycle
        deadline_str = cycle.employee_deadline.strftime('%d %B %Y')
        _notify(
            e.user,
            'Appraisal Deadline Missed — Please Report to HR',
            (
                f'Dear {e.user.first_name},\n\n'
                f'You did not complete your self-assessment for the appraisal cycle '
                f'"{cycle}" before the deadline of {deadline_str}.\n\n'
                f'Your appraisal section has been locked. You are required to report '
                f'to the HR Office as soon as possible to address this matter.\n\n'
                f'This is an automated notice. Please do not ignore it.'
            ),
            notification_type='appraisal_warning',
            url='/appraisals/my/',
        )
        record.warning_sent = True
        record.save(update_fields=['warning_sent'])
        count += 1

    if count:
        messages.success(request, f"Warning letters sent to {count} employee(s).")
    else:
        messages.info(request, "No pending warnings to send — all eligible employees already notified.")
    return redirect('appraisals:hr_deadline_missed')


@login_required
def distribute(request, cycle_pk):
    """HR marks cycle as distributed — staff can now see their completed form."""
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    cycle = get_object_or_404(AppraisalCycle, pk=cycle_pk)
    if request.method == 'POST':
        # Auto-complete any records still at STATUS_CEO (CEO review is optional)
        cycle.records.filter(
            status=AppraisalRecord.STATUS_CEO
        ).update(status=AppraisalRecord.STATUS_DONE)

        cycle.is_distributed = True
        cycle.distributed_at = timezone.now()
        cycle.save()

        # Notify all employees in this cycle
        for record in cycle.records.select_related('employee__user'):
            notify(
                record.employee.user,
                f'Appraisal Results Available — {cycle}',
                f'Your appraisal results for {cycle} have been released by HR. You can now view your completed form.',
                notification_type='general',
                url=f'/appraisals/my/',
            )
        messages.success(request, f"Appraisal cycle '{cycle}' results distributed to all staff.")
    return redirect('appraisals:hr_dashboard')


# ── Employee: My Appraisals ───────────────────────────────────────────────────

@login_required
def my_appraisals(request):
    emp = get_employee(request)
    if not emp:
        messages.error(request, "No employee profile found.")
        return redirect('dashboard:home')

    from datetime import date as _date
    today = _date.today()

    # Active = cycle not yet distributed and record awaiting employee action
    all_pending = AppraisalRecord.objects.filter(
        employee=emp,
        status=AppraisalRecord.STATUS_EMPLOYEE,
        cycle__is_distributed=False,
    ).select_related('cycle')

    active_records = []
    overdue_records = []
    for r in all_pending:
        dl = r.cycle.employee_deadline
        if dl and today > dl and not r.hr_unlocked:
            overdue_records.append(r)
        else:
            active_records.append(r)

    history = AppraisalRecord.objects.filter(
        employee=emp,
        cycle__is_distributed=True,
    ).select_related('cycle').order_by('-cycle__year', '-cycle__trimester')

    return render(request, 'appraisals/my_appraisals.html', {
        'active_records': active_records,
        'overdue_records': overdue_records,
        'history': history,
    })


@login_required
def employee_fill(request, record_pk):
    """Employee fills their section of the appraisal."""
    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    if record.employee != emp:
        messages.error(request, "Access denied.")
        return redirect('appraisals:my_appraisals')
    _editable_by_employee = {
        AppraisalRecord.STATUS_EMPLOYEE,
    }
    if record.status not in _editable_by_employee:
        messages.error(request, "You can no longer edit this appraisal.")
        return redirect('appraisals:my_appraisals')

    # Deadline enforcement — block if deadline passed and HR hasn't unlocked this record
    from datetime import date as _date
    deadline = record.cycle.employee_deadline
    if deadline and _date.today() > deadline and not record.hr_unlocked:
        return render(request, 'appraisals/deadline_passed.html', {
            'record': record,
            'deadline': deadline,
        })

    if request.method == 'POST':
        p = request.POST
        is_initial_submit = record.status == AppraisalRecord.STATUS_EMPLOYEE

        record.tasks_summary          = p.get('tasks_summary', '').strip()
        record.tasks_assimilated      = p.get('tasks_assimilated', '').strip()
        record.pf_quality_of_work     = _int_or_none(p.get('pf_quality_of_work'))
        record.pf_quantity_of_work    = _int_or_none(p.get('pf_quantity_of_work'))
        record.pf_knowledge_techniques= _int_or_none(p.get('pf_knowledge_techniques'))
        record.pf_ability_to_learn    = _int_or_none(p.get('pf_ability_to_learn'))
        record.aa_motivation          = _int_or_none(p.get('aa_motivation'))
        record.aa_attitude_colleagues = _int_or_none(p.get('aa_attitude_colleagues'))
        record.aa_relations_patients  = _int_or_none(p.get('aa_relations_patients'))
        record.aa_judgment_team       = _int_or_none(p.get('aa_judgment_team'))
        record.aa_punctuality         = _int_or_none(p.get('aa_punctuality'))
        record.aa_presentation        = _int_or_none(p.get('aa_presentation'))
        record.goals_to_reach         = p.get('goals_to_reach', '').strip()
        record.comment_on_self        = p.get('comment_on_self', '').strip()
        record.comment_on_supervision = p.get('comment_on_supervision', '').strip()
        record.comment_on_org         = p.get('comment_on_org', '').strip()
        _save_sig(record, 'employee_sig_b64', p.get('signature_data', ''))
        sig_b64 = p.get('signature_data', '')
        if sig_b64 and sig_b64.startswith('data:image/'):
            emp.signature_b64 = sig_b64
            emp.save(update_fields=['signature_b64'])

        if is_initial_submit:
            record.employee_signed_at = timezone.now()
            # First reviewer: unit_head if set, otherwise supervisor (they fill comment step first)
            first_reviewer = emp.unit_head or emp.supervisor
            if first_reviewer:
                record.status = AppraisalRecord.STATUS_UNIT_HEAD
                record.save()
                notify(
                    first_reviewer.user,
                    f'Appraisal Comment Needed — {emp.get_full_name()}',
                    f'{emp.get_full_name()} has submitted their appraisal for {record.cycle}. '
                    f'Please log in to add your comment.',
                    notification_type='general',
                    url=f'/appraisals/unit-head/{record.pk}/',
                )
            else:
                # No reviewer at all — go straight to HR
                record.status = AppraisalRecord.STATUS_HR
                record.save()
                for hr_emp in Employee.objects.filter(role='hr', is_active=True):
                    notify(
                        hr_emp.user,
                        f'Appraisal HR Review Needed — {emp.get_full_name()}',
                        f'{emp.get_full_name()} has submitted their appraisal for {record.cycle}.',
                        notification_type='general',
                        url=f'/appraisals/hr-review/{record.pk}/',
                    )
            messages.success(request, "Your appraisal section has been submitted.")
        else:
            record.save()
            messages.success(request, "Your appraisal has been updated.")
        return redirect('appraisals:my_appraisals')

    discipline_data = record.discipline_deductions()
    pf_fields = [
        ('pf_quality_of_work',      'Quality of Work'),
        ('pf_quantity_of_work',     'Quantity of Work'),
        ('pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('pf_ability_to_learn',     'Ability / Interest to Learn'),
    ]
    aa_fields = [
        ('aa_motivation',          'Motivation and Initiative'),
        ('aa_attitude_colleagues', 'Attitude towards Colleagues and Authority'),
        ('aa_relations_patients',  'Relations with Patients and Visitors'),
        ('aa_judgment_team',       'Judgment, Team Spirit and Discretion'),
        ('aa_punctuality',         'Punctuality, Attendance, Availability and Honesty'),
        ('aa_presentation',        'Personal Presentation and Professional Secrets'),
    ]
    discipline_labels = [
        ('verbal_warning',  'Verbal Warning'),
        ('written_caution', 'Request for Written Explanation / Written Caution'),
        ('final_warning',   'Written Warning / Final Warning'),
        ('suspension',      'Written Reprimand / Suspension'),
        ('dismissal',       'Dismissal'),
    ]
    current_values = {f: getattr(record, f) for f, _ in pf_fields + aa_fields}
    chain_steps = _build_chain_steps(record)
    return render(request, 'appraisals/employee_fill.html', {
        'record': record,
        'discipline_data': discipline_data,
        'discipline_labels': discipline_labels,
        'pf_fields': pf_fields,
        'aa_fields': aa_fields,
        'current_values': current_values,
        'chain_steps': chain_steps,
        'current_sig_b64': emp.signature_b64 or '',
    })


def _int_or_none(val):
    try:
        v = int(val)
        return v if 1 <= v <= 5 else None
    except (TypeError, ValueError):
        return None


def _build_chain_steps(record):
    """Build the signing-chain sidebar dynamically based on the employee's setup."""
    emp = record.employee
    has_unit_head  = bool(emp.unit_head_id)
    has_supervisor = bool(emp.supervisor_id)
    status = record.status

    done_employee  = status not in (AppraisalRecord.STATUS_EMPLOYEE,)
    done_unit_head = status in (
        AppraisalRecord.STATUS_MANAGER, AppraisalRecord.STATUS_HR,
        AppraisalRecord.STATUS_DIRECTOR, AppraisalRecord.STATUS_CEO, AppraisalRecord.STATUS_DONE,
    )
    done_manager   = status in (
        AppraisalRecord.STATUS_HR, AppraisalRecord.STATUS_DIRECTOR,
        AppraisalRecord.STATUS_CEO, AppraisalRecord.STATUS_DONE,
    )
    done_hr        = status in (
        AppraisalRecord.STATUS_DIRECTOR, AppraisalRecord.STATUS_CEO, AppraisalRecord.STATUS_DONE,
    )
    done_director  = status in (AppraisalRecord.STATUS_CEO, AppraisalRecord.STATUS_DONE)
    done_ceo       = status == AppraisalRecord.STATUS_DONE

    steps = [('employee', 'You (Employee)', done_employee)]

    if has_unit_head and has_supervisor:
        # Separate people for each role
        steps.append(('unit_head', f'Unit Head (Comment) — {emp.unit_head.get_full_name()}', done_unit_head))
        steps.append(('manager',   f'Line Manager (Grade & Comment) — {emp.supervisor.get_full_name()}', done_manager))
    elif has_supervisor:
        # Supervisor fills both: comment step first, then grade + comment step
        sv_name = emp.supervisor.get_full_name()
        steps.append(('unit_head', f'Supervisor (Comment) — {sv_name}', done_unit_head))
        steps.append(('manager',   f'Supervisor (Grade & Comment) — {sv_name}', done_manager))
    elif has_unit_head:
        steps.append(('unit_head', f'Unit Head (Comment) — {emp.unit_head.get_full_name()}', done_unit_head))

    steps += [
        ('hr',       'HR Manager',     done_hr),
        ('director', 'Admin Director', done_director),
        ('ceo',      'CEO',            done_ceo),
    ]
    return steps


_RATING_FNAMES = [
    'pf_quality_of_work', 'pf_quantity_of_work',
    'pf_knowledge_techniques', 'pf_ability_to_learn',
    'aa_motivation', 'aa_attitude_colleagues', 'aa_relations_patients',
    'aa_judgment_team', 'aa_punctuality', 'aa_presentation',
]


def _apply_score_override(post, record, by_emp, role='hr'):
    """Store score overrides only when values actually differ from the supervisor's scores.
    Saves a per-role snapshot of which fields changed and to what value.
    Notifies the line manager whenever their scores are adjusted."""
    snapshot = {}
    for fname in _RATING_FNAMES:
        v = _int_or_none(post.get(f'override_{fname}'))
        if v is None:
            continue
        if v != getattr(record, f'mgr_{fname}'):
            setattr(record, f'override_{fname}', v)
            snapshot[fname] = v
    if snapshot:
        now = timezone.now()
        record.score_override_by = by_emp
        record.score_override_at = now
        if role == 'hr':
            record.score_modified_by_hr = by_emp
            record.score_modified_at_hr = now
            record.hr_score_changes = snapshot
        elif role == 'director':
            record.score_modified_by_director = by_emp
            record.score_modified_at_director = now
            record.director_score_changes = snapshot
        elif role == 'ceo':
            record.score_modified_by_ceo = by_emp
            record.score_modified_at_ceo = now
            record.ceo_score_changes = snapshot

        # Notify the line manager that their grading was adjusted
        role_labels = {'hr': 'HR', 'director': 'Admin Director', 'ceo': 'CEO'}
        role_label = role_labels.get(role, role.upper())
        supervisor = record.employee.supervisor
        if supervisor:
            notify(
                supervisor.user,
                f'Appraisal Score Adjusted — {record.employee.get_full_name()}',
                f'{role_label} has adjusted {len(snapshot)} score(s) on '
                f'{record.employee.get_full_name()}\'s appraisal ({record.cycle}). '
                f'You can view the changes in the appraisal detail.',
                notification_type='general',
                url=f'/appraisals/detail/{record.pk}/',
            )


_IND_SCORE_FNAMES = [
    'pf_quality_of_work', 'pf_quantity_of_work',
    'pf_knowledge_techniques', 'pf_ability_to_learn',
    'aa_motivation', 'aa_attitude_colleagues', 'aa_relations_patients',
    'aa_judgment_team', 'aa_punctuality', 'aa_presentation',
]


def _save_independent_scores(post, record, prefix):
    """Save independent scores for a reviewer level (hr_ind, dir_ind, ceo_ind)."""
    for fname in _IND_SCORE_FNAMES:
        v = _int_or_none(post.get(f'ind_{fname}'))
        setattr(record, f'{prefix}_{fname}', v)


def _check_flag_ceo(record, stage_total, stage_label):
    """Flag record for CEO priority review if stage total is <12 or >18, and notify CEO."""
    if stage_total is None:
        return
    if stage_total <= 12 or stage_total >= 17:
        record.is_flagged_for_ceo = True
        record.save(update_fields=['is_flagged_for_ceo'])
        direction = 'low' if stage_total <= 12 else 'high'
        for ceo_emp in Employee.objects.filter(role='ceo', is_active=True):
            notify(
                ceo_emp.user,
                f'Appraisal Flagged for Review — {record.employee.get_full_name()}',
                f'{record.employee.get_full_name()}\'s appraisal ({record.cycle}) has been flagged for CEO review '
                f'due to a {direction} score of {stage_total:.1f} at the {stage_label} stage.',
                notification_type='warning',
                url=f'/appraisals/ceo-dashboard/',
            )


def _score_form_ctx(record):
    """Context for the optional override rating form in HR/Director/CEO templates."""
    pf_fields = [
        ('pf_quality_of_work',      'Quality of Work'),
        ('pf_quantity_of_work',     'Quantity of Work'),
        ('pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('pf_ability_to_learn',     'Ability / Interest to Learn'),
    ]
    aa_fields = [
        ('aa_motivation',          'Motivation and Initiative'),
        ('aa_attitude_colleagues', 'Attitude towards Colleagues and Authority'),
        ('aa_relations_patients',  'Relations with Patients and Visitors'),
        ('aa_judgment_team',       'Judgment, Team Spirit and Discretion'),
        ('aa_punctuality',         'Punctuality, Attendance, Availability and Honesty'),
        ('aa_presentation',        'Personal Presentation and Professional Secrets'),
    ]
    # Current values: show override if already set, else supervisor's original
    current_values = {
        f: getattr(record, f'override_{f}') or getattr(record, f'mgr_{f}')
        for f, _ in pf_fields + aa_fields
    }
    return {
        'pf_fields': pf_fields,
        'aa_fields': aa_fields,
        'current_values': current_values,
    }


# ── Co-Worker ────────────────────────────────────────────────────────────────

@login_required
def coworker_fill(request, record_pk):
    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    # Must be the specifically chosen co-worker
    if not emp or emp == record.employee:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    _coworker_editable = {AppraisalRecord.STATUS_COWORKER, AppraisalRecord.STATUS_UNIT_HEAD}
    if record.status not in _coworker_editable:
        messages.error(request, "This appraisal is not awaiting a co-worker comment.")
        return redirect('dashboard:home')
    if record.coworker_signed_by and record.coworker_signed_by != emp:
        messages.error(request, "You were not selected as the co-worker for this appraisal.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        is_initial_coworker_submit = record.status == AppraisalRecord.STATUS_COWORKER
        record.coworker_comment   = request.POST.get('coworker_comment', '').strip()
        record.coworker_signed_by = emp
        record.coworker_signed_at = timezone.now()
        _save_sig(record, 'coworker_sig_b64', request.POST.get('signature_data', ''))
        if is_initial_coworker_submit:
            record.status = AppraisalRecord.STATUS_UNIT_HEAD
        record.save()

        if is_initial_coworker_submit:
            target = record.employee.supervisor
            if target:
                notify(
                    target.user,
                    f'Appraisal Review Needed — {record.employee.get_full_name()}',
                    f'Co-worker comment added. Please add your supervisor comment for {record.employee.get_full_name()}.',
                    notification_type='general',
                    url=f'/appraisals/unit-head/{record.pk}/',
                )
            messages.success(request, "Co-worker comment submitted.")
        else:
            messages.success(request, "Co-worker comment updated.")
        return redirect('dashboard:home')

    return render(request, 'appraisals/coworker_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
    })


# ── Unit Head / Supervisor ────────────────────────────────────────────────────

@login_required
def unit_head_fill(request, record_pk):
    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    subj = record.employee
    # Unit head fills this step if set; otherwise the supervisor fills it (comment role)
    expected = subj.unit_head if subj.unit_head_id else subj.supervisor
    if not emp or emp != expected:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if record.status != AppraisalRecord.STATUS_UNIT_HEAD:
        messages.error(request, "This appraisal is not awaiting your review.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        p = request.POST
        # Unit head fills comment only — grading is done by the line manager
        record.unit_head_comment   = p.get('unit_head_comment', '').strip()
        record.unit_head_signed_by = emp
        record.unit_head_signed_at = timezone.now()
        _save_sig(record, 'unit_head_sig_b64', p.get('signature_data', ''))
        # After unit head comment → always go to line manager (supervisor) for grading
        record.status = AppraisalRecord.STATUS_MANAGER
        record.save()
        if subj.supervisor_id:
            notify(
                subj.supervisor.user,
                f'Appraisal Grading Needed — {subj.get_full_name()}',
                f'Unit Head has commented on {subj.get_full_name()}\'s appraisal ({record.cycle}). '
                f'Please log in to grade and add your line manager comment.',
                notification_type='general',
                url=f'/appraisals/manager/{record.pk}/',
            )
        messages.success(request, "Unit head comment submitted. Line manager notified.")
        return redirect('dashboard:home')

    return render(request, 'appraisals/unit_head_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
    })


# ── Line Manager ─────────────────────────────────────────────────────────────

@login_required
def manager_fill(request, record_pk):
    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    if not emp or emp != record.employee.supervisor:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    if record.status != AppraisalRecord.STATUS_MANAGER:
        messages.error(request, "This appraisal is not awaiting your review.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        p = request.POST
        record.mgr_pf_quality_of_work      = _int_or_none(p.get('mgr_pf_quality_of_work'))
        record.mgr_pf_quantity_of_work     = _int_or_none(p.get('mgr_pf_quantity_of_work'))
        record.mgr_pf_knowledge_techniques = _int_or_none(p.get('mgr_pf_knowledge_techniques'))
        record.mgr_pf_ability_to_learn     = _int_or_none(p.get('mgr_pf_ability_to_learn'))
        record.mgr_aa_motivation           = _int_or_none(p.get('mgr_aa_motivation'))
        record.mgr_aa_attitude_colleagues  = _int_or_none(p.get('mgr_aa_attitude_colleagues'))
        record.mgr_aa_relations_patients   = _int_or_none(p.get('mgr_aa_relations_patients'))
        record.mgr_aa_judgment_team        = _int_or_none(p.get('mgr_aa_judgment_team'))
        record.mgr_aa_punctuality          = _int_or_none(p.get('mgr_aa_punctuality'))
        record.mgr_aa_presentation         = _int_or_none(p.get('mgr_aa_presentation'))
        try:
            record.award_bonus_points = max(0, int(p.get('award_bonus_points', 0) or 0))
        except (ValueError, TypeError):
            pass
        record.award_employee_of_month = p.get('award_employee_of_month') == 'yes'
        record.award_other             = p.get('award_other', '').strip()
        record.manager_comment   = p.get('manager_comment', '').strip()
        record.manager_signed_by = emp
        record.manager_signed_at = timezone.now()
        _save_sig(record, 'manager_sig_b64', p.get('signature_data', ''))
        record.status = AppraisalRecord.STATUS_HR
        record.save()
        _check_flag_ceo(record, record.total_score, 'Manager')

        for hr_emp in Employee.objects.filter(role='hr', is_active=True):
            notify(
                hr_emp.user,
                f'Appraisal HR Review Needed — {record.employee.get_full_name()}',
                f'Line manager has completed the appraisal for {record.employee.get_full_name()}. Your review is next.',
                notification_type='general',
                url=f'/appraisals/hr-review/{record.pk}/',
            )
        messages.success(request, "Manager appraisal rating and comment submitted.")
        return redirect('dashboard:home')

    pf_fields = [
        ('mgr_pf_quality_of_work',      'Quality of Work'),
        ('mgr_pf_quantity_of_work',     'Quantity of Work'),
        ('mgr_pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('mgr_pf_ability_to_learn',     'Ability / Interest to Learn'),
    ]
    aa_fields = [
        ('mgr_aa_motivation',          'Motivation and Initiative'),
        ('mgr_aa_attitude_colleagues', 'Attitude towards Colleagues and Authority'),
        ('mgr_aa_relations_patients',  'Relations with Patients and Visitors'),
        ('mgr_aa_judgment_team',       'Judgment, Team Spirit and Discretion'),
        ('mgr_aa_punctuality',         'Punctuality, Attendance, Availability and Honesty'),
        ('mgr_aa_presentation',        'Personal Presentation and Professional Secrets'),
    ]
    current_values = {f: getattr(record, f) for f, _ in pf_fields + aa_fields}
    return render(request, 'appraisals/manager_fill.html', {
        'record': record,
        'pf_fields': pf_fields,
        'aa_fields': aa_fields,
        'current_values': current_values,
        'current_sig_b64': emp.signature_b64 or '',
    })


# ── HR Review ────────────────────────────────────────────────────────────────

@login_required
def hr_fill(request, record_pk):
    emp    = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    record = get_object_or_404(AppraisalRecord, pk=record_pk)
    if record.status != AppraisalRecord.STATUS_HR:
        messages.error(request, "This appraisal is not awaiting HR review.")
        return redirect('appraisals:hr_dashboard')

    if request.method == 'POST':
        _apply_score_override(request.POST, record, emp, role='hr')
        _save_independent_scores(request.POST, record, 'hr_ind')
        record.hr_comment   = request.POST.get('hr_comment', '').strip()
        record.hr_signed_by = emp
        record.hr_signed_at = timezone.now()
        _save_sig(record, 'hr_sig_b64', request.POST.get('signature_data', ''))
        record.status = AppraisalRecord.STATUS_DIRECTOR
        record.save()
        _check_flag_ceo(record, record.total_score, 'HR')

        _notify_director(record)
        messages.success(request, "HR comment submitted.")
        return redirect('appraisals:hr_dashboard')

    return render(request, 'appraisals/hr_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
        'discipline_data': record.discipline_deductions(),
        'ind_vals': {f: getattr(record, f'hr_ind_{f}') for f in _IND_SCORE_FNAMES},
        'ind_label': 'HR Manager',
        'ind_color': '#0891b2',
        **_score_form_ctx(record),
    })


# ── Admin Director ───────────────────────────────────────────────────────────

@login_required
def director_fill(request, record_pk):
    emp    = get_employee(request)
    if not emp or not emp.is_director():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    # Finance director can only act when admin director is on leave
    if emp.role == 'finance_director' and not _admin_director_on_leave():
        messages.error(request, "Admin Director is available. Finance Director acts as backup only when Admin Director is on leave.")
        return redirect('dashboard:home')
    record = get_object_or_404(AppraisalRecord, pk=record_pk)
    if record.status != AppraisalRecord.STATUS_DIRECTOR:
        messages.error(request, "This appraisal is not awaiting your review.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        _apply_score_override(request.POST, record, emp, role='director')
        _save_independent_scores(request.POST, record, 'dir_ind')
        try:
            record.award_bonus_points = max(0, int(request.POST.get('award_bonus_points', record.award_bonus_points) or record.award_bonus_points))
        except (ValueError, TypeError):
            pass
        record.director_comment   = request.POST.get('director_comment', '').strip()
        record.director_signed_by = emp
        record.director_signed_at = timezone.now()
        _save_sig(record, 'director_sig_b64', request.POST.get('signature_data', ''))
        record.status = AppraisalRecord.STATUS_CEO
        record.save()
        _check_flag_ceo(record, record.director_stage_total, 'Director')

        for ceo_emp in Employee.objects.filter(role='ceo', is_active=True):
            notify(
                ceo_emp.user,
                f'Appraisal CEO Review — {record.employee.get_full_name()}',
                f'Admin Director has commented on {record.employee.get_full_name()}\'s appraisal. Your final comment is next.',
                notification_type='general',
                url=f'/appraisals/ceo/{record.pk}/',
            )
        messages.success(request, "Director comment submitted.")
        return redirect('dashboard:home')

    return render(request, 'appraisals/director_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
        'discipline_data': record.discipline_deductions(),
        'ind_vals': {f: getattr(record, f'dir_ind_{f}') for f in _IND_SCORE_FNAMES},
        'ind_label': 'Administrative Director',
        'ind_color': '#7c3aed',
        **_score_form_ctx(record),
    })


# ── CEO ───────────────────────────────────────────────────────────────────────

@login_required
def ceo_fill(request, record_pk):
    emp    = get_employee(request)
    if not emp or not emp.is_ceo():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    record = get_object_or_404(AppraisalRecord, pk=record_pk)
    if record.status != AppraisalRecord.STATUS_CEO:
        messages.error(request, "This appraisal is not awaiting your review.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        _apply_score_override(request.POST, record, emp, role='ceo')
        _save_independent_scores(request.POST, record, 'ceo_ind')
        try:
            record.award_bonus_points = max(0, int(request.POST.get('award_bonus_points', record.award_bonus_points) or record.award_bonus_points))
        except (ValueError, TypeError):
            pass
        record.ceo_comment   = request.POST.get('ceo_comment', '').strip()
        record.ceo_signed_by = emp
        record.ceo_signed_at = timezone.now()
        _save_sig(record, 'ceo_sig_b64', request.POST.get('signature_data', ''))
        record.status = AppraisalRecord.STATUS_DONE
        record.save()

        # Notify HR that this appraisal is complete
        for hr_emp in Employee.objects.filter(role='hr', is_active=True):
            notify(
                hr_emp.user,
                f'Appraisal Complete — {record.employee.get_full_name()}',
                f'All signatures collected for {record.employee.get_full_name()}\'s appraisal. '
                f'Distribute results when all records in the cycle are done.',
                notification_type='general',
                url=f'/appraisals/cycles/{record.cycle.pk}/',
            )
        messages.success(request, "CEO comment submitted. Appraisal chain complete.")
        return redirect('appraisals:pending_ceo')

    return render(request, 'appraisals/ceo_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
        'discipline_data': record.discipline_deductions(),
        'ind_vals': {f: getattr(record, f'ceo_ind_{f}') for f in _IND_SCORE_FNAMES},
        'ind_label': 'CEO',
        'ind_color': '#b45309',
        **_score_form_ctx(record),
    })


# ── CEO Retroactive Review (rate/comment on any record, even after distribution) ─

@login_required
def ceo_review(request, record_pk):
    """CEO rates and comments on a record from any cycle — even after distribution."""
    emp = get_employee(request)
    if not emp or not emp.is_ceo():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    if request.method == 'POST':
        _apply_score_override(request.POST, record, emp, role='ceo')
        _save_independent_scores(request.POST, record, 'ceo_ind')
        try:
            record.award_bonus_points = max(0, int(request.POST.get('award_bonus_points',
                                                                      record.award_bonus_points)
                                                     or record.award_bonus_points))
        except (ValueError, TypeError):
            pass
        record.ceo_comment   = request.POST.get('ceo_comment', '').strip()
        record.ceo_signed_by = emp
        record.ceo_signed_at = timezone.now()
        _save_sig(record, 'ceo_sig_b64', request.POST.get('signature_data', ''))
        # If still in STATUS_CEO workflow, advance to DONE; otherwise keep current status
        if record.status == AppraisalRecord.STATUS_CEO:
            record.status = AppraisalRecord.STATUS_DONE
        record.save()

        messages.success(request, f"CEO review saved for {record.employee.get_full_name()}.")
        return redirect('appraisals:pending_ceo')

    return render(request, 'appraisals/ceo_fill.html', {
        'record': record,
        'current_sig_b64': emp.signature_b64 or '',
        'discipline_data': record.discipline_deductions(),
        'ind_vals': {f: getattr(record, f'ceo_ind_{f}') for f in _IND_SCORE_FNAMES},
        'ind_label': 'CEO',
        'ind_color': '#b45309',
        'is_retroactive': True,
        **_score_form_ctx(record),
    })


@login_required
def ceo_past_cycles(request):
    """CEO browses all past cycles to review any records."""
    emp = get_employee(request)
    if not emp or not emp.is_ceo():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    cycles = AppraisalCycle.objects.all().order_by('-year', '-trimester')
    return render(request, 'appraisals/ceo_past_cycles.html', {'cycles': cycles})


# ── Appraisal Detail (read-only view visible to all in the chain) ─────────────

@login_required
def appraisal_detail(request, record_pk):
    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    # Access: the employee, their chain, HR, director, CEO, superuser
    is_in_chain = (
        request.user.is_superuser or
        (emp and (
            emp == record.employee or
            emp == record.employee.supervisor or
            emp == record.employee.unit_head or
            emp.is_hr() or emp.is_director() or emp.is_ceo()
        ))
    )
    if not is_in_chain:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    discipline_data = record.discipline_deductions()

    # Build per-rater score rows for comparison table
    _pf_aa = [
        ('pf_quality_of_work',      'Quality of Work'),
        ('pf_quantity_of_work',     'Quantity of Work'),
        ('pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('pf_ability_to_learn',     'Ability / Interest to Learn'),
        ('aa_motivation',           'Motivation and Initiative'),
        ('aa_attitude_colleagues',  'Attitude towards Colleagues'),
        ('aa_relations_patients',   'Relations with Patients'),
        ('aa_judgment_team',        'Judgment / Team Spirit'),
        ('aa_punctuality',          'Punctuality'),
        ('aa_presentation',         'Presentation / Appearance'),
    ]
    score_rows = [
        {
            'label': label,
            'mgr': getattr(record, f'mgr_{fname}'),
            'hr':  getattr(record, f'hr_ind_{fname}'),
            'dir': getattr(record, f'dir_ind_{fname}'),
            'ceo': getattr(record, f'ceo_ind_{fname}'),
        }
        for fname, label in _pf_aa
    ]
    any_ind = any(
        row['hr'] is not None or row['dir'] is not None or row['ceo'] is not None
        for row in score_rows
    )

    return render(request, 'appraisals/appraisal_detail.html', {
        'record': record,
        'discipline_data': discipline_data,
        'score_rows': score_rows,
        'any_ind': any_ind,
    })


# ── Pending queue views for managers, HR, director, CEO ──────────────────────

@login_required
def pending_coworker(request):
    emp = get_employee(request)
    if not emp:
        return redirect('dashboard:home')
    # Only show the record where this specific employee was chosen as co-worker
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_COWORKER,
        coworker_signed_by=emp,
    ).select_related('employee__user', 'cycle')
    return render(request, 'appraisals/pending_list.html', {
        'records': records, 'role': 'coworker',
        'action_url_name': 'appraisals:coworker_fill',
        'title': 'Appraisals Awaiting Your Co-Worker Comment',
    })


@login_required
def pending_unit_head(request):
    emp = get_employee(request)
    if not emp:
        return redirect('dashboard:home')
    from django.db.models import Q
    # unit_head fills if set; otherwise the supervisor fills the comment step
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_UNIT_HEAD,
    ).filter(
        Q(employee__unit_head=emp) |
        Q(employee__unit_head__isnull=True, employee__supervisor=emp)
    ).select_related('employee__user', 'cycle')
    return render(request, 'appraisals/pending_list.html', {
        'records': records, 'role': 'unit_head',
        'action_url_name': 'appraisals:unit_head_fill',
        'title': 'Appraisals Awaiting Your Review',
    })


@login_required
def pending_manager(request):
    emp = get_employee(request)
    if not emp:
        return redirect('dashboard:home')
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_MANAGER,
        employee__supervisor=emp,
    ).select_related('employee__user', 'cycle')
    return render(request, 'appraisals/pending_list.html', {
        'records': records, 'role': 'manager',
        'action_url_name': 'appraisals:manager_fill',
        'title': 'Appraisals Awaiting Manager Rating & Comment',
    })


@login_required
def pending_hr(request):
    emp = get_employee(request)
    if not emp or (not emp.is_hr() and not request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_HR,
    ).select_related('employee__user', 'cycle')
    return render(request, 'appraisals/pending_list.html', {
        'records': records, 'role': 'hr',
        'action_url_name': 'appraisals:hr_fill',
        'title': 'Appraisals Awaiting HR Comment',
    })


@login_required
def pending_director(request):
    emp = get_employee(request)
    if not emp or not emp.is_director():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')
    records = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_DIRECTOR,
    ).select_related('employee__user', 'cycle')
    return render(request, 'appraisals/pending_list.html', {
        'records': records, 'role': 'director',
        'action_url_name': 'appraisals:director_fill',
        'title': 'Appraisals Awaiting Director Comment',
    })


@login_required
def pending_ceo(request):
    emp = get_employee(request)
    if not emp or not emp.is_ceo():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    # Regular queue: awaiting CEO in current workflow
    regular = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_CEO,
        is_flagged_for_ceo=False,
    ).select_related('employee__user', 'cycle').order_by('-cycle__year', '-cycle__trimester')

    # Flagged: any cycle — CEO hasn't yet reviewed (ceo_signed_at IS NULL)
    flagged = AppraisalRecord.objects.filter(
        is_flagged_for_ceo=True,
        ceo_signed_at__isnull=True,
    ).select_related('employee__user', 'cycle').order_by('-cycle__year', '-cycle__trimester')

    # Also include flagged records already in STATUS_CEO in the regular queue for clarity
    flagged_pending = AppraisalRecord.objects.filter(
        status=AppraisalRecord.STATUS_CEO,
        is_flagged_for_ceo=True,
    ).select_related('employee__user', 'cycle').order_by('-cycle__year', '-cycle__trimester')

    return render(request, 'appraisals/ceo_dashboard.html', {
        'regular': regular,
        'flagged': flagged,
        'flagged_pending': flagged_pending,
    })


# ── Appraisal PDF Download ────────────────────────────────────────────────────

@login_required
def appraisal_pdf(request, record_pk):
    from django.http import HttpResponse
    from .pdf_utils import generate_appraisal_pdf

    emp    = get_employee(request)
    record = get_object_or_404(AppraisalRecord, pk=record_pk)

    # Employee can only download after the cycle is distributed
    is_employee_access = (emp == record.employee and record.cycle.is_distributed)
    # HR, chain members, superuser can always download once the chain is done
    is_chain_access = (
        request.user.is_superuser or
        (emp and (
            emp == record.employee.supervisor or
            emp == record.employee.unit_head or
            emp.is_hr() or emp.is_director() or emp.is_ceo()
        ))
    )
    if not (is_employee_access or is_chain_access):
        messages.error(request, "Access denied. The appraisal results have not been distributed yet.")
        return redirect('appraisals:my_appraisals')

    buf = generate_appraisal_pdf(record)
    last  = record.employee.user.last_name.replace(' ', '_')
    cycle = str(record.cycle).replace(' ', '_')
    filename = f"appraisal_{last}_{cycle}.pdf"
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
