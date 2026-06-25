import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0026_employee_health_insurance'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecognitionProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recognition_type', models.CharField(choices=[('staff_of_month', 'Staff of the Month'), ('employee_of_quarter', 'Employee of the Quarter'), ('best_performer', 'Best Performer'), ('long_service', 'Long Service Award'), ('innovation', 'Innovation Award'), ('excellence', 'Excellence Award'), ('other', 'Other / Custom')], max_length=30)),
                ('custom_title', models.CharField(blank=True, help_text='Required when type is "Other / Custom".', max_length=120)),
                ('description', models.TextField(help_text='Why does this employee deserve this recognition?')),
                ('status', models.CharField(choices=[('proposed', 'Proposed'), ('endorsed', 'Endorsed'), ('executed', 'Executed'), ('rejected', 'Rejected')], default='proposed', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('execution_note', models.TextField(blank=True, help_text='HR note on how the recognition was delivered.')),
                ('executed_at', models.DateTimeField(blank=True, null=True)),
                ('rejected_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recognition_proposals', to='accounts.employee')),
                ('proposed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposed_recognitions', to=settings.AUTH_USER_MODEL)),
                ('executed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='executed_recognitions', to=settings.AUTH_USER_MODEL)),
                ('rejected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rejected_recognitions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RecognitionComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='recognition.recognitionproposal')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
