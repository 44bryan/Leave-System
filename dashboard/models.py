from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    ACTION_LOGIN         = 'login'
    ACTION_LOGOUT        = 'logout'
    ACTION_LEAVE_SUBMIT  = 'leave_submit'
    ACTION_LEAVE_APPROVE = 'leave_approve'
    ACTION_LEAVE_REJECT  = 'leave_reject'
    ACTION_CONTRACT      = 'contract'
    ACTION_DISCIPLINE    = 'discipline'
    ACTION_APPRAISAL     = 'appraisal'
    ACTION_EMPLOYEE      = 'employee'
    ACTION_OTHER         = 'other'

    ACTION_CHOICES = [
        (ACTION_LOGIN,         'Login'),
        (ACTION_LOGOUT,        'Logout'),
        (ACTION_LEAVE_SUBMIT,  'Leave Submitted'),
        (ACTION_LEAVE_APPROVE, 'Leave Approved'),
        (ACTION_LEAVE_REJECT,  'Leave Rejected'),
        (ACTION_CONTRACT,      'Contract Action'),
        (ACTION_DISCIPLINE,    'Discipline Action'),
        (ACTION_APPRAISAL,     'Appraisal Action'),
        (ACTION_EMPLOYEE,      'Employee Management'),
        (ACTION_OTHER,         'Other'),
    ]

    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action      = models.CharField(max_length=30, choices=ACTION_CHOICES, default=ACTION_OTHER)
    description = models.TextField()
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs_as_target')
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.get_action_display()} — {self.user}"

    @classmethod
    def log(cls, request, action, description, target_user=None):
        """Convenience class method to record an action from a request."""
        user = request.user if request.user.is_authenticated else None
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        ) or None
        cls.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip,
            target_user=target_user,
        )
