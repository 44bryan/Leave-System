from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_employeedocument_expiry'),
        ('leaves', '0007_add_sig_b64_snapshots'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveConsultation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('private_note', models.TextField(help_text='Private note — NOT visible to the employee.')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Awaiting Response'),
                        ('proceed', 'Proceed — Approve'),
                        ('hold', 'Hold — Do Not Approve Yet'),
                    ],
                    default='pending', max_length=20,
                )),
                ('response_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('leave_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consultations',
                    to='leaves.leaverequest',
                )),
                ('requested_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consultations_sent',
                    to='accounts.employee',
                )),
                ('consulted_with', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consultations_received',
                    to='accounts.employee',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
