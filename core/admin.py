from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import AuthUser


@admin.register(AuthUser)
class AuthUserAdmin(BaseUserAdmin):
    """
    Custom admin for AuthUser model with all custom fields visible.
    """

    # Fields to display in the list view
    list_display = (
        "email",
        "username",
        "full_name",
        "email_verified",
        "is_staff",
        "is_active",
        "date_joined",
    )

    # Fields for search
    search_fields = ("email", "username", "first_name", "last_name", "full_name")

    # Filters in the sidebar
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "email_verified",
        "date_joined",
    )

    # Ordering
    ordering = ("-date_joined",)

    # Fields to display when editing a user
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "full_name",
                    "profile_picture",
                    "email_verified",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields to display when adding a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "full_name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    # Make email_verified editable inline
    readonly_fields = ("date_joined", "last_login")
