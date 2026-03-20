from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


_category_validator = RegexValidator(
    regex=r'^(?:[1-9]|1[0-2])[A-Z]{0,3}$',
    message='Enter a valid category: a number 1–12 followed by optional letters (e.g. 5, 12, 12A, 12AB, 12AL).'
)


class Employee(models.Model):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('unit_head', 'Unit Head'),
        ('manager', 'Line Manager'),
        ('hr', 'HR Admin'),
        ('admin_director', 'Administration Director'),
        ('finance_director', 'Finance Director'),
        ('ceo', 'CEO'),
        ('intern', 'Intern'),
        ('wacs_resident', 'WACS Resident / Trainee'),
        ('super_admin', 'System Administrator'),
    ]

    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    staff_category = models.CharField(
        max_length=6, blank=True, default='',
        validators=[_category_validator],
        help_text='Category 1–12 with optional letter suffix (e.g. 5, 12, 12A, 12AB, 12AL)'
    )
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates'
    )
    unit_head = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unit_head_of',
        help_text='Optional Unit Head who approves before the Line Manager.'
    )
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined_company = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=6, choices=SEX_CHOICES, blank=True, default='')
    nationality = models.CharField(max_length=80, blank=True, default='')
    contract_number = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Official contract reference number'
    )
    qualifications = models.TextField(blank=True, default='', help_text='Academic and professional qualifications')
    signature = models.FileField(upload_to='signatures/', null=True, blank=True, help_text='Scanned signature image used on official PDF forms')
    signature_b64 = models.TextField(blank=True, default='', help_text='Base64 PNG of signature — persists across Railway redeploys')
    is_active = models.BooleanField(default=True)
    dismissal_date = models.DateField(null=True, blank=True, help_text='Date dismissal was issued — account deactivated after 14 days')
    # Intern-specific fields
    school_name = models.CharField(max_length=200, blank=True, default='', help_text='Name of university or school (interns only)')
    speciality = models.CharField(max_length=200, blank=True, default='', help_text='Field of study or speciality (interns only)')

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username

    def is_hr(self):
        return self.role == 'hr'

    def is_unit_head(self):
        return self.role == 'unit_head'

    def is_manager(self):
        return self.role == 'manager'

    def is_director(self):
        """Admin Director and Finance Director share the same operational role."""
        return self.role in ('admin_director', 'finance_director')

    def is_finance_director(self):
        return self.role == 'finance_director'

    def is_ceo(self):
        return self.role == 'ceo'

    def is_intern(self):
        return self.role == 'intern'

    def is_wacs_resident(self):
        return self.role == 'wacs_resident'

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
            'unit_head': 'info',
            'manager': 'primary',
            'hr': 'success',
            'admin_director': 'danger',
            'finance_director': 'danger',
            'ceo': 'dark',
            'intern': 'info',
            'wacs_resident': 'warning',
            'super_admin': 'dark',
        }
        if self.user.is_superuser:
            return 'dark'
        return badges.get(self.role, 'secondary')

    def get_effective_role_display(self):
        """Returns 'System Administrator' for superusers regardless of employee role."""
        if self.user.is_superuser:
            return 'System Administrator'
        return self.get_role_display()
