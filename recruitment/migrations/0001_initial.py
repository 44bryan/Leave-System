from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JobPosting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('location', models.CharField(blank=True, default='', max_length=100)),
                ('employment_type', models.CharField(choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'), ('contract', 'Contract'), ('internship', 'Internship')], default='full_time', max_length=20)),
                ('description', models.TextField()),
                ('requirements', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')], default='draft', max_length=10)),
                ('deadline', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.department')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_postings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FormFieldConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=80)),
                ('label', models.CharField(max_length=150)),
                ('field_type', models.CharField(choices=[('text', 'Short Text'), ('textarea', 'Long Text / Paragraph'), ('number', 'Number'), ('select', 'Dropdown / Select'), ('yesno', 'Yes / No'), ('file', 'File Upload'), ('date', 'Date')], default='text', max_length=20)),
                ('is_enabled', models.BooleanField(default=True)),
                ('is_required', models.BooleanField(default=False)),
                ('field_order', models.PositiveIntegerField(default=99)),
                ('options', models.TextField(blank=True, help_text='Comma-separated options for dropdown fields')),
                ('is_custom', models.BooleanField(default=False, help_text='True for HR-added custom fields')),
                ('placeholder', models.CharField(blank=True, max_length=200)),
                ('posting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='form_fields', to='recruitment.jobposting')),
            ],
            options={
                'ordering': ['field_order', 'pk'],
                'unique_together': {('posting', 'field_name')},
            },
        ),
        migrations.CreateModel(
            name='ScoringCriterion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(help_text='The field name to evaluate', max_length=80)),
                ('label', models.CharField(help_text='Short description of this rule', max_length=150)),
                ('condition', models.CharField(choices=[('equals', 'Equals (exact match)'), ('contains', 'Contains (partial match)'), ('gte', 'Greater than or equal to (numbers)'), ('lte', 'Less than or equal to (numbers)'), ('yes', 'Answer is Yes'), ('no', 'Answer is No')], max_length=20)),
                ('value', models.CharField(blank=True, help_text='Value to compare against (leave blank for yes/no conditions)', max_length=200)),
                ('points', models.IntegerField(help_text='Points awarded when condition is met')),
                ('posting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scoring_criteria', to='recruitment.jobposting')),
            ],
            options={
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applicant_name', models.CharField(max_length=150)),
                ('applicant_email', models.EmailField(max_length=254)),
                ('cv_file', models.FileField(upload_to='recruitment/cvs/%Y/%m/')),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('under_review', 'Under Review'), ('shortlisted', 'Shortlisted'), ('interview', 'Interview Scheduled'), ('hired', 'Hired'), ('rejected', 'Rejected')], default='submitted', max_length=20)),
                ('score', models.FloatField(default=0)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('hr_notes', models.TextField(blank=True)),
                ('interview_date', models.DateTimeField(blank=True, null=True)),
                ('interview_notes', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('posting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='recruitment.jobposting')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_applications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-score', '-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='ApplicationAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=80)),
                ('value', models.TextField(blank=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='recruitment.application')),
            ],
            options={
                'unique_together': {('application', 'field_name')},
            },
        ),
    ]
