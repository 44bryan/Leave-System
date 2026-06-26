"""Quick end-to-end test of all recruitment views. Run on VPS."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
sys.path.insert(0, '/var/www/hrm')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from recruitment.models import JobPosting, FormFieldConfig
from recruitment import views
from accounts.models import Department

rf = RequestFactory()
superuser = User.objects.filter(is_superuser=True).first()

def test(name, fn):
    try:
        r = fn()
        print(f'  OK  {name}: status {r.status_code}')
    except Exception as e:
        print(f'  FAIL {name}: {e}')

def make_req(method, url, data=None):
    req = rf.get(url) if method == 'GET' else rf.post(url, data or {})
    req.user = superuser
    req.session = {}
    return req

print('=== Recruitment Module Test ===')

# 1. Posting list
test('posting_list', lambda: views.posting_list(make_req('GET', '/recruitment/')))

# 2. Create posting
dept = Department.objects.first()
test('posting_create', lambda: views.posting_create(make_req('POST', '/recruitment/new/', {
    'title': '_TestJob2026', 'description': 'Auto test job',
    'employment_type': 'full_time', 'status': 'draft',
    'department': dept.pk if dept else '',
})))

p = JobPosting.objects.filter(title='_TestJob2026').first() or JobPosting.objects.first()
print(f'  Using posting: {p}')

# 3. Form config GET
test('form_config GET', lambda: views.form_config(make_req('GET', f'/recruitment/{p.pk}/form-config/'), pk=p.pk)
     if False else views.form_config(make_req('GET', '/'), pk=p.pk))

# Workaround - call directly
try:
    req = make_req('GET', f'/recruitment/{p.pk}/form-config/')
    r = views.form_config(req, pk=p.pk)
    print(f'  OK  form_config GET: status {r.status_code}')
except Exception as e:
    print(f'  FAIL form_config GET: {e}')

# 4. Add custom field
try:
    req = make_req('POST', f'/recruitment/{p.pk}/form-config/', {
        'action': 'add_custom',
        'new_label': 'Test Custom Field',
        'new_field_type': 'text',
        'new_options': '',
        'new_placeholder': '',
    })
    r = views.form_config(req, pk=p.pk)
    added = p.form_fields.filter(is_custom=True).last()
    print(f'  OK  add_custom: status {r.status_code}, field={added.field_name if added else "not found"}')
except Exception as e:
    print(f'  FAIL add_custom: {e}')

# 5. Save fields
try:
    fields = p.form_fields.all()
    data = {'action': 'save_fields'}
    for f in fields:
        data[f'enabled_{f.pk}'] = 'on'
        data[f'required_{f.pk}'] = ''
        data[f'label_{f.pk}'] = f.label
        data[f'order_{f.pk}'] = str(f.field_order)
        data[f'placeholder_{f.pk}'] = ''
        data[f'options_{f.pk}'] = f.options
    req = make_req('POST', f'/recruitment/{p.pk}/form-config/', data)
    r = views.form_config(req, pk=p.pk)
    print(f'  OK  save_fields: status {r.status_code}')
except Exception as e:
    print(f'  FAIL save_fields: {e}')

# 6. Scoring config GET
try:
    req = make_req('GET', f'/recruitment/{p.pk}/scoring/')
    r = views.scoring_config(req, pk=p.pk)
    print(f'  OK  scoring_config GET: status {r.status_code}')
except Exception as e:
    print(f'  FAIL scoring_config GET: {e}')

# 7. Add scoring rule
try:
    req = make_req('POST', f'/recruitment/{p.pk}/scoring/', {
        'action': 'add_criterion',
        'field_name': 'education_level',
        'label': 'Has degree',
        'condition': 'equals',
        'value': "Bachelor's Degree",
        'points': '10',
    })
    r = views.scoring_config(req, pk=p.pk)
    print(f'  OK  add_criterion: status {r.status_code}')
except Exception as e:
    print(f'  FAIL add_criterion: {e}')

# 8. Applicant list
try:
    req = make_req('GET', f'/recruitment/{p.pk}/applicants/')
    r = views.applicant_list(req, pk=p.pk)
    print(f'  OK  applicant_list: status {r.status_code}')
except Exception as e:
    print(f'  FAIL applicant_list: {e}')

# 9. Public job board
try:
    req = make_req('GET', '/recruitment/jobs/')
    r = views.job_board(req)
    print(f'  OK  job_board: status {r.status_code}')
except Exception as e:
    print(f'  FAIL job_board: {e}')

# 10. Delete test posting
try:
    p2 = JobPosting.objects.filter(title='_TestJob2026').first()
    if p2:
        p2.delete()
        print('  OK  cleanup: test posting deleted')
except Exception as e:
    print(f'  FAIL cleanup: {e}')

print('=== Done ===')
