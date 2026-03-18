from django.contrib import admin
from .models import CleaningOperation

@admin.register(CleaningOperation)
class CleaningOperationAdmin(admin.ModelAdmin):
    list_display = ("operation_type", "dataset", "column_name", "status", "applied_at", "created_at")
    list_filter = ("operation_type", "status", "applied_at")
    search_fields = ("column_name", "operation_type", "parameters")
    readonly_fields = ("applied_at", "created_at")
