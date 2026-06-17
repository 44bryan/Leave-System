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
            name='Payslip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_month', models.PositiveSmallIntegerField(choices=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')])),
                ('period_year', models.PositiveIntegerField()),
                ('gross_salary', models.DecimalField(decimal_places=2, max_digits=12)),
                ('transport_allowance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('housing_allowance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('other_allowances', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('other_allowances_label', models.CharField(blank=True, max_length=100)),
                ('cnps', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='CNPS')),
                ('income_tax', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Income Tax')),
                ('other_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('other_deductions_label', models.CharField(blank=True, max_length=100)),
                ('net_salary', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('payslip_file', models.FileField(blank=True, help_text='Optional: upload signed PDF payslip', null=True, upload_to='payslips/%Y/')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='accounts.employee')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payslips_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-period_year', '-period_month'],
                'unique_together': {('employee', 'period_month', 'period_year')},
            },
        ),
    ]
