"""
URL configuration for config project - RESTful API Structure

Main project URLs following REST best practices:
- API versioning (/api/v1/)
- Resource-based URLs
- Clear separation of concerns
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # ===== ADMIN =====
    # Django admin panel
    path("admin/", admin.site.urls),
    # ===== API v1 =====
    # Core API endpoints (versioned for future compatibility)
    path("api/v1/", include("core.urls")),
    # ===== SOCIAL AUTHENTICATION =====
    # OAuth Social Login (Google, etc.)
    # Provides: /accounts/google/login/, /accounts/google/login/callback/
    path("accounts/", include("allauth.urls")),
]
