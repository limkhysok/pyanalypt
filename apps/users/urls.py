"""
Users / Auth API URLs
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from django.conf import settings
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
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
    client_class = OAuth2Client


urlpatterns = [
    # ── Auth: login / logout / password / user profile ──────────────────────
    path("auth/", include("dj_rest_auth.urls")),

    # ── Auth: registration & email verification ──────────────────────────────
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # ── Google OAuth ─────────────────────────────────────────────────────────
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),

    # ── JWT Token Management ─────────────────────────────────────────────────
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
]
