import os
import pandas as pd
import json
import sqlite3
from rest_framework import mixins, viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from django.core.files.base import ContentFile
from .models import Dataset, DatasetActivityLog
from .serializers import DatasetSerializer, DatasetActivityLogSerializer
from apps.core.data_engine import load_data, generate_summary_stats

ERR_UNSUPPORTED_FORMAT = "Unsupported format."


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
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
      GET    /datasets/                    — list all datasets
      GET    /datasets/{id}/               — dataset detail + preview
      DELETE /datasets/{id}/               — delete dataset
      PATCH  /datasets/{id}/rename/        — rename file_name
      GET    /datasets/{id}/preview/       — preview dataframe (?rows=N)
      POST   /datasets/{id}/update_cell/   — edit a single cell
      GET    /datasets/{id}/export/        — export (?format=csv|json|xlsx|parquet)
      POST   /datasets/{id}/analyze_issues/ — generate AI insights via Ollama
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
            # 1. Connect to in-memory SQLite
            conn = sqlite3.connect(":memory:")
            try:
                # 2. Execute the script
                with open(path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                
                # 3. Find the first table name
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                if not tables:
                    return None
                
                table_name = tables[0][0]
                # 4. Load into DataFrame
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                return df
            except Exception:
                return None
            finally:
                conn.close()
        return None

    def _save_dataframe(self, df, path, file_format):
        if file_format == "csv":
            df.to_csv(path, index=False)
        elif file_format in ["xlsx"]:
            df.to_excel(path, index=False)
        elif file_format == "json":
            df.to_json(path, orient="records")
        elif file_format == "parquet":
            df.to_parquet(path, index=False)
        elif file_format == "sql":
            # Generate a SQL script file
            conn = sqlite3.connect(":memory:")
            table_name = "dataset"
            df.to_sql(table_name, conn, index=False)
            with open(path, "w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()

    def _get_preview_response(self, dataset, df, row_limit=10):
        preview_df = df.head(row_limit)
        dtypes = df.dtypes.apply(lambda x: str(x)).to_dict()
        summary = {}

        numeric_cols = df.select_dtypes(include=["number"]).columns
        if not numeric_cols.empty:
            summary_json = df[numeric_cols].describe().to_json()
            summary = json.loads(summary_json)

        rows_json = preview_df.to_json(orient="records", date_format="iso")
        rows = json.loads(rows_json)

        return {
            "columns": list(df.columns),
            "rows": rows,
            "metadata": {
                "dtypes": dtypes,
                "shape": [len(df), len(df.columns)],
            },
            "summary": summary,
            "total_rows_hint": len(df),
            "dataset_id": dataset.id,
            "file_name": dataset.file_name,
        }

    # ------------------------------------------------------------------
    # Detail (with embedded preview)
    # ------------------------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        try:
            df = self._load_dataframe(instance.file.path, instance.file_format)
            if df is not None:
                data["data_preview"] = self._get_preview_response(
                    instance, df, row_limit=50
                )
        except Exception:
            data["data_preview"] = None

        return Response(data)

    # ------------------------------------------------------------------
    # Rename
    # ------------------------------------------------------------------

    @action(detail=True, methods=["patch"])
    def rename(self, request, pk=None):
        """PATCH /datasets/{id}/rename/  — rename the dataset file_name."""
        dataset = self.get_object()
        new_name = request.data.get("file_name")

        if not new_name or not new_name.strip():
            return Response(
                {"detail": "file_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset.file_name = new_name.strip()
        dataset.save(update_fields=["file_name", "updated_date"])
        
        self._log_activity(dataset, "RENAME", {"new_name": dataset.file_name})
        
        return Response(self.get_serializer(dataset).data)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """GET /datasets/{id}/preview/?rows=N"""
        dataset = self.get_object()
        file_path = dataset.file.path

        try:
            row_limit = int(request.query_params.get("rows", 10))
            row_limit = min(max(row_limit, 1), 1000)
        except (ValueError, TypeError):
            row_limit = 10

        try:
            if dataset.file_format == "csv":
                df = pd.read_csv(file_path, nrows=row_limit + 100)
            elif dataset.file_format in ["xlsx"]:
                df = pd.read_excel(file_path, nrows=row_limit + 100)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path).head(row_limit + 100)
            elif dataset.file_format == "parquet":
                df = pd.read_parquet(file_path).head(row_limit + 100)
            else:
                return Response(
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._log_activity(dataset, "PREVIEW", {"rows_requested": row_limit})

            return Response(self._get_preview_response(dataset, df, row_limit))

        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Update Cell
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def update_cell(self, request, pk=None):
        """
        POST /datasets/{id}/update_cell/
        Body: { "row_index": 0, "column_name": "price", "value": 29.99 }
        """
        dataset = self.get_object()

        row_index = request.data.get("row_index")
        column_name = request.data.get("column_name")
        value = request.data.get("value")

        if row_index is None or column_name is None:
            return Response(
                {"detail": "row_index and column_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            row_index = int(row_index)
        except (ValueError, TypeError):
            return Response(
                {"detail": "row_index must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            df = self._load_dataframe(dataset.file.path, dataset.file_format)
            if df is None:
                return Response(
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if row_index < 0 or row_index >= len(df):
                return Response(
                    {"detail": f"row_index out of range (0–{len(df) - 1})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if column_name not in df.columns:
                return Response(
                    {"detail": f"Column '{column_name}' not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            df.at[row_index, column_name] = value
            self._save_dataframe(df, dataset.file.path, dataset.file_format)

            dataset.file_size = os.path.getsize(dataset.file.path)
            dataset.save(update_fields=["file_size", "updated_date"])

            self._log_activity(dataset, "UPDATE_CELL", {
                "row": row_index,
                "column": column_name,
                "new_value": str(value)[:100]
            })

            return Response({
                "detail": "Cell updated.",
                "row_index": row_index,
                "column_name": column_name,
                "new_value": value,
            })

        except Exception as e:
            return Response(
                {"detail": f"Update failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """GET /datasets/{id}/export/?format=csv|json|xlsx|parquet"""
        dataset = self.get_object()
        file_path = dataset.file.path
        export_format = request.query_params.get("format", dataset.file_format).lower()

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response(
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
                response = HttpResponse(
                    buf.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = f'attachment; filename="{base_name}.xlsx"'
            elif export_format == "json":
                data = df.to_json(orient="records")
                response = HttpResponse(data, content_type="application/json")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.json"'
            elif export_format == "parquet":
                buf = io.BytesIO()
                df.to_parquet(buf, index=False)
                buf.seek(0)
                response = HttpResponse(buf.getvalue(), content_type="application/octet-stream")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.parquet"'
            elif export_format == "sql":
                # Create an in-memory SQL dump
                conn = sqlite3.connect(":memory:")
                # Sanitize table name (replace spaces/special chars)
                table_name = "".join(e for e in base_name if e.isalnum()) or "dataset"
                df.to_sql(table_name, conn, index=False)
                
                buf = io.StringIO()
                for line in conn.iterdump():
                    buf.write(f"{line}\n")
                
                response = HttpResponse(buf.getvalue(), content_type="application/sql")
                response["Content-Disposition"] = f'attachment; filename="{base_name}.sql"'
                conn.close()
            else:
                return Response(
                    {"detail": f"Unsupported export format: {export_format}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._log_activity(dataset, "EXPORT", {"format": export_format})

            return response

        except Exception as e:
            return Response(
                {"detail": f"Export failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Duplicate
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """
        POST /datasets/{id}/duplicate/
        Body: { "new_file_name": "Copy of Data", "format": "parquet" }
        """
        source = self.get_object()
        new_name = request.data.get("new_file_name")
        new_format = request.data.get("format", source.file_format).lower()

        if not new_name:
            new_name = f"{source.file_name}_copy"

        try:
            # 1. Load data from source
            df = self._load_dataframe(source.file.path, source.file_format)
            if df is None:
                return Response(
                    {"detail": "Failed to load source data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 2. Prepare the new file in memory
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
                conn = sqlite3.connect(":memory:")
                # Sanitize table name
                table_name = "".join(e for e in new_name if e.isalnum()) or "dataset"
                df.to_sql(table_name, conn, index=False)
                for line in conn.iterdump():
                    buf.write(f"{line}\n")
                content = ContentFile(buf.getvalue().encode("utf-8"))
                conn.close()
            else:
                return Response(
                    {"detail": f"Unsupported format: {new_format}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 3. Create new Dataset instance
            new_dataset = Dataset(
                user=self.request.user,
                file_name=new_name,
                file_format=new_format,
                parent=source,
                is_cleaned=source.is_cleaned
            )
            # 4. Save the file (Django handles the path naming)
            ext = f".{new_format}"
            new_dataset.file.save(f"{new_name}{ext}", content, save=False)
            new_dataset.save()

            self._log_activity(source, "DUPLICATE", {
                "new_dataset_id": new_dataset.id,
                "new_name": new_name,
                "target_format": new_format
            })

            return Response(
                self.get_serializer(new_dataset).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"detail": f"Duplication failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_destroy(self, instance):
        # Log before the dataset link is nullified by SET_NULL in the model
        # We use a snapshot of name because SET_NULL will clear dataset FK in logs
        self._log_activity(instance, "DELETE", {"file_name": instance.file_name})
        instance.delete()

    @action(detail=False, methods=["get"])
    def activity_logs(self, request):
        """GET /datasets/activity_logs/  — list all logs for user's datasets."""
        logs = DatasetActivityLog.objects.filter(user=request.user)
        # Optional filtering by dataset
        dataset_id = request.query_params.get("dataset")
        if dataset_id:
            logs = logs.filter(dataset_id=dataset_id)
            
        serializer = DatasetActivityLogSerializer(logs, many=True)
        return Response(serializer.data)

