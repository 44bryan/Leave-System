from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_employeedocument_expiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='marital_status',
            field=models.CharField(
                blank=True,
                choices=[('single', 'Single'), ('married', 'Married')],
                default='single',
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name='HealthDependant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relation', models.CharField(
                    choices=[
                        ('spouse',      'Spouse'),
                        ('child_ben',   'Child — Beneficiary (≤18 yrs)'),
                        ('child_other', 'Child — Non-Beneficiary'),
                    ],
                    max_length=15,
                )),
                ('full_name', models.CharField(max_length=200)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='health_dependants',
                    to='accounts.employee',
                )),
            ],
            options={'ordering': ['relation', 'full_name']},
        ),
    ]
