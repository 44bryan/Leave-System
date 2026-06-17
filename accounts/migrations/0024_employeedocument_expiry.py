from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_merge_0021_branches'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeedocument',
            name='expiry_date',
            field=models.DateField(
                blank=True, null=True,
                help_text='Leave blank if document does not expire.',
            ),
        ),
        migrations.AddField(
            model_name='employeedocument',
            name='expiry_note',
            field=models.CharField(
                blank=True, max_length=200,
                help_text='Optional reminder note about expiry.',
            ),
        ),
    ]
