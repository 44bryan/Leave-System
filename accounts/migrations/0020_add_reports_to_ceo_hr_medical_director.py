from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_employee_reports_to_director'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='reports_to_ceo',
            field=models.BooleanField(
                default=False,
                help_text='Skip all intermediate steps. Leave goes directly to CEO for sole approval.'
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='reports_to_hr',
            field=models.BooleanField(
                default=False,
                help_text='Skip Unit Head and Line Manager steps. HR is the FINAL approver — no Director step needed.'
            ),
        ),
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(
                choices=[
                    ('employee', 'Employee'),
                    ('unit_head', 'Unit Head'),
                    ('manager', 'Line Manager'),
                    ('hr', 'HR Admin'),
                    ('admin_director', 'Administration Director'),
                    ('medical_director', 'Medical Director'),
                    ('finance_director', 'Finance Director'),
                    ('ceo', 'CEO'),
                    ('intern', 'Intern'),
                    ('wacs_resident', 'WACS Resident / Trainee'),
                    ('super_admin', 'System Administrator'),
                ],
                default='employee',
                max_length=20,
            ),
        ),
    ]
