from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0008_add_leave_consultation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveReversal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('reversed', 'Leave Reversed / Cancelled'), ('modified', 'Leave Dates Modified')], max_length=20)),
                ('reason', models.TextField(help_text='Mandatory reason for this reversal/modification.')),
                ('reversed_at', models.DateTimeField(auto_now_add=True)),
                ('original_status', models.CharField(max_length=30)),
                ('original_start_date', models.DateField()),
                ('original_end_date', models.DateField()),
                ('original_total_days', models.PositiveIntegerField()),
                ('new_start_date', models.DateField(blank=True, null=True)),
                ('new_end_date', models.DateField(blank=True, null=True)),
                ('new_total_days', models.PositiveIntegerField(blank=True, null=True)),
                ('leave_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reversals', to='leaves.leaverequest')),
                ('reversed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leave_reversals_made', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-reversed_at']},
        ),
    ]
