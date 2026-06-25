from django.db import models
from django.contrib.auth.models import User
from accounts.models import Employee


class RecognitionProposal(models.Model):
    TYPE_STAFF_OF_MONTH    = 'staff_of_month'
    TYPE_EMPLOYEE_QUARTER  = 'employee_of_quarter'
    TYPE_BEST_PERFORMER    = 'best_performer'
    TYPE_LONG_SERVICE      = 'long_service'
    TYPE_INNOVATION        = 'innovation'
    TYPE_EXCELLENCE        = 'excellence'
    TYPE_OTHER             = 'other'

    TYPE_CHOICES = [
        (TYPE_STAFF_OF_MONTH,   'Staff of the Month'),
        (TYPE_EMPLOYEE_QUARTER, 'Employee of the Quarter'),
        (TYPE_BEST_PERFORMER,   'Best Performer'),
        (TYPE_LONG_SERVICE,     'Long Service Award'),
        (TYPE_INNOVATION,       'Innovation Award'),
        (TYPE_EXCELLENCE,       'Excellence Award'),
        (TYPE_OTHER,            'Other / Custom'),
    ]

    STATUS_PROPOSED  = 'proposed'
    STATUS_ENDORSED  = 'endorsed'
    STATUS_EXECUTED  = 'executed'
    STATUS_REJECTED  = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PROPOSED,  'Proposed'),
        (STATUS_ENDORSED,  'Endorsed'),
        (STATUS_EXECUTED,  'Executed'),
        (STATUS_REJECTED,  'Rejected'),
    ]

    employee       = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='recognition_proposals')
    proposed_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='proposed_recognitions')
    recognition_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    custom_title   = models.CharField(max_length=120, blank=True,
                                      help_text='Required when type is "Other / Custom".')
    description    = models.TextField(help_text='Why does this employee deserve this recognition?')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROPOSED)
    created_at     = models.DateTimeField(auto_now_add=True)

    # HR execution fields
    executed_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='executed_recognitions')
    executed_at    = models.DateTimeField(null=True, blank=True)
    execution_note = models.TextField(blank=True, help_text='HR note on how the recognition was delivered.')

    # Rejection fields
    rejected_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='rejected_recognitions')
    rejected_at    = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_recognition_type_display()} — {self.employee.get_full_name()}'

    def get_display_title(self):
        if self.recognition_type == self.TYPE_OTHER and self.custom_title:
            return self.custom_title
        return self.get_recognition_type_display()


class RecognitionComment(models.Model):
    proposal   = models.ForeignKey(RecognitionProposal, on_delete=models.CASCADE, related_name='comments')
    author     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.proposal}'
