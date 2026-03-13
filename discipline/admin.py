from django.contrib import admin
from .models import DisciplineRecord


@admin.register(DisciplineRecord)
class DisciplineRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'action_type', 'issued_by', 'date_issued', 'suspension_start', 'suspension_end']
    list_filter = ['action_type', 'date_issued']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'reason']
    ordering = ['-date_issued']
