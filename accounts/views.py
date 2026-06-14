from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from .models import Employee, Department
from .forms import LoginForm, EmployeeCreateForm, EmployeeEditForm, DepartmentForm, ChangePasswordForm, AdminResetCredentialsForm, EmployeeSelfEditForm
from .signature_utils import process_signature


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', 'dashboard:home'))

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        messages.error(request, "No employee profile found.")
        return redirect('dashboard:home')

    change_form = ChangePasswordForm(request.user)
    self_edit_form = EmployeeSelfEditForm(instance=employee)

    if request.method == 'POST' and 'self_edit' in request.POST:
        self_edit_form = EmployeeSelfEditForm(request.POST, request.FILES, instance=employee)
        if self_edit_form.is_valid():
            self_edit_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'employee': employee,
        'change_form': change_form,
        'self_edit_form': self_edit_form,
    })


def _is_hr_or_superuser(user):
    """HR Admin or Superuser — can manage employees."""
    if user.is_superuser:
        return True
    try:
        return user.employee.is_hr()
    except Exception:
        return False


def hr_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            if request.user.employee.role != 'hr':
                messages.error(request, "Access denied. HR Admin only.")
                return redirect('dashboard:home')
        except Employee.DoesNotExist:
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Admin only.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_employee(request):
    try:
        return request.user.employee
    except Exception:
        return None


