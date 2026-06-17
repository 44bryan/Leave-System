from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_onboardingchecklist'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='totp_secret',
            field=models.CharField(blank=True, default='', help_text='TOTP secret for 2FA', max_length=64),
        ),
        migrations.AddField(
            model_name='employee',
            name='totp_enabled',
            field=models.BooleanField(default=False, help_text='2FA enabled for this account'),
        ),
    ]
