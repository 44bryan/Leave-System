from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recognition', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recognitionproposal',
            name='certificate_file',
            field=models.FileField(blank=True, help_text='Optional: scanned certificate or award letter (PDF/image)', null=True, upload_to='recognition_certificates/'),
        ),
    ]