def hr_or_superuser_required(view_func):
    """Decorator allowing HR Admin OR Superuser."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _is_hr_or_superuser(request.user):
            messages.error(request, "Access denied. HR or Admin only.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def _generate_username(first_name, last_name=''):
    """Generate username as firstname.lastname (e.g. john.smith).
    If already taken, appends incrementing numbers: john.smith2, john.smith3, …
    Falls back gracefully when only first_name is provided (AJAX suggest endpoint).
    """
    from django.contrib.auth.models import User
    import re
    first = re.sub(r'[^a-z]', '', first_name.lower()) or 'user'
    last = re.sub(r'[^a-z]', '', last_name.lower())
    base = f"{first}.{last}" if last else first
    candidate = base
    counter = 2
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate


@hr_or_superuser_required
def employee_list(request):
    from django.db.models import Q, Value
    from django.db.models.functions import Concat
    show_former = request.GET.get('show_former', '0') == '1'
    name_q = request.GET.get('q', '').strip()
    dept_q = request.GET.get('dept', '').strip()
    role_q = request.GET.get('role', '').strip()

    employees = Employee.objects.filter(
        is_active=not show_former
    ).select_related('user', 'department', 'supervisor__user').annotate(
        full_name=Concat('user__first_name', Value(' '), 'user__last_name')
    )

    if name_q:
        employees = employees.filter(
            Q(full_name__icontains=name_q) |
            Q(user__first_name__icontains=name_q) |
            Q(user__last_name__icontains=name_q) |
            Q(employee_id__icontains=name_q) |
            Q(position__icontains=name_q)
        )
    if dept_q:
        employees = employees.filter(department_id=dept_q)
    if role_q:
        employees = employees.filter(role=role_q)

    # Chronological order — most recently joined first; fall back to account creation date
    employees = employees.order_by(
        '-date_joined_company', '-user__date_joined'
    )

    from accounts.models import Department
    departments = Department.objects.all().order_by('name')
    managers = Employee.objects.filter(
        role__in=('manager', 'unit_head', 'hr', 'admin_director', 'finance_director', 'ceo')
    ).select_related('user').order_by('user__last_name', 'user__first_name')

    return render(request, 'accounts/employee_list.html', {
        'employees': employees,
        'show_former': show_former,
        'departments': departments,
        'name_q': name_q,
        'dept_q': dept_q,
        'role_q': role_q,
        'role_choices': Employee.ROLE_CHOICES,
        'managers': managers,
    })


@hr_or_superuser_required
def employee_create(request):
    # Auto-generate username suggestion on GET (or from POST first_name + last_name)
    auto_username = ''
    first_name_hint = request.POST.get('first_name', '')
    last_name_hint = request.POST.get('last_name', '')
    if first_name_hint:
        auto_username = _generate_username(first_name_hint, last_name_hint)

    form = EmployeeCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                employee = form.save()

                # Auto-set role based on contract type if role wasn't explicitly changed
                ct = form.cleaned_data.get('contract_type', '')
                if ct == 'INTERN' and employee.role == 'employee':
                    employee.role = 'intern'
                    employee.save(update_fields=['role'])
                elif ct == 'WACS' and employee.role == 'employee':
                    employee.role = 'wacs_resident'
                    employee.save(update_fields=['role'])

                from leaves.models import LeaveBalance
                from datetime import date
                LeaveBalance.objects.get_or_create(
                    employee=employee,
                    year=date.today().year,
                    defaults={'total_entitlement': 18}
                )

                # Create initial contract from registration data
                from contracts.models import Contract
                contract = Contract.objects.create(
                    employee=employee,
                    contract_type=form.cleaned_data['contract_type'],
                    contract_number=form.cleaned_data.get('contract_number', ''),
                    start_date=form.cleaned_data['contract_start_date'],
                    end_date=form.cleaned_data.get('contract_end_date') or None,
                    status='active',
                    created_by=request.user,
                    notes='Issued at registration.',
                )

                # Welcome notification to the new employee
                from notifications.utils import notify
                from contracts.views import _contract_issue_message
                from django.conf import settings
                _ctitle, _cmsg = _contract_issue_message(contract)
                ct = contract.contract_type
                if ct == 'INTERN':
                    welcome_intro = f"Welcome to AEF HRM, {employee.get_full_name()}! Your internship account has been created and activated."
                elif ct == 'WACS':
                    welcome_intro = f"Welcome to AEF HRM, {employee.get_full_name()}! Your WACS Residency account has been created and activated."
                else:
                    welcome_intro = f"Welcome to AEF HRM, {employee.get_full_name()}! Your account has been created and activated."
                site_base = getattr(settings, 'SITE_URL', '').rstrip('/')
                login_url = f"{site_base}/accounts/login/" if site_base else "/accounts/login/"
                _plain_password = form.cleaned_data['password']
                credentials_msg = (
                    f"\n\nYour login credentials:\n"
                    f"Username: {employee.user.username}\n"
                    f"Password: {_plain_password}\n"
                    f"Login at: {login_url}\n\n"
                    f"Please change your password after your first login."
                )
                notify(
                    employee.user,
                    title='Welcome — Your Account Is Now Active',
                    message=f"{welcome_intro}{credentials_msg}{_cmsg}",
                    notification_type='account_activated',
                    url='/contracts/my/',
                )

            messages.success(request, f"Employee {employee.get_full_name()} created and contract issued successfully.")
            return redirect('accounts:employee_list')
        except Exception as e:
            messages.error(request, f"Error creating employee: {e}")
    return render(request, 'accounts/employee_form.html', {
        'form': form,
        'title': 'Add New Employee',
        'auto_username': auto_username,
    })


@hr_or_superuser_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeEditForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        emp_obj = form.save()
        # Handle signature upload separately from the form
        sig_file = request.FILES.get('signature')
        if sig_file:
            from django.core.files.base import ContentFile
            import os
            processed = process_signature(sig_file)
            if processed:
                # Delete old signature file if exists
                if emp_obj.signature:
                    try:
                        emp_obj.signature.delete(save=False)
                    except Exception:
                        pass
                fname = os.path.splitext(sig_file.name)[0] + '_sig.png'
                raw_bytes = processed.read()
                emp_obj.signature.save(fname, ContentFile(raw_bytes), save=False)
                import base64 as _b64
                emp_obj.signature_b64 = 'data:image/png;base64,' + _b64.b64encode(raw_bytes).decode('utf-8')
                emp_obj.save(update_fields=['signature', 'signature_b64'])
        messages.success(request, "Employee updated successfully.")
        return redirect('accounts:employee_list')

    from contracts.models import Contract
    active_contract = employee.contracts.filter(status='active').first()
    contract_history = employee.contracts.exclude(pk=active_contract.pk).order_by('-start_date') if active_contract else employee.contracts.order_by('-start_date')

    return render(request, 'accounts/employee_form.html', {
        'form': form,
        'title': 'Edit Employee',
        'employee': employee,
        'active_contract': active_contract,
        'contract_history': contract_history,
    })


@hr_or_superuser_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        name = employee.get_full_name()
        employee.user.delete()  # cascades to employee record
        messages.success(request, f"Employee {name} deleted successfully.")
        return redirect('accounts:employee_list')
    return render(request, 'accounts/employee_confirm_delete.html', {'employee': employee})


@superuser_required
def department_list(request):
    departments = Department.objects.all()
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Department added.")
        return redirect('accounts:department_list')
    return render(request, 'accounts/department_list.html', {'departments': departments, 'form': form})


@superuser_required
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        dept.delete()
        messages.success(request, "Department deleted.")
    return redirect('accounts:department_list')


@login_required
def set_employee_signature(request, pk):
    """Superuser-only: draw and save a signature on behalf of a key approver."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('accounts:employee_list')
    if request.method != 'POST':
        return redirect('accounts:employee_edit', pk=pk)

    employee = get_object_or_404(Employee, pk=pk)
    b64_data = request.POST.get('signature_data', '')

    if not b64_data or not b64_data.startswith('data:image/png;base64,'):
        messages.error(request, "No signature drawn.")
        return redirect('accounts:employee_edit', pk=pk)

    import base64
    from django.core.files.base import ContentFile
    try:
        raw = base64.b64decode(b64_data.split(',', 1)[1])
        if employee.signature:
            try:
                employee.signature.delete(save=False)
            except Exception:
                pass
        fname = f"{employee.employee_id}_sig.png"
        employee.signature.save(fname, ContentFile(raw), save=False)
        employee.signature_b64 = b64_data
        employee.save(update_fields=['signature', 'signature_b64'])
        messages.success(request, f"Signature saved for {employee.get_full_name()}.")
    except Exception:
        messages.error(request, "Could not save signature. Please try again.")
    return redirect('accounts:employee_edit', pk=pk)


