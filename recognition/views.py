from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from .models import RecognitionProposal, RecognitionComment
from accounts.models import Employee
from notifications.utils import notify


def _can_propose(user):
    """Only line managers and above (manager, HR, director, CEO, superuser) can propose."""
    if user.is_superuser:
        return True
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_director() or emp.is_ceo() or emp.is_manager()
    except Exception:
        return False


def _can_comment(user):
    return _can_propose(user)


def _is_manager_level(user):
    """Returns True if user can access the proposal list (manager and above)."""
    return _can_propose(user)


@login_required
def proposal_list(request):
    user = request.user
    try:
        emp = user.employee
    except Exception:
        emp = None

    # Employees and unit_heads have no business here — redirect to their own awards
    if not _is_manager_level(user):
        return redirect('recognition:my_awards')

    if user.is_superuser or (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo())):
        proposals = RecognitionProposal.objects.select_related('employee__user', 'proposed_by').all()
    elif emp and emp.is_manager():
        proposals = RecognitionProposal.objects.filter(
            Q(employee__supervisor=emp) | Q(proposed_by=user)
        ).distinct().select_related('employee__user', 'proposed_by')
    else:
        proposals = RecognitionProposal.objects.none()

    status_filter = request.GET.get('status', '')
    if status_filter:
        proposals = proposals.filter(status=status_filter)

    return render(request, 'recognition/list.html', {
        'proposals': proposals,
        'status_filter': status_filter,
        'STATUS_CHOICES': RecognitionProposal.STATUS_CHOICES,
        'can_propose': _can_propose(request.user),
    })


@login_required
def my_awards(request):
    """Employee view: only see your own executed recognitions."""
    try:
        emp = request.user.employee
    except Exception:
        emp = None

    awards = RecognitionProposal.objects.filter(
        employee__user=request.user,
        status=RecognitionProposal.STATUS_EXECUTED,
    ).order_by('-executed_at')

    return render(request, 'recognition/my_awards.html', {'awards': awards, 'employee': emp})


@login_required
def propose(request):
    if not _can_propose(request.user):
        messages.error(request, 'Only line managers and above can propose a recognition.')
        return redirect('recognition:my_awards')
    employees = Employee.objects.filter(user__is_active=True).order_by('user__last_name')
    if request.method == 'POST':
        employee_pk = request.POST.get('employee')
        recognition_type = request.POST.get('recognition_type')
        custom_title = request.POST.get('custom_title', '').strip()
        description = request.POST.get('description', '').strip()

        if not employee_pk or not recognition_type or not description:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'recognition/propose.html', {
                'employees': employees,
                'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
                'post': request.POST,
            })

        if recognition_type == RecognitionProposal.TYPE_OTHER and not custom_title:
            messages.error(request, 'Please enter a custom title for "Other" recognition type.')
            return render(request, 'recognition/propose.html', {
                'employees': employees,
                'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
                'post': request.POST,
            })

        employee = get_object_or_404(Employee, pk=employee_pk)
        proposal = RecognitionProposal.objects.create(
            employee=employee,
            proposed_by=request.user,
            recognition_type=recognition_type,
            custom_title=custom_title,
            description=description,
        )

        # Notify HR users
        for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
            notify(
                hr_emp.user,
                f'New Recognition Proposal — {proposal.get_display_title()}',
                f'{request.user.get_full_name()} has proposed {proposal.get_display_title()} '
                f'for {employee.get_full_name()}.\n\nReason: {description[:200]}',
                notification_type='system',
                url=reverse('recognition:detail', kwargs={'pk': proposal.pk}),
            )

        messages.success(request, f'Recognition proposal submitted for {employee.get_full_name()}.')
        return redirect('recognition:detail', pk=proposal.pk)

    return render(request, 'recognition/propose.html', {
        'employees': employees,
        'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
        'post': {},
    })


