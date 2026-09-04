"""
Management command: clear_expired_acting_roles
Runs daily to remove acting_role from backup employees whose covered leave has ended.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Remove acting_role from backup employees whose covered leave has ended.'

    def handle(self, *args, **options):
        from leaves.models import LeaveRequest
        from notifications.utils import notify

        today = timezone.now().date()

        # Find approved leaves that ended yesterday or earlier and have a backup with acting_role
        expired = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_APPROVED,
            end_date__lt=today,
            backup_employee__isnull=False,
        ).select_related('employee__user', 'backup_employee__user')

        cleared = 0
        for leave in expired:
            backup = leave.backup_employee
            absent = leave.employee
            if backup.acting_role and backup.acting_role == absent.role:
                # Make sure there's no other active leave still needing this acting role
                still_active = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_APPROVED,
                    end_date__gte=today,
                    backup_employee=backup,
                    employee__role=backup.acting_role,
                ).exists()
                if not still_active:
                    backup.acting_role = ''
                    backup.save(update_fields=['acting_role'])
                    cleared += 1
                    notify(
                        backup.user,
                        f'Acting role ended — {absent.get_full_name()} has returned',
                        f'Your acting role covering for {absent.get_full_name()} has ended. '
                        f'Your original permissions have been restored.',
                        'leave',
                    )
                    self.stdout.write(f'Cleared acting_role for {backup.get_full_name()} (was covering {absent.get_full_name()})')

        self.stdout.write(self.style.SUCCESS(f'Done. {cleared} acting role(s) cleared.'))
