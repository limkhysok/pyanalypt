from django.conf import settings
from django.db import models
from django.core.validators import (
    RegexValidator,
    MinLengthValidator,
)
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone

NAME_REGEX = r"^[a-zA-ZÀ-ÿ'\- ]+$"
NAME_REGEX_MESSAGE = "Only letters, hyphens, apostrophes, and spaces are allowed."


class AuthUserManager(BaseUserManager):
    """
    Custom manager for AuthUser where username is the primary identifier.
    """
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        email = extra_fields.get("email")
        if email:
            extra_fields["email"] = self.normalize_email(email)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, password, **extra_fields)


class AuthUser(AbstractUser):
    objects = AuthUserManager()

    first_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[
            RegexValidator(regex=NAME_REGEX, message=NAME_REGEX_MESSAGE),
            MinLengthValidator(2, message="First name must be at least 2 characters long."),
        ],
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[
            RegexValidator(regex=NAME_REGEX, message=NAME_REGEX_MESSAGE),
            MinLengthValidator(2, message="Last name must be at least 2 characters long."),
        ],
    )

    username = models.CharField(
        max_length=150,
        unique=True,
        null=False,
        blank=False,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9._-]+$",
                message="Username can only contain letters, numbers, dots, underscores, and hyphens.",
            ),
            MinLengthValidator(3, message="Username must be at least 3 characters long."),
        ],
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
        validators=[
            RegexValidator(regex=NAME_REGEX, message=NAME_REGEX_MESSAGE),
            MinLengthValidator(2, message="Full name must be at least 2 characters long."),
        ],
    )

    email = models.EmailField(
        unique=True,
        max_length=254,
        null=False,
        blank=False,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                message="Enter a valid email address.",
            ),
        ],
    )

    email_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether the user's email has been verified.",
    )

    profile_picture = models.URLField(
        max_length=1024,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^https://.*",
                message="Profile picture URL must use HTTPS protocol for security.",
            ),
        ],
        help_text="URL to the user's profile picture (typically from Google OAuth or uploaded to CDN).",
    )

    # ── Two-Factor Authentication ────────────────────────────────────────────
    # totp_secret is generated during setup and stored until 2FA is disabled.
    # Store encrypted at rest in production (e.g. via django-encrypted-fields).
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        managed = True
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()

        if self.first_name and self.last_name:
            derived = f"{self.first_name} {self.last_name}"
            # Only auto-derive full_name when it is blank or still matches the
            # previously derived value; a manually set full_name is left intact.
            if not self.full_name or self.full_name == derived:
                self.full_name = derived

        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Returns the user's preferred display name."""
        if self.full_name:
            return self.full_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class UserSession(models.Model):
    """
    Tracks active JWT refresh token sessions per user.
    One record per login; updated on every token refresh.
    Revoking a session blacklists the corresponding refresh token.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_sessions",
    )
    jti = models.CharField(
        max_length=255,
        unique=True,
        help_text="JWT ID of the current refresh token for this session.",
    )
    device = models.CharField(max_length=200, blank=True)
    browser = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "user_session"
        ordering = ["-last_active"]

    def __str__(self):
        return f"{self.user} — {self.browser} ({self.ip_address})"