@login_required
def profile_save_signature(request):
    """Any logged-in employee can save/update their own signature from the profile page."""
    if request.method != 'POST':
        return redirect('accounts:profile')

    try:
        employee = request.user.employee
    except Exception:
        messages.error(request, "Employee profile not found.")
        return redirect('accounts:profile')

    b64_data = request.POST.get('signature_data', '')
    if not b64_data or not b64_data.startswith('data:image/png;base64,'):
        messages.error(request, "No signature drawn.")
        return redirect('accounts:profile')

    import base64
    from django.core.files.base import ContentFile
    try:
        raw = base64.b64decode(b64_data.split(',', 1)[1])
        if employee.signature:
            try:
                employee.signature.delete(save=False)
            except Exception:
                pass
        fname = f"{employee.employee_id}_sig.png"
        employee.signature.save(fname, ContentFile(raw), save=False)
        employee.signature_b64 = b64_data
        employee.save(update_fields=['signature', 'signature_b64'])
        messages.success(request, "Signature saved successfully.")
    except Exception:
        messages.error(request, "Could not save signature. Please try again.")
    return redirect('accounts:profile')


@login_required
def change_password(request):
    """Allows any logged-in user to change their own password."""
    from django.contrib.auth import update_session_auth_hash
    form = ChangePasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        update_session_auth_hash(request, request.user)  # keep user logged in
        messages.success(request, "Password changed successfully.")
        return redirect('accounts:profile')
    return render(request, 'accounts/change_password.html', {'form': form})


