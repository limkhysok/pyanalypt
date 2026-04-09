"""
Main URL Configuration
API documentation: API_DOCS.md
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/",
        include(
            [
                path("", include("apps.users.urls")),
                path("datasets/", include("apps.datasets.urls")),
                path("issues/", include("apps.issues.urls")),
                path("cleaning/", include("apps.cleaning.urls")),
            ]
        ),
    ),
    path("accounts/", include("allauth.urls")),  # Google OAuth
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
