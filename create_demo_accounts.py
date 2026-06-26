"""
Run on VPS: venv/bin/python create_demo_accounts.py
Creates demo/test accounts for board member testing.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
sys.path.insert(0, '/var/www/hrm')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

from accounts.models import Department, Employee
from contracts.models import Contract
from leaves.models import LeaveType, LeaveBalance

PASSWORD = 'DemoBoard@2026'

# ── Department ────────────────────────────────────────────────────────────────
dept, _ = Department.objects.get_or_create(
    code='DEMO',
    defaults={'name': 'Board Demo Department'}
)
print(f"Department: {dept.name}")

def make_user(username, first, last, role, emp_id, position, supervisor=None, unit_head_emp=None):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': first,
            'last_name': last,
            'email': f'{username}@demo.micei.org',
            'is_active': True,
        }
    )
    if created:
        user.set_password(PASSWORD)
        user.save()

    emp, _ = Employee.objects.get_or_create(
        user=user,
        defaults={
            'employee_id': emp_id,
            'department': dept,
            'role': role,
            'position': position,
            'date_joined_company': date(2026, 1, 1),
            'date_of_birth': date(1990, 6, 15),
            'phone': '+237600000000',
            'is_active': True,
        }
    )
    if not created:
        emp.department = dept
    if supervisor:
        emp.supervisor = supervisor
    if unit_head_emp:
        emp.unit_head = unit_head_emp
    emp.save()
    return user, emp

# ── Create accounts (top → down so FKs resolve) ──────────────────────────────

# CEOs
_, ceo1 = make_user('demo_ceo1',      'Alice', 'Board',   'ceo',            'DEMO-C01', 'Chief Executive Officer (Demo)')
_, ceo2 = make_user('demo_ceo2',      'Robert','Board',   'ceo',            'DEMO-C02', 'Chief Executive Officer (Demo)')

# Admin Directors
_, dir1 = make_user('demo_director1', 'Marie', 'Dupont',  'admin_director', 'DEMO-D01', 'Administration Director (Demo)')
_, dir2 = make_user('demo_director2', 'Jean',  'Martin',  'admin_director', 'DEMO-D02', 'Administration Director (Demo)')

# HR
_, hr1  = make_user('demo_hr1',       'Sophie','Nguema',  'hr',             'DEMO-H01', 'HR Administrator (Demo)')
_, hr2  = make_user('demo_hr2',       'Paul',  'Effa',    'hr',             'DEMO-H02', 'HR Administrator (Demo)')

# Line Manager
_, mgr1 = make_user('demo_manager1',  'David', 'Nkemelu', 'manager',        'DEMO-M01', 'Line Manager (Demo)')

# Unit Heads
_, uh1  = make_user('demo_unithead1', 'Grace', 'Ateba',   'unit_head',      'DEMO-U01', 'Unit Head (Demo)', supervisor=mgr1)
_, uh2  = make_user('demo_unithead2', 'Felix', 'Owona',   'unit_head',      'DEMO-U02', 'Unit Head (Demo)', supervisor=mgr1)

# Employees
_, emp1 = make_user('demo_employee1', 'Chloe', 'Foka',    'employee',       'DEMO-E01', 'Staff (Demo)', supervisor=mgr1, unit_head_emp=uh1)
_, emp2 = make_user('demo_employee2', 'Marc',  'Bello',   'employee',       'DEMO-E02', 'Staff (Demo)', supervisor=mgr1, unit_head_emp=uh1)

print("Users created.")

# ── Contracts ─────────────────────────────────────────────────────────────────
all_emps = [ceo1,ceo2,dir1,dir2,hr1,hr2,mgr1,uh1,uh2,emp1,emp2]
for emp in all_emps:
    if not emp.contracts.exists():
        Contract.objects.create(
            employee=emp,
            contract_type='cdi',
            start_date=date(2026, 1, 1),
            end_date=None,
            position=emp.position,
            department=dept,
            issued_by=User.objects.filter(is_superuser=True).first(),
            status='active',
            notes='Demo / test contract for board testing.'
        )
print("Contracts created.")

# ── Leave Balances ────────────────────────────────────────────────────────────
leave_types = LeaveType.objects.all()
for emp in all_emps:
    for lt in leave_types:
        LeaveBalance.objects.get_or_create(
            employee=emp,
            leave_type=lt,
            year=2026,
            defaults={'total_days': lt.default_days, 'used_days': 0}
        )
print("Leave balances created.")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"PASSWORD FOR ALL ACCOUNTS: {PASSWORD}")
print("="*60)
rows = [
    ("demo_ceo1",      "Alice Board",   "CEO"),
    ("demo_ceo2",      "Robert Board",  "CEO"),
    ("demo_director1", "Marie Dupont",  "Admin Director"),
    ("demo_director2", "Jean Martin",   "Admin Director"),
    ("demo_hr1",       "Sophie Nguema", "HR Admin"),
    ("demo_hr2",       "Paul Effa",     "HR Admin"),
    ("demo_manager1",  "David Nkemelu", "Line Manager"),
    ("demo_unithead1", "Grace Ateba",   "Unit Head"),
    ("demo_unithead2", "Felix Owona",   "Unit Head"),
    ("demo_employee1", "Chloe Foka",    "Employee"),
    ("demo_employee2", "Marc Bello",    "Employee"),
]
for uname, name, role in rows:
    print(f"  {role:<20} {uname:<20} {name}")
print("="*60)
