import logging
from django.db import models
from django.contrib.auth.models import User
from accounts.models import Department

logger = logging.getLogger(__name__)


FIELD_TYPE_TEXT     = 'text'
FIELD_TYPE_TEXTAREA = 'textarea'
FIELD_TYPE_NUMBER   = 'number'
FIELD_TYPE_EMAIL    = 'email'
FIELD_TYPE_SELECT   = 'select'
FIELD_TYPE_YESNO    = 'yesno'
FIELD_TYPE_FILE       = 'file'
FIELD_TYPE_FILE_MULTI = 'file_multi'
FIELD_TYPE_DATE       = 'date'

FIELD_TYPE_CHOICES = [
    (FIELD_TYPE_TEXT,       'Short Text'),
    (FIELD_TYPE_TEXTAREA,   'Long Text / Paragraph'),
    (FIELD_TYPE_NUMBER,     'Number'),
    (FIELD_TYPE_SELECT,     'Dropdown / Select'),
    (FIELD_TYPE_YESNO,      'Yes / No'),
    (FIELD_TYPE_FILE,       'File Upload (single)'),
    (FIELD_TYPE_FILE_MULTI, 'File Upload (multiple files)'),
    (FIELD_TYPE_DATE,       'Date'),
]

# Default field configuration for every new job posting
DEFAULT_FIELDS = [
    {'field_name': 'age',              'label': 'Age',                        'field_type': FIELD_TYPE_NUMBER,   'is_enabled': True,  'is_required': True,  'field_order': 1,  'options': ''},
    {'field_name': 'phone',            'label': 'Phone Number',               'field_type': FIELD_TYPE_TEXT,     'is_enabled': True,  'is_required': True,  'field_order': 2,  'options': ''},
    {'field_name': 'address',          'label': 'Address / City',             'field_type': FIELD_TYPE_TEXT,     'is_enabled': True,  'is_required': False, 'field_order': 3,  'options': ''},
    {'field_name': 'nationality',      'label': 'Nationality',                'field_type': FIELD_TYPE_TEXT,     'is_enabled': True,  'is_required': False, 'field_order': 4,  'options': ''},
    {'field_name': 'sex',              'label': 'Gender',                     'field_type': FIELD_TYPE_SELECT,   'is_enabled': True,  'is_required': False, 'field_order': 5,
     'options': 'Male,Female,Prefer not to say'},
    {'field_name': 'education_level',  'label': 'Highest Education Level',    'field_type': FIELD_TYPE_SELECT,   'is_enabled': True,  'is_required': False, 'field_order': 6,
     'options': "High School,Bachelor's Degree,Master's Degree,PhD / Doctorate,Professional Certification,Other"},
    {'field_name': 'years_experience', 'label': 'Years of Experience',        'field_type': FIELD_TYPE_NUMBER,   'is_enabled': True,  'is_required': False, 'field_order': 7,  'options': ''},
    {'field_name': 'current_employer', 'label': 'Current / Last Employer',    'field_type': FIELD_TYPE_TEXT,     'is_enabled': True,  'is_required': False, 'field_order': 8,  'options': ''},
    {'field_name': 'cover_letter',          'label': 'Cover Letter',                  'field_type': FIELD_TYPE_TEXTAREA, 'is_enabled': True,  'is_required': False, 'field_order': 9,  'options': ''},
    {'field_name': 'recommendation_letter', 'label': 'Recommendation Letter',          'field_type': FIELD_TYPE_TEXTAREA, 'is_enabled': False, 'is_required': False, 'field_order': 10, 'options': ''},
    {'field_name': 'linkedin_url',          'label': 'LinkedIn Profile URL',           'field_type': FIELD_TYPE_TEXT,     'is_enabled': False, 'is_required': False, 'field_order': 11, 'options': ''},
    {'field_name': 'expected_salary',       'label': 'Expected Salary (XAF)',          'field_type': FIELD_TYPE_TEXT,     'is_enabled': False, 'is_required': False, 'field_order': 12, 'options': ''},
    {'field_name': 'available_from',        'label': 'Available Start Date',           'field_type': FIELD_TYPE_DATE,     'is_enabled': True,  'is_required': False, 'field_order': 13, 'options': ''},
    {'field_name': 'source',                'label': 'How did you hear about us?',     'field_type': FIELD_TYPE_SELECT,   'is_enabled': True,  'is_required': False, 'field_order': 14,
     'options': 'Job Board,Employee Referral,LinkedIn,Facebook / Social Media,Company Website,Other'},
]


