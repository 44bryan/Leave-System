from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import ExitRequest, OffboardingTask, DEFAULT_TASKS


def _is_hr_or_super(request):
    emp = request.user.employee
    return emp.is_hr() or emp.is_ceo() or request.user.is_superuser


@login_required
def exit_list(request):
    emp = request.user.employee
    if _is_hr_or_super(request):
        qs = ExitRequest.objects.select_related('employee__user', 'employee__department').all()
    else:
        qs = ExitRequest.objects.filter(employee=emp).select_related('employee__user')

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, 'offboarding/exit_list.html', {
        'exits': qs,
        'status_filter': status_filter,
        'status_choices': ExitRequest.STATUS_CHOICES,
        'is_hr': _is_hr_or_super(request),
    })


@login_required
def exit_create(request):
    if not _is_hr_or_super(request):
        messages.error(request, "Only HR can open exit requests.")
        return redirect('offboarding:exit_list')

    from accounts.models import Employee
    employees = Employee.objects.filter(is_active=True).select_related('user', 'department').order_by('user__last_name')

    if request.method == 'POST':
        emp_pk    = request.POST.get('employee')
        exit_type = request.POST.get('exit_type')
        exit_date = request.POST.get('exit_date')
        reason    = request.POST.get('reason', '').strip()
        notes     = request.POST.get('notes', '').strip()

        if not (emp_pk and exit_type and exit_date):
            messages.error(request, "Employee, exit type and last working day are required.")
        else:
            employee = get_object_or_404(Employee, pk=emp_pk)
            er = ExitRequest.objects.create(
                employee=employee,
                exit_type=exit_type,
                exit_date=exit_date,
                reason=reason,
                notes=notes,
                initiated_by=request.user,
                status='in_progress',
            )
            for title, owner, order in DEFAULT_TASKS:
                OffboardingTask.objects.create(
                    exit_request=er, title=title, owner=owner, order=order,
                )
            try:
                from dashboard.models import AuditLog
                AuditLog.log(request, AuditLog.ACTION_EMPLOYEE,
                             f'Exit request opened for {employee.get_full_name()} ({er.get_exit_type_display()})',
                             target_user=employee.user)
            except Exception:
                pass
            messages.success(request, f"Exit request opened for {employee.get_full_name()}.")
            return redirect('offboarding:exit_detail', pk=er.pk)

    return render(request, 'offboarding/exit_form.html', {
        'employees': employees,
        'exit_types': ExitRequest.EXIT_TYPES,
    })


@login_required
def exit_detail(request, pk):
    er = get_object_or_404(
        ExitRequest.objects.select_related('employee__user', 'employee__department', 'initiated_by'),
        pk=pk,
    )
    emp = request.user.employee
    is_hr = _is_hr_or_super(request)

    if not is_hr and er.employee != emp:
        messages.error(request, "Access denied.")
        return redirect('offboarding:exit_list')

    tasks = er.tasks.select_related('completed_by').all()

    if request.method == 'POST' and is_hr:
        action = request.POST.get('action')

        if action == 'complete_task':
            task = get_object_or_404(OffboardingTask, pk=request.POST.get('task_pk'), exit_request=er)
            task.completed    = True
            task.completed_by = request.user
            task.completed_at = timezone.now()
            task.notes        = request.POST.get('task_notes', '').strip()[:300]
            task.save()
            messages.success(request, f'"{task.title}" marked complete.')

        elif action == 'undo_task':
            task = get_object_or_404(OffboardingTask, pk=request.POST.get('task_pk'), exit_request=er)
            task.completed = False
            task.completed_by = None
            task.completed_at = None
            task.save()

        elif action == 'add_task':
            title = request.POST.get('new_task_title', '').strip()
            owner = request.POST.get('new_task_owner', 'hr')
            if title:
                OffboardingTask.objects.create(exit_request=er, title=title, owner=owner, order=99)
                messages.success(request, 'Task added.')

        elif action == 'save_interview':
            er.interview_date     = request.POST.get('interview_date') or None
            er.interview_feedback = request.POST.get('interview_feedback', '').strip()
            er.interview_done     = bool(request.POST.get('interview_done'))
            er.notes              = request.POST.get('notes', '').strip()
            er.save()
            messages.success(request, 'Exit interview notes saved.')

        elif action == 'change_status':
            new_status = request.POST.get('new_status')
            if new_status in dict(ExitRequest.STATUS_CHOICES):
                er.status = new_status
                er.save()
                messages.success(request, f'Status updated to {er.get_status_display()}.')

        return redirect('offboarding:exit_detail', pk=er.pk)

    return render(request, 'offboarding/exit_detail.html', {
        'er': er,
        'tasks': tasks,
        'is_hr': is_hr,
        'task_owners': OffboardingTask.OWNER_CHOICES,
        'status_choices': ExitRequest.STATUS_CHOICES,
    })
