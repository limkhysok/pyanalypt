from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "status",
        "is_favorite",
        "created_at",
        "last_accessed_at",
    )
    list_filter = ("status", "is_favorite", "created_at", "category")
    search_fields = ("name", "description", "user__email")
    readonly_fields = ("id", "slug", "created_at", "updated_at", "last_accessed_at")

    fieldsets = (
        ("Identity", {"fields": ("id", "user", "name", "slug")}),
        (
            "Organization",
            {"fields": ("description", "category", "status", "is_favorite")},
        ),
        ("UI & UX", {"fields": ("color_code", "thumbnail", "settings")}),
        ("Audit", {"fields": ("created_at", "updated_at", "last_accessed_at")}),
    )
