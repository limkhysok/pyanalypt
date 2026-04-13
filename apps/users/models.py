from django.db import models
from django.core.validators import (
    RegexValidator,
    MinLengthValidator,
    MaxLengthValidator,
)
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager

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
            MaxLengthValidator(255),
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

    is_superuser = models.BooleanField(
        default=False,
        help_text="Designates that this user has all permissions without explicitly assigning them.",
    )

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account should be treated as active. Unselect this instead of deleting accounts.",
    )

    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the user account was created.",
    )

    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time of the user's last successful login.",
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
