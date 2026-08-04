from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0010_nurse_supt_approval_stage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TentativeLeavePlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveIntegerField()),
                ('planned_start', models.DateField()),
                ('planned_end', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Draft'),
                        ('submitted', 'Submitted to Manager'),
                        ('confirmed', 'Manager Confirmed'),
                        ('rejected', 'Rejected by Manager'),
                    ],
                    default='draft', max_length=20,
                )),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('manager_notes', models.TextField(blank=True)),
                ('manager_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tentative_plans',
                    to='accounts.employee',
                )),
                ('leave_type', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='leaves.leavetype',
                )),
                ('manager_confirmed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='confirmed_tentative_plans',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['planned_start']},
        ),
    ]
