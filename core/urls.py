"""
Core API URLs - RESTful structure with API versioning.
All endpoint documentation is in API_DOCS.md
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView


class GoogleLogin(SocialLoginView):
    """
    Google OAuth2 login endpoint for frontend applications.

    Frontend should:
    1. Use Google Sign-In to get access_token
    2. Send access_token to this endpoint
    3. Receive JWT tokens back
    """

    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:8000/api/v1/auth/google/callback/"
    client_class = OAuth2Client


urlpatterns = [
    # Authentication & User Management (dj-rest-auth)
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    # Google OAuth (API-based for frontend apps)
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),
    # JWT Token Management
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # Add your app resources here:
    # path("projects/", include("projects.urls")),
    # path("analytics/", include("analytics.urls")),
]
