from django.contrib import admin
from .models import ProjectDataset


@admin.register(ProjectDataset)
class ProjectDatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "file_format", "row_count", "uploaded_at")
    list_filter = ("file_format", "uploaded_at")
    search_fields = ("name", "user__username")
    readonly_fields = ("uploaded_at",)
