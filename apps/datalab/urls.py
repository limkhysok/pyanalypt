from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatalabViewSet

router = DefaultRouter()
router.register(r"", DatalabViewSet, basename="datalab")

urlpatterns = [
    path("", include(router.urls)),
]
