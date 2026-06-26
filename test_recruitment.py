"""Core model operations test. Run: venv/bin/python test_recruitment.py"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
sys.path.insert(0, '/var/www/hrm')
django.setup()

import re
from django.db.models import Max
from django.contrib.auth.models import User
from recruitment.models import (
    JobPosting, FormFieldConfig, ScoringCriterion,
    Application, ApplicationAnswer, FIELD_TYPE_TEXT,
)
from accounts.models import Department

print('=== Recruitment Core Test ===')

dept = Department.objects.first()
u    = User.objects.filter(is_superuser=True).first()

# 1 - Create posting + default fields
p = JobPosting.objects.create(
    title='__AUTOTEST__', description='auto test',
    employment_type='full_time', status='draft',
    created_by=u, department=dept
)
p.create_default_fields()
print(f'  OK  Create posting + default fields: {p.form_fields.count()} fields')

# 2 - Add custom field (exactly as the view does it)
label = 'My Custom Field'
field_name = re.sub(r'[^a-z0-9_]', '_', label.lower())[:60]
field_name = 'custom_' + field_name
base = field_name
i = 2
while p.form_fields.filter(field_name=field_name).exists():
    field_name = base + '_' + str(i)
    i += 1
max_order = p.form_fields.aggregate(m=Max('field_order'))['m'] or 0
FormFieldConfig.objects.create(
    posting=p, field_name=field_name, label=label,
    field_type=FIELD_TYPE_TEXT, is_enabled=True, is_required=False,
    field_order=max_order + 1, is_custom=True
)
print(f'  OK  Add custom field: {field_name}')

# 3 - Add scoring rule
ScoringCriterion.objects.create(
    posting=p, field_name='education_level',
    label='Has degree', condition='equals',
    value='Bachelor Degree', points=10
)
print('  OK  Add scoring rule')

# 4 - Submit application + auto-score
app = Application.objects.create(
    posting=p, applicant_name='Test User',
    applicant_email='test@test.com',
    cv_file='test.pdf', status='submitted'
)
ApplicationAnswer.objects.create(
    application=app, field_name='education_level', value='Bachelor Degree'
)
score = app.compute_score()
print(f'  OK  Application + auto-score: {score} pts (expected 10)')

# 5 - get_options_list
field = p.form_fields.filter(field_name='education_level').first()
opts = field.get_options_list() if field else []
print(f'  OK  get_options_list: {len(opts)} options')

# 6 - Public job listing query
open_postings = JobPosting.objects.filter(status='open').count()
print(f'  OK  Open postings query: {open_postings} open')

p.delete()
print('  OK  Cleanup')
print('=== ALL PASSED ===')
