from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discipline', '0004_add_is_proposal_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='disciplinerecord',
            name='is_system_generated',
            field=models.BooleanField(
                default=False,
                help_text='Issued automatically by the system, not by a human. Does not count toward appraisal score.'
            ),
        ),
    ]
