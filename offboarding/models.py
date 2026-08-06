from django.db import models
from django.contrib.auth.models import User


class ExitRequest(models.Model):
    EXIT_TYPES = [
        ('resignation',  'Resignation'),
        ('retirement',   'Retirement'),
        ('termination',  'Termination'),
        ('transfer',     'Transfer'),
        ('contract_end', 'Contract End'),
    ]
    STATUS_CHOICES = [
        ('pending',      'Pending Clearance'),
        ('in_progress',  'In Progress'),
        ('completed',    'Completed'),
        ('cancelled',    'Cancelled'),
    ]

    employee     = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE, related_name='exit_requests')
    exit_type    = models.CharField(max_length=20, choices=EXIT_TYPES)
    exit_date    = models.DateField(help_text='Last working day')
    reason       = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    initiated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='exits_initiated',
        help_text='HR/manager who opened this request',
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    notes        = models.TextField(blank=True, help_text='HR internal notes')

    # Exit interview
    interview_date     = models.DateField(null=True, blank=True)
    interview_feedback = models.TextField(blank=True)
    interview_done     = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.employee.get_full_name()} — {self.get_exit_type_display()} ({self.exit_date})'

    @property
    def tasks_total(self):
        return self.tasks.count()

    @property
    def tasks_done(self):
        return self.tasks.filter(completed=True).count()

    @property
    def completion_pct(self):
        t = self.tasks_total
        return int((self.tasks_done / t) * 100) if t else 0


class OffboardingTask(models.Model):
    OWNER_CHOICES = [
        ('hr',       'HR Department'),
        ('it',       'IT Department'),
        ('finance',  'Finance'),
        ('manager',  'Line Manager'),
        ('employee', 'Employee'),
        ('security', 'Security'),
    ]

    exit_request = models.ForeignKey(ExitRequest, on_delete=models.CASCADE, related_name='tasks')
    title        = models.CharField(max_length=200)
    owner        = models.CharField(max_length=20, choices=OWNER_CHOICES, default='hr')
    completed    = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='offboarding_tasks_done',
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes        = models.CharField(max_length=300, blank=True)
    order        = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


# Default checklist items created when an exit is opened
DEFAULT_TASKS = [
    ('Return staff ID / access badge',          'security', 0),
    ('Return hospital equipment / devices',     'it',       1),
    ('IT account deactivation',                 'it',       2),
    ('Handover of duties / knowledge transfer', 'manager',  3),
    ('Final salary & benefits computation',     'finance',  4),
    ('NSSF / pension clearance',                'finance',  5),
    ('Return department keys',                  'security', 6),
    ('Exit interview completed',                'hr',       7),
    ('Employee file archived',                  'hr',       8),
]
