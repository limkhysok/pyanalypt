import os
import pandas as pd
import json
from rest_framework import mixins, viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from .models import Dataset
from .serializers import DatasetSerializer
from apps.core.data_engine import load_data, generate_summary_stats
from apps.core.ollama_client import analyze_dataset_metadata

ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class CreateDatasetView(generics.CreateAPIView):
    """
    POST /datasets/upload/
    Handle file uploads (Drag and Drop / File Input).
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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
            else:
                return Response(
                    {"detail": f"Unsupported export format: {export_format}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return response

        except Exception as e:
            return Response(
                {"detail": f"Export failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # AI Analysis (Ollama)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def analyze_issues(self, request, pk=None):
        """
        POST /datasets/{id}/analyze_issues/
        Uses local Ollama to generate problem statements based on column metadata.
        """
        dataset = self.get_object()
        
        try:
            # 1. Load data and generate stats
            df = load_data(dataset.file.path)
            stats = generate_summary_stats(df)
            
            # 2. Extract column names and a smaller version of stats for the prompt
            columns = stats.get("columns", [])
            column_names = [col["name"] for col in columns]
            
            # We don't want to send too much data, just the essence
            simplified_stats = []
            for col in columns:
                simplified_stats.append({
                    "name": col["name"],
                    "type": col["type"],
                    "missing": col["missing"],
                    "unique": col["unique"]
                })
            
            # 3. Call Ollama
            ai_response = analyze_dataset_metadata(column_names, simplified_stats)
            
            return Response({
                "dataset_id": dataset.id,
                "file_name": dataset.file_name,
                "problem_statements": ai_response
            })
            
        except Exception as e:
            return Response(
                {"detail": f"AI Analysis failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
