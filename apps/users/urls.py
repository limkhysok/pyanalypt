"""
Users / Auth API URLs
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from .views import GoogleLogin

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