@login_required
def direct_award(request):
    """HR/Admin: create and immediately execute a recognition in one step."""
    user = request.user
    try:
        emp = user.employee
    except Exception:
        emp = None
    is_hr_or_admin = user.is_superuser or (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo()))
    if not is_hr_or_admin:
        messages.error(request, 'Only HR and above can issue direct awards.')
        return redirect('recognition:list')

    if request.method == 'POST':
        employee_pk = request.POST.get('employee')
        recognition_type = request.POST.get('recognition_type')
        custom_title = request.POST.get('custom_title', '').strip()
        description = request.POST.get('description', '').strip()
        execution_note = request.POST.get('execution_note', '').strip()

        if not employee_pk or not recognition_type or not description:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'recognition/direct_award.html', {
                'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
                'post': request.POST,
            })

        if recognition_type == RecognitionProposal.TYPE_OTHER and not custom_title:
            messages.error(request, 'Please enter a custom title for "Other" recognition type.')
            return render(request, 'recognition/direct_award.html', {
                'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
                'post': request.POST,
            })

        employee = get_object_or_404(Employee, pk=employee_pk)
        proposal = RecognitionProposal(
            employee=employee,
            proposed_by=user,
            recognition_type=recognition_type,
            custom_title=custom_title,
            description=description,
            status=RecognitionProposal.STATUS_EXECUTED,
            executed_by=user,
            executed_at=timezone.now(),
            execution_note=execution_note,
        )
        proposal.save()

        cert_file = request.FILES.get('certificate_file')
        if cert_file:
            proposal.certificate_file = cert_file
            proposal.save(update_fields=['certificate_file'])

        notify(
            employee.user,
            f'Congratulations! {proposal.get_display_title()}',
            f'Dear {employee.get_full_name()},\n\n'
            f'Congratulations! You have been formally recognized with: {proposal.get_display_title()}.\n\n'
            f'{execution_note or ""}',
            notification_type='appraisal',
            url=reverse('recognition:my_awards'),
        )
        messages.success(request, f'Recognition awarded directly to {employee.get_full_name()}.')
        return redirect('recognition:detail', pk=proposal.pk)

    return render(request, 'recognition/direct_award.html', {
        'TYPE_CHOICES': RecognitionProposal.TYPE_CHOICES,
        'post': {},
    })


