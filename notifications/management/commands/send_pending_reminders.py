"""
Daily reminder command.

Runs every morning (via cron) and sends email + WhatsApp reminders to every
user who has at least one pending action waiting for them.

Pending actions checked:
  • Employee  — appraisal self-assessment not yet submitted
  • Employee  — leave request they filed is still pending (not fully approved/rejected)
  • Unit Head — leave requests waiting for their first approval
  • Manager   — leave requests waiting for their approval
  • HR        — leave requests pending HR approval
  • Director  — leave requests pending Director approval
  • Any role  — pending leave consultation requests sent to them
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q


class Command(BaseCommand):
    help = 'Send daily pending-action reminders via email and WhatsApp.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print who would be reminded without sending anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        from notifications.utils import notify
        from appraisals.models import AppraisalRecord
        from leaves.models import LeaveRequest, LeaveConsultation
        from accounts.models import Employee

        reminded = 0

        for user in User.objects.filter(is_active=True).select_related('employee'):
            try:
                emp = user.employee
            except Exception:
                continue

            items = []  # list of human-readable pending items for this user

            # ── 1. Appraisal self-assessment ──────────────────────────────────
            pending_appraisals = AppraisalRecord.objects.filter(
                employee=emp,
                status=AppraisalRecord.STATUS_EMPLOYEE,
                hr_unlocked=False,
                warning_sent=False,
            ).select_related('cycle')
            for ap in pending_appraisals:
                deadline = ap.cycle.employee_deadline
                deadline_str = deadline.strftime('%d %B %Y') if deadline else 'no deadline set'
                items.append(
                    f'• Appraisal self-assessment for "{ap.cycle}" — deadline: {deadline_str}'
                )

            # ── 2. Own pending leave requests ──────────────────────────────────
            own_pending_leaves = LeaveRequest.objects.filter(
                employee=emp,
                status__in=[
                    LeaveRequest.STATUS_PENDING,
                    LeaveRequest.STATUS_UNIT_HEAD_APPROVED,
                    LeaveRequest.STATUS_MANAGER_APPROVED,
                    LeaveRequest.STATUS_HR_APPROVED,
                ],
            ).select_related('leave_type')
            for lr in own_pending_leaves:
                items.append(
                    f'• Leave request ({lr.leave_type}) from {lr.start_date} to {lr.end_date} — still pending approval'
                )

            # ── 3. Leave requests waiting for THIS employee's approval ─────────
            leaves_to_approve = []

            if emp.role == 'unit_head':
                leaves_to_approve = list(LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_PENDING,
                    employee__unit_head=emp,
                ).select_related('employee__user', 'leave_type'))

            elif emp.is_manager():
                # Direct reports with no unit head
                leaves_to_approve = list(LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_PENDING,
                    employee__supervisor=emp,
                    employee__unit_head__isnull=True,
                ).select_related('employee__user', 'leave_type'))
                # Reports escalated from unit head
                leaves_to_approve += list(LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_UNIT_HEAD_APPROVED,
                    employee__supervisor=emp,
                ).select_related('employee__user', 'leave_type'))

            elif emp.is_hr():
                leaves_to_approve = list(LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_MANAGER_APPROVED,
                ).select_related('employee__user', 'leave_type'))

            elif emp.is_director():
                leaves_to_approve = list(LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_HR_APPROVED,
                ).select_related('employee__user', 'leave_type'))

            for lr in leaves_to_approve:
                items.append(
                    f'• Leave approval needed for {lr.employee.get_full_name()} ({lr.leave_type}) — {lr.start_date} to {lr.end_date}'
                )

            # ── 4. Pending consultation requests sent TO this employee ─────────
            pending_consults = LeaveConsultation.objects.filter(
                consulted_with=emp,
                status=LeaveConsultation.STATUS_PENDING,
            ).select_related('leave_request__employee__user', 'leave_request__leave_type')
            for c in pending_consults:
                lr = c.leave_request
                items.append(
                    f'• Leave consultation opinion needed for {lr.employee.get_full_name()} ({lr.leave_type})'
                )

            if not items:
                continue

            # ── Build and send the reminder ────────────────────────────────────
            count = len(items)
            title = f'You have {count} pending action{"s" if count > 1 else ""} in AEF HRM'
            message = (
                f'Dear {user.first_name or user.username},\n\n'
                f'This is a reminder that the following item{"s require" if count > 1 else " requires"} your attention:\n\n'
                + '\n'.join(items)
                + '\n\nPlease log in to AEF HRM to take action.'
            )

            if dry_run:
                self.stdout.write(f'\n[DRY RUN] {user.get_full_name()} ({user.username}) — {count} item(s):')
                for item in items:
                    self.stdout.write(f'  {item}')
            else:
                notify(
                    user,
                    title,
                    message,
                    notification_type='reminder',
                    url='/dashboard/',
                )
            reminded += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n{reminded} user(s) would be reminded (dry run).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Reminders sent to {reminded} user(s).'))
