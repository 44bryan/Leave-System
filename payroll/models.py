from django.db import models
from django.contrib.auth.models import User
from accounts.models import Employee

MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'),
    (4, 'April'), (5, 'May'), (6, 'June'),
    (7, 'July'), (8, 'August'), (9, 'September'),
    (10, 'October'), (11, 'November'), (12, 'December'),
]


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    period_month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    period_year = models.PositiveIntegerField()

    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)

    # Allowances
    transport_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowances_label = models.CharField(max_length=100, blank=True)

    # Deductions
    cnps = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='CNPS')
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Income Tax')
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions_label = models.CharField(max_length=100, blank=True)

    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payslip_file = models.FileField(upload_to='payslips/%Y/', null=True, blank=True,
                                    help_text='Optional: upload signed PDF payslip')
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='payslips_uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'period_month', 'period_year')
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.get_period_month_display()} {self.period_year}"

    @property
    def total_allowances(self):
        return self.transport_allowance + self.housing_allowance + self.other_allowances

    @property
    def total_deductions(self):
        return self.cnps + self.income_tax + self.other_deductions

    def save(self, *args, **kwargs):
        self.net_salary = self.gross_salary + self.total_allowances - self.total_deductions
        super().save(*args, **kwargs)