@login_required
def proposal_detail(request, pk):
    proposal = get_object_or_404(
        RecognitionProposal.objects.select_related('employee__user', 'proposed_by', 'executed_by', 'rejected_by'),
        pk=pk
    )
    comments = proposal.comments.select_related('author')
    can_comment = _can_comment(request.user)

    user = request.user
    try:
        emp = user.employee
    except Exception:
        emp = None

    is_hr_or_admin = (user.is_superuser or (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo())))
    is_manager_of = (emp and emp.is_manager() and (
        emp == proposal.employee.supervisor
    ))
    is_proposer = (proposal.proposed_by_id == user.pk)
    is_subject = (proposal.employee.user_id == user.pk)

    # Employees/unit_heads can only see their own executed recognitions
    if is_subject and not _is_manager_level(user):
        if proposal.status != RecognitionProposal.STATUS_EXECUTED:
            messages.error(request, 'This recognition is not yet available.')
            return redirect('recognition:my_awards')
    elif not (is_hr_or_admin or is_manager_of or is_proposer or is_subject or can_comment):
        messages.error(request, 'You do not have permission to view this proposal.')
        return redirect('recognition:my_awards')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'comment' and can_comment:
            body = request.POST.get('body', '').strip()
            if body:
                RecognitionComment.objects.create(proposal=proposal, author=user, body=body)
                recipients = set()
                if proposal.proposed_by_id:
                    recipients.add(proposal.proposed_by)
                for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
                    recipients.add(hr_emp.user)
                for recipient in recipients:
                    if recipient != user:
                        notify(
                            recipient,
                            f'New comment on recognition: {proposal.get_display_title()}',
                            f'{user.get_full_name()} commented on the recognition proposal for {proposal.employee.get_full_name()}:\n\n"{body[:200]}"',
                            notification_type='system',
                            url=reverse('recognition:detail', kwargs={'pk': proposal.pk}),
                        )
                messages.success(request, 'Comment added.')
            return redirect('recognition:detail', pk=pk)

        if action == 'endorse' and is_hr_or_admin and proposal.status == RecognitionProposal.STATUS_PROPOSED:
            proposal.status = RecognitionProposal.STATUS_ENDORSED
            proposal.save(update_fields=['status'])
            if proposal.proposed_by:
                notify(
                    proposal.proposed_by,
                    f'Recognition endorsed: {proposal.get_display_title()}',
                    f'Your recognition proposal for {proposal.employee.get_full_name()} has been endorsed.',
                    notification_type='appraisal',
                    url=reverse('recognition:detail', kwargs={'pk': proposal.pk}),
                )
            messages.success(request, 'Proposal endorsed.')
            return redirect('recognition:detail', pk=pk)

        if action == 'execute' and is_hr_or_admin and proposal.status in (
            RecognitionProposal.STATUS_PROPOSED, RecognitionProposal.STATUS_ENDORSED
        ):
            execution_note = request.POST.get('execution_note', '').strip()
            proposal.status = RecognitionProposal.STATUS_EXECUTED
            proposal.executed_by = user
            proposal.executed_at = timezone.now()
            proposal.execution_note = execution_note
            save_fields = ['status', 'executed_by', 'executed_at', 'execution_note']
            cert_file = request.FILES.get('certificate_file')
            if cert_file:
                proposal.certificate_file = cert_file
                save_fields.append('certificate_file')
            proposal.save(update_fields=save_fields)

            # Notify the employee
            notify(
                proposal.employee.user,
                f'Congratulations! {proposal.get_display_title()}',
                f'Dear {proposal.employee.get_full_name()},\n\n'
                f'Congratulations! You have been formally recognized with: {proposal.get_display_title()}.\n\n'
                f'{execution_note or ""}',
                notification_type='appraisal',
                url=reverse('recognition:my_awards'),
            )
            # Notify the proposer
            if proposal.proposed_by and proposal.proposed_by != user:
                notify(
                    proposal.proposed_by,
                    f'Recognition executed: {proposal.get_display_title()}',
                    f'Your nomination of {proposal.employee.get_full_name()} for {proposal.get_display_title()} has been officially awarded.',
                    notification_type='appraisal',
                    url=reverse('recognition:detail', kwargs={'pk': proposal.pk}),
                )
            messages.success(request, f'Recognition awarded. {proposal.employee.get_full_name()} has been notified.')
            return redirect('recognition:detail', pk=pk)

        if action == 'reject' and is_hr_or_admin and proposal.status not in (
            RecognitionProposal.STATUS_EXECUTED, RecognitionProposal.STATUS_REJECTED
        ):
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            proposal.status = RecognitionProposal.STATUS_REJECTED
            proposal.rejected_by = user
            proposal.rejected_at = timezone.now()
            proposal.rejection_reason = rejection_reason
            proposal.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason'])
            if proposal.proposed_by:
                notify(
                    proposal.proposed_by,
                    f'Recognition proposal not approved: {proposal.get_display_title()}',
                    f'Your recognition proposal for {proposal.employee.get_full_name()} was not approved.\n\nReason: {rejection_reason}',
                    notification_type='leave_rejected',
                    url=reverse('recognition:detail', kwargs={'pk': proposal.pk}),
                )
            messages.warning(request, 'Proposal rejected.')
            return redirect('recognition:detail', pk=pk)

    return render(request, 'recognition/detail.html', {
        'proposal': proposal,
        'comments': comments,
        'can_comment': can_comment,
        'is_hr_or_admin': is_hr_or_admin,
    })
