from django.contrib import admin
from .models import RecognitionProposal, RecognitionComment


@admin.register(RecognitionProposal)
class RecognitionProposalAdmin(admin.ModelAdmin):
    list_display = ('employee', 'recognition_type', 'status', 'proposed_by', 'created_at')
    list_filter = ('status', 'recognition_type')
    search_fields = ('employee__user__first_name', 'employee__user__last_name')


@admin.register(RecognitionComment)
class RecognitionCommentAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'author', 'created_at')