class JobPosting(models.Model):
    STATUS_DRAFT  = 'draft'
    STATUS_OPEN   = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_DRAFT,  'Draft'),
        (STATUS_OPEN,   'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]

    TYPE_FULL_TIME  = 'full_time'
    TYPE_PART_TIME  = 'part_time'
    TYPE_CONTRACT   = 'contract'
    TYPE_INTERNSHIP = 'internship'
    TYPE_CHOICES = [
        (TYPE_FULL_TIME,  'Full Time'),
        (TYPE_PART_TIME,  'Part Time'),
        (TYPE_CONTRACT,   'Contract'),
        (TYPE_INTERNSHIP, 'Internship'),
    ]

    title           = models.CharField(max_length=150)
    department      = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    location        = models.CharField(max_length=100, blank=True, default='')
    employment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FULL_TIME)
    advert          = models.TextField(blank=True, default='', help_text='Short text shown on the job card listing.')
    about           = models.TextField(blank=True, default='', help_text='Legacy — use advert instead.')
    description     = models.TextField(blank=True, default='')
    requirements    = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    deadline        = models.DateField(null=True, blank=True)
    created_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='job_postings')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def applicant_count(self):
        return self.applications.count()

    def create_default_fields(self):
        """Create default FormFieldConfig entries. Safe to call multiple times."""
        for f in DEFAULT_FIELDS:
            FormFieldConfig.objects.get_or_create(
                posting=self,
                field_name=f['field_name'],
                defaults={
                    'label':        f['label'],
                    'field_type':   f['field_type'],
                    'is_enabled':   f['is_enabled'],
                    'is_required':  f['is_required'],
                    'field_order':  f['field_order'],
                    'options':      f['options'],
                    'is_custom':    False,
                }
            )


class FormFieldConfig(models.Model):
    posting     = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='form_fields')
    field_name  = models.CharField(max_length=80)
    label       = models.CharField(max_length=150)
    field_type  = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default=FIELD_TYPE_TEXT)
    is_enabled  = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    field_order = models.PositiveIntegerField(default=99)
    options     = models.TextField(blank=True, help_text='Comma-separated options for dropdown fields')
    is_custom   = models.BooleanField(default=False, help_text='True for HR-added custom fields')
    placeholder = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['field_order', 'pk']
        unique_together = [['posting', 'field_name']]

    def __str__(self):
        return f'{self.posting.title} — {self.label}'

    def get_options_list(self):
        if self.options:
            return [o.strip() for o in self.options.split(',') if o.strip()]
        return []


class PostingSection(models.Model):
    """A content section (heading + body) on a job posting. Like LinkedIn/Greenhouse sections."""
    posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='sections')
    heading = models.CharField(max_length=150)
    body    = models.TextField()
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return f'{self.posting.title} — {self.heading}'


class ScoringCriterion(models.Model):
    COND_EQUALS   = 'equals'
    COND_CONTAINS = 'contains'
    COND_GTE      = 'gte'
    COND_LTE      = 'lte'
    COND_YES      = 'yes'
    COND_NO       = 'no'
    COND_CHOICES = [
        (COND_EQUALS,   'Equals (exact match)'),
        (COND_CONTAINS, 'Contains (partial match)'),
        (COND_GTE,      'Greater than or equal to (numbers)'),
        (COND_LTE,      'Less than or equal to (numbers)'),
        (COND_YES,      'Answer is Yes'),
        (COND_NO,       'Answer is No'),
    ]

    posting    = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='scoring_criteria')
    field_name = models.CharField(max_length=80, help_text='The field name to evaluate')
    label      = models.CharField(max_length=150, help_text='Short description of this rule')
    condition  = models.CharField(max_length=20, choices=COND_CHOICES)
    value      = models.CharField(max_length=200, blank=True,
                                  help_text='Value to compare against (leave blank for yes/no conditions)')
    points     = models.IntegerField(help_text='Points awarded when condition is met')

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f'{self.label} (+{self.points} pts)'


