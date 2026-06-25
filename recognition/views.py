from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import RecognitionProposal, RecognitionComment
from accounts.models import Employee
from notifications.utils import notify


def _can_comment(user):
    """HR, directors, CEO, managers, unit heads, and superusers can comment."""
    if user.is_superuser:
        return True
    try:
        emp = user.employee
        return (emp.is_hr() or emp.is_director() or emp.is_ceo() or
                emp.is_manager() or emp.role == 'unit_head')
    except Exception:
        return False


@login_required
def proposal_list(request):
    user = request.user
    try:
        emp = user.employee
    except Exception:
        emp = None

    if user.is_superuser or (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo())):
        proposals = RecognitionProposal.objects.select_related('employee__user', 'proposed_by').all()
    elif emp and (emp.is_manager() or emp.role == 'unit_head'):
        # Managers/unit heads see proposals for their reports + their own
        proposals = RecognitionProposal.objects.filter(
            Q(employee__supervisor=emp) | Q(employee__unit_head=emp) | Q(proposed_by=user)
        ).distinct().select_related('employee__user', 'proposed_by')
    else:
        proposals = RecognitionProposal.objects.filter(
            Q(proposed_by=user) | Q(employee__user=user)
        ).select_related('employee__user', 'proposed_by')

    status_filter = request.GET.get('status', '')
    if status_filter:
        proposals = proposals.filter(status=status_filter)

    return render(request, 'recognition/list.html', {
        'proposals': proposals,
        'status_filter': status_filter,
        'STATUS_CHOICES': RecognitionProposal.STATUS_CHOICES,
    })


@login_required
def propose(request):
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
        hr_users = Employee.objects.filter(role__in=['hr', 'hr_manager'])
        for hr_emp in hr_users:
            if hr_emp.user_id:
                notify(
                    hr_emp.user,
                    f'New Recognition Proposal — {proposal.get_display_title()}',
                    f'{request.user.get_full_name()} has proposed {proposal.get_display_title()} for {employee.get_full_name()}.\n\n'
                    f'Reason: {description[:200]}',
                    notification_type='info',
                    url=f'/recognition/{proposal.pk}/',
                )

        messages.success(request, f'Recognition proposal submitted for {employee.get_full_name()}.')
        return redirect('recognition:detail', pk=proposal.pk)

    return render(request, 'recognition/propose.html', {
        'employees': employees,
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

    # Allow the proposer and the employee themselves to view
    user = request.user
    try:
        emp = user.employee
    except Exception:
        emp = None

    is_hr_or_admin = (user.is_superuser or (emp and (emp.is_hr() or emp.is_director() or emp.is_ceo())))
    is_manager_of = (emp and (
        emp == proposal.employee.supervisor or emp == proposal.employee.unit_head
    ))
    is_proposer = (proposal.proposed_by_id == user.pk)
    is_subject = (proposal.employee.user_id == user.pk)

    if not (is_hr_or_admin or is_manager_of or is_proposer or is_subject or can_comment):
        messages.error(request, 'You do not have permission to view this proposal.')
        return redirect('recognition:list')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'comment' and can_comment:
            body = request.POST.get('body', '').strip()
            if body:
                RecognitionComment.objects.create(proposal=proposal, author=user, body=body)
                # Notify HR and proposer
                recipients = set()
                if proposal.proposed_by_id:
                    recipients.add(proposal.proposed_by)
                for hr_emp in Employee.objects.filter(role__in=['hr', 'hr_manager']):
                    if hr_emp.user_id:
                        recipients.add(hr_emp.user)
                for recipient in recipients:
                    if recipient != user:
                        notify(
                            recipient,
                            f'New comment on recognition: {proposal.get_display_title()}',
                            f'{user.get_full_name()} commented on the recognition proposal for {proposal.employee.get_full_name()}:\n\n"{body[:200]}"',
                            notification_type='info',
                            url=f'/recognition/{proposal.pk}/',
                        )
                messages.success(request, 'Comment added.')
            return redirect('recognition:detail', pk=pk)

        if action == 'endorse' and is_hr_or_admin and proposal.status == RecognitionProposal.STATUS_PROPOSED:
            proposal.status = RecognitionProposal.STATUS_ENDORSED
            proposal.save(update_fields=['status'])
            notify(
                proposal.proposed_by,
                f'Recognition endorsed: {proposal.get_display_title()}',
                f'Your recognition proposal for {proposal.employee.get_full_name()} has been endorsed.',
                notification_type='success',
                url=f'/recognition/{proposal.pk}/',
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
            proposal.save(update_fields=['status', 'executed_by', 'executed_at', 'execution_note'])
            # Notify employee
            notify(
                proposal.employee.user,
                f'Congratulations! {proposal.get_display_title()}',
                f'Dear {proposal.employee.get_full_name()},\n\n'
                f'Congratulations! You have been recognized with: {proposal.get_display_title()}.\n\n'
                f'{execution_note or ""}',
                notification_type='success',
                url=f'/recognition/{proposal.pk}/',
            )
            messages.success(request, f'Recognition executed and {proposal.employee.get_full_name()} has been notified.')
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
                    notification_type='warning',
                    url=f'/recognition/{proposal.pk}/',
                )
            messages.warning(request, 'Proposal rejected.')
            return redirect('recognition:detail', pk=pk)

    return render(request, 'recognition/detail.html', {
        'proposal': proposal,
        'comments': comments,
        'can_comment': can_comment,
        'is_hr_or_admin': is_hr_or_admin,
    })
