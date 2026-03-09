"""
Management command to seed the database with initial data.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Seeds the database with initial demo data'

    def handle(self, *args, **kwargs):
        from accounts.models import Department, Employee
        from leaves.models import LeaveType, LeaveBalance

        self.stdout.write('🌱 Seeding database...')

        # --- Departments ---
        depts_data = [
            ('Ophthalmology', 'OPH'),
            ('Human Resources', 'HR'),
            ('Administration', 'ADMIN'),
            ('Nursing', 'NURS'),
            ('Pharmacy', 'PHARM'),
            ('IT & Support', 'IT'),
        ]
        departments = {}
        for name, code in depts_data:
            dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name})
            departments[code] = dept
            self.stdout.write(f'  ✓ Department: {name}')

        # --- Leave Types ---
        leave_types_data = [
            ('Annual Leave', 'Regular annual leave entitlement', False, 'primary'),
            ('Sick Leave', 'Medical or illness-related absence', True, 'danger'),
            ('Marriage Leave', 'Leave for personal marriage ceremony', True, 'success'),
            ('Maternity Leave', 'Maternity leave for expecting mothers', True, 'info'),
            ('Paternity Leave', 'Paternity leave for new fathers', True, 'info'),
            ('Compassionate Leave', 'Leave for bereavement or family emergency', True, 'warning'),
            ('Study Leave', 'Leave for educational purposes or exams', True, 'secondary'),
        ]
        for name, desc, req_doc, color in leave_types_data:
            LeaveType.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'requires_document': req_doc, 'color': color}
            )
            self.stdout.write(f'  ✓ Leave type: {name}')

        # --- Users & Employees ---
        def make_user(username, first, last, email, password='hospital2024'):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.first_name = first
                user.last_name = last
                user.email = email
                user.set_password(password)
                user.save()
            return user

        # HR Admin
        hr_user = make_user('hr_admin', 'Grace', 'Nkemdirim', 'grace.hr@eyehospital.cm')
        hr_emp, _ = Employee.objects.get_or_create(
            user=hr_user,
            defaults={
                'employee_id': 'EH001',
                'department': departments['HR'],
                'role': 'hr',
                'position': 'HR Manager',
                'phone': '+237 6XX XXX XXX',
                'date_joined_company': date(2019, 3, 1),
            }
        )

        # Line Manager - Ophthalmology
        mgr_user = make_user('dr_fon', 'Emmanuel', 'Fon', 'e.fon@eyehospital.cm')
        mgr_emp, _ = Employee.objects.get_or_create(
            user=mgr_user,
            defaults={
                'employee_id': 'EH002',
                'department': departments['OPH'],
                'role': 'manager',
                'position': 'Senior Ophthalmologist',
                'phone': '+237 6XX XXX XXX',
                'date_joined_company': date(2018, 6, 15),
            }
        )

        # Employees
        employees_data = [
            ('nurse_mary', 'Mary', 'Tanyi', 'mary.tanyi@eyehospital.cm', 'EH003', 'NURS', 'Ophthalmic Nurse'),
            ('tech_paul', 'Paul', 'Ngwa', 'paul.ngwa@eyehospital.cm', 'EH004', 'IT', 'IT Support'),
            ('pharm_alice', 'Alice', 'Mbeki', 'alice.mbeki@eyehospital.cm', 'EH005', 'PHARM', 'Pharmacist'),
            ('admin_john', 'John', 'Achebe', 'john.achebe@eyehospital.cm', 'EH006', 'ADMIN', 'Admin Officer'),
        ]

        for uname, first, last, email, emp_id, dept_code, position in employees_data:
            user = make_user(uname, first, last, email)
            emp, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': emp_id,
                    'department': departments[dept_code],
                    'role': 'employee',
                    'position': position,
                    'supervisor': mgr_emp,
                    'date_joined_company': date(2021, 1, 10),
                }
            )
            if created:
                LeaveBalance.objects.get_or_create(
                    employee=emp, year=date.today().year,
                    defaults={'total_entitlement': 18}
                )
            self.stdout.write(f'  ✓ Employee: {first} {last}')

        # Ensure HR and manager have balances
        for emp in [hr_emp, mgr_emp]:
            LeaveBalance.objects.get_or_create(
                employee=emp, year=date.today().year,
                defaults={'total_entitlement': 18}
            )

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!'))
        self.stdout.write('\n📋 Login Credentials:')
        self.stdout.write('  HR Admin:     username=hr_admin     password=hospital2024')
        self.stdout.write('  Line Manager: username=dr_fon       password=hospital2024')
        self.stdout.write('  Employee:     username=nurse_mary   password=hospital2024')
        self.stdout.write('\nRun: python manage.py runserver')
