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

urlpatterns = [
    # Authentication & User Management (dj-rest-auth)
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    # JWT Token Management
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # Add your app resources here:
    # path("projects/", include("projects.urls")),
    # path("analytics/", include("analytics.urls")),
]
