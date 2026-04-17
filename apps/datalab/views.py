import io
import logging
import pandas as pd

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset

logger = logging.getLogger(__name__)


class DatalabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _load_dataframe(self, path, file_format):
        try:
            if file_format == "csv":
                return pd.read_csv(path)
            if file_format in ["xlsx", "xls"]:
                return pd.read_excel(path)
            if file_format == "json":
                return pd.read_json(path)
            if file_format == "parquet":
                return pd.read_parquet(path)
        except Exception as e:
            logger.error("Failed to load dataframe: %s", e)
        return None

    @action(detail=False, methods=["get"], url_path=r"preview/(?P<dataset_id>\d+)")
    def preview(self, request, dataset_id=None):
        """
        GET /datalab/preview/{dataset_id}/
        Returns the dataset rendered as a dataframe table.
        """
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = self._load_dataframe(dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": "Unsupported file format."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "columns": list(df.columns),
            "rows": df.where(pd.notna(df), None).to_dict(orient="records"),
            "total_rows": len(df),
            "total_columns": len(df.columns),
        })

    @action(detail=False, methods=["get"], url_path=r"inspect/(?P<dataset_id>\d+)")
    def inspect(self, request, dataset_id=None):
        """
        GET /datalab/inspect/{dataset_id}/
        Returns df.shape, df.dtypes, and df.info() for the dataset.
        """
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = self._load_dataframe(dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": "Unsupported file format."}, status=status.HTTP_400_BAD_REQUEST)

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
