from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from datetime import date
from .models import LeaveRequest, LeaveBalance, LeaveType
from .forms import LeaveRequestForm, ApprovalForm
from accounts.models import Employee


def get_employee(request):
    try:
        return request.user.employee
    except Employee.DoesNotExist:
        return None


@login_required
def submit_leave(request):
    employee = get_employee(request)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect('dashboard:home')

    # Get or create balance
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': 18}
    )

    form = LeaveRequestForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = employee

        # Validate balance
        if leave.total_days > balance.remaining_days:
            messages.error(request, f"Insufficient leave balance. You have {balance.remaining_days} days remaining.")
        else:
            # Check for overlapping requests
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['pending', 'manager_approved', 'approved'],
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date,
            )
            if overlapping.exists():
                messages.error(request, "You already have a leave request for overlapping dates.")
            else:
                leave.save()
                messages.success(request, f"Leave request submitted successfully for {leave.total_days} day(s). Awaiting manager approval.")
                return redirect('leaves:my_requests')

    return render(request, 'leaves/request_form.html', {
        'form': form,
        'balance': balance,
    })


@login_required
def my_requests(request):
    employee = get_employee(request)
    if not employee:
        return redirect('dashboard:home')

    requests = LeaveRequest.objects.filter(employee=employee).select_related('leave_type', 'manager_action_by__user', 'hr_action_by__user')
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, year=date.today().year,
        defaults={'total_entitlement': 18}
    )

    return render(request, 'leaves/my_requests.html', {
        'leave_requests': requests,
        'balance': balance,
    })


@login_required
def cancel_request(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=employee)
    if leave.can_cancel():
        leave.status = LeaveRequest.STATUS_CANCELLED
        leave.save()
        messages.success(request, "Leave request cancelled.")
    else:
        messages.error(request, "This request cannot be cancelled.")
    return redirect('leaves:my_requests')


@login_required
def manager_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_manager():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    if request.user.is_superuser:
        pending = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_PENDING
        ).select_related('employee__user', 'employee__department', 'leave_type')
    else:
        pending = LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_PENDING,
            employee__supervisor=employee
        ).select_related('employee__user', 'employee__department', 'leave_type')

    return render(request, 'leaves/manager_approvals.html', {
        'pending_requests': pending,
    })


@login_required
def manager_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_manager():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk, status=LeaveRequest.STATUS_PENDING, employee__supervisor=employee)

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.manager_action_by = employee
            leave.manager_action_date = timezone.now()
            leave.manager_remarks = remarks
            if action == 'approve':
                leave.status = LeaveRequest.STATUS_MANAGER_APPROVED
                messages.success(request, f"Leave request approved. Forwarded to HR for final approval.")
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_MANAGER
                messages.warning(request, "Leave request rejected.")
            leave.save()
            return redirect('leaves:manager_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'Manager Review',
        'action_type': 'manager',
    })


@login_required
def hr_approvals(request):
    employee = get_employee(request)
    if not employee or not employee.is_hr():
        messages.error(request, "Access denied. HR Admin only.")
        return redirect('dashboard:home')

    pending = LeaveRequest.objects.filter(
        status=LeaveRequest.STATUS_MANAGER_APPROVED
    ).select_related('employee__user', 'employee__department', 'leave_type', 'manager_action_by__user')

    return render(request, 'leaves/hr_approvals.html', {
        'pending_requests': pending,
    })


@login_required
def hr_action(request, pk):
    employee = get_employee(request)
    if not employee or not employee.is_hr():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    leave = get_object_or_404(LeaveRequest, pk=pk, status=LeaveRequest.STATUS_MANAGER_APPROVED)

    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            remarks = form.cleaned_data['remarks']
            leave.hr_action_by = employee
            leave.hr_action_date = timezone.now()
            leave.hr_remarks = remarks
            if action == 'approve':
                leave.status = LeaveRequest.STATUS_APPROVED
                messages.success(request, "Leave request FULLY APPROVED.")
            else:
                leave.status = LeaveRequest.STATUS_REJECTED_HR
                messages.warning(request, "Leave request rejected by HR.")
            leave.save()
            return redirect('leaves:hr_approvals')
    else:
        form = ApprovalForm()

    return render(request, 'leaves/action_form.html', {
        'leave': leave,
        'form': form,
        'action_title': 'HR Final Review',
        'action_type': 'hr',
    })


@login_required
def leave_detail(request, pk):
    employee = get_employee(request)
    leave = get_object_or_404(LeaveRequest, pk=pk)

    # Only owner, their manager, or HR can view
    can_view = (
        leave.employee == employee or
        (employee and employee.is_hr()) or
        (employee and employee.is_manager() and leave.employee.supervisor == employee)
    )
    if not can_view:
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    return render(request, 'leaves/leave_detail.html', {'leave': leave})


@login_required
def all_leaves_hr(request):
    """HR view of all leave requests"""
    employee = get_employee(request)
    if not employee or not employee.is_hr():
        messages.error(request, "Access denied.")
        return redirect('dashboard:home')

    status_filter = request.GET.get('status', '')
    dept_filter = request.GET.get('dept', '')
    year_filter = request.GET.get('year', str(date.today().year))

    qs = LeaveRequest.objects.select_related(
        'employee__user', 'employee__department', 'leave_type'
    ).filter(start_date__year=year_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)
    if dept_filter:
        qs = qs.filter(employee__department_id=dept_filter)

    from accounts.models import Department
    departments = Department.objects.all()

    return render(request, 'leaves/all_leaves.html', {
        'leave_requests': qs,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
        'year_filter': year_filter,
        'departments': departments,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'years': range(2023, date.today().year + 2),
    })
