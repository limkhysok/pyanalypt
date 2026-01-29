from django.db import models
from django.contrib.auth.models import AbstractUser

# This is a REPRESENTATION of the Django Built-in User Model
# You do NOT run migration for this file, it is for reference only.
# This matches exactly what is currently in your 'auth_user' table in PostgreSQL.


class User(AbstractUser):
    # Primary Key (Hidden in abstract class but exists effectively)
    # id = models.AutoField(primary_key=True)

    # Core Auth Fields
    username = models.CharField(max_length=150, unique=True)
    email = models.CharField(max_length=254, blank=True)
    password = models.CharField(max_length=128)

    # Status Flags
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Metadata
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Personal Info (Optional in default Django)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Note: Using 'django-allauth' adds a separate table 'account_emailaddress'
    # linked to this User to handle multiple emails and verification status.
