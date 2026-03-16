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


@superuser_required
def employee_list(request):
    employees = Employee.objects.select_related('user', 'department', 'supervisor__user').all()
    return render(request, 'accounts/employee_list.html', {'employees': employees})


@superuser_required
def employee_create(request):
    form = EmployeeCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                employee = form.save()

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
                    start_date=form.cleaned_data['contract_start_date'],
                    end_date=form.cleaned_data.get('contract_end_date') or None,
                    status='active',
                    created_by=request.user,
                    notes='Issued at registration.',
                )

                # Welcome notification to the new employee
                from notifications.utils import notify
                contract_label = contract.get_contract_type_display()
                notify(
                    employee.user,
                    title='Welcome — Your Account Is Now Active',
                    message=(
                        f"Welcome to LeaveDesk, {employee.get_full_name()}! Your account has been created and activated. "
                        f"A {contract_label} contract starting {contract.start_date.strftime('%d %b %Y')} has been issued. "
                        f"Please visit the HR Office to sign and collect your contract document."
                    ),
                    notification_type='account_activated',
                    url='/contracts/my-contract/',
                )

            messages.success(request, f"Employee {employee.get_full_name()} created and contract issued successfully.")
            return redirect('accounts:employee_list')
        except Exception as e:
            messages.error(request, f"Error creating employee: {e}")
    return render(request, 'accounts/employee_form.html', {'form': form, 'title': 'Add New Employee'})


@superuser_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeEditForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Employee updated successfully.")
        return redirect('accounts:employee_list')
    return render(request, 'accounts/employee_form.html', {'form': form, 'title': 'Edit Employee', 'employee': employee})


@superuser_required
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
