import io
import logging
import pandas as pd

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset
from apps.core.data_engine import load_dataframe

logger = logging.getLogger(__name__)


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
            "columns": list(df.columns),
            "rows": df.astype(object).where(pd.notna(df), None).to_dict(orient="records"),
            "total_rows": len(df),
            "total_columns": len(df.columns),
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

        rows, cols = df.shape

        buf = io.StringIO()
        df.info(buf=buf)

        return Response({
            "shape": {
                "rows": rows,
                "columns": cols,
            },
            "dtypes": df.dtypes.astype(str).to_dict(),
            "info": {
                "text": buf.getvalue(),
                "columns": [
                    {
                        "column": col,
                        "dtype": str(df[col].dtype),
                        "non_null_count": int(df[col].notna().sum()),
                        "null_count": int(df[col].isna().sum()),
                    }
                    for col in df.columns
                ],
                "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
            },
        })
