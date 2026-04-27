import logging
import pandas as pd

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset, DatasetActivityLog
from apps.core.data_engine import (
    get_cached_dataframe,
    invalidate_dataframe_cache,
    save_dataframe,
    apply_cast,
    validate_cast,
    apply_stored_casts,
    update_cell as df_update_cell,
    rename_column as df_rename_column,
    replace_values as df_replace_values,
    drop_nulls as df_drop_nulls,
    fill_nulls as df_fill_nulls,
    describe_dataframe,
    fill_derived as df_fill_derived,
    validate_formula as df_validate_formula,
    fix_formula_errors as df_fix_formula_errors,
    detect_outliers as df_detect_outliers,
    trim_outliers as df_trim_outliers,
    impute_outliers as df_impute_outliers,
    cap_outliers as df_cap_outliers,
    transform_column as df_transform_column,
    FILL_STRATEGIES,
    SUPPORTED_CASTS,
    SUPPORTED_FORMULAS,
    OUTLIER_METHODS,
    OUTLIER_IMPUTE_STRATEGIES,
    COLUMN_TRANSFORMS,
)

logger = logging.getLogger(__name__)

_UNSUPPORTED_FORMAT = "Unsupported file format."
_SAVE_FAILED = "Failed to save updated dataset."
_INVALID_THRESHOLD = "'threshold' must be a positive number."


def _validate_casts(df, casts):
    """Run pre-flight validation on each requested cast. Returns (validated, warnings, errors)."""
    validated = {}
    warnings = []
    errors = []
    for col, target in casts.items():
        cast_status, message = validate_cast(df[col], target)
        validated[col] = {"status": cast_status, "message": message}
        if cast_status == "warning":
            warnings.append({"column": col, "warning": message})
        elif cast_status == "error":
            errors.append({"column": col, "target": target, "status": "error", "detail": message})
    return validated, warnings, errors


def _format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


_DEDUP_MODES = ("all_first", "all_last", "subset_keep", "drop_all")


