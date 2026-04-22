from django.urls import path
from .views import DatalabViewSet

preview = DatalabViewSet.as_view({"get": "preview"})
inspect = DatalabViewSet.as_view({"get": "inspect"})
cast = DatalabViewSet.as_view({"post": "cast_columns"})
drop_duplicates = DatalabViewSet.as_view({"post": "drop_duplicates"})

urlpatterns = [
    path("preview/<int:dataset_id>/", preview, name="datalab-preview"),
    path("inspect/<int:dataset_id>/", inspect, name="datalab-inspect"),
    path("cast/<int:dataset_id>/", cast, name="datalab-cast"),
    path("drop-duplicates/<int:dataset_id>/", drop_duplicates, name="datalab-drop-duplicates"),
]
