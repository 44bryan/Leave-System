from django.contrib import admin
from .models import MedicalSickLeave


@admin.register(MedicalSickLeave)
class MedicalSickLeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'issued_by', 'date_of_issuance', 'start_date', 'end_date', 'days_count', 'status')
    list_filter = ('status', 'date_of_issuance')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'employee__employee_id')
    readonly_fields = ('days_count', 'created_at', 'updated_at')
    date_hierarchy = 'date_of_issuance'
