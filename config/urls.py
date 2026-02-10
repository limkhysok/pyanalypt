"""
Main URL Configuration
API documentation: API_DOCS.md
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
    path("accounts/", include("allauth.urls")),  # Google OAuth
]
