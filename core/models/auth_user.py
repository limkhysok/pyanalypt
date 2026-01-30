from django.db import models


# This is a REPRESENTATION of the Django Built-in User Model
# You do NOT run migration for this file, it is for reference only.
# This matches exactly what is currently in your 'auth_user' table in PostgreSQL.


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE. This exists only to visualize the explicit schema structure.


class AuthUser(models.Model):
    # Standard Django Fields
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    email = models.CharField(max_length=254)

    # Flags
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Timestamps
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Custom fields from mermaid_live.md (Differences from standard Django)
    full_name = models.CharField(max_length=255)
    profile_picture = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False  # Ensure Django doesn't try to create this table
        db_table = "auth_user"

    def __str__(self):
        return self.username
