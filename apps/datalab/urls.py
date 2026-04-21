from django.urls import path
from .views import DatalabViewSet

preview = DatalabViewSet.as_view({"get": "preview"})
inspect = DatalabViewSet.as_view({"get": "inspect"})
cast = DatalabViewSet.as_view({"post": "cast_columns"})

urlpatterns = [
    path("preview/<int:dataset_id>/", preview, name="datalab-preview"),
    path("inspect/<int:dataset_id>/", inspect, name="datalab-inspect"),
    path("cast/<int:dataset_id>/", cast, name="datalab-cast"),
]
