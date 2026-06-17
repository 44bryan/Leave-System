from django.db import migrations


class Migration(migrations.Migration):
    """Merge the stub 0021_add_cycle_deadline_and_hr_unlock branch
    with the 0021_onboardingchecklist → 0022_employee_2fa branch."""

    dependencies = [
        ('accounts', '0021_add_cycle_deadline_and_hr_unlock'),
        ('accounts', '0022_employee_2fa'),
    ]

    operations = []
