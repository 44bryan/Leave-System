from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Employee
from notifications.utils import notify

ACTING_ROLE_LABELS = {
    'admin_director':       'Acting Administration Director',
    'finance_director':     'Acting Finance Director',
    'medical_director':     'Acting Medical Director',
    'manager':              'Acting Line Manager',
    'unit_head':            'Acting Unit Head',
    'nurse_superintendent': 'Acting Nurse Superintendent',
    'hr':                   'Acting HR',
}


class Command(BaseCommand):
    help = 'Clear expired acting role assignments and notify affected employees.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        expired = Employee.objects.filter(
            acting_role__gt='',
            acting_until__lt=today,
            is_active=True,
        ).select_related('user')

        count = 0
        for emp in expired:
            role_label = ACTING_ROLE_LABELS.get(emp.acting_role, emp.acting_role)
            self.stdout.write(f'Clearing acting role for {emp.get_full_name()} ({role_label}, expired {emp.acting_until})')

            notify(
                emp.user,
                f'Acting Role Ended — {role_label}',
                f'Your acting assignment as {role_label} ended on {emp.acting_until}. '
                f'Your regular role and responsibilities have been restored. '
                f'Thank you for covering during this period.',
                notification_type='leave_approved',
            )

            emp.acting_role  = ''
            emp.acting_for   = None
            emp.acting_since = None
            emp.acting_until = None
            emp.save(update_fields=['acting_role', 'acting_for', 'acting_since', 'acting_until'])
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Cleared {count} expired acting role(s).'))
