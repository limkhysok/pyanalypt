import pandas as pd
import sqlite3
from rest_framework import mixins, viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from django.core.files.base import ContentFile
from .models import Dataset, DatasetActivityLog
from .serializers import DatasetSerializer, DatasetActivityLogSerializer

ERR_UNSUPPORTED_FORMAT = "Unsupported format."
SQLITE_MEMORY = ":memory:"


class CreateDatasetView(generics.CreateAPIView):
    """
    POST /datasets/upload/
    Handle file uploads (Drag and Drop / File Input).
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # Log upload
        DatasetActivityLog.objects.create(
            user=self.request.user,
            dataset=instance,
            dataset_name_snap=instance.file_name,
            action="UPLOAD",
            details={"format": instance.file_format, "size": instance.file_size},
        )


class DatasetViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
      GET    /datasets/             — list all datasets
      DELETE /datasets/{id}/         — delete dataset
      PATCH  /datasets/{id}/rename/  — rename file_name
      GET    /datasets/{id}/export/  — export (?format=csv|json|xlsx|parquet|sql)
      POST   /datasets/{id}/duplicate/ — duplicate (?format=...)
      GET    /datasets/activity_logs/ — list activities
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(user=self.request.user)

    def _log_activity(self, dataset, action, details=None):
        """Helper to create activity logs."""
        DatasetActivityLog.objects.create(
            user=self.request.user,
            dataset=dataset,
            dataset_name_snap=dataset.file_name if dataset else "N/A",
            action=action,
            details=details or {},
        )

    def _load_dataframe(self, path, file_format):
        if file_format == "csv":
            return pd.read_csv(path)
        if file_format in ["xlsx"]:
            return pd.read_excel(path)
        if file_format == "json":
            return pd.read_json(path)
        if file_format == "parquet":
            return pd.read_parquet(path)
        if file_format == "sql":
            conn = sqlite3.connect(SQLITE_MEMORY)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                if not tables:
                    return None
                return pd.read_sql(f"SELECT * FROM {tables[0][0]}", conn)
            except Exception:
                return None
            finally:
                conn.close()
        return None

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

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            import io
            base_name = dataset.file_name.split(".")[0]

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
            elif export_format == "sql":
                conn = sqlite3.connect(SQLITE_MEMORY)
                table_name = "".join(e for e in base_name if e.isalnum()) or "dataset"
                df.to_sql(table_name, conn, index=False)
                buf = io.StringIO()
                for line in conn.iterdump():
                    buf.write(f"{line}\n")
                response = HttpResponse(buf.getvalue(), content_type="application/sql")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.sql"'
                conn.close()
            else:
                return Response({"detail": f"Unsupported format: {export_format}"}, status=status.HTTP_400_BAD_REQUEST)

            self._log_activity(dataset, "EXPORT", {"format": export_format})
            return response
        except Exception as e:
            return Response({"detail": f"Export failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        source = self.get_object()
        new_name = request.data.get("new_file_name")
        new_format = request.data.get("format", source.file_format).lower()
        if not new_name:
            new_name = f"{source.file_name}_copy"

        try:
            df = self._load_dataframe(source.file.path, source.file_format)
            if df is None:
                return Response({"detail": "Failed to load source."}, status=status.HTTP_400_BAD_REQUEST)

            import io
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
            elif new_format == "sql":
                buf = io.StringIO()
                conn = sqlite3.connect(SQLITE_MEMORY)
                table_name = "".join(e for e in new_name if e.isalnum()) or "dataset"
                df.to_sql(table_name, conn, index=False)
                for line in conn.iterdump():
                    buf.write(f"{line}\n")
                content = ContentFile(buf.getvalue().encode("utf-8"))
                conn.close()
            else:
                return Response({"detail": "Unsupported format"}, status=status.HTTP_400_BAD_REQUEST)

            new_ds = Dataset(user=self.request.user, file_name=new_name, file_format=new_format, parent=source)
            new_ds.file.save(f"{new_name}.{new_format}", content, save=True)
            self._log_activity(source, "DUPLICATE", {"new_name": new_name, "format": new_format})
            return Response(self.get_serializer(new_ds).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": f"Failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        self._log_activity(instance, "DELETE", {"file_name": instance.file_name})
        instance.delete()

    @action(detail=False, methods=["get"])
    def activity_logs(self, request):
        logs = DatasetActivityLog.objects.filter(user=request.user)
        dataset_id = request.query_params.get("dataset")
        if dataset_id:
            logs = logs.filter(dataset_id=dataset_id)
        return Response(DatasetActivityLogSerializer(logs, many=True).data)

