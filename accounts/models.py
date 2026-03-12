from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('manager', 'Line Manager'),
        ('hr', 'HR Admin'),
        ('admin_director', 'Administration Director'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates'
    )
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_joined_company = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username

    def is_hr(self):
        return self.role == 'hr'

    def is_manager(self):
        return self.role == 'manager'

    def is_director(self):
        return self.role == 'admin_director'

    def get_role_display_badge(self):
        badges = {
            'employee': 'secondary',
            'manager': 'primary',
            'hr': 'success',
            'admin_director': 'danger',
        }
        return badges.get(self.role, 'secondary')
