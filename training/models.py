from django.db import models
from accounts.models import Employee


class Trainee(models.Model):
    GENDER_CHOICES = [('M', 'Male / Homme'), ('F', 'Female / Femme'), ('O', 'Other / Autre')]

    PROGRAM_CHOICES = [
        ('Ophthalmic Nursing', 'Ophthalmic Nursing'),
        ('Ophthalmic Technology', 'Ophthalmic Technology'),
        ('Optometry', 'Optometry'),
        ('Clinical Attachment', 'Clinical Attachment'),
        ('Research Fellowship', 'Research Fellowship'),
        ('Other', 'Other / Autre'),
    ]

    full_name           = models.CharField(max_length=200)
    email               = models.EmailField(blank=True)
    phone               = models.CharField(max_length=30, blank=True)
    gender              = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    program             = models.CharField(max_length=200)
    start_date          = models.DateField()
    end_date            = models.DateField()
    home_institution    = models.CharField(max_length=200)
    country             = models.CharField(max_length=100)
    supervisor          = models.ForeignKey(
        Employee, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='supervised_trainees'
    )
    certificate_issued  = models.BooleanField(default=False)
    remarks             = models.TextField(blank=True)
    registered_by       = models.ForeignKey(
        Employee, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='registered_trainees'
    )
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'full_name']

    def __str__(self):
        return f"{self.full_name} — {self.program} ({self.start_date})"

    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return None

    def status(self):
        from datetime import date
        today = date.today()
        if today < self.start_date:
            return 'upcoming'
        elif today > self.end_date:
            return 'completed'
        return 'active'
