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
        ('unit_head', 'Unit Head'),
        ('manager', 'Line Manager'),
        ('hr', 'HR Admin'),
        ('admin_director', 'Administration Director'),
        ('medical_director', 'Medical Director'),
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
        max_length=20, blank=True, default='',
        help_text='Staff category (any format, e.g. 5, 12B-J, A, III)'
    )
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
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
    reports_to_director = models.BooleanField(
        default=False,
        help_text='Skip Unit Head and Line Manager steps. Leave goes directly to HR then Admin Director.'
    )
    reports_to_ceo = models.BooleanField(
        default=False,
        help_text='Skip all intermediate steps. Leave goes directly to CEO for sole approval.'
    )
    reports_to_hr = models.BooleanField(
        default=False,
        help_text='Skip Unit Head and Line Manager steps. HR is the FINAL approver — no Director step needed.'
    )
    is_active = models.BooleanField(default=True)
    dismissal_date = models.DateField(null=True, blank=True, help_text='Date dismissal was issued — account deactivated after 14 days')
    # Intern-specific fields
    school_name = models.CharField(max_length=200, blank=True, default='', help_text='Name of university or school (interns only)')
    speciality = models.CharField(max_length=200, blank=True, default='', help_text='Field of study or speciality (interns only)')

    # Two-Factor Authentication
    totp_secret = models.CharField(max_length=64, blank=True, default='', help_text='TOTP secret for 2FA')
    totp_enabled = models.BooleanField(default=False, help_text='2FA enabled for this account')

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

    def is_medical_director(self):
        return self.role == 'medical_director'

    def is_ceo(self):
        return self.role == 'ceo'

    def is_intern(self):
        return self.role == 'intern'

    def is_wacs_resident(self):
        return self.role == 'wacs_resident'

    def years_of_service(self):
        """Years since date_joined_company. None if not set."""
        if not self.date_joined_company:
            return None
        from datetime import date
        today = date.today()
        years = today.year - self.date_joined_company.year
        if (today.month, today.day) < (self.date_joined_company.month, self.date_joined_company.day):
            years -= 1
        return max(years, 0)

    def seniority_leave_entitlement(self):
        """
        Annual leave entitlement based on seniority (Cameroonian Labour Code):
          0–5 years  → 18 days
          6–10 years → 20 days
          11+ years  → 22 days
        Returns None if date_joined_company is not set.
        """
        years = self.years_of_service()
        if years is None:
            return None
        if years <= 5:
            return 18
        if years <= 10:
            return 20
        return 22

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

    def save(self, *args, **kwargs):
        dept_changed = False
        old_dept = None
        if self.pk:
            try:
                old = Employee.objects.get(pk=self.pk)
                if old.department_id != self.department_id:
                    dept_changed = True
                    old_dept = old.department
            except Employee.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if dept_changed:
            DepartmentHistory.objects.create(
                employee=self,
                from_department=old_dept,
                to_department=self.department,
            )


class EmployeeDocument(models.Model):
    CATEGORY_CHOICES = [
        ('id', 'ID Card / Passport'),
        ('contract', 'Contract Copy'),
        ('diploma', 'Diploma / Certificate'),
        ('medical', 'Medical Certificate'),
        ('other', 'Other'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='employee_docs/%Y/')
    expiry_date = models.DateField(null=True, blank=True, help_text='Leave blank if document does not expire.')
    expiry_note = models.CharField(max_length=200, blank=True, help_text='Optional reminder note about expiry.')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} — {self.employee.get_full_name()}'

    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        from datetime import date
        return (self.expiry_date - date.today()).days

    def expiry_status(self):
        """Returns 'expired', 'critical' (<30d), 'warning' (<90d), or 'ok'."""
        days = self.days_until_expiry()
        if days is None:
            return 'ok'
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'critical'
        if days <= 90:
            return 'warning'
        return 'ok'


class OnboardingChecklist(models.Model):
    """Auto-created when a new employee is added. HR ticks tasks off as they onboard."""
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='onboarding')
    issue_contract = models.BooleanField(default=False, verbose_name='Contract issued')
    set_leave_balance = models.BooleanField(default=False, verbose_name='Leave balance configured')
    assign_manager = models.BooleanField(default=False, verbose_name='Manager assigned')
    profile_photo = models.BooleanField(default=False, verbose_name='Profile photo uploaded')
    signature_captured = models.BooleanField(default=False, verbose_name='Signature captured')
    credentials_sent = models.BooleanField(default=False, verbose_name='Login credentials sent')
    id_document_uploaded = models.BooleanField(default=False, verbose_name='ID / Passport uploaded')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Onboarding — {self.employee.get_full_name()}"

    @property
    def completed_count(self):
        fields = ['issue_contract', 'set_leave_balance', 'assign_manager',
                  'profile_photo', 'signature_captured', 'credentials_sent', 'id_document_uploaded']
        return sum(1 for f in fields if getattr(self, f))

    @property
    def total_count(self):
        return 7

    @property
    def is_complete(self):
        return self.completed_count == self.total_count


class DepartmentHistory(models.Model):
    """Tracks every department transfer for an employee."""
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='department_history'
    )
    from_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transfers_from'
    )
    to_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transfers_to'
    )
    changed_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        frm = self.from_department or '(none)'
        to  = self.to_department or '(none)'
        return f'{self.employee.get_full_name()} — {frm} → {to} on {self.changed_at}'
