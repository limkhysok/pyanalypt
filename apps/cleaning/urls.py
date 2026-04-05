from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CleaningOperationViewSet

router = DefaultRouter()
router.register(r"", CleaningOperationViewSet, basename="cleaningoperation")

urlpatterns = [
    path("", include(router.urls)),
]
