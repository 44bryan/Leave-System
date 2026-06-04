from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_profile_photo_any_staff_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='reports_to_director',
            field=models.BooleanField(
                default=False,
                help_text='Skip Unit Head and Line Manager approval steps. Leave goes directly to HR then Director. '
                          'Use for Admin staff, HR, and others who report directly to the Administration Director.'
            ),
        ),
    ]
