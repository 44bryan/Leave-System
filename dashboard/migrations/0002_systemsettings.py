from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_add_auditlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payroll_enabled', models.BooleanField(
                    default=False,
                    help_text='Allow HR to upload payslips and employees to view pay history.',
                )),
            ],
            options={
                'verbose_name': 'System Settings',
            },
        ),
    ]
