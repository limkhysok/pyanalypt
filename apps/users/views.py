import pyotp
import user_agents

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from dj_rest_auth.views import LoginView

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

from .models import UserSession
from .serializers import (
    CustomUserDetailsSerializer,
    UserSessionSerializer,
    TOTPEnableSerializer,
    TOTPDisableSerializer,
    TOTPVerifyLoginSerializer,
)

User = get_user_model()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_user_agent(request):
    ua_str = request.META.get("HTTP_USER_AGENT", "")
    ua = user_agents.parse(ua_str)
    device = ua.device.family if ua.device.family != "Other" else "Desktop"
    browser = ua.browser.family
    if ua.os.family and ua.os.family != "Other":
        browser = f"{browser} on {ua.os.family}"
    return device, browser


def _create_session(request, user, refresh_token_str):
    """Create a UserSession record for a newly issued refresh token."""
    try:
        jti = JWTRefreshToken(refresh_token_str)["jti"]
    except Exception:
        return  # Never block login due to session-tracking failure

    device, browser = _parse_user_agent(request)
    UserSession.objects.create(
        user=user,
        jti=jti,
        device=device,
        browser=browser,
        ip_address=_get_client_ip(request),
    )


def _revoke_session(session):
    """Blacklist the token and mark the session inactive."""
    try:
        outstanding = OutstandingToken.objects.get(jti=session.jti)
        BlacklistedToken.objects.get_or_create(token=outstanding)
    except OutstandingToken.DoesNotExist:
        pass  # Token already expired and removed from outstanding table
    session.is_active = False
    session.save(update_fields=["is_active"])


# ── Google OAuth ──────────────────────────────────────────────────────────────

class GoogleLogin(SocialLoginView):
    """
    Google OAuth2 login endpoint for frontend applications.

    Frontend should:
    1. Use Google Sign-In to get access_token
    2. Send access_token to this endpoint
    3. Receive JWT tokens back
    """

    adapter_class = GoogleOAuth2Adapter
    callback_url = getattr(settings, "GOOGLE_OAUTH_CALLBACK_URL", None)
    client_class = OAuth2Client


# ── Custom login (adds 2FA gate + session tracking) ───────────────────────────

class CustomLoginView(LoginView):
    """
    Overrides dj-rest-auth LoginView to:
    - Intercept login when 2FA is enabled and return a short-lived totp_token
      instead of JWT tokens (frontend must complete via /auth/2fa/verify-login/).
    - Create a UserSession record on every successful full login.
    """

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=request.data)
        self.serializer.is_valid(raise_exception=True)

        user = self.serializer.validated_data["user"]

        if user.totp_enabled:
            # Issue a short-lived signed token (5-minute TTL).
            # Tokens are NOT yet issued — the user must complete 2FA first.
            totp_token = signing.dumps(
                {"uid": user.pk, "purpose": "2fa-login"},
                salt="2fa-login",
            )
            return Response(
                {"requires_2fa": True, "totp_token": totp_token},
                status=status.HTTP_200_OK,
            )

        self.login()
        _create_session(request, user, str(self.refresh_token))
        return self.get_response()


# ── Token refresh (keeps UserSession.jti in sync after rotation) ─────────────

class CustomTokenRefreshView(TokenRefreshView):
    """
    Wraps simplejwt's TokenRefreshView to update the UserSession record
    when a refresh token is rotated (ROTATE_REFRESH_TOKENS=True).
    """

    def post(self, request, *args, **kwargs):
        old_jti = None
        try:
            old_jti = JWTRefreshToken(request.data.get("refresh", ""))["jti"]
        except Exception:
            pass

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200 and old_jti:
            try:
                new_jti = JWTRefreshToken(response.data.get("refresh", ""))["jti"]
                UserSession.objects.filter(jti=old_jti, is_active=True).update(
                    jti=new_jti,
                    last_active=timezone.now(),
                )
            except Exception:
                pass

        return response


# ── 2FA ───────────────────────────────────────────────────────────────────────

class TOTPSetupView(APIView):
    """
    GET  /auth/2fa/setup/
    Generates a fresh TOTP secret and returns the otpauth:// URI for QR display.
    The secret is saved to the user but 2FA is NOT enabled until /auth/2fa/enable/.
    """

    def get(self, request):
        user = request.user
        if user.totp_enabled:
            return Response(
                {"detail": "2FA is already enabled. Disable it first to reset."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.save(update_fields=["totp_secret"])

        totp = pyotp.TOTP(secret)
        otpauth_uri = totp.provisioning_uri(name=user.email, issuer_name="PyAnalypt")
        return Response({"secret": secret, "otpauth_uri": otpauth_uri})


class TOTPEnableView(APIView):
    """
    POST /auth/2fa/enable/   { "code": "123456" }
    Verifies the TOTP code against the stored secret and activates 2FA.
    """

    def post(self, request):
        serializer = TOTPEnableSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.totp_enabled = True
        request.user.save(update_fields=["totp_enabled"])
        return Response({"detail": "2FA enabled successfully."})


class TOTPDisableView(APIView):
    """
    POST /auth/2fa/disable/   { "code": "123456", "password": "..." }
    Disables 2FA after verifying both the current password and a valid TOTP code.
    """

    def post(self, request):
        serializer = TOTPDisableSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.totp_enabled = False
        user.totp_secret = ""
        user.save(update_fields=["totp_enabled", "totp_secret"])
        return Response({"detail": "2FA disabled successfully."})


class TOTPVerifyLoginView(APIView):
    """
    POST /auth/2fa/verify-login/   { "totp_token": "...", "code": "123456" }
    Completes a login that was paused for 2FA.
    Returns JWT access + refresh tokens identical to the normal login response.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TOTPVerifyLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        totp_token = serializer.validated_data["totp_token"]
        code = serializer.validated_data["code"]

        try:
            payload = signing.loads(totp_token, salt="2fa-login", max_age=300)
        except signing.SignatureExpired:
            return Response(
                {"detail": "Token expired, please log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=payload["uid"])
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.totp_secret:
            return Response(
                {"detail": "2FA is not configured for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = JWTRefreshToken.for_user(user)
        access_str = str(refresh.access_token)
        refresh_str = str(refresh)

        _create_session(request, user, refresh_str)

        return Response({
            "access": access_str,
            "refresh": refresh_str,
            "user": CustomUserDetailsSerializer(user, context={"request": request}).data,
        })


# ── Sessions ──────────────────────────────────────────────────────────────────

class UserSessionListView(generics.ListAPIView):
    """GET /auth/sessions/  — list all active sessions for the current user."""

    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)


class UserSessionRevokeView(APIView):
    """DELETE /auth/sessions/{id}/  — revoke a specific session."""

    def delete(self, request, pk):
        session = get_object_or_404(
            UserSession, pk=pk, user=request.user, is_active=True
        )
        _revoke_session(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSessionRevokeAllView(APIView):
    """
    POST /auth/sessions/revoke-all/
    Revokes ALL active sessions for the current user (forces logout everywhere).
    """

    def post(self, request):
        sessions = list(UserSession.objects.filter(user=request.user, is_active=True))
        for session in sessions:
            _revoke_session(session)
        return Response({"detail": f"Revoked {len(sessions)} session(s)."})
