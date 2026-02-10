"""
Custom Serializers

Note: Authentication serializers are handled by dj-rest-auth.
These are kept for reference or future custom endpoints.
"""

from rest_framework import serializers
from .models import AuthUser


class UserSerializer(serializers.ModelSerializer):
    """Serializer for AuthUser model"""

    class Meta:
        model = AuthUser
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "profile_picture",
            "email_verified",
            "is_staff",
            "is_active",
            "date_joined",
            "last_login",
        )
        read_only_fields = ("id", "email_verified", "date_joined", "last_login")