def _validate_dedup_params(mode, subset, keep):
    if mode not in _DEDUP_MODES:
        return Response(
            {"detail": f"Invalid 'mode'. Choose one of: {list(_DEDUP_MODES)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if mode == "subset_keep":
        if subset is None:
            return Response(
                {"detail": "'subset' is required for mode 'subset_keep'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if keep not in ("first", "last"):
            return Response(
                {"detail": "For mode 'subset_keep', 'keep' must be 'first' or 'last'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return None


def _validate_subset_cols(subset, df):
    if subset is None:
        return None
    if not isinstance(subset, list) or not subset:
        return Response(
            {"detail": "'subset' must be a non-empty list of column names."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not all(isinstance(c, str) for c in subset):
        return Response(
            {"detail": "'subset' must be a list of column name strings."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    unknown_cols = [c for c in subset if c not in df.columns]
    if unknown_cols:
        return Response(
            {"detail": f"Columns not found in dataset: {unknown_cols}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _apply_dedup(df, mode, subset, keep):
    if mode == "all_first":
        return df.drop_duplicates(keep="first")
    if mode == "all_last":
        return df.drop_duplicates(keep="last")
    if mode == "subset_keep":
        return df.drop_duplicates(subset=subset, keep=keep)
    return df.drop_duplicates(subset=subset, keep=False)  # drop_all


def _parse_outlier_columns(source, df):
    """
    Parse and validate the 'columns' param for outlier/transform endpoints.
    source: list from request.data, or comma-separated string from query_params.
    Returns (columns_list, error_response_or_None).
    """
    if not source:
        return None, Response(
            {"detail": "'columns' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(source, str):
        columns = [c.strip() for c in source.split(",") if c.strip()]
    elif isinstance(source, list):
        columns = source
    else:
        return None, Response(
            {"detail": "'columns' must be a list or comma-separated string."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not columns:
        return None, Response(
            {"detail": "'columns' must not be empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    unknown = [c for c in columns if c not in df.columns]
    if unknown:
        return None, Response(
            {"detail": f"Columns not found in dataset: {unknown}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    non_numeric = [c for c in columns if not pd.api.types.is_numeric_dtype(df[c])]
    if non_numeric:
        return None, Response(
            {"detail": f"Outlier operations require numeric columns: {non_numeric}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return columns, None


def _validate_drop_nulls_params(axis, how, thresh_pct):
    if axis not in ("rows", "columns"):
        return Response(
            {"detail": "'axis' must be 'rows' or 'columns'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if axis == "rows" and how not in ("any", "all"):
        return Response(
            {"detail": "'how' must be 'any' or 'all'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if axis == "columns":
        if thresh_pct is None:
            return Response(
                {"detail": "'thresh_pct' is required when axis is 'columns'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(thresh_pct, (int, float)) or not (0 <= thresh_pct <= 100):
            return Response(
                {"detail": "'thresh_pct' must be a number between 0 and 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return None


class DatalabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def preview(self, request, dataset_id=None):
        """GET /datalab/preview/{dataset_id}/"""
        try:
            limit = int(request.query_params.get("limit", 100))
            if limit < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "'limit' must be a non-negative integer (0 = all rows)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        total_rows = len(df)
        view_df = df if limit == 0 else df.iloc[:limit]

        return Response({
            "dataset_id": dataset.id,
            "file_name": dataset.file_name,
            "file_format": dataset.file_format,
            "dataset_size": _format_size(dataset.file_size),
            "total_rows": total_rows,
            "total_columns": len(df.columns),
            "limit": limit,
            "columns": list(df.columns),
            "rows": view_df.astype(object).where(pd.notna(view_df), None).to_dict(orient="records"),
        })

    def inspect(self, request, dataset_id=None):
        """GET /datalab/inspect/{dataset_id}/"""
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        total_rows = len(df)
        unique_counts = df.nunique()

        return Response({
            "info": {
                "columns": [
                    {
                        "column": col,
                        "dtype": str(df[col].dtype),
                        "non_null_count": int(df[col].notna().sum()),
                        "null_count": int(df[col].isna().sum()),
                        "null_pct": round(df[col].isna().sum() / total_rows * 100, 1) if total_rows > 0 else 0.0,
                        "unique_count": int(unique_counts[col]),
                        "is_unique": bool(unique_counts[col] == total_rows),
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

        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
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
        col_validated_data, validation_warnings, results = _validate_casts(df, casts)

        if validation_warnings and not force:
            return Response({
                "detail": "Some conversions are risky. Use 'force: true' to proceed.",
                "warnings": validation_warnings,
                "errors": results,
            }, status=status.HTTP_400_BAD_REQUEST)

        error_cols = {r["column"] for r in results}
        for col, target in casts.items():
            if col in error_cols:
                continue
            from_dtype = str(df[col].dtype)
            try:
                df[col] = apply_cast(df[col], target)
                results.append({
                    "column": col,
                    "from_dtype": from_dtype,
                    "to_dtype": str(df[col].dtype),
                    "status": "ok",
                    "validation": col_validated_data[col],
                })
            except Exception as exc:
                results.append({
                    "column": col,
                    "from_dtype": from_dtype,
                    "to_dtype": None,
                    "status": "error",
                    "detail": str(exc),
                })

        # Persist cast preferences so they survive reload (flat files lose type info)
        successful = {r["column"]: casts[r["column"]] for r in results if r["status"] == "ok"}
        if successful:
            if not save_dataframe(df, dataset.file.path, dataset.file_format):
                return Response(
                    {"detail": _SAVE_FAILED},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            invalidate_dataframe_cache(dataset.id)
            dataset.column_casts = {**dataset.column_casts, **successful}
            dataset.save(update_fields=["column_casts"])

        return Response({"updated_columns": results})

    def update_cell(self, request, dataset_id=None):
        """PATCH /datalab/update-cell/{dataset_id}/"""
        row_index = request.data.get("row_index")
        column = request.data.get("column", "").strip()
        value = request.data.get("value")  # None means set to null

        if row_index is None or not column:
            return Response(
                {"detail": "'row_index' and 'column' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(row_index, int) or row_index < 0:
            return Response(
                {"detail": "'row_index' must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        if column not in df.columns:
            return Response(
                {"detail": f"Column '{column}' not found in dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if row_index >= len(df):
            return Response(
                {"detail": f"Row index {row_index} is out of range (dataset has {len(df)} rows)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            df, coerced = df_update_cell(df, row_index, column, value)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response(
                {"detail": _SAVE_FAILED},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invalidate_dataframe_cache(dataset.id)

        DatasetActivityLog.objects.create(
            user=request.user,
            dataset=dataset,
            dataset_name_snap=dataset.file_name,
            action="UPDATE_CELL",
            details={"row_index": row_index, "column": column, "value": str(coerced)},
        )

        serialized = coerced.isoformat() if hasattr(coerced, "isoformat") else coerced
        return Response({"row_index": row_index, "column": column, "value": serialized})

    def rename_column(self, request, dataset_id=None):
        """POST /datalab/rename-column/{dataset_id}/"""
        old_name = request.data.get("old_name", "").strip()
        new_name = request.data.get("new_name", "").strip()

        if not old_name or not new_name:
            return Response(
                {"detail": "'old_name' and 'new_name' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if old_name == new_name:
            return Response(
                {"detail": "New name is identical to the current name."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response(
                {"detail": _UNSUPPORTED_FORMAT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if old_name not in df.columns:
            return Response(
                {"detail": f"Column '{old_name}' not found in dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_name in df.columns:
            return Response(
                {"detail": f"Column '{new_name}' already exists in dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        df = df_rename_column(df, old_name, new_name)

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response(
                {"detail": _SAVE_FAILED},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invalidate_dataframe_cache(dataset.id)

        # Migrate stored cast key so the renamed column keeps its dtype override
        if old_name in dataset.column_casts:
            dataset.column_casts[new_name] = dataset.column_casts.pop(old_name)
            dataset.save(update_fields=["column_casts"])

        return Response({
            "old_name": old_name,
            "new_name": new_name,
            "columns": list(df.columns),
        })

    def drop_duplicates(self, request, dataset_id=None):
        """POST /datalab/drop-duplicates/{dataset_id}/

        mode="all_first"   — compare all columns, keep first occurrence (default)
        mode="all_last"    — compare all columns, keep last occurrence
        mode="subset_keep" — compare subset columns, keep first/last (requires subset + keep)
        mode="drop_all"    — drop every copy of any duplicate (optional subset)
        """
        mode = request.data.get("mode", "all_first")
        subset = request.data.get("subset")
        keep = request.data.get("keep", "first")

        error = _validate_dedup_params(mode, subset, keep)
        if error:
            return error

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        error = _validate_subset_cols(subset, df)
        if error:
            return error

        rows_before = len(df)
        df = _apply_dedup(df, mode, subset, keep)
        rows_dropped = rows_before - len(df)

        if rows_dropped == 0:
            return Response({
                "rows_before": rows_before,
                "rows_after": rows_before,
                "rows_dropped": 0,
                "detail": "No duplicate rows found.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response(
                {"detail": _SAVE_FAILED},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "mode": mode,
            "rows_before": rows_before,
            "rows_after": len(df),
            "rows_dropped": rows_dropped,
        })

    def replace_values(self, request, dataset_id=None):
        """POST /datalab/replace-values/{dataset_id}/"""
        replacements = request.data.get("replacements")
        columns = request.data.get("columns")

        if not replacements or not isinstance(replacements, dict):
            return Response(
                {"detail": "'replacements' must be an object mapping old values to new values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        if columns is not None:
            if not isinstance(columns, list) or not columns:
                return Response(
                    {"detail": "'columns' must be a non-empty list of column names."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            unknown_cols = [c for c in columns if c not in df.columns]
            if unknown_cols:
                return Response(
                    {"detail": f"Columns not found in dataset: {unknown_cols}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        df, cells_replaced = df_replace_values(df, replacements, columns)

        if cells_replaced == 0:
            return Response({
                "replacements": replacements,
                "columns_affected": columns or list(df.columns),
                "cells_replaced": 0,
                "detail": "No matching values found.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "replacements": replacements,
            "columns_affected": columns or list(df.columns),
            "cells_replaced": cells_replaced,
        })

    def drop_nulls(self, request, dataset_id=None):
        """POST /datalab/drop-nulls/{dataset_id}/"""
        axis = request.data.get("axis", "rows")
        how = request.data.get("how", "any")
        subset = request.data.get("subset")
        thresh_pct = request.data.get("thresh_pct")

        error = _validate_drop_nulls_params(axis, how, thresh_pct)
        if error:
            return error

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        if axis == "rows" and subset is not None:
            error = _validate_subset_cols(subset, df)
            if error:
                return error

        df, stats = df_drop_nulls(df, axis, how=how, subset=subset, thresh_pct=thresh_pct)

        dropped_count = stats.get("rows_dropped", 0) or len(stats.get("columns_dropped", []))
        if dropped_count == 0:
            return Response({"axis": axis, **stats, "detail": "No null rows/columns matched the criteria."})

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({"axis": axis, **stats})

    def describe(self, request, dataset_id=None):
        """GET /datalab/describe/{dataset_id}/"""
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        return Response({"columns": describe_dataframe(df)})

    def fill_derived(self, request, dataset_id=None):
        """POST /datalab/fill-derived/{dataset_id}/"""
        target = request.data.get("target", "").strip()
        formula = request.data.get("formula", "").strip()
        operand_a = request.data.get("operand_a", "").strip()
        operand_b = request.data.get("operand_b", "").strip()

        if not all([target, formula, operand_a, operand_b]):
            return Response(
                {"detail": "'target', 'formula', 'operand_a', and 'operand_b' are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if formula not in SUPPORTED_FORMULAS:
            return Response(
                {"detail": f"Invalid 'formula'. Choose one of: {list(SUPPORTED_FORMULAS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        missing = [c for c in [target, operand_a, operand_b] if c not in df.columns]
        if missing:
            return Response(
                {"detail": f"Columns not found in dataset: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        non_numeric = [c for c in [operand_a, operand_b] if not pd.api.types.is_numeric_dtype(df[c])]
        if non_numeric:
            return Response(
                {"detail": f"Operand columns must be numeric: {non_numeric}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        df, cells_filled = df_fill_derived(df, target, formula, operand_a, operand_b)

        if cells_filled == 0:
            return Response({
                "target": target,
                "formula": formula,
                "operand_a": operand_a,
                "operand_b": operand_b,
                "cells_filled": 0,
                "detail": f"No null values in '{target}' with complete operand data.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "target": target,
            "formula": formula,
            "operand_a": operand_a,
            "operand_b": operand_b,
            "cells_filled": cells_filled,
        })

    def validate_formula(self, request, dataset_id=None):
        """POST /datalab/validate-formula/{dataset_id}/"""
        result_column = request.data.get("result_column", "").strip()
        formula = request.data.get("formula", "").strip()
        operand_a = request.data.get("operand_a", "").strip()
        operand_b = request.data.get("operand_b", "").strip()
        tolerance = request.data.get("tolerance", 0.01)

        if not all([result_column, formula, operand_a, operand_b]):
            return Response(
                {"detail": "'result_column', 'formula', 'operand_a', and 'operand_b' are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if formula not in SUPPORTED_FORMULAS:
            return Response(
                {"detail": f"Invalid 'formula'. Choose one of: {list(SUPPORTED_FORMULAS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tolerance = float(tolerance)
            if tolerance < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "'tolerance' must be a non-negative number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        missing = [c for c in [result_column, operand_a, operand_b] if c not in df.columns]
        if missing:
            return Response(
                {"detail": f"Columns not found in dataset: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        non_numeric = [c for c in [result_column, operand_a, operand_b] if not pd.api.types.is_numeric_dtype(df[c])]
        if non_numeric:
            return Response(
                {"detail": f"All three columns must be numeric: {non_numeric}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = df_validate_formula(df, result_column, formula, operand_a, operand_b, tolerance)
        return Response({
            "result_column": result_column,
            "formula": formula,
            "operand_a": operand_a,
            "operand_b": operand_b,
            **result,
        })

    def fix_formula(self, request, dataset_id=None):
        """POST /datalab/fix-formula/{dataset_id}/"""
        target = request.data.get("target", "").strip()
        formula = request.data.get("formula", "").strip()
        operand_a = request.data.get("operand_a", "").strip()
        operand_b = request.data.get("operand_b", "").strip()
        tolerance = request.data.get("tolerance", 0.01)

        if not all([target, formula, operand_a, operand_b]):
            return Response(
                {"detail": "'target', 'formula', 'operand_a', and 'operand_b' are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if formula not in SUPPORTED_FORMULAS:
            return Response(
                {"detail": f"Invalid 'formula'. Choose one of: {list(SUPPORTED_FORMULAS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tolerance = float(tolerance)
            if tolerance < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "'tolerance' must be a non-negative number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        missing = [c for c in [target, operand_a, operand_b] if c not in df.columns]
        if missing:
            return Response(
                {"detail": f"Columns not found in dataset: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        non_numeric = [c for c in [target, operand_a, operand_b] if not pd.api.types.is_numeric_dtype(df[c])]
        if non_numeric:
            return Response(
                {"detail": f"All three columns must be numeric: {non_numeric}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        df, cells_fixed = df_fix_formula_errors(df, target, formula, operand_a, operand_b, tolerance)

        if cells_fixed == 0:
            return Response({
                "target": target,
                "formula": formula,
                "operand_a": operand_a,
                "operand_b": operand_b,
                "tolerance": tolerance,
                "cells_fixed": 0,
                "detail": "No inconsistent rows found within the given tolerance.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "target": target,
            "formula": formula,
            "operand_a": operand_a,
            "operand_b": operand_b,
            "tolerance": tolerance,
            "cells_fixed": cells_fixed,
        })

    def fill_nulls(self, request, dataset_id=None):
        """POST /datalab/fill-nulls/{dataset_id}/"""
        strategy = str(request.data.get("strategy", "")).strip()
        columns = request.data.get("columns")
        value = request.data.get("value")

        if strategy not in FILL_STRATEGIES:
            return Response(
                {"detail": f"'strategy' must be one of: {sorted(FILL_STRATEGIES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if strategy == "constant" and value is None:
            return Response(
                {"detail": "'value' is required when strategy is 'constant'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        if columns is not None:
            error = _validate_subset_cols(columns, df)
            if error:
                return error

        df, cells_filled, skipped_columns = df_fill_nulls(df, strategy, columns=columns, value=value)

        if cells_filled == 0:
            return Response({
                "strategy": strategy,
                "cells_filled": 0,
                "skipped_columns": skipped_columns,
                "detail": "No null values found to fill.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)

        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "strategy": strategy,
            "cells_filled": cells_filled,
            "skipped_columns": skipped_columns,
        })

    def detect_outliers(self, request, dataset_id=None):
        """GET /datalab/detect-outliers/{dataset_id}/"""
        method = request.query_params.get("method", "iqr")
        threshold_raw = request.query_params.get("threshold", "1.5" if method == "iqr" else "3.0")
        columns_raw = request.query_params.get("columns", "")

        if method not in OUTLIER_METHODS:
            return Response(
                {"detail": f"'method' must be one of: {list(OUTLIER_METHODS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            threshold = float(threshold_raw)
            if threshold <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": _INVALID_THRESHOLD},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)
        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        columns, err = _parse_outlier_columns(columns_raw, df)
        if err:
            return err

        result = df_detect_outliers(df, columns, method=method, threshold=threshold)
        return Response({
            "dataset_id": dataset_id,
            "method": method,
            "threshold": threshold,
            "columns": result,
        })

    def trim_outliers(self, request, dataset_id=None):
        """POST /datalab/trim-outliers/{dataset_id}/"""
        columns_raw = request.data.get("columns")
        method = request.data.get("method", "iqr")
        threshold_raw = request.data.get("threshold", 1.5)

        if method not in OUTLIER_METHODS:
            return Response(
                {"detail": f"'method' must be one of: {list(OUTLIER_METHODS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            threshold = float(threshold_raw)
            if threshold <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": _INVALID_THRESHOLD},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)
        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        columns, err = _parse_outlier_columns(columns_raw, df)
        if err:
            return err

        rows_before = len(df)
        df, rows_dropped = df_trim_outliers(df, columns, method=method, threshold=threshold)

        if rows_dropped == 0:
            return Response({
                "columns": columns,
                "method": method,
                "threshold": threshold,
                "rows_before": rows_before,
                "rows_after": rows_before,
                "rows_dropped": 0,
                "detail": "No outlier rows found.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)
        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "columns": columns,
            "method": method,
            "threshold": threshold,
            "rows_before": rows_before,
            "rows_after": len(df),
            "rows_dropped": rows_dropped,
        })

    def impute_outliers(self, request, dataset_id=None):
        """POST /datalab/impute-outliers/{dataset_id}/"""
        columns_raw = request.data.get("columns")
        method = request.data.get("method", "iqr")
        threshold_raw = request.data.get("threshold", 1.5)
        strategy = request.data.get("strategy", "median")

        if method not in OUTLIER_METHODS:
            return Response(
                {"detail": f"'method' must be one of: {list(OUTLIER_METHODS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if strategy not in OUTLIER_IMPUTE_STRATEGIES:
            return Response(
                {"detail": f"'strategy' must be one of: {list(OUTLIER_IMPUTE_STRATEGIES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            threshold = float(threshold_raw)
            if threshold <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": _INVALID_THRESHOLD},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)
        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        columns, err = _parse_outlier_columns(columns_raw, df)
        if err:
            return err

        df, cells_imputed = df_impute_outliers(df, columns, method=method, threshold=threshold, strategy=strategy)

        if cells_imputed == 0:
            return Response({
                "columns": columns,
                "method": method,
                "threshold": threshold,
                "strategy": strategy,
                "cells_imputed": 0,
                "detail": "No outliers found.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)
        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "columns": columns,
            "method": method,
            "threshold": threshold,
            "strategy": strategy,
            "cells_imputed": cells_imputed,
        })

    def cap_outliers(self, request, dataset_id=None):
        """POST /datalab/cap-outliers/{dataset_id}/"""
        columns_raw = request.data.get("columns")
        lower_pct_raw = request.data.get("lower_pct", 5.0)
        upper_pct_raw = request.data.get("upper_pct", 95.0)

        try:
            lower_pct = float(lower_pct_raw)
            upper_pct = float(upper_pct_raw)
            if not (0 <= lower_pct < upper_pct <= 100):
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "'lower_pct' and 'upper_pct' must be numbers where 0 <= lower_pct < upper_pct <= 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)
        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        columns, err = _parse_outlier_columns(columns_raw, df)
        if err:
            return err

        df, cells_capped = df_cap_outliers(df, columns, lower_pct=lower_pct, upper_pct=upper_pct)

        if cells_capped == 0:
            return Response({
                "columns": columns,
                "lower_pct": lower_pct,
                "upper_pct": upper_pct,
                "cells_capped": 0,
                "detail": "No values outside the percentile bounds.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)
        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "columns": columns,
            "lower_pct": lower_pct,
            "upper_pct": upper_pct,
            "cells_capped": cells_capped,
        })

    def transform_column(self, request, dataset_id=None):
        """POST /datalab/transform-column/{dataset_id}/"""
        columns_raw = request.data.get("columns")
        function = request.data.get("function", "log")

        if function not in COLUMN_TRANSFORMS:
            return Response(
                {"detail": f"'function' must be one of: {list(COLUMN_TRANSFORMS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        if df is None:
            return Response({"detail": _UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)
        if dataset.column_casts:
            df = apply_stored_casts(df, dataset.column_casts)

        columns, err = _parse_outlier_columns(columns_raw, df)
        if err:
            return err

        df, transformed, skipped = df_transform_column(df, columns, function=function)

        if not transformed:
            return Response({
                "function": function,
                "transformed_columns": [],
                "skipped_columns": skipped,
                "detail": "No columns were transformed.",
            })

        if not save_dataframe(df, dataset.file.path, dataset.file_format):
            return Response({"detail": _SAVE_FAILED}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        invalidate_dataframe_cache(dataset.id)
        dataset.file_size = dataset.file.size
        dataset.save(update_fields=["file_size", "updated_date"])

        return Response({
            "function": function,
            "transformed_columns": transformed,
            "skipped_columns": skipped,
        })
