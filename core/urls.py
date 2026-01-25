from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import FileUploadView, RegisterView, UserDetailView

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    # Auth Endpoints
    path("auth/register/", RegisterView.as_view(), name="auth_register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/user/", UserDetailView.as_view(), name="auth_user"),
]
