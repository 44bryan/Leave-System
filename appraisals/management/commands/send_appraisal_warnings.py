from django.core.management.base import BaseCommand
from datetime import date

from appraisals.models import AppraisalRecord
from discipline.models import DisciplineRecord
from notifications.utils import notify


class Command(BaseCommand):
    help = 'Auto-issue warning letters to employees who missed their appraisal deadline.'

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
                self.stdout.write(
                    f'  [DRY RUN] Would warn: {emp.get_full_name()} ({emp.employee_id}) — {cycle}'
                )
            else:
                reason = (
                    f'Failure to submit appraisal self-assessment for cycle "{cycle}" '
                    f'before the deadline of {deadline_str}. '
                    f'This notice is system-generated and does not affect the appraisal '
                    f'score for this trimester.'
                )

                # Create system-generated discipline record
                DisciplineRecord.objects.create(
                    employee=emp,
                    action_type='written_caution',
                    issued_by=None,
                    date_issued=today,
                    reason=reason,
                    is_system_generated=True,
                    notes=f'Auto-issued for appraisal cycle ID {cycle.pk}',
                )

                # In-app notification
                notify(
                    emp.user,
                    'Appraisal Deadline Missed — Warning Letter Issued',
                    (
                        f'Dear {emp.user.first_name},\n\n'
                        f'You did not complete your self-assessment for the appraisal cycle '
                        f'"{cycle}" before the deadline of {deadline_str}.\n\n'
                        f'A written caution has been automatically placed on your record. '
                        f'This notice is issued by the system and does NOT affect your appraisal '
                        f'score for this trimester.\n\n'
                        f'You are required to report to the HR Office as soon as possible.\n\n'
                        f'This is an automated notice. Please do not ignore it.'
                    ),
                    notification_type='appraisal_warning',
                    url='/appraisals/my/',
                )

                record.warning_sent = True
                record.save(update_fields=['warning_sent'])

            count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'{count} warning(s) would be issued (dry run — nothing sent).')
            )
        else:
            self.stdout.write(self.style.SUCCESS(f'Warning letters issued: {count}'))
