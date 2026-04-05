from django.contrib import admin
from .models import Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "issue_type",
        "dataset",
        "column_name",
        "detected_at",
    )
    list_filter = (
        "issue_type",
        "detected_at",
    )
    search_fields = ("description", "column_name", "dataset__file_name")
    readonly_fields = ("detected_at",)
    fieldsets = (
        (
            "Issue Details",
            {
                "fields": (
                    "dataset",
                    "issue_type",
                    "column_name",
                    "row_index",
                    "affected_rows",
                )
            },
        ),
        (
            "Description & Fix",
            {
                "fields": ("description", "suggested_fix"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("detected_at",),
                "classes": ("collapse",),
            },
        ),
    )
