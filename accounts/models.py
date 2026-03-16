from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


def _build_category_choices():
    """A–L, AA–AL, BA–BL staff classification categories."""
    letters = [chr(c) for c in range(ord('A'), ord('L') + 1)]
    choices = [(l, l) for l in letters]
    choices += [(f'A{l}', f'A{l}') for l in letters]
    choices += [(f'B{l}', f'B{l}') for l in letters]
    return choices


class Employee(models.Model):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('manager', 'Line Manager'),
        ('hr', 'HR Admin'),
        ('admin_director', 'Administration Director'),
    ]

    CATEGORY_CHOICES = _build_category_choices()

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    staff_category = models.CharField(
        max_length=3, choices=CATEGORY_CHOICES, blank=True, default='',
        help_text='Staff classification category (A–L, AA–AL, BA–BL)'
    )
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates'
    )
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
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

    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years

    def years_to_retirement(self):
        """Years remaining until retirement age (60). None if no date_of_birth."""
        a = self.age()
        if a is None:
            return None
        return max(0, 60 - a)

    def is_near_retirement(self):
        """True if within 5 years of retirement age (60)."""
        ytr = self.years_to_retirement()
        if ytr is None:
            return False
        return ytr <= 5

    def get_role_display_badge(self):
        badges = {
            'employee': 'secondary',
            'manager': 'primary',
            'hr': 'success',
            'admin_director': 'danger',
        }
        return badges.get(self.role, 'secondary')
