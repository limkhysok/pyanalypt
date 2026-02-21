from dj_rest_auth.serializers import UserDetailsSerializer
from .models import AuthUser


class CustomUserDetailsSerializer(UserDetailsSerializer):
    """
    Extends dj-rest-auth's UserDetailsSerializer to return all
    AuthUser fields on login, registration, and GET /auth/user/.
    """

    class Meta(UserDetailsSerializer.Meta):
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
        read_only_fields = (
            "id",
            "email",
            "email_verified",
            "date_joined",
            "last_login",
        )
