from django.contrib import admin
from .models import DatalabIssue, WrangleOperation

@admin.register(DatalabIssue)
class DatalabIssueAdmin(admin.ModelAdmin):
    list_display = ("issue_type", "column_name", "dataset", "detected_at")
    list_filter = ("issue_type", "detected_at")
    search_fields = ("column_name", "description")

@admin.register(WrangleOperation)
class WrangleOperationAdmin(admin.ModelAdmin):
    list_display = ("operation_type", "column_name", "dataset", "status", "created_at")
    list_filter = ("operation_type", "status", "created_at")
    search_fields = ("column_name", "operation_type")
