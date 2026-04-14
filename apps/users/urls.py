"""
Users / Auth API URLs
"""

from django.urls import path, include
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    GoogleLogin,
    CustomLoginView,
    CustomTokenRefreshView,
    TOTPSetupView,
    TOTPEnableView,
    TOTPDisableView,
    TOTPVerifyLoginView,
    UserSessionListView,
    UserSessionRevokeView,
    UserSessionRevokeAllView,
)

urlpatterns = [
    # ── Auth: login (overrides dj_rest_auth to add 2FA gate + session tracking)
    path("auth/login/", CustomLoginView.as_view(), name="rest_login"),

    # ── Auth: logout / password / user profile ───────────────────────────────
    path("auth/", include("dj_rest_auth.urls")),

    # ── Auth: registration & email verification ──────────────────────────────
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # ── Google OAuth ─────────────────────────────────────────────────────────
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),

    # ── JWT Token Management ─────────────────────────────────────────────────
    path("auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),

    # ── 2FA ──────────────────────────────────────────────────────────────────
    path("auth/2fa/setup/", TOTPSetupView.as_view(), name="2fa-setup"),
    path("auth/2fa/enable/", TOTPEnableView.as_view(), name="2fa-enable"),
    path("auth/2fa/disable/", TOTPDisableView.as_view(), name="2fa-disable"),
    path("auth/2fa/verify-login/", TOTPVerifyLoginView.as_view(), name="2fa-verify-login"),

    # ── Sessions ─────────────────────────────────────────────────────────────
    path("auth/sessions/", UserSessionListView.as_view(), name="session-list"),
    path("auth/sessions/<int:pk>/", UserSessionRevokeView.as_view(), name="session-revoke"),
    path("auth/sessions/revoke-all/", UserSessionRevokeAllView.as_view(), name="session-revoke-all"),
]
