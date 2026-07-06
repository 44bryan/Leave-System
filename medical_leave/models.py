from django.db import models
from django.utils import timezone
from accounts.models import Employee


class MedicalSickLeave(models.Model):
    STATUS_PENDING_LINE_MANAGER = 'pending_line_manager'
    STATUS_PENDING_HR = 'pending_hr'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED_LINE_MANAGER = 'rejected_line_manager'
    STATUS_REJECTED_HR = 'rejected_hr'

    STATUS_CHOICES = [
        (STATUS_PENDING_LINE_MANAGER, 'Pending Line Manager Endorsement'),
        (STATUS_PENDING_HR, 'Pending HR Endorsement'),
        (STATUS_APPROVED, 'Fully Endorsed'),
        (STATUS_REJECTED_LINE_MANAGER, 'Rejected by Line Manager'),
        (STATUS_REJECTED_HR, 'Rejected by HR'),
    ]

    # Core fields
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='medical_sick_leaves',
        verbose_name='Patient / Employee'
    )
    issued_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True,
        related_name='medical_sick_leaves_issued',
        verbose_name='Issuing Physician'
    )
    date_of_issuance = models.DateField(default=timezone.localdate)
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, help_text='Optional medical notes (internal use only, not printed).')

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING_LINE_MANAGER)

    # Line Manager endorsement
    line_manager_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medical_leave_lm_actions'
    )
    line_manager_action_date = models.DateTimeField(null=True, blank=True)
    line_manager_remarks = models.TextField(blank=True)

    # HR endorsement
    hr_action_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medical_leave_hr_actions'
    )
    hr_action_date = models.DateTimeField(null=True, blank=True)
    hr_remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_of_issuance', '-created_at']
        verbose_name = 'Medical Sick Leave'
        verbose_name_plural = 'Medical Sick Leaves'

    def __str__(self):
        return (f"Medical Sick Leave — {self.employee.get_full_name()} "
                f"({self.start_date} → {self.end_date})")

    @staticmethod
    def _count_working_days(start, end):
        """Count Mon–Fri between start and end inclusive (same logic as LeaveRequest)."""
        from datetime import timedelta
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # 0=Mon … 4=Fri
                count += 1
            current += timedelta(days=1)
        return count

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.days_count = self._count_working_days(self.start_date, self.end_date)
        super().save(*args, **kwargs)

    def get_status_badge(self):
        return {
            self.STATUS_PENDING_LINE_MANAGER: 'warning',
            self.STATUS_PENDING_HR: 'info',
            self.STATUS_APPROVED: 'success',
            self.STATUS_REJECTED_LINE_MANAGER: 'danger',
            self.STATUS_REJECTED_HR: 'danger',
        }.get(self.status, 'secondary')

    def is_fully_endorsed(self):
        return self.status == self.STATUS_APPROVED