@superuser_required
def admin_reset_credentials(request, pk):
    """Allows superuser to reset any employee's username and/or password."""
    employee = get_object_or_404(Employee, pk=pk)
    form = AdminResetCredentialsForm(employee.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Credentials updated for {employee.get_full_name()}.")
        return redirect('accounts:employee_list')
    return render(request, 'accounts/admin_reset_credentials.html', {
        'form': form,
        'employee': employee,
    })


@login_required
def employee_history(request, pk):
    """Comprehensive employee record: profile, contracts, leaves, discipline.
    Access: HR, Admin Director, Finance Director, CEO, Superuser only.
    """
    viewer = None
    try:
        viewer = request.user.employee
    except Employee.DoesNotExist:
        pass

    is_privileged = (
        request.user.is_superuser
        or (viewer and (viewer.is_hr() or viewer.is_director() or viewer.is_ceo()))
    )
    if not is_privileged:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    employee = get_object_or_404(
        Employee.objects.select_related('user', 'department', 'supervisor__user'),
        pk=pk
    )

    from contracts.models import Contract
    from leaves.models import LeaveRequest, LeaveBalance
    from discipline.models import DisciplineRecord

    contracts = Contract.objects.filter(employee=employee).order_by('start_date', 'created_at')
    leave_requests = LeaveRequest.objects.filter(employee=employee).select_related(
        'leave_type', 'manager_action_by__user', 'hr_action_by__user'
    ).order_by('-created_at')
    discipline_records = DisciplineRecord.objects.filter(employee=employee).select_related(
        'issued_by'
    ).order_by('-date_issued')

    from datetime import date
    today = date.today()
    balance = LeaveBalance.objects.filter(employee=employee, year=today.year).first()

    from accounts.models import EmployeeDocument
    documents = EmployeeDocument.objects.filter(employee=employee).select_related("uploaded_by")

    return render(request, 'accounts/employee_history.html', {
        'employee': employee,
        'contracts': contracts,
        'leave_requests': leave_requests,
        'discipline_records': discipline_records,
        'balance': balance,
        'today': today,
        'documents': documents,
        'is_privileged': is_privileged,
    })


@login_required
def username_suggest(request):
    """AJAX endpoint: suggest next available username for a given first_name + last_name."""
    from django.http import JsonResponse
    first_name = request.GET.get('first_name', '').strip()
    last_name = request.GET.get('last_name', '').strip()
    if not first_name:
        return JsonResponse({'username': ''})
    username = _generate_username(first_name, last_name)
    return JsonResponse({'username': username})


@hr_or_superuser_required
def bulk_assign_manager(request):
    """Assign a line manager or unit head to multiple selected employees at once."""
    if request.method != 'POST':
        return redirect('accounts:employee_list')

    employee_ids = request.POST.getlist('employee_ids')
    assignment_type = request.POST.get('assignment_type')
    manager_id = request.POST.get('manager_id')

    if not employee_ids:
        messages.error(request, "No employees selected.")
        return redirect('accounts:employee_list')
    if not manager_id:
        messages.error(request, "Please select a manager to assign.")
        return redirect('accounts:employee_list')

    try:
        manager = Employee.objects.get(pk=manager_id)
    except Employee.DoesNotExist:
        messages.error(request, "Selected manager/unit head not found.")
        return redirect('accounts:employee_list')

    qs = Employee.objects.filter(pk__in=employee_ids)
    count = qs.count()

    if assignment_type == 'department':
        try:
            dept = Department.objects.get(pk=manager_id)
        except Department.DoesNotExist:
            messages.error(request, "Selected department not found.")
            return redirect('accounts:employee_list')
        qs.update(department=dept)
        messages.success(request, f"Department set to {dept.name} for {count} employee(s).")
    elif assignment_type == 'unit_head':
        qs.update(unit_head=manager)
        messages.success(request, f"Unit Head set to {manager.get_full_name()} for {count} employee(s).")
    else:
        qs.update(supervisor=manager)
        messages.success(request, f"Line Manager set to {manager.get_full_name()} for {count} employee(s).")

    return redirect('accounts:employee_list')


@login_required
def employee_import(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. System Admin only.")
        return redirect('dashboard:home')
    """Bulk-import employees from an Excel (.xlsx) file."""
    from django.http import HttpResponse
    import openpyxl
    from contracts.models import Contract
    from datetime import date as _date, datetime as _datetime

    COLUMN_MAP = [
        'first_name', 'last_name', 'email', 'employee_id', 'department',
        'role', 'position', 'phone', 'date_of_birth', 'date_joined_company',
        'sex', 'nationality', 'qualifications', 'staff_category',
        'contract_number', 'contract_type', 'contract_start_date', 'contract_end_date',
    ]

    if request.method == 'GET' and request.GET.get('template') == '1':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Employees'
        for col_idx, h in enumerate(COLUMN_MAP, 1):
            ws.cell(row=1, column=col_idx, value=h)
        example = [
            'Jane', 'Doe', 'jane.doe@example.com', 'EMP001', 'Nursing',
            'employee', 'Staff Nurse', '+237600000000', '1990-05-20', '2020-01-15',
            'F', 'Cameroonian', 'BSc Nursing', 'A',
            'CTR-2024-001', 'CDI', '2020-01-15', '',
        ]
        for col_idx, val in enumerate(example, 1):
            ws.cell(row=2, column=col_idx, value=val)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="employee_import_template.xlsx"'
        wb.save(response)
        return response

    results = []
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "Please select an Excel file to upload.")
            return redirect('accounts:employee_import')
        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active
        except Exception as e:
            messages.error(request, f"Could not read Excel file: {e}")
            return redirect('accounts:employee_import')

        headers_raw = [
            str(ws.cell(row=1, column=c).value or '').strip().lower().replace(' ', '_')
            for c in range(1, ws.max_column + 1)
        ]

        def _get(row_vals, key):
            return str(row_vals.get(key, '') or '').strip()

        def _parse_date(val):
            if not val:
                return None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
                try:
                    return _datetime.strptime(val, fmt).date()
                except ValueError:
                    pass
            return None

        created_count = 0
        error_count = 0

        for row_idx in range(2, ws.max_row + 1):
            row_vals = {}
            for col_idx, h in enumerate(headers_raw, 1):
                row_vals[h] = ws.cell(row=row_idx, column=col_idx).value

            if not any(v for v in row_vals.values() if v is not None):
                continue

            first_name = _get(row_vals, 'first_name')
            last_name  = _get(row_vals, 'last_name')
            emp_id     = _get(row_vals, 'employee_id')

            if not (first_name and last_name and emp_id):
                results.append({'row': row_idx, 'status': 'error',
                    'name': f"{first_name} {last_name}".strip() or f"Row {row_idx}",
                    'message': "Missing first_name, last_name or employee_id."})
                error_count += 1
                continue

            if Employee.objects.filter(employee_id=emp_id).exists():
                results.append({'row': row_idx, 'status': 'skipped',
                    'name': f"{first_name} {last_name}",
                    'message': f"Employee ID {emp_id} already exists."})
                error_count += 1
                continue

            try:
                with transaction.atomic():
                    from django.contrib.auth.models import User as _User

                    dept_name = _get(row_vals, 'department')
                    dept = Department.objects.filter(name__iexact=dept_name).first() if dept_name else None

                    role = _get(row_vals, 'role') or 'employee'
                    ct   = (_get(row_vals, 'contract_type') or 'CDI').upper()
                    if ct not in ('CDI', 'CDD', 'INTERN', 'WACS'):
                        ct = 'CDI'
                    if ct == 'INTERN' and role == 'employee':
                        role = 'intern'
                    elif ct == 'WACS' and role == 'employee':
                        role = 'wacs_resident'

                    username = _generate_username(first_name)
                    email    = _get(row_vals, 'email') or f"{username}@hospital.local"

                    user = _User.objects.create_user(
                        username=username, first_name=first_name,
                        last_name=last_name, email=email, password='Micei2021',
                    )
                    employee = Employee.objects.create(
                        user=user, employee_id=emp_id, department=dept, role=role,
                        position=_get(row_vals, 'position'),
                        phone=_get(row_vals, 'phone'),
                        date_of_birth=_parse_date(_get(row_vals, 'date_of_birth')),
                        date_joined_company=_parse_date(_get(row_vals, 'date_joined_company')),
                        sex=_get(row_vals, 'sex'),
                        nationality=_get(row_vals, 'nationality'),
                        qualifications=_get(row_vals, 'qualifications'),
                        staff_category=_get(row_vals, 'staff_category'),
                        contract_number=_get(row_vals, 'contract_number'),
                    )

                    from leaves.models import LeaveBalance
                    LeaveBalance.objects.get_or_create(
                        employee=employee, year=_date.today().year,
                        defaults={'total_entitlement': 18},
                    )
                    Contract.objects.create(
                        employee=employee, contract_type=ct,
                        contract_number=_get(row_vals, 'contract_number'),
                        start_date=_parse_date(_get(row_vals, 'contract_start_date')) or _date.today(),
                        end_date=_parse_date(_get(row_vals, 'contract_end_date')),
                        status='active', created_by=request.user,
                        notes='Imported via Excel.',
                    )

                results.append({'row': row_idx, 'status': 'created',
                    'name': f"{first_name} {last_name}",
                    'message': f"Created (username: {username})."})
                created_count += 1

            except Exception as exc:
                results.append({'row': row_idx, 'status': 'error',
                    'name': f"{first_name} {last_name}",
                    'message': str(exc)})
                error_count += 1

        messages.success(request, f"Import complete: {created_count} created, {error_count} errors/skipped.")

    return render(request, 'accounts/employee_import.html', {
        'results': results,
        'column_map': COLUMN_MAP,
    })


# ─────────────────────────────────────────────────────────────
#  EXCEL BULK UPLOAD
# ─────────────────────────────────────────────────────────────

# Column name → (Employee field, type)
# Required columns are marked True; optional are False.
EXCEL_COLUMNS = {
    # Personal
    'first_name':         ('first_name',          'str',  True),
    'last_name':          ('last_name',           'str',  True),
    'email':              ('email',               'str',  True),
    'employee_id':        ('employee_id',         'str',  True),
    'date_of_birth':      ('date_of_birth',       'date', False),
    'sex':                ('sex',                 'str',  False),
    'nationality':        ('nationality',         'str',  False),
    'phone':              ('phone',               'str',  False),
    # Employment
    'position':           ('position',            'str',  False),
    'department':         ('department',          'dept', False),
    'role':               ('role',               'str',  False),
    'staff_category':     ('staff_category',     'str',  False),
    'date_joined_hospital': ('date_joined_company', 'date', False),
    'qualifications':     ('qualifications',      'str',  False),
    'contract_number':    ('contract_number',     'str',  False),
    # Contract (REQUIRED at creation)
    'contract_type':      ('contract_type',       'str',  True),
    'contract_start_date': ('contract_start_date', 'date', True),
    'contract_end_date':  ('contract_end_date',   'date', False),
}

VALID_ROLES = {v for v, _ in Employee.ROLE_CHOICES}
VALID_CONTRACT_TYPES = {'CDI', 'CDD', 'INTERN', 'WACS'}
DEFAULT_PASSWORD = 'Micei2021'


def _parse_cell(value, cell_type):
    """Parse a raw Excel cell value to the target Python type."""
    from datetime import date as _date
    import datetime as _dt

    if value is None or str(value).strip() == '':
        return None

    if cell_type == 'str':
        return str(value).strip()
    if cell_type == 'date':
        if isinstance(value, (_date, _dt.datetime)):
            return value.date() if hasattr(value, 'date') else value
        # Try ISO string
        try:
            return _dt.date.fromisoformat(str(value).strip()[:10])
        except ValueError:
            return None
    if cell_type == 'dept':
        return str(value).strip()
    return value


def _normalize_col(val):
    """Normalise a column header: lowercase, collapse non-alphanumeric runs to underscore."""
    import re
    return re.sub(r'[^a-z0-9]+', '_', str(val or '').strip().lower()).strip('_')


# Maps normalised column names from any source (staff list, custom template) to internal keys.
_COL_ALIAS = {
    'matricule':            'employee_id',
    'employee_id':          'employee_id',
    'name':                 'full_name',
    'full_name':            'full_name',
    'first_name':           'first_name',
    'last_name':            'last_name',
    'category':             'staff_category',
    'staff_category':       'staff_category',
    'date_of_birth':        'date_of_birth',
    'sex':                  'sex',
    'nat':                  'nationality',
    'nationality':          'nationality',
    'date_employment':      'date_joined_company',
    'date_joined_hospital': 'date_joined_company',
    'date_joined_company':  'date_joined_company',
    'contrat_n':            'contract_number',
    'contract_n':           'contract_number',
    'contract_number':      'contract_number',
    'status':               'contract_type_raw',
    'contract_type':        'contract_type_raw',
    'position':             'position',
    'department':           'department',
    'qualifications':       'qualifications',
    'certifications':       'certifications',
    'email':                'email',
    'phone':                'phone',
    'contract_start_date':  'contract_start_date',
    'contract_end_date':    'contract_end_date',
    'role':                 'role',
}

_RECOGNIZED = set(_COL_ALIAS.keys())


def _map_contract_type(raw):
    """Map any Status/contract_type string to a valid contract type code."""
    raw = str(raw or '').strip().upper()
    for code in ('CDI', 'CDD', 'INTERN', 'WACS'):
        if code in raw:
            return code
    return 'CDI'  # default


@hr_or_superuser_required
def employee_excel_upload(request):
    """
    GET  → show upload form / template download
    POST → parse Excel (supports the actual staff list format), create employees
    """
    from datetime import date as _today_dt

    if request.method == 'GET':
        if request.GET.get('download_template') == '1':
            return _excel_template_download()
        return render(request, 'accounts/employee_excel_upload.html', {
            'column_info': EXCEL_COLUMNS,
        })

    # ── POST ────────────────────────────────────────────────
    uploaded = request.FILES.get('excel_file')
    if not uploaded:
        messages.error(request, "No file uploaded.")
        return redirect('accounts:employee_excel_upload')

    try:
        import openpyxl
        wb = openpyxl.load_workbook(uploaded, data_only=True)
        ws = wb.active
    except Exception as e:
        messages.error(request, f"Could not open Excel file: {e}")
        return redirect('accounts:employee_excel_upload')

    # ── Detect header row (row 1 may be a title row) ────────
    def _read_headers(row_idx):
        return [_normalize_col(ws.cell(row=row_idx, column=c).value)
                for c in range(1, ws.max_column + 1)]

    headers_r1 = _read_headers(1)
    headers_r2 = _read_headers(2)
    recognized_r1 = sum(1 for h in headers_r1 if h in _RECOGNIZED)
    recognized_r2 = sum(1 for h in headers_r2 if h in _RECOGNIZED)

    if recognized_r2 > recognized_r1:
        # Row 1 is a title; real headers are on row 2
        headers = headers_r2
        data_start_row = 3
    else:
        headers = headers_r1
        data_start_row = 2

    # Map positional headers → internal keys
    mapped_headers = [_COL_ALIAS.get(h, h) for h in headers]

    created_rows = []
    skipped_rows = []
    today = _today_dt.today()

    for row_idx, row in enumerate(ws.iter_rows(min_row=data_start_row, values_only=True), start=data_start_row):
        if all(v is None or str(v).strip() == '' for v in row):
            continue  # blank

        row_data = {mapped_headers[i]: row[i] for i in range(min(len(mapped_headers), len(row)))}
        errors = []

        # ── Name resolution ──────────────────────────────────
        if row_data.get('full_name'):
            full = _parse_cell(row_data['full_name'], 'str') or ''
            parts = full.split(None, 1)
            last_name  = parts[0] if parts else ''
            first_name = parts[1] if len(parts) > 1 else last_name
        else:
            first_name = _parse_cell(row_data.get('first_name'), 'str') or ''
            last_name  = _parse_cell(row_data.get('last_name'),  'str') or ''

        emp_id = _parse_cell(row_data.get('employee_id'), 'str') or ''

        if not first_name:
            errors.append("Missing name / first_name")
        if not emp_id:
            errors.append("Missing Matricule / employee_id")

        # ── Contract type ───────────────────────────────────
        contract_type = _map_contract_type(
            _parse_cell(row_data.get('contract_type_raw'), 'str') or ''
        )

        # ── Dates ───────────────────────────────────────────
        date_joined = _parse_cell(row_data.get('date_joined_company'), 'date')
        contract_start = _parse_cell(row_data.get('contract_start_date'), 'date') or date_joined
        contract_end   = _parse_cell(row_data.get('contract_end_date'), 'date')
        if not contract_start:
            contract_start = today  # last resort default

        # ── Department ──────────────────────────────────────
        dept_name = _parse_cell(row_data.get('department'), 'dept')
        dept_obj = None
        if dept_name:
            dept_obj = Department.objects.filter(name__iexact=dept_name).first()
            if not dept_obj:
                errors.append(f"Department '{dept_name}' not found")

        # ── Role ────────────────────────────────────────────
        role = _parse_cell(row_data.get('role'), 'str') or ''
        if not role:
            if contract_type == 'INTERN':
                role = 'intern'
            elif contract_type == 'WACS':
                role = 'wacs_resident'
            else:
                role = 'employee'
        if role not in VALID_ROLES:
            role = 'employee'

        # ── Duplicate check ─────────────────────────────────
        if emp_id and Employee.objects.filter(employee_id=emp_id).exists():
            errors.append(f"Employee ID '{emp_id}' already exists")

        # ── Qualifications (merge qualifications + certifications) ──
        qualif = _parse_cell(row_data.get('qualifications'), 'str') or ''
        certif = _parse_cell(row_data.get('certifications'), 'str') or ''
        combined_qualif = ' | '.join(filter(None, [qualif, certif]))

        if errors:
            skipped_rows.append({'row': row_idx, 'name': f"{first_name} {last_name}".strip(), 'errors': errors})
            continue

        # ── Create user + employee + contract ───────────────
        try:
            with transaction.atomic():
                from django.contrib.auth.models import User as _User
                username = _generate_username(first_name, last_name)
                email = _parse_cell(row_data.get('email'), 'str') or ''
                if not email:
                    email = f"{username}@hospital.local"

                user = _User(username=username, first_name=first_name,
                             last_name=last_name, email=email)
                user.set_password(DEFAULT_PASSWORD)
                user.save()

                emp = Employee(
                    user=user,
                    employee_id=emp_id,
                    department=dept_obj,
                    role=role,
                    staff_category=_parse_cell(row_data.get('staff_category'), 'str') or '',
                    position=_parse_cell(row_data.get('position'), 'str') or '',
                    phone=_parse_cell(row_data.get('phone'), 'str') or '',
                    date_of_birth=_parse_cell(row_data.get('date_of_birth'), 'date'),
                    date_joined_company=date_joined,
                    sex=(_parse_cell(row_data.get('sex'), 'str') or '')[:1].upper(),
                    nationality=_parse_cell(row_data.get('nationality'), 'str') or '',
                    contract_number=_parse_cell(row_data.get('contract_number'), 'str') or '',
                    qualifications=combined_qualif,
                )
                emp.save()

                from leaves.models import LeaveBalance
                LeaveBalance.objects.get_or_create(
                    employee=emp, year=today.year,
                    defaults={'total_entitlement': 18},
                )

                from contracts.models import Contract
                Contract.objects.create(
                    employee=emp,
                    contract_type=contract_type,
                    start_date=contract_start,
                    end_date=contract_end,
                    status='active',
                    created_by=request.user,
                    notes='Imported via Excel upload.',
                )

                from notifications.utils import notify
                from django.conf import settings as _settings
                _site_base = getattr(_settings, 'SITE_URL', '').rstrip('/')
                _login_url = f"{_site_base}/accounts/login/" if _site_base else "/accounts/login/"
                notify(
                    user,
                    title='Welcome — Your Account Is Now Active',
                    message=(
                        f"Welcome to AEF HRM, {emp.get_full_name()}! Your account has been created. "
                        f"A {contract_type} contract starting {contract_start.strftime('%d %b %Y')} has been issued.\n\n"
                        f"Username: {username}\nPassword: {DEFAULT_PASSWORD}\nLogin at: {_login_url}\n\n"
                        f"Please change your password after first login."
                    ),
                    notification_type='account_activated',
                    url='/contracts/my/',
                )

            created_rows.append({'row': row_idx, 'name': emp.get_full_name(), 'emp_id': emp_id, 'contract': contract_type})
        except Exception as exc:
            skipped_rows.append({'row': row_idx, 'name': f"{first_name} {last_name}".strip(), 'errors': [str(exc)]})

    return render(request, 'accounts/employee_excel_results.html', {
        'created': created_rows,
        'skipped': skipped_rows,
        'total_processed': len(created_rows) + len(skipped_rows),
    })


def _excel_template_download():
    """Return a .xlsx template that mirrors the staff list column layout."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"

    # Columns match the actual staff list format
    headers = [
        'Matricule', 'Name', 'Category', 'Date of Birth', 'Sex',
        'Nat.', 'Date Employment', 'Contrat N°', 'Status',
        'Position', 'Department', 'Qualifications', 'Certifications',
        'Email', 'Contract End Date',
    ]
    required_cols = {'Matricule', 'Name', 'Status'}

    header_fill   = PatternFill(start_color="0A4D68", end_color="0A4D68", fill_type="solid")
    required_fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
    header_font   = Font(color="FFFFFF", bold=True)

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.fill = required_fill if h in required_cols else header_fill
        ws.column_dimensions[cell.column_letter].width = max(18, len(h) + 4)

    # Sample row
    ws.append([
        'AEF001', 'Doe Jane', '12B-J', '1990-05-15', 'F',
        'CMR', '2020-01-15', 'AEF00120200115', 'CDI',
        'Staff Nurse', 'Nursing', 'BSc Nursing', 'WACS',
        'jane.doe@hospital.cm', '',
    ])

    # Notes sheet
    notes_ws = wb.create_sheet("Notes")
    notes_ws['A1'] = "Field Notes"
    notes_ws['A1'].font = Font(bold=True)
    notes = [
        ('Matricule',         'Unique employee ID (required)'),
        ('Name',              'Full name — Family name first, e.g. "Doe Jane". Required.'),
        ('Category',          'Staff category — any format (e.g. 5, 12B-J, A, III)'),
        ('Date of Birth',     'Format: YYYY-MM-DD or DD/MM/YYYY'),
        ('Sex',               'M or F'),
        ('Nat.',              'Nationality (e.g. CMR, Cameroonian)'),
        ('Date Employment',   'Employment start date — used as contract start if Contract Start Date is absent'),
        ('Contrat N°',        'Official contract/personnel number'),
        ('Status',            'Contract type: CDI | CDD | INTERN | WACS  (default: CDI)'),
        ('Position',          'Job title / position'),
        ('Department',        'Must match an existing department name'),
        ('Qualifications',    'Academic qualifications'),
        ('Certifications',    'Professional certifications (merged with Qualifications)'),
        ('Email',             'Work email — auto-generated if blank'),
        ('Contract End Date', 'Required for CDD, INTERN, WACS. Leave blank for CDI.'),
    ]
    for r, (field, note) in enumerate(notes, start=3):
        notes_ws.cell(row=r, column=1, value=field).font = Font(bold=True)
        notes_ws.cell(row=r, column=2, value=note)
    notes_ws.column_dimensions['A'].width = 22
    notes_ws.column_dimensions['B'].width = 65

    buf = __import__('io').BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="staff_import_template.xlsx"'
    return response



@hr_or_superuser_required
def export_credentials(request):
    """Download a CSV of all employee usernames (passwords cannot be recovered - shows default)."""
    import csv
    from django.http import HttpResponse
    from datetime import date as _date

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="staff_credentials_' + str(_date.today()) + '.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Full Name', 'Username', 'Email', 'Role', 'Department', 'Default Password'])

    for emp in Employee.objects.select_related('user', 'department').order_by('user__last_name', 'user__first_name'):
        writer.writerow([
            emp.employee_id,
            emp.get_full_name(),
            emp.user.username,
            emp.user.email,
            emp.get_role_display(),
            emp.department.name if emp.department else '',
            'Micei2021 (default - may have been changed by employee)',
        ])
    return response


@login_required
def document_upload(request, employee_pk):
    """HR/superuser uploads a document to an employee's file."""
    from accounts.models import EmployeeDocument
    employee = get_object_or_404(Employee, pk=employee_pk)
    viewer = get_employee(request)
    is_privileged = (
        request.user.is_superuser
        or (viewer and (viewer.is_hr() or viewer.is_director() or viewer.is_ceo()))
    )
    if not is_privileged:
        return redirect('dashboard:home')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'other')
        file = request.FILES.get('file')
        if title and file:
            EmployeeDocument.objects.create(
                employee=employee,
                title=title,
                category=category,
                file=file,
                uploaded_by=request.user,
            )
            messages.success(request, f'Document "{title}" uploaded successfully.')
        else:
            messages.error(request, 'Title and file are required.')
    return redirect(reverse('accounts:employee_history', args=[employee_pk]) + '#documents')


