from django.contrib import admin
from .models import LeaveType, LeaveRequest, LeaveBalance


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'requires_document', 'is_active']
    list_filter = ['is_active']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'status']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    readonly_fields = ['total_days', 'created_at', 'updated_at']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'year', 'total_entitlement']
    list_filter = ['year']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
