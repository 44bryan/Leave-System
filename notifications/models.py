from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        ('leave_submitted',        'Leave Submitted'),
        ('leave_manager_approved', 'Leave Manager Approved'),
        ('leave_hr_approved',      'Leave HR Approved'),
        ('leave_approved',         'Leave Fully Approved'),
        ('leave_rejected',         'Leave Rejected'),
        ('leave_cancelled',        'Leave Cancelled'),
        ('discipline',             'Discipline Notice'),
        ('contract_issued',        'Contract Issued'),
        ('contract_renewed',       'Contract Renewed'),
        ('contract_terminated',    'Contract Terminated'),
        ('account_activated',      'Account Activated'),
        ('contract_expiry',        'Contract Expiry Alert'),
        ('birthday',               'Birthday Greeting'),
        ('system',                 'System'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='system_notifications'
    )
    title            = models.CharField(max_length=255)
    message          = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    url              = models.CharField(max_length=500, blank=True, default='')
    is_read          = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"

    def icon(self):
        return {
            'leave_submitted':        'bi-calendar-plus',
            'leave_manager_approved': 'bi-check-circle',
            'leave_hr_approved':      'bi-check-circle',
            'leave_approved':         'bi-check2-all',
            'leave_rejected':         'bi-x-circle',
            'leave_cancelled':        'bi-x-circle',
            'discipline':             'bi-exclamation-triangle-fill',
            'contract_issued':        'bi-file-earmark-text',
            'contract_renewed':       'bi-arrow-repeat',
            'contract_terminated':    'bi-file-earmark-x',
            'account_activated':      'bi-person-check-fill',
            'contract_expiry':        'bi-calendar-x-fill',
            'birthday':               'bi-cake2',
            'system':                 'bi-bell',
        }.get(self.notification_type, 'bi-bell')

    def badge_color(self):
        return {
            'leave_submitted':        '#0A4D68',
            'leave_manager_approved': '#059669',
            'leave_hr_approved':      '#059669',
            'leave_approved':         '#059669',
            'leave_rejected':         '#dc2626',
            'leave_cancelled':        '#6b7a8d',
            'discipline':             '#d97706',
            'contract_issued':        '#0891b2',
            'contract_renewed':       '#7c3aed',
            'contract_terminated':    '#dc2626',
            'account_activated':      '#059669',
            'contract_expiry':        '#dc2626',
            'birthday':               '#f59e0b',
            'system':                 '#374151',
        }.get(self.notification_type, '#374151')
