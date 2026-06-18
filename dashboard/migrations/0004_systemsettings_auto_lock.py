from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_add_signatory_fields_to_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='contract_auto_lock_enabled',
            field=models.BooleanField(default=False, help_text='Automatically lock accounts of employees whose fixed-term contract expired with no renewal, after the grace period below.'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='contract_auto_lock_grace_days',
            field=models.IntegerField(default=60, help_text='Days after contract expiry before the account is auto-locked (default 60 = ~2 months).'),
        ),
    ]
