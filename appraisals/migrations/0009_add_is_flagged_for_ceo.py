from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0008_add_independent_scores'),
    ]

    operations = [
        migrations.AddField(
            model_name='appraisalrecord',
            name='is_flagged_for_ceo',
            field=models.BooleanField(default=False),
        ),
    ]
