from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Employee, Department
from .forms import LoginForm, EmployeeCreateForm, EmployeeEditForm, DepartmentForm, ChangePasswordForm, AdminResetCredentialsForm


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
    return render(request, 'accounts/profile.html', {'employee': employee, 'change_form': change_form})


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
    show_former = request.GET.get('show_former', '0') == '1'
    if show_former:
        employees = Employee.objects.filter(is_active=False).select_related('user', 'department', 'supervisor__user')
    else:
        employees = Employee.objects.filter(is_active=True).select_related('user', 'department', 'supervisor__user')
    return render(request, 'accounts/employee_list.html', {'employees': employees, 'show_former': show_former})


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
                _ctitle, _cmsg = _contract_issue_message(contract)
                ct = contract.contract_type
                if ct == 'INTERN':
                    welcome_intro = f"Welcome to LeaveDesk, {employee.get_full_name()}! Your internship account has been created and activated."
                elif ct == 'WACS':
                    welcome_intro = f"Welcome to LeaveDesk, {employee.get_full_name()}! Your WACS Residency account has been created and activated."
                else:
                    welcome_intro = f"Welcome to LeaveDesk, {employee.get_full_name()}! Your account has been created and activated."
                notify(
                    employee.user,
                    title='Welcome — Your Account Is Now Active',
                    message=f"{welcome_intro} {_cmsg}",
                    notification_type='account_activated',
                    url='/contracts/my-contract/',
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
                emp_obj.signature.save(fname, ContentFile(processed.read()), save=True)
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
        employee.signature.save(fname, ContentFile(raw), save=True)
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
        employee.signature.save(fname, ContentFile(raw), save=True)
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
def username_suggest(request):
    """AJAX endpoint: suggest next available username for a given first_name + last_name."""
    from django.http import JsonResponse
    first_name = request.GET.get('first_name', '').strip()
    last_name = request.GET.get('last_name', '').strip()
    if not first_name:
        return JsonResponse({'username': ''})
    username = _generate_username(first_name, last_name)
    return JsonResponse({'username': username})


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


@hr_or_superuser_required
def employee_excel_upload(request):
    """
    GET  → show upload form with template download
    POST → parse Excel, create employees, return results page
    """
    import io
    from django.http import HttpResponse as _HR
    from datetime import date as _today_dt

    if request.method == 'GET':
        # Check if template download requested
        if request.GET.get('download_template') == '1':
            return _excel_template_download()
        return render(request, 'accounts/employee_excel_upload.html', {
            'column_info': EXCEL_COLUMNS,
        })

    # ── POST: process uploaded file ──────────────────────────
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

    # Read header row (row 1) — normalise to lowercase, replace spaces with underscores
    headers = []
    for cell in ws[1]:
        val = str(cell.value or '').strip().lower().replace(' ', '_')
        headers.append(val)

    created_rows = []
    skipped_rows = []
    today = _today_dt.today()

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None or str(v).strip() == '' for v in row):
            continue  # blank row

        row_data = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        errors = []

        # ── Extract values ──
        first_name = _parse_cell(row_data.get('first_name'), 'str') or ''
        last_name  = _parse_cell(row_data.get('last_name'),  'str') or ''
        email      = _parse_cell(row_data.get('email'),      'str') or ''
        emp_id     = _parse_cell(row_data.get('employee_id'), 'str') or ''

        if not first_name:
            errors.append("Missing first_name")
        if not last_name:
            errors.append("Missing last_name")
        if not emp_id:
            errors.append("Missing employee_id")

        contract_type = (_parse_cell(row_data.get('contract_type'), 'str') or '').upper()
        if contract_type not in VALID_CONTRACT_TYPES:
            errors.append(f"Invalid contract_type '{contract_type}' (use CDI, CDD, INTERN, WACS)")
        contract_start = _parse_cell(row_data.get('contract_start_date'), 'date')
        if not contract_start:
            errors.append("Missing contract_start_date")
        contract_end = _parse_cell(row_data.get('contract_end_date'), 'date')
        if contract_type in ('CDD', 'INTERN', 'WACS') and not contract_end:
            errors.append(f"contract_end_date required for {contract_type}")

        # Department lookup
        dept_name = _parse_cell(row_data.get('department'), 'dept')
        dept_obj = None
        if dept_name:
            try:
                dept_obj = Department.objects.get(name__iexact=dept_name)
            except Department.DoesNotExist:
                errors.append(f"Department '{dept_name}' not found")

        # Role
        role = _parse_cell(row_data.get('role'), 'str') or ''
        if not role:
            role = 'intern' if contract_type == 'INTERN' else ('wacs_resident' if contract_type == 'WACS' else 'employee')
        if role not in VALID_ROLES:
            errors.append(f"Invalid role '{role}'")

        # Duplicate checks
        if emp_id and Employee.objects.filter(employee_id=emp_id).exists():
            errors.append(f"Employee ID '{emp_id}' already exists")

        from django.contrib.auth.models import User as _User
        if email and _User.objects.filter(email=email).exists():
            errors.append(f"Email '{email}' already in use")

        if errors:
            skipped_rows.append({'row': row_idx, 'name': f"{first_name} {last_name}", 'errors': errors})
            continue

        # ── Create user + employee + contract ──
        try:
            with transaction.atomic():
                username = _generate_username(first_name)
                user = _User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )
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
                    date_joined_company=_parse_cell(row_data.get('date_joined_hospital'), 'date'),
                    sex=_parse_cell(row_data.get('sex'), 'str') or '',
                    nationality=_parse_cell(row_data.get('nationality'), 'str') or '',
                    contract_number=_parse_cell(row_data.get('contract_number'), 'str') or '',
                    qualifications=_parse_cell(row_data.get('qualifications'), 'str') or '',
                )
                emp.save()

                from leaves.models import LeaveBalance
                LeaveBalance.objects.create(employee=emp, year=today.year, total_entitlement=18)

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
                notify(
                    user,
                    title='Welcome — Your Account Is Now Active',
                    message=(
                        f"Welcome to LeaveDesk, {emp.get_full_name()}! Your account has been created. "
                        f"A {contract_type} contract starting {contract_start.strftime('%d %b %Y')} has been issued."
                    ),
                    notification_type='account_activated',
                    url='/contracts/my-contract/',
                )

            created_rows.append({'row': row_idx, 'name': emp.get_full_name(), 'emp_id': emp_id, 'contract': contract_type})
        except Exception as exc:
            skipped_rows.append({'row': row_idx, 'name': f"{first_name} {last_name}", 'errors': [str(exc)]})

    return render(request, 'accounts/employee_excel_results.html', {
        'created': created_rows,
        'skipped': skipped_rows,
        'total_processed': len(created_rows) + len(skipped_rows),
    })


