import logging
import pandas as pd

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset
from apps.core.data_engine import load_dataframe

logger = logging.getLogger(__name__)


def _format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class DatalabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def preview(self, request, dataset_id=None):
        """GET /datalab/preview/{dataset_id}/"""
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = load_dataframe(dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": "Unsupported file format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "dataset_id": dataset.id,
            "file_name": dataset.file_name,
            "file_format": dataset.file_format,
            "dataset_size": _format_size(dataset.file_size),
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "rows": df.astype(object).where(pd.notna(df), None).to_dict(orient="records"),
        })

    def inspect(self, request, dataset_id=None):
        """GET /datalab/inspect/{dataset_id}/"""
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = load_dataframe(dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": "Unsupported file format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_rows = len(df)

        return Response({
            "info": {
                "columns": [
                    {
                        "column": col,
                        "dtype": str(df[col].dtype),
                        "non_null_count": int(df[col].notna().sum()),
                        "null_count": int(df[col].isna().sum()),
                        "null_pct": round(df[col].isna().sum() / total_rows * 100, 1) if total_rows > 0 else 0.0,
                    }
                    for col in df.columns
                ],
                "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
            },
        })
