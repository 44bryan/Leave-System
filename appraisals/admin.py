from django.contrib import admin
from .models import AppraisalCycle, AppraisalRecord


@admin.register(AppraisalCycle)
class AppraisalCycleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'year', 'trimester', 'initiated_by', 'initiated_at', 'is_distributed']
    list_filter  = ['year', 'trimester', 'is_distributed']


@admin.register(AppraisalRecord)
class AppraisalRecordAdmin(admin.ModelAdmin):
    list_display  = ['employee', 'cycle', 'status', 'updated_at']
    list_filter   = ['status', 'cycle']
    search_fields = ['employee__user__last_name', 'employee__user__first_name']
