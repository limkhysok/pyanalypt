import io
import os
import logging

from rest_framework import mixins, viewsets, permissions, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404

from apps.core.data_engine import get_cached_dataframe
from .models import Dataset, DatasetActivityLog
from .serializers import DatasetSerializer, DatasetActivityLogSerializer

logger = logging.getLogger(__name__)

ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CreateDatasetView(generics.CreateAPIView):
    """
    POST /datasets/upload/
    Handle file uploads (Drag and Drop / File Input).
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        DatasetActivityLog.objects.create(
            user=self.request.user,
            dataset=instance,
            dataset_name_snap=instance.file_name,
            action="UPLOAD",
            details={"format": instance.file_format, "size": instance.file_size},
        )


class DatasetViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
      GET    /datasets/             — list all datasets
      GET    /datasets/{id}/         — retrieve dataset
      DELETE /datasets/{id}/         — delete dataset
      PATCH  /datasets/{id}/rename/  — rename file_name
      GET    /datasets/{id}/export/  — export (?format=csv|json|xlsx|parquet)
      POST   /datasets/{id}/duplicate/ — duplicate (?format=...)
      GET    /datasets/activity_logs/ — list activities (?dataset_id=<id>)
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Dataset.objects.filter(user=self.request.user).select_related("user")

    def _log_activity(self, dataset, action, details=None):
        DatasetActivityLog.objects.create(
            user=self.request.user,
            dataset=dataset,
            dataset_name_snap=dataset.file_name if dataset else "N/A",
            action=action,
            details=details or {},
        )

    @action(detail=True, methods=["patch"])
    def rename(self, request, pk=None):
        dataset = self.get_object()
        new_name = request.data.get("file_name")
        if not new_name or not new_name.strip():
            return Response({"detail": "file_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset.file_name = new_name.strip()
        dataset.save(update_fields=["file_name", "updated_date"])
        self._log_activity(dataset, "RENAME", {"new_name": dataset.file_name})
        return Response(self.get_serializer(dataset).data)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        dataset = self.get_object()
        file_path = dataset.file.path
        export_format = request.query_params.get("format", dataset.file_format).lower()
        base_name = os.path.splitext(dataset.file_name)[0]

        try:
            df = get_cached_dataframe(dataset.id, file_path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            if export_format == "csv":
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                response = HttpResponse(buf.getvalue(), content_type="text/csv")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.csv"'
            elif export_format in ["xlsx", "excel"]:
                buf = io.BytesIO()
                df.to_excel(buf, index=False)
                buf.seek(0)
                response = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.xlsx"'
            elif export_format == "json":
                response = HttpResponse(df.to_json(orient="records"), content_type="application/json")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.json"'
            elif export_format == "parquet":
                buf = io.BytesIO()
                df.to_parquet(buf, index=False)
                buf.seek(0)
                response = HttpResponse(buf.getvalue(), content_type="application/octet-stream")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.parquet"'
            else:
                return Response({"detail": f"Unsupported format: {export_format}"}, status=status.HTTP_400_BAD_REQUEST)

            self._log_activity(dataset, "EXPORT", {"format": export_format})
            return response
        except OSError:
            logger.exception("File not accessible during export for dataset %s", pk)
            return Response({"detail": "Dataset file not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Unexpected error during export for dataset %s", pk)
            return Response({"detail": "Export failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        source = self.get_object()
        new_name = request.data.get("new_file_name") or f"{source.file_name}_copy"
        new_format = request.data.get("format", source.file_format).lower()

        try:
            df = get_cached_dataframe(source.id, source.file.path, source.file_format)
            if df is None:
                return Response({"detail": "Failed to load source."}, status=status.HTTP_400_BAD_REQUEST)

            if new_format == "csv":
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                content = ContentFile(buf.getvalue().encode("utf-8"))
            elif new_format == "json":
                buf = io.StringIO()
                df.to_json(buf, orient="records")
                content = ContentFile(buf.getvalue().encode("utf-8"))
            elif new_format == "xlsx":
                buf = io.BytesIO()
                df.to_excel(buf, index=False)
                content = ContentFile(buf.getvalue())
            elif new_format == "parquet":
                buf = io.BytesIO()
                df.to_parquet(buf, index=False)
                content = ContentFile(buf.getvalue())
            else:
                return Response({"detail": "Unsupported format."}, status=status.HTTP_400_BAD_REQUEST)

            new_ds = Dataset(user=self.request.user, file_name=new_name, file_format=new_format, parent=source)
            new_ds.file.save(f"{new_name}.{new_format}", content, save=True)
            self._log_activity(source, "DUPLICATE", {"new_name": new_name, "format": new_format})
            return Response(self.get_serializer(new_ds).data, status=status.HTTP_201_CREATED)
        except OSError:
            logger.exception("File not accessible during duplicate for dataset %s", pk)
            return Response({"detail": "Source file not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Unexpected error during duplicate for dataset %s", pk)
            return Response({"detail": "Duplicate failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        self._log_activity(instance, "DELETE", {"file_name": instance.file_name})
        instance.delete()

    @action(detail=False, methods=["get"])
    def activity_logs(self, request):
        logs = DatasetActivityLog.objects.filter(user=request.user).select_related("user", "dataset")
        dataset_id = request.query_params.get("dataset_id")
        if dataset_id is not None:
            try:
                dataset_id = int(dataset_id)
            except (TypeError, ValueError):
                return Response({"detail": "dataset_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            get_object_or_404(Dataset, id=dataset_id, user=request.user)
            logs = logs.filter(dataset_id=dataset_id)
        page = self.paginate_queryset(logs)
        if page is not None:
            return self.get_paginated_response(DatasetActivityLogSerializer(page, many=True).data)
        return Response(DatasetActivityLogSerializer(logs, many=True).data)
