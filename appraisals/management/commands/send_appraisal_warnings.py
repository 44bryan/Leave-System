from django.core.management.base import BaseCommand
from datetime import date

from appraisals.models import AppraisalRecord
from notifications.utils import notify


class Command(BaseCommand):
    help = 'Send automated warning letters to employees who missed their appraisal deadline.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List who would receive warnings without actually sending.',
        )

    def handle(self, *args, **options):
        today = date.today()
        dry_run = options['dry_run']

        missed = AppraisalRecord.objects.filter(
            status=AppraisalRecord.STATUS_EMPLOYEE,
            hr_unlocked=False,
            warning_sent=False,
            cycle__employee_deadline__lt=today,
            cycle__is_distributed=False,
        ).select_related('employee__user', 'cycle')

        if not missed.exists():
            self.stdout.write(self.style.SUCCESS('No pending warnings to send.'))
            return

        count = 0
        for record in missed:
            emp = record.employee
            cycle = record.cycle
            deadline_str = cycle.employee_deadline.strftime('%d %B %Y')

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would warn: {emp.get_full_name()} ({emp.employee_id}) — {cycle}')
            else:
                notify(
                    emp.user,
                    'Appraisal Deadline Missed — Please Report to HR',
                    (
                        f'Dear {emp.user.first_name},\n\n'
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

        if dry_run:
            self.stdout.write(self.style.WARNING(f'{count} warning(s) would be sent (dry run — nothing sent).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Warning letters sent: {count}'))
