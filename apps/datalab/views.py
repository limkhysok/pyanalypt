import logging
import pandas as pd

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset
from apps.core.data_engine import load_dataframe, save_dataframe, apply_cast, validate_cast, apply_stored_casts, SUPPORTED_CASTS

logger = logging.getLogger(__name__)

_UNSUPPORTED_FORMAT = "Unsupported file format."


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
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

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
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

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

    def cast_columns(self, request, dataset_id=None):
        """POST /datalab/cast/{dataset_id}/"""
        casts = request.data.get("casts")
        if not casts or not isinstance(casts, dict):
            return Response(
                {"detail": "Provide a 'casts' object mapping column names to target types."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invalid_types = [t for t in casts.values() if t not in SUPPORTED_CASTS]
        if invalid_types:
            return Response(
                {"detail": f"Unsupported types: {invalid_types}. Supported: {sorted(SUPPORTED_CASTS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)

        if dataset.file_format.lower() == "sql":
            return Response(
                {"detail": "Cast is not supported for SQL files."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        df = load_dataframe(dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unknown_cols = [c for c in casts if c not in df.columns]
        if unknown_cols:
            return Response(
                {"detail": f"Columns not found in dataset: {unknown_cols}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        force = request.data.get("force", False)
        results = []
        validation_warnings = []
        
        # Phase 1: Validation
        col_validated_data = {}
        for col, target in casts.items():
            status, message = validate_cast(df[col], target)
            col_validated_data[col] = {"status": status, "message": message}
            if status == "warning":
                validation_warnings.append({"column": col, "warning": message})
            elif status == "error":
                results.append({
                    "column": col,
                    "target": target,
                    "status": "error",
                    "detail": message
                })

        # Phase 2: Handle Warnings (Block if not forced)
        if validation_warnings and not force:
            return Response({
                "detail": "Some conversions are risky. Use 'force: true' to proceed.",
                "warnings": validation_warnings,
                "errors": [r for r in results if r["status"] == "error"]
            }, status=status.HTTP_400_BAD_REQUEST)

        # Phase 3: Apply (only for non-error columns)
        for col, target in casts.items():
            # Skip if we already logged an error during validation
            if any(r["column"] == col and r["status"] == "error" for r in results):
                continue
                
            from_dtype = str(df[col].dtype)
            try:
                df[col] = apply_cast(df[col], target)
                results.append({
                    "column": col,
                    "from_dtype": from_dtype,
                    "to_dtype": str(df[col].dtype),
                    "status": "ok",
                    "validation": col_validated_data[col]
                })
            except Exception as exc:
                results.append({
                    "column": col,
                    "from_dtype": from_dtype,
                    "to_dtype": None,
                    "status": "error",
                    "detail": str(exc),
                })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response(
                {"detail": "Failed to save updated dataset."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist cast preferences so they survive reload (flat files lose type info)
        successful = {r["column"]: casts[r["column"]] for r in results if r["status"] == "ok"}
        dataset.column_casts = {**dataset.column_casts, **successful}
        dataset.save(update_fields=["column_casts"])

        return Response({"updated_columns": results})
