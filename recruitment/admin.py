from django.contrib import admin
from .models import JobPosting, FormFieldConfig, ScoringCriterion, Application, ApplicationAnswer


class FormFieldInline(admin.TabularInline):
    model = FormFieldConfig
    extra = 0


class ScoringInline(admin.TabularInline):
    model = ScoringCriterion
    extra = 0


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'status', 'employment_type', 'deadline', 'created_by', 'created_at']
    list_filter = ['status', 'employment_type']
    inlines = [FormFieldInline, ScoringInline]


class ApplicationAnswerInline(admin.TabularInline):
    model = ApplicationAnswer
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant_name', 'applicant_email', 'posting', 'status', 'score', 'submitted_at']
    list_filter = ['status', 'posting']
    inlines = [ApplicationAnswerInline]
