from django.db import models
from django.contrib.auth.models import AbstractUser

# This is a REPRESENTATION of the Django Built-in User Model
# You do NOT run migration for this file, it is for reference only.
# This matches exactly what is currently in your 'auth_user' table in PostgreSQL.


class AuthUser(AbstractUser):
    # Custom fields from mermaid_live.md (Differences from standard Django)
    full_name = models.CharField(max_length=255)
    profile_picture = models.URLField(max_length=500, null=True, blank=True)
    email = models.EmailField(unique=True)

    class Meta:
        managed = False  # Ensure Django doesn't try to create this table
        db_table = "auth_user"

    def __str__(self):
        return self.username