APPLICATION_STATUS_CHOICES = [
    ('submitted',   'Submitted'),
    ('under_review','Under Review'),
    ('shortlisted', 'Shortlisted'),
    ('interview',   'Interview Scheduled'),
    ('offered',     'Offer Extended'),
    ('hired',       'Hired'),
    ('rejected',    'Rejected'),
]

APPLICATION_STATUS_COLORS = {
    'submitted':    'secondary',
    'under_review': 'info',
    'shortlisted':  'primary',
    'interview':    'warning',
    'offered':      'success',
    'hired':        'success',
    'rejected':     'danger',
}


AI_RECOMMENDATION_INVITE  = 'invite'
AI_RECOMMENDATION_HOLD    = 'hold'
AI_RECOMMENDATION_REJECT  = 'reject'
AI_RECOMMENDATION_CHOICES = [
    (AI_RECOMMENDATION_INVITE,  'Invite for Interview'),
    (AI_RECOMMENDATION_HOLD,    'Hold / Consider Later'),
    (AI_RECOMMENDATION_REJECT,  'Reject'),
]


class Application(models.Model):
    posting          = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    applicant_name   = models.CharField(max_length=150)
    applicant_email  = models.EmailField()
    cv_file          = models.FileField(upload_to='recruitment/cvs/%Y/%m/')
    status           = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='submitted')
    score            = models.FloatField(default=0)
    submitted_at     = models.DateTimeField(auto_now_add=True)
    hr_notes         = models.TextField(blank=True)
    interview_date   = models.DateTimeField(null=True, blank=True)
    interview_notes  = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    reviewed_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='reviewed_applications')
    # AI analysis fields
    ai_score          = models.FloatField(null=True, blank=True)
    ai_summary        = models.TextField(blank=True)
    ai_strengths      = models.TextField(blank=True)
    ai_gaps           = models.TextField(blank=True)
    ai_recommendation = models.CharField(max_length=10, choices=AI_RECOMMENDATION_CHOICES, blank=True)
    ai_analysed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-score', '-submitted_at']

    def __str__(self):
        return f'{self.applicant_name} → {self.posting.title}'

    def get_status_color(self):
        return APPLICATION_STATUS_COLORS.get(self.status, 'secondary')

    def compute_score(self):
        """Calculate score from the posting's ScoringCriteria against this application's answers."""
        total = 0
        answers = {a.field_name: a.value for a in self.answers.all()}
        for crit in self.posting.scoring_criteria.all():
            raw = answers.get(crit.field_name, '').strip()
            try:
                if crit.condition == ScoringCriterion.COND_EQUALS:
                    if raw.lower() == crit.value.strip().lower():
                        total += crit.points
                elif crit.condition == ScoringCriterion.COND_CONTAINS:
                    if crit.value.strip().lower() in raw.lower():
                        total += crit.points
                elif crit.condition == ScoringCriterion.COND_GTE:
                    if float(raw) >= float(crit.value):
                        total += crit.points
                elif crit.condition == ScoringCriterion.COND_LTE:
                    if float(raw) <= float(crit.value):
                        total += crit.points
                elif crit.condition == ScoringCriterion.COND_YES:
                    if raw.lower() in ('yes', 'true', '1'):
                        total += crit.points
                elif crit.condition == ScoringCriterion.COND_NO:
                    if raw.lower() in ('no', 'false', '0'):
                        total += crit.points
            except (ValueError, TypeError) as e:
                logger.debug('Scoring criterion "%s" skipped for application %s: %s', crit.label, self.pk, e)
        self.score = total
        self.save(update_fields=['score'])
        return total


class ApplicationAnswer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='answers')
    field_name  = models.CharField(max_length=80)
    value       = models.TextField(blank=True)

    class Meta:
        unique_together = [['application', 'field_name']]

    def __str__(self):
        return f'{self.application.applicant_name} — {self.field_name}'
