from django.db import models
from django.utils import timezone
from accounts.models import Employee


class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_document = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default='primary')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_MANAGER_APPROVED = 'manager_approved'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED_MANAGER = 'rejected_manager'
    STATUS_REJECTED_HR = 'rejected_hr'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Manager Approval'),
        (STATUS_MANAGER_APPROVED, 'Pending HR Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED_MANAGER, 'Rejected by Manager'),
        (STATUS_REJECTED_HR, 'Rejected by HR'),
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

    # Manager action
    manager_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manager_actions'
    )
    manager_action_date = models.DateTimeField(null=True, blank=True)
    manager_remarks = models.TextField(blank=True)

    # HR action
    hr_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hr_actions'
    )
    hr_action_date = models.DateTimeField(null=True, blank=True)
    hr_remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.total_days = delta.days + 1
        super().save(*args, **kwargs)

    def get_status_badge(self):
        badges = {
            'pending': 'warning',
            'manager_approved': 'info',
            'approved': 'success',
            'rejected_manager': 'danger',
            'rejected_hr': 'danger',
            'cancelled': 'secondary',
        }
        return badges.get(self.status, 'secondary')

    def get_status_icon(self):
        icons = {
            'pending': 'clock',
            'manager_approved': 'hourglass-split',
            'approved': 'check-circle',
            'rejected_manager': 'x-circle',
            'rejected_hr': 'x-circle',
            'cancelled': 'slash-circle',
        }
        return icons.get(self.status, 'circle')

    def can_cancel(self):
        return self.status in (self.STATUS_PENDING, self.STATUS_MANAGER_APPROVED)

    def is_active(self):
        from datetime import date
        return self.status == self.STATUS_APPROVED and self.start_date <= date.today() <= self.end_date


class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.PositiveIntegerField()
    total_entitlement = models.PositiveIntegerField(default=18)

    class Meta:
        unique_together = ('employee', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.employee} - {self.year}"

    @property
    def used_days(self):
        approved = self.employee.leave_requests.filter(
            status='approved',
            start_date__year=self.year
        ).aggregate(total=models.Sum('total_days'))['total'] or 0
        return approved

    @property
    def remaining_days(self):
        return max(0, self.total_entitlement - self.used_days)

    @property
    def usage_percentage(self):
        if self.total_entitlement == 0:
            return 0
        return round((self.used_days / self.total_entitlement) * 100)
