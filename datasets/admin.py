from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("file_name", "user", "file_format", "row_count", "uploaded_date", "updated_date")
    list_filter = ("file_format", "uploaded_date")
    search_fields = ("file_name", "user__username")
    readonly_fields = ("uploaded_date", "updated_date")
