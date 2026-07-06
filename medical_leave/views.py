from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import Http404

from accounts.models import Employee
from notifications.utils import notify
from .models import MedicalSickLeave


def _get_employee(request):
    return get_object_or_404(Employee, user=request.user)


def _create_leave_request_for_sick_leave(sl, hr_emp):
    """
    When a MedicalSickLeave is fully endorsed, automatically create
    an approved, non-deductible LeaveRequest so it appears in the
    employee's leave history and dashboard.
    """
    from leaves.models import LeaveRequest, LeaveType
    leave_type, _ = LeaveType.objects.get_or_create(
        name='Medical Sick Leave',
        defaults={
            'description': 'Sick leave issued by the Internal Medicine Specialist.',
            'is_deductible': False,
            'is_active': True,
            'color': 'info',
        },
    )
    # Avoid duplicates if somehow called twice
    if LeaveRequest.objects.filter(
        employee=sl.employee,
        leave_type=leave_type,
        start_date=sl.start_date,
        end_date=sl.end_date,
    ).exists():
        return
    LeaveRequest.objects.create(
        employee=sl.employee,
        leave_type=leave_type,
        start_date=sl.start_date,
        end_date=sl.end_date,
        total_days=sl.days_count,
        reason=f'Medical sick leave issued by {sl.issued_by.get_full_name()} (MSL-{sl.pk:04d}).',
        status=LeaveRequest.STATUS_APPROVED,
        hr_action_by=hr_emp,
        hr_action_date=timezone.now(),
    )


# ─── Physician ────────────────────────────────────────────────────────────────

@login_required
def issue(request):
    """Physician creates a new Medical Sick Leave."""
    emp = _get_employee(request)
    if not (emp.can_issue_sick_leave() or request.user.is_superuser):
        raise Http404

    employees = Employee.objects.filter(is_active=True).exclude(pk=emp.pk).order_by(
        'user__last_name', 'user__first_name'
    )

    if request.method == 'POST':
        patient_id = request.POST.get('employee')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        notes = request.POST.get('notes', '')

        if not (patient_id and start_date and end_date):
            messages.error(request, 'Please fill in all required fields.')
        else:
            from datetime import date
            try:
                patient = Employee.objects.get(pk=patient_id, is_active=True)
                sd = date.fromisoformat(start_date)
                ed = date.fromisoformat(end_date)
                if ed < sd:
                    messages.error(request, 'End date cannot be before start date.')
                else:
                    sl = MedicalSickLeave.objects.create(
                        employee=patient,
                        issued_by=emp,
                        date_of_issuance=date.today(),
                        start_date=sd,
                        end_date=ed,
                        notes=notes,
                        status=MedicalSickLeave.STATUS_PENDING_LINE_MANAGER,
                    )
                    # Notify the patient's line manager
                    manager = patient.supervisor
                    if manager:
                        notify(
                            manager.user,
                            'Medical Sick Leave — Endorsement Required',
                            f'{patient.get_full_name()} has been issued a medical sick leave '
                            f'({sl.start_date} → {sl.end_date}). Please log in to endorse.',
                            'leave',
                            f'/medical-leave/{sl.pk}/endorse/line-manager/',
                        )
                    # Notify the employee themselves
                    notify(
                        patient.user,
                        'Medical Sick Leave Issued',
                        f'A medical sick leave has been issued for you by Dr. {emp.get_full_name()} '
                        f'from {sl.start_date} to {sl.end_date} ({sl.days_count} day(s)).',
                        'leave',
                        f'/medical-leave/{sl.pk}/view/',
                    )
                    messages.success(request, 'Medical Sick Leave issued successfully.')
                    return redirect('medical_leave:detail', pk=sl.pk)
            except Employee.DoesNotExist:
                messages.error(request, 'Selected employee not found.')
            except ValueError:
                messages.error(request, 'Invalid date format.')

    return render(request, 'medical_leave/issue.html', {'employees': employees})


@login_required
def physician_list(request):
    """All sick leaves issued by this physician."""
    emp = _get_employee(request)
    if not (emp.can_issue_sick_leave() or request.user.is_superuser):
        raise Http404
    leaves = MedicalSickLeave.objects.filter(issued_by=emp).select_related(
        'employee__user', 'line_manager_action_by__user', 'hr_action_by__user'
    )
    return render(request, 'medical_leave/physician_list.html', {'leaves': leaves})


# ─── Detail / Print ───────────────────────────────────────────────────────────

@login_required
def detail(request, pk):
    """View a single sick leave record — accessible to physician, patient, managers, HR, superuser."""
    sl = get_object_or_404(MedicalSickLeave, pk=pk)
    emp = _get_employee(request)

    allowed = (
        request.user.is_superuser
        or sl.issued_by == emp
        or sl.employee == emp
        or emp.is_hr()
        or emp.is_manager()
        or emp.is_director()
        or emp.is_ceo()
        or emp == sl.employee.supervisor
    )
    if not allowed:
        raise Http404

    return render(request, 'medical_leave/detail.html', {'sl': sl})


@login_required
def print_view(request, pk):
    """Printable version styled like the official form."""
    sl = get_object_or_404(MedicalSickLeave, pk=pk)
    emp = _get_employee(request)

    allowed = (
        request.user.is_superuser
        or sl.issued_by == emp
        or sl.employee == emp
        or emp.is_hr()
        or emp.is_manager()
        or emp.is_director()
        or emp.is_ceo()
        or emp == sl.employee.supervisor
    )
    if not allowed:
        raise Http404

    return render(request, 'medical_leave/print.html', {'sl': sl})


