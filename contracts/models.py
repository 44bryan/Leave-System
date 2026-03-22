from django.db import models
from django.contrib.auth.models import User
from datetime import date
from accounts.models import Employee


class Contract(models.Model):
    CONTRACT_TYPE_CHOICES = [
        ('CDI',    'CDI — Permanent (Contrat à Durée Indéterminée)'),
        ('CDD',    'CDD — Fixed Term (Contrat à Durée Déterminée)'),
        ('INTERN', 'Internship'),
        ('WACS',   'Residents'),
    ]
    INTERNSHIP_TYPE_CHOICES = [
        ('academic',        'Academic Internship'),
        ('professional',    'Professional Internship'),
        ('pre_employment',  'Pre-Employment Internship'),
        ('vocational',      'Vocational / Technical Internship'),
        ('observation',     'Observation / Discovery Internship'),
        ('other',           'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('renewed', 'Renewed'),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='contracts'
    )
    contract_number = models.CharField(max_length=50, blank=True, default='', help_text='Official contract reference number')
    contract_type = models.CharField(max_length=10, choices=CONTRACT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(
        null=True, blank=True,
        help_text="Required for CDD. Leave blank for CDI (permanent)."
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    internship_type = models.CharField(
        max_length=20, choices=INTERNSHIP_TYPE_CHOICES, blank=True, default='',
        help_text='Type of internship — only applicable for INTERN contracts'
    )
    working_department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contract_placements',
        help_text='Department where the intern or resident will be working'
    )
    notes = models.TextField(blank=True)

    # Renewal chain — points to the contract this one replaced
    renewed_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='renewals'
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='contracts_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return (
            f"{self.get_contract_type_display()} — "
            f"{self.employee.get_full_name()} "
            f"(from {self.start_date})"
        )

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def _has_end_date(self):
        return self.contract_type in ('CDD', 'INTERN', 'WACS') and self.end_date

    @property
    def days_remaining(self):
        if not self._has_end_date:
            return None
        delta = (self.end_date - date.today()).days
        return max(0, delta)

    @property
    def months_remaining(self):
        if not self._has_end_date:
            return None
        today = date.today()
        if self.end_date <= today:
            return 0
        months = (self.end_date.year - today.year) * 12 + (self.end_date.month - today.month)
        if self.end_date.day < today.day:
            months -= 1
        return max(0, months)

    @property
    def is_expired(self):
        if self._has_end_date:
            return self.end_date < date.today()
        return False

    @property
    def is_expiring_soon(self):
        """True if contract expires within 60 days."""
        if not self._has_end_date:
            return False
        return 0 < self.days_remaining <= 60

    @property
    def years_of_service(self):
        """Years since contract start date."""
        today = date.today()
        years = today.year - self.start_date.year
        if (today.month, today.day) < (self.start_date.month, self.start_date.day):
            years -= 1
        return max(0, years)

    @property
    def duration_display(self):
        if self.contract_type == 'CDI':
            return "Permanent (no fixed end date)"
        m = self.months_remaining
        d = self.days_remaining
        if d is None:
            return "—"
        if d == 0:
            return "Expired"
        if m and m > 0:
            leftover_days = d - (m * 30)
            if leftover_days > 0:
                return f"{m} month{'s' if m != 1 else ''}, ~{leftover_days} day{'s' if leftover_days != 1 else ''} remaining"
            return f"{m} month{'s' if m != 1 else ''} remaining"
        return f"{d} day{'s' if d != 1 else ''} remaining"

    @property
    def urgency_class(self):
        if self.is_expired:
            return "danger"
        if self.contract_type == 'CDD' and self.days_remaining is not None:
            if self.days_remaining <= 30:
                return "danger"
            if self.days_remaining <= 60:
                return "warning"
        return "success"


class ContractNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('renewed', 'Contract Renewed'),
        ('terminated', 'Contract Terminated'),
        ('expiry_warning', 'Expiry Warning'),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='contract_notifications'
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} — {self.employee.get_full_name()}"
