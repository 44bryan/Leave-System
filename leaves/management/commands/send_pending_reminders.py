"""
Management command: send_pending_reminders

Sends in-app (+ email) reminders to people who have pending actions
waiting on them. Safe to run daily via cron — only reminders for items
that have been sitting untouched for at least MIN_HOURS_OLD hours are sent,
and each item is only reminded once per day (checked via notification title
deduplication within the last 20 hours).

Usage:
    python manage.py send_pending_reminders
    python manage.py send_pending_reminders --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


MIN_HOURS_OLD = 24   # only remind if item has been pending this long


class Command(BaseCommand):
    help = 'Send reminder notifications for pending leave approvals and appraisals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would be sent without actually sending.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        now = timezone.now()
        cutoff = now - timedelta(hours=MIN_HOURS_OLD)
        recent = now - timedelta(hours=20)   # dedupe window

        from notifications.models import Notification
        from notifications.utils import notify

        sent = 0

        def already_reminded(user, title_contains):
            """Return True if we already sent a reminder with this title in the last 20 h."""
            return Notification.objects.filter(
                recipient=user,
                title__icontains=title_contains,
                created_at__gte=recent,
                notification_type='reminder',
            ).exists()

        def send(user, title, msg, url=''):
            nonlocal sent
            if dry:
                self.stdout.write(f'  [DRY RUN] → {user.username}: {title}')
            else:
                notify(user, title, msg, notification_type='reminder', url=url)
            sent += 1

        # ── Leave Requests ──────────────────────────────────────────────────
        from leaves.models import LeaveRequest
        from accounts.models import Employee

        # Pending (awaiting unit head / manager)
        pending_leaves = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_PENDING,
            updated_at__lte=cutoff,
        ).select_related('employee__user', 'employee__unit_head__user',
                         'employee__supervisor__user')

        self.stdout.write(f'Pending leave requests (>{MIN_HOURS_OLD}h): {pending_leaves.count()}')

        for lr in pending_leaves:
            emp = lr.employee
            approvers = set()
            if emp.unit_head:
                approvers.add(emp.unit_head)
            if emp.supervisor:
                approvers.add(emp.supervisor)
            for approver in approvers:
                title = 'Reminder: Leave Request Awaiting Your Approval'
                if not already_reminded(approver.user, 'Leave Request Awaiting'):
                    send(
                        approver.user,
                        title,
                        f'You have a leave request from {emp.get_full_name()} '
                        f'({lr.leave_type}, {lr.start_date} – {lr.end_date}) '
                        f'that is still awaiting your approval.',
                        url='/leaves/all/',
                    )

        # Unit head approved — awaiting manager
        uh_approved = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_UNIT_HEAD_APPROVED,
            updated_at__lte=cutoff,
        ).select_related('employee__user', 'employee__supervisor__user')

        for lr in uh_approved:
            emp = lr.employee
            if emp.supervisor:
                title = 'Reminder: Leave Request Awaiting Your Approval'
                if not already_reminded(emp.supervisor.user, 'Leave Request Awaiting'):
                    send(
                        emp.supervisor.user,
                        title,
                        f'A leave request from {emp.get_full_name()} '
                        f'({lr.leave_type}, {lr.start_date} – {lr.end_date}) '
                        f'is awaiting your approval.',
                        url='/leaves/all/',
                    )

        # Manager approved — awaiting HR
        mgr_approved = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_MANAGER_APPROVED,
            updated_at__lte=cutoff,
        ).select_related('employee__user')

        if mgr_approved.exists():
            count = mgr_approved.count()
            hr_staff = Employee.objects.filter(role='hr', is_active=True).select_related('user')
            for hr_emp in hr_staff:
                title = 'Reminder: Leave Requests Awaiting HR Approval'
                if not already_reminded(hr_emp.user, 'Leave Requests Awaiting HR'):
                    send(
                        hr_emp.user,
                        title,
                        f'There {"is" if count == 1 else "are"} {count} leave request{"s" if count > 1 else ""} '
                        f'awaiting HR approval.',
                        url='/leaves/all/',
                    )

        # ── Appraisals ──────────────────────────────────────────────────────
        from appraisals.models import AppraisalRecord
        from datetime import date

        today = date.today()

        # Employee has not yet submitted (deadline not yet passed)
        pending_emp = AppraisalRecord.objects.filter(
            status=AppraisalRecord.STATUS_EMPLOYEE,
            hr_unlocked=False,
            cycle__is_distributed=False,
        ).exclude(
            cycle__employee_deadline__lt=today,  # exclude already-overdue (those get warning letters)
        ).filter(
            updated_at__lte=cutoff,
        ).select_related('employee__user', 'cycle')

        self.stdout.write(f'Pending employee appraisals: {pending_emp.count()}')
        for rec in pending_emp:
            emp = rec.employee
            deadline_str = rec.cycle.employee_deadline.strftime('%d %B %Y') if rec.cycle.employee_deadline else 'soon'
            title = 'Reminder: Appraisal Awaiting Your Submission'
            if not already_reminded(emp.user, 'Appraisal Awaiting Your Submission'):
                send(
                    emp.user,
                    title,
                    f'Your self-assessment for the appraisal cycle "{rec.cycle}" '
                    f'has not been submitted yet. The deadline is {deadline_str}. '
                    f'Please log in and complete your appraisal.',
                    url='/appraisals/my/',
                )

        # Each HR-side pending stage — remind the responsible role group
        stage_map = [
            (AppraisalRecord.STATUS_HR,       'hr',       'Reminder: Appraisal Awaiting HR Review'),
            (AppraisalRecord.STATUS_DIRECTOR,  'admin_director', 'Reminder: Appraisal Awaiting Director Review'),
            (AppraisalRecord.STATUS_CEO,       'ceo',      'Reminder: Appraisal Awaiting CEO Review'),
        ]
        for status, role, title in stage_map:
            recs = AppraisalRecord.objects.filter(
                status=status,
                cycle__is_distributed=False,
                updated_at__lte=cutoff,
            )
            if recs.exists():
                count = recs.count()
                reviewers = Employee.objects.filter(role=role, is_active=True).select_related('user')
                for reviewer in reviewers:
                    if not already_reminded(reviewer.user, title):
                        send(
                            reviewer.user,
                            title,
                            f'There {"is" if count == 1 else "are"} {count} appraisal{"s" if count > 1 else ""} '
                            f'awaiting your review.',
                            url='/appraisals/hr/',
                        )

        if dry:
            self.stdout.write(self.style.WARNING(f'Dry run complete — {sent} reminder(s) would be sent.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Reminders sent: {sent}'))
