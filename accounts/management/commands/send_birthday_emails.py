from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send birthday email & in-app notification to every employee whose birthday is today.'

    def handle(self, *args, **options):
        from accounts.models import Employee
        from notifications.models import Notification
        from notifications.utils import notify

        today = date.today()

        birthday_employees = Employee.objects.filter(
            is_active=True,
            date_of_birth__isnull=False,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        ).select_related('user')

        if not birthday_employees.exists():
            self.stdout.write(self.style.SUCCESS('No birthdays today.'))
            return

        sent = 0
        for emp in birthday_employees:
            # Deduplicate — skip if already sent today
            already_sent = Notification.objects.filter(
                recipient=emp.user,
                notification_type='birthday',
                created_at__date=today,
            ).exists()
            if already_sent:
                self.stdout.write(f'  Skipped (already sent): {emp.get_full_name()}')
                continue

            age = today.year - emp.date_of_birth.year
            suffix = 'st' if age % 10 == 1 and age != 11 else \
                     'nd' if age % 10 == 2 and age != 12 else \
                     'rd' if age % 10 == 3 and age != 13 else 'th'

            notify(
                emp.user,
                title='Happy Birthday!',
                message=(
                    f"Wishing you a very Happy Birthday, {emp.user.first_name or emp.get_full_name()}!\n\n"
                    f"On behalf of the entire MICEI / Africa Eye Foundation family, "
                    f"we hope your {age}{suffix} birthday is filled with joy, laughter and wonderful memories.\n\n"
                    f"Thank you for your dedication and hard work — "
                    f"you are a valued member of our team. Have a fantastic day!"
                ),
                notification_type='birthday',
                url='/accounts/profile/',
            )
            sent += 1
            self.stdout.write(f'  Sent birthday greeting to: {emp.get_full_name()}')

        self.stdout.write(self.style.SUCCESS(f'Done — {sent} birthday greeting(s) sent.'))
