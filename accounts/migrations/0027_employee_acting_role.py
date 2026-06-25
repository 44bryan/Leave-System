from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_employee_health_insurance'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='acting_role',
            field=models.CharField(blank=True, default='', help_text='Temporary role held while covering for a colleague on leave', max_length=20),
        ),
        migrations.AddField(
            model_name='employee',
            name='acting_for',
            field=models.ForeignKey(blank=True, help_text='The colleague this employee is currently covering for', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acting_delegates', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='employee',
            name='acting_since',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='acting_until',
            field=models.DateField(blank=True, null=True),
        ),
    ]