@login_required
def my_documents(request):
    """Any employee uploads and views their own documents."""
    from accounts.models import EmployeeDocument
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        messages.error(request, "No employee profile found.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'other')
        file = request.FILES.get('file')
        if title and file:
            EmployeeDocument.objects.create(
                employee=employee,
                title=title,
                category=category,
                file=file,
                uploaded_by=request.user,
            )
            messages.success(request, f'Document "{title}" uploaded successfully.')
        else:
            messages.error(request, 'Title and file are required.')
        return redirect('accounts:my_documents')

    documents = EmployeeDocument.objects.filter(employee=employee).select_related('uploaded_by')
    from accounts.models import EmployeeDocument as _ED
    return render(request, 'accounts/my_documents.html', {
        'employee': employee,
        'documents': documents,
        'categories': _ED.CATEGORY_CHOICES,
    })


@login_required
def my_document_delete(request, doc_pk):
    """Employee deletes one of their own documents."""
    from accounts.models import EmployeeDocument
    doc = get_object_or_404(EmployeeDocument, pk=doc_pk)
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return redirect('dashboard:home')
    if doc.employee != employee and not request.user.is_superuser:
        messages.error(request, "You can only delete your own documents.")
        return redirect('accounts:my_documents')
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document deleted.')
    return redirect('accounts:my_documents')


@login_required
def document_delete(request, doc_pk):
    """HR/superuser deletes an employee document."""
    from accounts.models import EmployeeDocument
    doc = get_object_or_404(EmployeeDocument, pk=doc_pk)
    viewer = get_employee(request)
    is_privileged = (
        request.user.is_superuser
        or (viewer and (viewer.is_hr() or viewer.is_director() or viewer.is_ceo()))
    )
    if not is_privileged:
        return redirect('dashboard:home')
    employee_pk = doc.employee.pk
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document deleted.')
    return redirect(reverse('accounts:employee_history', args=[employee_pk]) + '#documents')
