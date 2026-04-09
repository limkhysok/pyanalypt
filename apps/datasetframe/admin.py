from django.contrib import admin
from .models import DatasetFrame


@admin.register(DatasetFrame)
class DatasetFrameAdmin(admin.ModelAdmin):
    list_display = ["id", "dataset", "model_used", "created_at"]
    list_filter = ["model_used"]
    search_fields = ["dataset__file_name", "result"]
    readonly_fields = ["model_used", "result", "created_at"]
