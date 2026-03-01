from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models.auth_user import AuthUser
from .models.account_emailaddress import AccountEmailAddress
from .models.account_emailconfirmation import AccountEmailConfirmation
from .models.authtoken_token import Token as AuthtokenToken
from .models.auth_group import AuthGroup
from .models.auth_group_permissions import AuthGroupPermissions
from .models.auth_permission import AuthPermission
from .models.auth_user_groups import AuthUserGroups
from .models.auth_user_user_permissions import AuthUserUserPermissions
from .models.django_admin_log import DjangoAdminLog
from .models.django_content_type import DjangoContentType
from .models.django_migrations import DjangoMigrations
from .models.django_session import DjangoSession
from .models.django_site import DjangoSite
from .models.socialaccount_socialaccount import SocialAccount
from .models.socialaccount_socialapp import SocialApp
from .models.socialaccount_socialtoken import SocialToken


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


@admin.register(AccountEmailAddress)
class AccountEmailAddressAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "verified", "primary")
    list_filter = ("verified", "primary")
    search_fields = ("email", "user__email")


@admin.register(AccountEmailConfirmation)
class AccountEmailConfirmationAdmin(admin.ModelAdmin):
    list_display = ("email_address", "created", "sent", "key")
    list_filter = ("sent",)
    search_fields = ("email_address__email", "key")


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "uid", "last_login")
    list_filter = ("provider",)
    search_fields = ("user__email", "uid")


@admin.register(SocialApp)
class SocialAppAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "client_id")
    search_fields = ("name", "provider", "client_id")


@admin.register(SocialToken)
class SocialTokenAdmin(admin.ModelAdmin):
    list_display = ("app", "account", "token_truncated")

    def token_truncated(self, obj):
        return obj.token[:20] + "..." if obj.token else ""


@admin.register(AuthtokenToken)
class AuthtokenTokenAdmin(admin.ModelAdmin):
    list_display = ("key", "user", "created")
    search_fields = ("user__email", "key")


@admin.register(DjangoAdminLog)
class DjangoAdminLogAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type")
    search_fields = ("object_repr", "change_message")


@admin.register(DjangoContentType)
class DjangoContentTypeAdmin(admin.ModelAdmin):
    list_display = ("app_label", "model")
    list_filter = ("app_label",)
    search_fields = ("model",)


@admin.register(DjangoMigrations)
class DjangoMigrationsAdmin(admin.ModelAdmin):
    list_display = ("app", "name", "applied")
    list_filter = ("app",)
    search_fields = ("name",)


@admin.register(DjangoSession)
class DjangoSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "expire_date")
    search_fields = ("session_key",)


@admin.register(DjangoSite)
class DjangoSiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "name")
    search_fields = ("domain", "name")


@admin.register(AuthPermission)
class AuthPermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "content_type", "codename")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")


@admin.register(AuthGroup)
class AuthGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(AuthGroupPermissions)
class AuthGroupPermissionsAdmin(admin.ModelAdmin):
    list_display = ("group", "permission")
    list_filter = ("group",)


@admin.register(AuthUserGroups)
class AuthUserGroupsAdmin(admin.ModelAdmin):
    list_display = ("user", "group")
    list_filter = ("group",)


@admin.register(AuthUserUserPermissions)
class AuthUserUserPermissionsAdmin(admin.ModelAdmin):
    list_display = ("user", "permission")
    list_filter = ("user",)
