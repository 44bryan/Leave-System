"""
Management command: notify HR about employee documents expiring within 30/60/90 days.
Run daily via cron:
    /var/www/hrm/venv/bin/python /var/www/hrm/manage.py notify_expiring_documents
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import EmployeeDocument, Employee


class Command(BaseCommand):
    help = 'Notify HR of employee documents expiring within 90 days.'

    THRESHOLDS = [30, 60, 90]

    def handle(self, *args, **options):
        from notifications.utils import notify
        from django.contrib.auth import get_user_model

        User = get_user_model()
        today = date.today()

        # Notify for each threshold on the exact day (avoids duplicate spam)
        notified = 0
        for days in self.THRESHOLDS:
            target_date = today + timedelta(days=days)
            docs = EmployeeDocument.objects.filter(
                expiry_date=target_date,
                expiry_date__isnull=False,
            ).select_related('employee__user', 'employee__department')

            for doc in docs:
                emp = doc.employee
                msg = (
                    f"Document '{doc.title}' for {emp.get_full_name()} "
                    f"({emp.department.name if emp.department else 'No dept'}) "
                    f"expires in {days} days ({doc.expiry_date})."
                )
                if doc.expiry_note:
                    msg += f" Note: {doc.expiry_note}"

                # Notify all HR users and superusers
                hr_users = User.objects.filter(
                    employee__role__in=['hr', 'admin_director', 'medical_director', 'finance_director', 'ceo'],
                    is_active=True,
                ) | User.objects.filter(is_superuser=True, is_active=True)

                for hr_user in hr_users.distinct():
                    notify(
                        hr_user,
                        title=f"Document Expiry in {days} days — {emp.get_full_name()}",
                        message=msg,
                        notification_type='system',
                        url=f'/accounts/employees/{emp.pk}/history/#documents',
                    )
                notified += 1
                self.stdout.write(f"  Notified: {doc.title} — {emp.get_full_name()} ({days}d)")

        self.stdout.write(self.style.SUCCESS(f'Done. {notified} document expiry notification(s) sent.'))
