"""Full end-to-end test using Django test Client. Run on VPS."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
sys.path.insert(0, '/var/www/hrm')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from recruitment.models import JobPosting, FormFieldConfig, ScoringCriterion
from accounts.models import Department

c = Client()
superuser = User.objects.filter(is_superuser=True).first()
c.force_login(superuser)
dept = Department.objects.first()

results = []

def check(label, r, expected=302):
    ok = r.status_code == expected
    results.append((label, ok, r.status_code))
    status = 'OK  ' if ok else 'FAIL'
    print(f'  {status} {label}: {r.status_code}')

# 1. Create posting
r = c.post('/recruitment/new/', {
    'title': '_BoardTest', 'description': 'Test posting',
    'employment_type': 'full_time', 'status': 'draft',
    'department': dept.pk if dept else '',
})
check('Create posting (POST)', r, 302)
p = JobPosting.objects.filter(title='_BoardTest').first()
print(f'       Posting pk={p.pk if p else None}')

# 2. Form config page
r = c.get(f'/recruitment/{p.pk}/form-config/')
check('Form config (GET)', r, 200)

# 3. Add custom field
r = c.post(f'/recruitment/{p.pk}/form-config/', {
    'action': 'add_custom',
    'new_label': 'Years in Field',
    'new_field_type': 'number',
    'new_options': '',
    'new_placeholder': '',
})
check('Add custom field (POST)', r, 302)
added = p.form_fields.filter(is_custom=True).last()
print(f'       Field name: {added.field_name if added else "NOT FOUND"}')

# 4. Save fields
fields = p.form_fields.all()
data = {'action': 'save_fields'}
for f in fields:
    data[f'enabled_{f.pk}'] = 'on'
    data[f'label_{f.pk}'] = f.label
    data[f'order_{f.pk}'] = str(f.field_order)
    data[f'placeholder_{f.pk}'] = ''
    data[f'options_{f.pk}'] = f.options
r = c.post(f'/recruitment/{p.pk}/form-config/', data)
check('Save fields (POST)', r, 302)

# 5. Scoring config page
r = c.get(f'/recruitment/{p.pk}/scoring/')
check('Scoring config (GET)', r, 200)

# 6. Add scoring rule
r = c.post(f'/recruitment/{p.pk}/scoring/', {
    'action': 'add_criterion',
    'field_name': 'education_level',
    'label': 'Has degree',
    'condition': 'equals',
    'value': "Bachelor Degree",
    'points': '10',
})
check('Add scoring rule (POST)', r, 302)
cr = ScoringCriterion.objects.filter(posting=p).last()
print(f'       Rule: {cr.label if cr else "NOT FOUND"}')

# 7. Publish posting
r = c.post(f'/recruitment/{p.pk}/edit/', {
    'title': '_BoardTest', 'description': 'Test',
    'employment_type': 'full_time', 'status': 'open',
})
check('Publish posting (POST)', r, 302)

# 8. Public job board (no login)
c2 = Client()
r = c2.get('/recruitment/jobs/')
check('Job board public (GET)', r, 200)

r = c2.get(f'/recruitment/jobs/{p.pk}/')
check('Job detail public (GET)', r, 200)

r = c2.get(f'/recruitment/jobs/{p.pk}/apply/')
check('Apply form public (GET)', r, 200)

# 9. Applicant list
r = c.get(f'/recruitment/{p.pk}/applicants/')
check('Applicant list (GET)', r, 200)

# Cleanup
p.delete()
print('  OK  Cleanup done')

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f'\n=== {passed} passed, {failed} failed ===')