def _excel_template_download():
    """Return a downloadable .xlsx template with the correct column headers."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"

    headers = [
        'first_name', 'last_name', 'email', 'employee_id',
        'date_of_birth', 'sex', 'nationality', 'phone',
        'position', 'department', 'role', 'staff_category',
        'date_joined_hospital', 'qualifications', 'contract_number',
        'contract_type', 'contract_start_date', 'contract_end_date',
    ]

    required = {'first_name', 'last_name', 'email', 'employee_id', 'contract_type', 'contract_start_date'}

    header_fill   = PatternFill(start_color="0A4D68", end_color="0A4D68", fill_type="solid")
    required_fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
    header_font   = Font(color="FFFFFF", bold=True)

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        if h in required:
            cell.fill = required_fill
        else:
            cell.fill = header_fill
        ws.column_dimensions[cell.column_letter].width = max(18, len(h) + 4)

    # Sample row
    ws.append([
        'Jane', 'Doe', 'jane.doe@hospital.cm', 'EMP-001',
        '1990-05-15', 'F', 'Cameroonian', '+237 600000000',
        'Nurse', 'Nursing', 'employee', 'A',
        '2024-01-01', 'BSc Nursing', 'CTR-2024-001',
        'CDI', '2024-01-01', '',
    ])

    # Notes sheet
    notes_ws = wb.create_sheet("Notes")
    notes_ws['A1'] = "Field Notes"
    notes_ws['A1'].font = Font(bold=True)
    notes = [
        ['sex',           'Use: M or F'],
        ['role',          'employee | manager | hr | admin_director | finance_director | ceo | intern | wacs_resident'],
        ['contract_type', 'CDI | CDD | INTERN | WACS'],
        ['department',    'Must match an existing department name exactly'],
        ['staff_category','A–L, AA–AL, or BA–BL'],
        ['contract_end_date', 'Required for CDD, INTERN, WACS. Leave blank for CDI.'],
        ['date_of_birth / contract dates', 'Format: YYYY-MM-DD'],
    ]
    for r, (field, note) in enumerate(notes, start=3):
        notes_ws.cell(row=r, column=1, value=field).font = Font(bold=True)
        notes_ws.cell(row=r, column=2, value=note)
    notes_ws.column_dimensions['A'].width = 30
    notes_ws.column_dimensions['B'].width = 70

    buf = __import__('io').BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="employee_import_template.xlsx"'
    return response
