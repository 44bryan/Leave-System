from django.db import models
from django.utils import timezone
from accounts.models import Employee


class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_document = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default='primary')
    is_active = models.BooleanField(default=True)
    is_deductible = models.BooleanField(
        default=True,
        help_text="If checked, approved days are subtracted from annual leave balance."
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_UNIT_HEAD_APPROVED = 'unit_head_approved'
    STATUS_MANAGER_APPROVED = 'manager_approved'
    STATUS_NURSE_SUPT_APPROVED = 'nurse_supt_approved'
    STATUS_HR_APPROVED = 'hr_approved'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED_UNIT_HEAD = 'rejected_unit_head'
    STATUS_REJECTED_MANAGER = 'rejected_manager'
    STATUS_REJECTED_NURSE_SUPT = 'rejected_nurse_supt'
    STATUS_REJECTED_HR = 'rejected_hr'
    STATUS_REJECTED_DIRECTOR = 'rejected_director'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_UNIT_HEAD_APPROVED, 'Pending Manager Approval'),
        (STATUS_MANAGER_APPROVED, 'Pending Nurse Superintendent / HR Approval'),
        (STATUS_NURSE_SUPT_APPROVED, 'Pending HR Approval'),
        (STATUS_HR_APPROVED, 'Pending Director Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED_UNIT_HEAD, 'Rejected by Unit Head'),
        (STATUS_REJECTED_MANAGER, 'Rejected by Manager'),
        (STATUS_REJECTED_NURSE_SUPT, 'Rejected by Nurse Superintendent'),
        (STATUS_REJECTED_HR, 'Rejected by HR'),
        (STATUS_REJECTED_DIRECTOR, 'Rejected by Director'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField(default=0)
    reason = models.TextField()
    supporting_document = models.FileField(upload_to='leave_docs/', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    backup_employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='backup_leaves',
        help_text='Colleague covering during this leave.'
    )

    # Unit Head action (optional first step)
    unit_head_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unit_head_actions'
    )
    unit_head_action_date = models.DateTimeField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Manager action
    manager_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manager_actions'
    )
    manager_action_date = models.DateTimeField(null=True, blank=True)
    manager_remarks = models.TextField(blank=True)

    # Nurse Superintendent action (optional — only for nursing staff)
    nurse_supt_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='nurse_supt_actions'
    )
    nurse_supt_action_date = models.DateTimeField(null=True, blank=True)
    nurse_supt_remarks = models.TextField(blank=True)

    # HR action
    hr_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hr_actions'
    )
    hr_action_date = models.DateTimeField(null=True, blank=True)
    hr_remarks = models.TextField(blank=True)

    # Administration Director action (final approval)
    director_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='director_actions'
    )
    director_action_date = models.DateTimeField(null=True, blank=True)
    director_remarks = models.TextField(blank=True)

    # Signature snapshots — stored at approval time, permanent regardless of redeploys
    employee_sig_b64    = models.TextField(blank=True, default='')
    unit_head_sig_b64   = models.TextField(blank=True, default='')
    manager_sig_b64     = models.TextField(blank=True, default='')
    nurse_supt_sig_b64  = models.TextField(blank=True, default='')
    hr_sig_b64          = models.TextField(blank=True, default='')
    director_sig_b64    = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.total_days = self._count_working_days(self.start_date, self.end_date)
        super().save(*args, **kwargs)

    @staticmethod
    def _count_working_days(start, end):
        """Count Mon–Fri (exclude Saturday and Sunday) between start and end inclusive."""
        from datetime import timedelta
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # 0=Mon … 4=Fri
                count += 1
            current += timedelta(days=1)
        return count

    def get_status_badge(self):
        badges = {
            'pending': 'warning',
            'unit_head_approved': 'info',
            'manager_approved': 'info',
            'nurse_supt_approved': 'info',
            'hr_approved': 'primary',
            'approved': 'success',
            'rejected_unit_head': 'danger',
            'rejected_manager': 'danger',
            'rejected_nurse_supt': 'danger',
            'rejected_hr': 'danger',
            'rejected_director': 'danger',
            'cancelled': 'secondary',
        }
        return badges.get(self.status, 'secondary')

    def get_status_icon(self):  # noqa
        icons = {
            'pending': 'clock',
            'unit_head_approved': 'hourglass-split',
            'manager_approved': 'hourglass-split',
            'nurse_supt_approved': 'hourglass-split',
            'hr_approved': 'hourglass-split',
            'approved': 'check-circle',
            'rejected_unit_head': 'x-circle',
            'rejected_manager': 'x-circle',
            'rejected_nurse_supt': 'x-circle',
            'rejected_hr': 'x-circle',
            'rejected_director': 'x-circle',
            'cancelled': 'slash-circle',
        }
        return icons.get(self.status, 'circle')

    def can_cancel(self):
        return self.status in (
            self.STATUS_PENDING, self.STATUS_UNIT_HEAD_APPROVED,
            self.STATUS_MANAGER_APPROVED, self.STATUS_NURSE_SUPT_APPROVED,
            self.STATUS_HR_APPROVED
        )

    def is_active(self):
        from datetime import date
        return self.status == self.STATUS_APPROVED and self.start_date <= date.today() <= self.end_date


