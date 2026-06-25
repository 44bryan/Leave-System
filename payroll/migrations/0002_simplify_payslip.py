from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='payslip', name='gross_salary'),
        migrations.RemoveField(model_name='payslip', name='transport_allowance'),
        migrations.RemoveField(model_name='payslip', name='housing_allowance'),
        migrations.RemoveField(model_name='payslip', name='other_allowances'),
        migrations.RemoveField(model_name='payslip', name='other_allowances_label'),
        migrations.RemoveField(model_name='payslip', name='cnps'),
        migrations.RemoveField(model_name='payslip', name='income_tax'),
        migrations.RemoveField(model_name='payslip', name='other_deductions'),
        migrations.RemoveField(model_name='payslip', name='other_deductions_label'),
        migrations.RemoveField(model_name='payslip', name='net_salary'),
    ]
