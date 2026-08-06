from django.contrib import admin
from .models import ExitRequest, OffboardingTask


class TaskInline(admin.TabularInline):
    model = OffboardingTask
    extra = 0
    fields = ['title', 'owner', 'completed', 'completed_by', 'completed_at', 'notes', 'order']
    readonly_fields = ['completed_by', 'completed_at']


@admin.register(ExitRequest)
class ExitRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'exit_type', 'exit_date', 'status', 'completion_pct', 'created_at']
    list_filter = ['exit_type', 'status']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    inlines = [TaskInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OffboardingTask)
class OffboardingTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'exit_request', 'owner', 'completed', 'completed_by', 'completed_at']
    list_filter = ['owner', 'completed']