class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.PositiveIntegerField()
    total_entitlement = models.PositiveIntegerField(default=18)
    carried_forward = models.PositiveIntegerField(
        default=0,
        help_text="Unused days carried over from the previous year (accumulated leave)."
    )

    class Meta:
        unique_together = ('employee', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.employee} - {self.year}"

    @property
    def total_available(self):
        """Annual entitlement + accumulated days carried forward from prior year."""
        return self.total_entitlement + self.carried_forward

    @property
    def used_days(self):
        approved = self.employee.leave_requests.filter(
            status='approved',
            start_date__year=self.year,
            leave_type__is_deductible=True
        ).aggregate(total=models.Sum('total_days'))['total'] or 0
        return approved

    @property
    def remaining_days(self):
        return max(0, self.total_available - self.used_days)

    @property
    def usage_percentage(self):
        if self.total_available == 0:
            return 0
        return round((self.used_days / self.total_available) * 100)

    def non_deductible_by_type(self):
        """Returns list of {name, days} for approved non-deductible leaves this year."""
        from django.db.models import Sum
        rows = (
            self.employee.leave_requests
            .filter(status='approved', start_date__year=self.year, leave_type__is_deductible=False)
            .values('leave_type__name')
            .annotate(days=Sum('total_days'))
            .order_by('leave_type__name')
        )
        return [{'name': r['leave_type__name'], 'days': r['days']} for r in rows]

    def non_deductible_total(self):
        from django.db.models import Sum
        return (
            self.employee.leave_requests
            .filter(status='approved', start_date__year=self.year, leave_type__is_deductible=False)
            .aggregate(total=Sum('total_days'))['total'] or 0
        )


class LeaveConsultation(models.Model):
    """Private guidance request from an approver to a senior colleague before deciding on a leave."""
    STATUS_PENDING = 'pending'
    STATUS_PROCEED = 'proceed'
    STATUS_HOLD    = 'hold'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Awaiting Response'),
        (STATUS_PROCEED, 'Proceed — Approve'),
        (STATUS_HOLD,    'Hold — Do Not Approve Yet'),
    ]

    leave_request  = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                       related_name='consultations')
    requested_by   = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                       related_name='consultations_sent')
    consulted_with = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                       related_name='consultations_received')
    private_note   = models.TextField(help_text='Private note — NOT visible to the employee.')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                      default=STATUS_PENDING)
    response_note  = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    responded_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (f'Consultation #{self.pk}: {self.requested_by} → {self.consulted_with} '
                f'[{self.leave_request}] ({self.status})')


class LeaveReversal(models.Model):
    """Audit trail for every HR-initiated leave reversal or modification."""
    ACTION_REVERSE  = 'reversed'
    ACTION_MODIFIED = 'modified'
    ACTION_CHOICES = [
        (ACTION_REVERSE,  'Leave Reversed / Cancelled'),
        (ACTION_MODIFIED, 'Leave Dates Modified'),
    ]

    leave_request    = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                         related_name='reversals')
    action_type      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason           = models.TextField(help_text='Mandatory reason for this reversal/modification.')
    reversed_by      = models.ForeignKey('auth.User',
                                         on_delete=models.SET_NULL, null=True,
                                         related_name='leave_reversals_made')
    reversed_at      = models.DateTimeField(auto_now_add=True)

    # Snapshot of values BEFORE the change
    original_status      = models.CharField(max_length=30)
    original_start_date  = models.DateField()
    original_end_date    = models.DateField()
    original_total_days  = models.PositiveIntegerField()

    # New values — only populated for modifications
    new_start_date  = models.DateField(null=True, blank=True)
    new_end_date    = models.DateField(null=True, blank=True)
    new_total_days  = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-reversed_at']

    def __str__(self):
        return (f'{self.get_action_type_display()} — '
                f'{self.leave_request.employee.get_full_name()} '
                f'(#{self.leave_request.pk}) by {self.reversed_by}')
