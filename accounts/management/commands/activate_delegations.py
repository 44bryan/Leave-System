"""
Daily cron command: activate and deactivate leave delegations automatically.

Run at midnight (or early morning) so that:
- When a leave starts today → backup employee gains the acting_role
- When a leave ended → backup employee's acting_role is cleared

Cron: 0 0 * * * (midnight daily)
"""
from datetime import date

from django.core.management.base import BaseCommand

from leaves.models import LeaveApplication
from notifications.utils import notify


# Roles that are delegated to the backup
DELEGATABLE_ROLES = {
    'unit_head', 'manager', 'hr',
    'admin_director', 'finance_director', 'medical_director', 'ceo',
}


class Command(BaseCommand):
    help = 'Activate and deactivate leave delegations based on approved leave dates.'

    def handle(self, *args, **options):
        today = date.today()
        activated = 0
        deactivated = 0

        # ── 1. Activate: approved leaves that start today and have a backup ──
        starting = LeaveApplication.objects.filter(
            status='approved',
            start_date=today,
            backup_employee__isnull=False,
        ).select_related('employee__user', 'backup_employee__user')

        for leave in starting:
            original = leave.employee
            backup = leave.backup_employee

            if original.role not in DELEGATABLE_ROLES:
                continue  # no delegation for regular employees

            backup.acting_role = original.role
            backup.acting_for = original
            backup.acting_since = today
            backup.acting_until = leave.end_date
            backup.save(update_fields=['acting_role', 'acting_for', 'acting_since', 'acting_until'])

            # Notify backup
            notify(
                backup.user,
                title=f'You are now Acting {original.get_role_display()}',
                message=(
                    f'{original.get_full_name()} is on leave from {leave.start_date} to {leave.end_date}. '
                    f'You have been designated as their backup and now hold the Acting {original.get_role_display()} role '
                    f'for this period.'
                ),
                notification_type='system',
                url='/accounts/profile/',
            )
            # Notify the person going on leave
            notify(
                original.user,
                title='Leave delegation activated',
                message=(
                    f'Your leave has started. {backup.get_full_name()} is now acting as {original.get_role_display()} '
                    f'in your absence until {leave.end_date}.'
                ),
                notification_type='system',
                url='/accounts/profile/',
            )

            activated += 1
            self.stdout.write(
                f'  Activated: {backup.get_full_name()} acting as {original.role} for {original.get_full_name()}'
            )

        # ── 2. Deactivate: backup employees whose acting_until is yesterday or earlier ──
        from accounts.models import Employee
        expired = Employee.objects.filter(
            acting_role__gt='',           # has an acting role
            acting_until__lt=today,       # period has ended
        ).select_related('user', 'acting_for__user')

        for emp in expired:
            original = emp.acting_for
            old_role = emp.acting_role

            emp.acting_role = ''
            emp.acting_for = None
            emp.acting_since = None
            emp.acting_until = None
            emp.save(update_fields=['acting_role', 'acting_for', 'acting_since', 'acting_until'])

            notify(
                emp.user,
                title='Acting role ended',
                message=(
                    f'Your acting {old_role.replace("_", " ").title()} role has ended. '
                    f'You have returned to your regular responsibilities.'
                    + (f' {original.get_full_name()} is back.' if original else '')
                ),
                notification_type='system',
                url='/accounts/profile/',
            )
            if original:
                notify(
                    original.user,
                    title='Welcome back — delegation ended',
                    message=(
                        f'Your leave period has ended and {emp.get_full_name()} is no longer acting '
                        f'in your role. Your full responsibilities have been restored.'
                    ),
                    notification_type='system',
                    url='/accounts/profile/',
                )

            deactivated += 1
            self.stdout.write(f'  Deactivated: {emp.get_full_name()} acting role cleared')

        self.stdout.write(
            self.style.SUCCESS(
                f'activate_delegations: {activated} activated, {deactivated} deactivated.'
            )
        )
