from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_add_reports_to_ceo_hr_medical_director'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnboardingChecklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('issue_contract', models.BooleanField(default=False, verbose_name='Contract issued')),
                ('set_leave_balance', models.BooleanField(default=False, verbose_name='Leave balance configured')),
                ('assign_manager', models.BooleanField(default=False, verbose_name='Manager assigned')),
                ('profile_photo', models.BooleanField(default=False, verbose_name='Profile photo uploaded')),
                ('signature_captured', models.BooleanField(default=False, verbose_name='Signature captured')),
                ('credentials_sent', models.BooleanField(default=False, verbose_name='Login credentials sent')),
                ('id_document_uploaded', models.BooleanField(default=False, verbose_name='ID / Passport uploaded')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='onboarding',
                    to='accounts.employee',
                )),
            ],
        ),
    ]
