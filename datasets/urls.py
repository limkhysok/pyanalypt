from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetViewSet, CreateDatasetView, PasteDatasetView

router = DefaultRouter()
router.register(r"", DatasetViewSet, basename="dataset")

urlpatterns = [
    path("upload/", CreateDatasetView.as_view(), name="dataset-upload"),
    path("paste/", PasteDatasetView.as_view(), name="dataset-paste"),
    path("", include(router.urls)),
]
