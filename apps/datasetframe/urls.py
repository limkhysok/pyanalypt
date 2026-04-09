from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetFrameViewSet

router = DefaultRouter()
router.register(r"", DatasetFrameViewSet, basename="datasetframe")

urlpatterns = [
    path("", include(router.urls)),
]
