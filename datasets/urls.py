from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetViewSet, CreateDatasetView

router = DefaultRouter()
router.register(r"", DatasetViewSet, basename="dataset")

urlpatterns = [
    path("upload/", CreateDatasetView.as_view(), name="dataset-upload"),
    path("", include(router.urls)),
]
