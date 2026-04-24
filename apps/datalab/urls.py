from django.urls import path
from .views import DatalabViewSet

preview = DatalabViewSet.as_view({"get": "preview"})
inspect = DatalabViewSet.as_view({"get": "inspect"})
cast = DatalabViewSet.as_view({"post": "cast_columns"})
drop_duplicates = DatalabViewSet.as_view({"post": "drop_duplicates"})
update_cell = DatalabViewSet.as_view({"patch": "update_cell"})
rename_column = DatalabViewSet.as_view({"post": "rename_column"})

urlpatterns = [
    path("preview/<int:dataset_id>/", preview, name="datalab-preview"),
    path("inspect/<int:dataset_id>/", inspect, name="datalab-inspect"),
    path("cast/<int:dataset_id>/", cast, name="datalab-cast"),
    path("drop-duplicates/<int:dataset_id>/", drop_duplicates, name="datalab-drop-duplicates"),
    path("rename-column/<int:dataset_id>/", rename_column, name="datalab-rename-column"),
    path("update-cell/<int:dataset_id>/", update_cell, name="datalab-update-cell"),
]
