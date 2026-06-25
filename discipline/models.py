from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from accounts.models import Employee


class DisciplineRecord(models.Model):
    ACTION_CHOICES = [
        ('verbal_warning', 'Verbal Warning'),
        ('written_caution', 'Written Caution'),
        ('final_warning', 'Final Written Warning'),
        ('suspension', 'Suspension'),
        ('dismissal', 'Dismissal'),
    ]

    RECOMMENDED_ACTION_CHOICES = [
        ('', '— No recommendation —'),
        ('written_caution', 'Written Caution'),
        ('final_warning', 'Final Written Warning'),
        ('suspension', 'Suspension'),
        ('dismissal', 'Dismissal'),
        ('no_further_action', 'No Further Action Required'),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='discipline_records'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='issued_disciplines'
    )
    date_issued = models.DateField(default=date.today)
    reason = models.TextField()
    document = models.FileField(upload_to='discipline_docs/', blank=True, null=True)

    # Suspension fields
    suspension_start = models.DateField(null=True, blank=True)
    suspension_end = models.DateField(null=True, blank=True)  # auto = start + 8 days

    # Manager recommendation (hidden from employee — visible to HR/Director/Superuser only)
    recommended_sanction = models.CharField(
        max_length=20, choices=RECOMMENDED_ACTION_CHOICES,
        blank=True, default='',
        help_text='Proposed follow-up action recommended by the issuing manager (not visible to employee)'
    )
    recommendation_note = models.TextField(blank=True, default='')

    # HR proposed sanction (after reviewing manager recommendation)
    hr_proposed_sanction = models.CharField(
        max_length=20, choices=RECOMMENDED_ACTION_CHOICES, blank=True, default=''
    )
    hr_proposed_note = models.TextField(blank=True, default='')

    # Admin Director proposed sanction
    director_proposed_sanction = models.CharField(
        max_length=20, choices=RECOMMENDED_ACTION_CHOICES, blank=True, default=''
    )
    director_proposed_note = models.TextField(blank=True, default='')

    notes = models.TextField(blank=True)

    # Proposal flag — True when submitted by non-HR awaiting formal HR execution
    is_proposal = models.BooleanField(
        default=False,
        help_text='Awaiting formal HR execution; not yet visible to the employee as a notice'
    )
    proposal_note = models.TextField(blank=True, default='', help_text='Additional context submitted with the proposal')

    # System-generated flag — True when auto-issued by the system (e.g. missed appraisal deadline)
    is_system_generated = models.BooleanField(
        default=False,
        help_text='Issued automatically by the system, not by a human. Does not count toward appraisal score.'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_issued', '-created_at']

    def __str__(self):
        return f"{self.get_action_type_display()} — {self.employee.get_full_name()} ({self.date_issued})"

    def save(self, *args, **kwargs):
        if self.action_type == 'suspension' and self.suspension_start and not self.suspension_end:
            start = self.suspension_start
            if isinstance(start, str):
                from datetime import datetime
                try:
                    start = datetime.strptime(start, '%Y-%m-%d').date()
                except ValueError:
                    start = None
                self.suspension_start = start
            self.suspension_end = start + timedelta(days=8)
        super().save(*args, **kwargs)

    def is_currently_suspended(self):
        if self.action_type != 'suspension':
            return False
        today = date.today()
        return (
            self.suspension_start and self.suspension_end and
            self.suspension_start <= today <= self.suspension_end
        )

    def badge_color(self):
        colors = {
            'verbal_warning': 'warning',
            'written_caution': 'orange',
            'final_warning': 'danger',
            'suspension': 'dark',
            'dismissal': 'danger',
        }
        return colors.get(self.action_type, 'secondary')