# ─── Line Manager Endorsement ─────────────────────────────────────────────────

@login_required
def lm_queue(request):
    """Line manager sees sick leaves awaiting their endorsement."""
    emp = _get_employee(request)
    if not (emp.is_manager() or request.user.is_superuser):
        raise Http404

    # Sick leaves for employees whose supervisor is this manager
    leaves = MedicalSickLeave.objects.filter(
        status=MedicalSickLeave.STATUS_PENDING_LINE_MANAGER,
        employee__supervisor=emp,
    ).select_related('employee__user', 'issued_by__user')

    return render(request, 'medical_leave/lm_queue.html', {'leaves': leaves})


@login_required
def lm_endorse(request, pk):
    emp = _get_employee(request)
    sl = get_object_or_404(MedicalSickLeave, pk=pk, status=MedicalSickLeave.STATUS_PENDING_LINE_MANAGER)

    is_manager = emp.is_manager() or request.user.is_superuser
    is_supervising = sl.employee.supervisor == emp
    if not (is_manager and (is_supervising or request.user.is_superuser)):
        raise Http404

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        sl.line_manager_action_by = emp
        sl.line_manager_action_date = timezone.now()
        sl.line_manager_remarks = remarks

        if action == 'approve':
            sl.status = MedicalSickLeave.STATUS_PENDING_HR
            sl.save()
            # Notify HR
            hr_employees = Employee.objects.filter(role='hr', is_active=True)
            for hr in hr_employees:
                notify(
                    hr.user,
                    'Medical Sick Leave — HR Endorsement Required',
                    f'{sl.employee.get_full_name()} sick leave endorsed by Line Manager. '
                    f'Please log in to complete HR endorsement.',
                    'leave',
                    f'/medical-leave/{sl.pk}/endorse/hr/',
                )
            messages.success(request, 'Sick leave endorsed and forwarded to HR.')
        elif action == 'reject':
            sl.status = MedicalSickLeave.STATUS_REJECTED_LINE_MANAGER
            sl.save()
            notify(
                sl.employee.user,
                'Medical Sick Leave — Not Endorsed by Line Manager',
                f'Your medical sick leave ({sl.start_date} → {sl.end_date}) was not endorsed by your Line Manager.',
                'leave',
                f'/medical-leave/{sl.pk}/view/',
            )
            messages.warning(request, 'Sick leave has been rejected.')

        return redirect('medical_leave:lm_queue')

    return render(request, 'medical_leave/lm_endorse.html', {'sl': sl})


# ─── HR Endorsement ───────────────────────────────────────────────────────────

@login_required
def hr_queue(request):
    emp = _get_employee(request)
    if not (emp.is_hr() or request.user.is_superuser):
        raise Http404

    leaves = MedicalSickLeave.objects.filter(
        status=MedicalSickLeave.STATUS_PENDING_HR,
    ).select_related('employee__user', 'issued_by__user', 'line_manager_action_by__user')

    return render(request, 'medical_leave/hr_queue.html', {'leaves': leaves})


@login_required
def hr_endorse(request, pk):
    emp = _get_employee(request)
    if not (emp.is_hr() or request.user.is_superuser):
        raise Http404

    sl = get_object_or_404(MedicalSickLeave, pk=pk, status=MedicalSickLeave.STATUS_PENDING_HR)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        sl.hr_action_by = emp
        sl.hr_action_date = timezone.now()
        sl.hr_remarks = remarks

        if action == 'approve':
            sl.status = MedicalSickLeave.STATUS_APPROVED
            sl.save()
            _create_leave_request_for_sick_leave(sl, emp)
            notify(
                sl.employee.user,
                'Medical Sick Leave Fully Endorsed',
                f'Your medical sick leave ({sl.start_date} → {sl.end_date}) has been fully endorsed.',
                'leave',
                f'/medical-leave/{sl.pk}/view/',
            )
            messages.success(request, 'Sick leave fully endorsed.')
        elif action == 'reject':
            sl.status = MedicalSickLeave.STATUS_REJECTED_HR
            sl.save()
            notify(
                sl.employee.user,
                'Medical Sick Leave — Not Endorsed by HR',
                f'Your medical sick leave ({sl.start_date} → {sl.end_date}) was not endorsed by HR.',
                'leave',
                f'/medical-leave/{sl.pk}/view/',
            )
            messages.warning(request, 'Sick leave has been rejected.')

        return redirect('medical_leave:hr_queue')

    return render(request, 'medical_leave/hr_endorse.html', {'sl': sl})


# ─── All Records (HR / Admin) ─────────────────────────────────────────────────

@login_required
def all_records(request):
    emp = _get_employee(request)
    if not (emp.is_hr() or emp.is_director() or emp.is_ceo() or request.user.is_superuser):
        raise Http404

    leaves = MedicalSickLeave.objects.select_related(
        'employee__user', 'issued_by__user',
        'line_manager_action_by__user', 'hr_action_by__user'
    )
    return render(request, 'medical_leave/all_records.html', {'leaves': leaves})


# ─── My Sick Leaves (Employee self-view) ──────────────────────────────────────

@login_required
def my_sick_leaves(request):
    emp = _get_employee(request)
    leaves = MedicalSickLeave.objects.filter(employee=emp).select_related(
        'issued_by__user', 'line_manager_action_by__user', 'hr_action_by__user'
    )
    return render(request, 'medical_leave/my_sick_leaves.html', {'leaves': leaves})
