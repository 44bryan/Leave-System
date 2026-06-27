"""
Management command: notify_expiring_contracts

Sends HR an in-app + email notification at each expiry milestone:
  • 3 months  (90 days) before expiry
  • 1 month   (30 days) before expiry
  • 2 weeks   (14 days) before expiry
  • Expiry day (0 days)

Each milestone fires exactly once per contract — deduplicated by checking
whether a notification with that exact milestone label was already sent today.

Run daily via cron: python manage.py notify_expiring_contracts
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.urls import reverse


MILESTONES = [
    (90, '3 months'),
    (30, '1 month'),
    (14, '2 weeks'),
    (0,  'TODAY'),
]


class Command(BaseCommand):
    help = 'Notify HR of contract expiry milestones (3 months / 1 month / 2 weeks / today).'

    def handle(self, *args, **options):
        from contracts.models import Contract
        from accounts.models import Employee
        from notifications.models import Notification
        from notifications.utils import notify

        today = date.today()

        # Collect contracts that hit a milestone today
        target_dates = [today + timedelta(days=d) for d, _ in MILESTONES]

        contracts = Contract.objects.filter(
            status='active',
            end_date__isnull=False,
            end_date__in=target_dates,
        ).select_related('employee__user', 'employee__department')

        if not contracts.exists():
            self.stdout.write('No contract expiry milestones today.')
            return

        hr_recipients = list(
            Employee.objects.filter(
                is_active=True, role__in=['hr', 'admin_director']
            ).select_related('user')
        )
        if not hr_recipients:
            self.stdout.write(self.style.WARNING('No HR/Director recipients found.'))
            return

        sent = 0
        for contract in contracts:
            days_left = (contract.end_date - today).days
            # Find the label for this milestone
            label = next((lbl for d, lbl in MILESTONES if d == days_left), f'{days_left} days')
            emp_name = contract.employee.get_full_name()
            title = f'Contract Expiry — {emp_name} — {label}'

            for hr_emp in hr_recipients:
                # Deduplicate: skip if this exact title was already sent today
                already = Notification.objects.filter(
                    recipient=hr_emp.user,
                    title=title,
                    created_at__date=today,
                ).exists()
                if already:
                    self.stdout.write(f'  Skip (already sent): {title}')
                    continue

                if days_left == 0:
                    msg = (
                        f"{emp_name}'s {contract.get_contract_type_display()} contract "
                        f"EXPIRES TODAY ({contract.end_date.strftime('%d %b %Y')}). "
                        f"Please take immediate action — renew, extend, or terminate."
                    )
                else:
                    msg = (
                        f"{emp_name}'s {contract.get_contract_type_display()} contract "
                        f"expires in {label} on {contract.end_date.strftime('%d %b %Y')}. "
                        f"Please review and take action before it lapses."
                    )

                notify(
                    hr_emp.user,
                    title=title,
                    message=msg,
                    notification_type='contract_issued',
                    url=reverse('contracts:detail', kwargs={'pk': contract.pk}),
                )
                sent += 1
                self.stdout.write(
                    self.style.WARNING(f'  Notified {hr_emp.get_full_name()}: {title}')
                )

        self.stdout.write(self.style.SUCCESS(f'Done — {sent} notification(s) sent.'))
