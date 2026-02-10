from django.db import models
from django.core.validators import (
    RegexValidator,
    MinLengthValidator,
    MaxLengthValidator,
)
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# Custom User Model for pyanalypt
# This WILL be migrated to create the auth_user table


class AuthUser(AbstractUser):
    # Custom fields from mermaid_live.md (Differences from standard Django)

    # first_name: Letters only (including accented characters), hyphens, apostrophes, min 2 chars
    first_name = models.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-ZÀ-ÿ'\- ]+$",
                message="First name can only contain letters, hyphens, apostrophes, and spaces.",
            ),
            MinLengthValidator(
                2, message="First name must be at least 2 characters long."
            ),
        ],
    )

    # last_name: Letters only (including accented characters), hyphens, apostrophes, min 2 chars
    last_name = models.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-ZÀ-ÿ'\- ]+$",
                message="Last name can only contain letters, hyphens, apostrophes, and spaces.",
            ),
            MinLengthValidator(
                2, message="Last name must be at least 2 characters long."
            ),
        ],
    )

    # username: Alphanumeric + underscores/hyphens/dots, min 3 chars, unique
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9._-]+$",
                message="Username can only contain letters, numbers, dots, underscores, and hyphens.",
            ),
            MinLengthValidator(
                3, message="Username must be at least 3 characters long."
            ),
        ],
    )

    # full_name: Letters only, spaces allowed, min 10 chars, max 255 chars, no special characters, no numbers
    full_name = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-ZÀ-ÿ ]+$",
                message="Full name can only contain letters and spaces.",
            ),
            MinLengthValidator(
                10, message="Full name must be at least 10 characters long."
            ),
            MaxLengthValidator(255),
        ],
    )
    # email: Unique, valid email format, domain validation
    email = models.EmailField(
        unique=True,
        max_length=254,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                message="Enter a valid email address.",
            ),
        ],
    )

    # email_verified: Tracks email verification status (Google OAuth auto-verifies)
    email_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether the user's email has been verified.",
    )

    # password: Hashed password string (validation done via AUTH_PASSWORD_VALIDATORS in settings)
    # Model-level validation for minimum length of hashed passwords
    password = models.CharField(
        max_length=128,
        validators=[
            MinLengthValidator(
                8,
                message="Password hash must be at least 8 characters (this should be set via Django settings).",
            ),
        ],
        help_text="Hashed password stored in the database.",
    )

    # is_superuser: Admin privileges flag
    is_superuser = models.BooleanField(
        default=False,
        help_text="Designates that this user has all permissions without explicitly assigning them.",
    )

    # is_staff: Staff status flag
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )

    # is_active: Account active status
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account should be treated as active. Unselect this instead of deleting accounts.",
    )

    # date_joined: Account creation timestamp (cannot be in the future)
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the user account was created.",
    )

    # last_login: Last successful login timestamp (nullable, cannot be in the future)
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time of the user's last successful login.",
    )

    # Must be HTTPS for security, supports Google/CDN URLs
    profile_picture = models.URLField(
        max_length=1024,  # Increased for long CDN URLs (Google, Cloudinary, etc.)
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

    # USERNAME_FIELD defines what field is used for login (we use email)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name", "full_name"]

    class Meta:
        managed = True  # Enable Django migrations for this model
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate full_name if not provided.
        Also ensures email is lowercase for consistency.
        """
        if not self.full_name and self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"

        # Normalize email to lowercase
        if self.email:
            self.email = self.email.lower()

        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Returns the user's preferred display name."""
        return self.full_name or f"{self.first_name} {self.last_name}" or self.username
