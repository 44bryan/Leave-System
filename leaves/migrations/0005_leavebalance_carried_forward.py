from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0004_seed_default_leave_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='leavebalance',
            name='carried_forward',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Unused days carried over from the previous year (accumulated leave).',
            ),
        ),
    ]
