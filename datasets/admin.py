from django.contrib import admin
from .models import ProjectDataset


@admin.register(ProjectDataset)
class ProjectDatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "file_format", "row_count", "uploaded_at")
    list_filter = ("file_format", "uploaded_at")
    search_fields = ("name", "project__name")
    readonly_fields = ("uploaded_at",)
