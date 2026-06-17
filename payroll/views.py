from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import date

from accounts.models import Employee
from .models import Payslip, MONTH_CHOICES


def _payroll_enabled():
    from dashboard.models import SystemSettings
    return SystemSettings.get().payroll_enabled


def _is_hr_or_above(user):
    if user.is_superuser:
        return True
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_director() or emp.is_ceo()
    except Exception:
        return False


@login_required
def payslip_list(request):
    """HR/Admin: list all payslips. Employee: only own payslips."""
    if not _payroll_enabled() and not request.user.is_superuser:
        messages.error(request, "The Payroll module is not currently active.")
        return redirect('dashboard:home')
    is_hr = _is_hr_or_above(request.user)

    year_filter = request.GET.get('year', '')
    month_filter = request.GET.get('month', '')
    emp_filter = request.GET.get('employee', '')

    if is_hr:
        qs = Payslip.objects.select_related('employee__user', 'employee__department')
        if emp_filter:
            qs = qs.filter(employee__pk=emp_filter)
        employees = Employee.objects.filter(is_active=True).order_by('user__last_name')
    else:
        try:
            qs = request.user.employee.payslips.all()
        except Exception:
            qs = Payslip.objects.none()
        employees = None

    if year_filter:
        qs = qs.filter(period_year=year_filter)
    if month_filter:
        qs = qs.filter(period_month=month_filter)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    years = list(range(date.today().year, 2015, -1))

    return render(request, 'payroll/payslip_list.html', {
        'page_obj': page_obj,
        'is_hr': is_hr,
        'employees': employees,
        'months': MONTH_CHOICES,
        'years': years,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'emp_filter': emp_filter,
    })


@login_required
def payslip_create(request):
    """HR only: create a payslip for an employee."""
    if not _payroll_enabled() and not request.user.is_superuser:
        messages.error(request, "The Payroll module is not currently active.")
        return redirect('dashboard:home')
    if not _is_hr_or_above(request.user):
        messages.error(request, "Access denied.")
        return redirect('payroll:list')

    employees = Employee.objects.filter(is_active=True).order_by('user__last_name')
    today = date.today()

    if request.method == 'POST':
        emp_pk = request.POST.get('employee')
        month = request.POST.get('period_month')
        year = request.POST.get('period_year')
        gross = request.POST.get('gross_salary', '0')
        transport = request.POST.get('transport_allowance', '0')
        housing = request.POST.get('housing_allowance', '0')
        other_allow = request.POST.get('other_allowances', '0')
        other_allow_label = request.POST.get('other_allowances_label', '')
        cnps = request.POST.get('cnps', '0')
        income_tax = request.POST.get('income_tax', '0')
        other_ded = request.POST.get('other_deductions', '0')
        other_ded_label = request.POST.get('other_deductions_label', '')
        notes = request.POST.get('notes', '')
        payslip_file = request.FILES.get('payslip_file')

        try:
            employee = Employee.objects.get(pk=emp_pk)
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
            return redirect('payroll:create')

        try:
            slip, created = Payslip.objects.update_or_create(
                employee=employee,
                period_month=int(month),
                period_year=int(year),
                defaults={
                    'gross_salary': float(gross or 0),
                    'transport_allowance': float(transport or 0),
                    'housing_allowance': float(housing or 0),
                    'other_allowances': float(other_allow or 0),
                    'other_allowances_label': other_allow_label,
                    'cnps': float(cnps or 0),
                    'income_tax': float(income_tax or 0),
                    'other_deductions': float(other_ded or 0),
                    'other_deductions_label': other_ded_label,
                    'notes': notes,
                    'uploaded_by': request.user,
                },
            )
            if payslip_file:
                slip.payslip_file = payslip_file
                slip.save()

            action = "created" if created else "updated"
            messages.success(request, f"Payslip {action} for {employee.get_full_name()}.")

            from notifications.utils import notify
            notify(
                employee.user,
                title=f"Payslip Available — {slip.get_period_month_display()} {slip.period_year}",
                message=(
                    f"Your payslip for {slip.get_period_month_display()} {slip.period_year} "
                    f"is now available. Net salary: {slip.net_salary:,.0f} XAF."
                ),
                notification_type='system',
                url=f'/payroll/{slip.pk}/',
            )

            from dashboard.models import AuditLog
            AuditLog.log(
                request, AuditLog.ACTION_OTHER,
                f"Payslip {action} for {employee.get_full_name()} — "
                f"{slip.get_period_month_display()} {slip.period_year}",
                target_user=employee.user,
            )

            return redirect('payroll:list')

        except Exception as e:
            messages.error(request, f"Error saving payslip: {e}")

    return render(request, 'payroll/payslip_form.html', {
        'employees': employees,
        'months': MONTH_CHOICES,
        'years': list(range(today.year + 1, 2015, -1)),
        'current_year': today.year,
        'current_month': today.month,
    })


@login_required
def payslip_detail(request, pk):
    if not _payroll_enabled() and not request.user.is_superuser:
        messages.error(request, "The Payroll module is not currently active.")
        return redirect('dashboard:home')
    slip = get_object_or_404(Payslip, pk=pk)

    # Employees can only see their own
    if not _is_hr_or_above(request.user):
        try:
            if slip.employee != request.user.employee:
                messages.error(request, "Access denied.")
                return redirect('payroll:list')
        except Exception:
            messages.error(request, "Access denied.")
            return redirect('payroll:list')

    return render(request, 'payroll/payslip_detail.html', {'slip': slip})


@login_required
def payslip_delete(request, pk):
    if not _payroll_enabled() and not request.user.is_superuser:
        messages.error(request, "The Payroll module is not currently active.")
        return redirect('dashboard:home')
    if not _is_hr_or_above(request.user):
        messages.error(request, "Access denied.")
        return redirect('payroll:list')

    slip = get_object_or_404(Payslip, pk=pk)
    if request.method == 'POST':
        emp_name = slip.employee.get_full_name()
        period = f"{slip.get_period_month_display()} {slip.period_year}"
        slip.delete()
        messages.success(request, f"Payslip deleted for {emp_name} — {period}.")
        return redirect('payroll:list')
    return redirect('payroll:list')


@login_required
def my_payslips(request):
    """Employee self-service: view own payslip history."""
    if not _payroll_enabled() and not request.user.is_superuser:
        messages.error(request, "The Payroll module is not currently active.")
        return redirect('dashboard:home')
    try:
        employee = request.user.employee
    except Exception:
        messages.error(request, "No employee profile found.")
        return redirect('dashboard:home')

    qs = employee.payslips.all()
    year_filter = request.GET.get('year', '')
    if year_filter:
        qs = qs.filter(period_year=year_filter)

    years = list(range(date.today().year, 2015, -1))
    return render(request, 'payroll/my_payslips.html', {
        'payslips': qs,
        'years': years,
        'year_filter': year_filter,
        'employee': employee,
    })
