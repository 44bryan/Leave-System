"""
Management command: notify_expiring_contracts

Sends email + in-app notifications to HR staff for contracts expiring within 30 days.
Run daily via Railway cron or manually: python manage.py notify_expiring_contracts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Send notifications to HR for contracts expiring within 30 days'

    def handle(self, *args, **options):
        from contracts.models import Contract
        from accounts.models import Employee
        from notifications.utils import notify

        today = date.today()

        expiring = Contract.objects.filter(
            status='active',
            end_date__isnull=False,
            end_date__gt=today,
            end_date__lte=today.replace(day=today.day) if False else
                (today.__class__(today.year, today.month, today.day) if False else
                 date(today.year, today.month, today.day + 30 if today.day <= 1 else today.day)
                )
        )
        # Simpler approach:
        from datetime import timedelta
        expiring = Contract.objects.filter(
            status='active',
            end_date__isnull=False,
            end_date__gt=today,
            end_date__lte=today + timedelta(days=30),
        ).select_related('employee__user', 'employee__department')

        if not expiring.exists():
            self.stdout.write('No contracts expiring within 30 days.')
            return

        # Notify all HR staff and superusers
        hr_users = Employee.objects.filter(
            is_active=True, role__in=['hr', 'admin_director']
        ).select_related('user')

        for contract in expiring:
            days_left = (contract.end_date - today).days
            emp_name = contract.employee.get_full_name()
            msg = (
                f"{emp_name}'s {contract.contract_type} contract expires in {days_left} day(s) "
                f"(on {contract.end_date.strftime('%d %b %Y')}). "
                f"Please review and take action."
            )
            for hr_emp in hr_users:
                notify(
                    hr_emp.user,
                    title=f'Contract Expiring Soon — {emp_name}',
                    message=msg,
                    notification_type='contract_expiry',
                    url=f'/contracts/{contract.pk}/',
                )
            self.stdout.write(
                self.style.WARNING(f'  Notified HR: {emp_name} — {days_left} days left')
            )

        self.stdout.write(self.style.SUCCESS(
            f'Done. Processed {expiring.count()} expiring contract(s).'
        ))
