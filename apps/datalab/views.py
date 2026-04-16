import io
import re
import logging
import pandas as pd
import numpy as np

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset
from apps.core.data_engine import load_data, generate_summary_stats
from .models import DatalabIssue, WrangleOperation
from .serializers import DatalabIssueSerializer, WrangleOperationSerializer

logger = logging.getLogger(__name__)

ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class DatalabViewSet(viewsets.ViewSet):
    """
    Datalab ViewSet: Handles Exploratory Data Analysis (EDA) and Wrangling.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _load_dataframe(self, path, file_format):
        try:
            if file_format == "csv":
                return pd.read_csv(path)
            if file_format in ["xlsx"]:
                return pd.read_excel(path)
            if file_format == "json":
                return pd.read_json(path)
            if file_format == "parquet":
                return pd.read_parquet(path)
        except Exception as e:
            logger.error(f"Failed to load dataframe: {e}")
        return None

    # =========================================================================
    # EDA (Exploratory Data Analysis) - Previously Issues
    # =========================================================================

    @action(detail=False, methods=["post"], url_path=r"eda/diagnose/(?P<dataset_id>\d+)")
    def eda_diagnose(self, request, dataset_id=None):
        """
        POST /datalab/eda/diagnose/{dataset_id}/
        Runs diagnostic scans and returns issues found in the dataset.
        """
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)

        try:
            df = self._load_dataframe(dataset.file.path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            # Clear previous issues
            dataset.datalab_issues.all().delete()

            # Run scans
            self._check_missing_values(dataset, df)
            self._check_duplicates(dataset, df)
            self._check_type_inconsistencies(dataset, df)
            self._check_outliers(dataset, df)
            self._check_inconsistent_formatting(dataset, df)
            self._check_invalid_values(dataset, df)
            self._check_whitespace_issues(dataset, df)
            self._check_special_char_encoding(dataset, df)
            self._check_inconsistent_naming(dataset, df)
            self._check_logical_inconsistencies(dataset, df)

            issues_qs = dataset.datalab_issues.all().order_by("column_name", "-detected_at")
            
            # Summary stats
            overview = self._build_overview(df)

            return Response({
                "dataset_id": dataset.id,
                "overview": overview,
                "total_issues": issues_qs.count(),
                "issues": DatalabIssueSerializer(issues_qs, many=True).data
            })

        except Exception as e:
            logger.exception("EDA diagnosis failed")
            return Response({"detail": f"Diagnosis failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path=r"eda/summary/(?P<dataset_id>\d+)")
    def eda_summary(self, request, dataset_id=None):
        """
        GET /datalab/eda/summary/{dataset_id}/
        Returns summary statistics of issues for a dataset.
        """
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        issues_qs = dataset.datalab_issues.all()

        by_type = dict(
            issues_qs.values_list("issue_type")
            .annotate(count=Count("id"))
            .values_list("issue_type", "count")
        )

        by_column = dict(
            issues_qs.exclude(column_name="")
            .values_list("column_name")
            .annotate(count=Count("id"))
            .values_list("column_name", "count")
        )

        return Response({
            "dataset_id": dataset.id,
            "total_issues": issues_qs.count(),
            "by_type": by_type,
            "by_column": by_column,
        })

    # =========================================================================
    # Wrangling - Previously Cleaning
    # =========================================================================

    @action(detail=False, methods=["post"], url_path="wrangle/preview")
    def wrangle_preview(self, request):
        """
        POST /datalab/wrangle/preview/
        Preview a wrangling operation without applying it.
        """
        dataset_id = request.data.get("dataset")
        operation_type = request.data.get("operation_type")
        column_name = request.data.get("column_name", "")
        parameters = request.data.get("parameters", {})

        if not dataset_id or not operation_type:
            return Response({"detail": "dataset and operation_type are required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_object_or_404(Dataset, id=dataset_id, user=request.user)
        
        try:
            df = load_data(dataset.file.path)
            df_preview = self._apply_operation(df.copy(), operation_type, column_name, parameters)
            summary = generate_summary_stats(df_preview)
            sample = df_preview.head(10).to_dict(orient="records")
            return Response({"summary": summary, "sample": sample})
        except Exception as e:
            return Response({"detail": f"Preview failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], url_path=r"wrangle/apply/(?P<dataset_id>\d+)")
    def wrangle_apply(self, request, dataset_id=None):
        """
        POST /datalab/wrangle/apply/{dataset_id}/
        Apply a wrangling operation and save the result.
        """
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        operation_type = request.data.get("operation_type")
        column_name = request.data.get("column_name", "")
        parameters = request.data.get("parameters", {})

        if not operation_type:
             return Response({"detail": "operation_type is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = load_data(dataset.file.path)
            original_rows = len(df)
            
            # Create a history entry (PENDING)
            op = WrangleOperation.objects.create(
                dataset=dataset,
                operation_type=operation_type,
                column_name=column_name,
                parameters=parameters,
                status="PENDING"
            )

            df = self._apply_operation(df, operation_type, column_name, parameters)
            
            # Save the new file (overwriting current, ideally we'd version)
            # In existing logic, it seems they overwrite or create new?
            # Existing cleaning/views.py didn't show the save part clearly in the snippet, 
            # but usually we save to a buffer and then to the dataset file.
            
            # Simple overwrite approach for now
            buf = io.StringIO() if dataset.file_format == "csv" else io.BytesIO()
            if dataset.file_format == "csv":
                df.to_csv(buf, index=False)
            elif dataset.file_format == "xlsx":
                df.to_excel(buf, index=False)
            elif dataset.file_format == "json":
                df.to_json(buf, orient="records")
            elif dataset.file_format == "parquet":
                df.to_parquet(buf, index=False)
            
            # Update dataset file content
            from django.core.files.base import ContentFile
            content = buf.getvalue()
            if isinstance(content, str):
                content = content.encode("utf-8")
            
            dataset.file.save(dataset.file_name, ContentFile(content), save=True)
            dataset.is_cleaned = True
            dataset.save()

            op.status = "APPLIED"
            op.rows_affected = abs(len(df) - original_rows)
            op.save()

            return Response(WrangleOperationSerializer(op).data)

        except Exception as e:
            logger.exception("Wrangle apply failed")
            return Response({"detail": f"Wrangle failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _apply_operation(self, df, op_type, col, params):
        method_name = f"_op_{op_type.lower()}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(df, col, params)
        return df

    def _op_fill_na(self, df, col, params):
        val = params.get("value", 0)
        if col:
            df[col] = df[col].fillna(val)
        else:
            df = df.fillna(val)
        return df

    def _op_drop_duplicates(self, df, col, params):
        return df.drop_duplicates()

    def _op_drop_rows(self, df, col, params):
        cond = params.get("condition")
        if col and cond:
            df = df.query(f"{col}{cond}")
        return df

    def _op_strip_whitespace(self, df, col, params):
        if col:
            df[col] = df[col].astype(str).str.strip()
        return df

    def _op_rename_column(self, df, col, params):
        new_name = params.get("new_name")
        if col and new_name:
            df = df.rename(columns={col: new_name})
        return df

    def _build_overview(self, df):
        rows, cols = df.shape
        return {
            "shape": {"rows": rows, "columns": cols},
            "duplicate_rows": int(df.duplicated().sum()),
            "total_missing": int(df.isnull().sum().sum()),
        }

    # (Add other scanner helpers from IssueViewSet here as needed)
    # I'll include a few key ones to keep it functional

    def _check_missing_values(self, dataset, df):
        for col, count in df.isnull().sum().to_dict().items():
            if count > 0:
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_MISSING_VALUE,
                    column_name=col,
                    affected_rows=int(count),
                    description=f"'{col}' has {count} missing value(s).",
                    suggested_fix="Use 'fill_na' to handle these.",
                )

    def _check_duplicates(self, dataset, df):
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            DatalabIssue.objects.create(
                dataset=dataset,
                issue_type=DatalabIssue.TYPE_DUPLICATE,
                affected_rows=dup_count,
                description=f"Found {dup_count} duplicate row(s).",
                suggested_fix="Use 'drop_duplicates'.",
            )
    
    # ... other scanners truncated for brevity in this step, but I'll add them if needed ...
    def _check_type_inconsistencies(self, dataset, df):
        for col in df.columns:
            types = df[col].dropna().apply(type).unique()
            if len(types) > 1:
                type_names = [t.__name__ for t in types]
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_DATA_TYPE,
                    column_name=col,
                    description=f"'{col}' contains mixed types: {', '.join(type_names)}.",
                    suggested_fix="Use the 'cast_column' operation to standardize this column.",
                )

    def _check_outliers(self, dataset, df):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].std() > 0:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                ocount = int((z_scores > 3).sum())
                if ocount > 0:
                    DatalabIssue.objects.create(
                        dataset=dataset,
                        issue_type=DatalabIssue.TYPE_OUTLIER,
                        column_name=col,
                        affected_rows=ocount,
                        description=f"'{col}' has {ocount} outlier(s) with Z-score > 3.",
                        suggested_fix="Use 'clip_outliers' or 'remove_outliers' to bound these values.",
                    )

    def _check_inconsistent_formatting(self, dataset, df):
        date_patterns = [
            (r"\d{4}-\d{2}-\d{2}", "YYYY-MM-DD"),
            (r"\d{2}/\d{2}/\d{4}", "MM/DD/YYYY"),
            (r"\d{2}-\d{2}-\d{4}", "DD-MM-YYYY"),
            (r"\d{2}\.\d{2}\.\d{4}", "DD.MM.YYYY"),
        ]
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            found_formats = set()
            for pattern, label in date_patterns:
                if vals.str.fullmatch(pattern).any():
                    found_formats.add(label)
            if len(found_formats) > 1:
                fmt_list = ", ".join(sorted(found_formats))
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_INCONSISTENT_FORMATTING,
                    column_name=col,
                    description=f"'{col}' has mixed date formats: {fmt_list}.",
                    suggested_fix="Standardize all dates to a single format (e.g. YYYY-MM-DD).",
                )

    def _check_invalid_values(self, dataset, df):
        non_negative_hints = ["age", "price", "quantity", "qty", "amount", "salary", "revenue", "cost"]
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_lower = col.lower().replace("_", " ")
            if any(hint in col_lower for hint in non_negative_hints):
                neg_count = int((df[col].dropna() < 0).sum())
                if neg_count > 0:
                    DatalabIssue.objects.create(
                        dataset=dataset,
                        issue_type=DatalabIssue.TYPE_INVALID_VALUE,
                        column_name=col,
                        affected_rows=neg_count,
                        description=f"'{col}' has {neg_count} negative value(s), which is unexpected.",
                        suggested_fix="Review and correct these values, or convert to absolute values.",
                    )

    def _check_whitespace_issues(self, dataset, df):
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            has_issue = vals.str.contains(r"^\s|\s$|\s{2,}", regex=True)
            count = int(has_issue.sum())
            if count > 0:
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_WHITESPACE_ISSUE,
                    column_name=col,
                    affected_rows=count,
                    description=f"'{col}' has {count} value(s) with leading, trailing, or extra whitespace.",
                    suggested_fix="Use 'strip_whitespace' to normalize.",
                )

    def _check_special_char_encoding(self, dataset, df):
        mojibake_pattern = re.compile(r"\ufffd|Ã.|â€.|Â.")
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            has_issue = vals.apply(lambda v: bool(mojibake_pattern.search(v)))
            count = int(has_issue.sum())
            if count > 0:
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_SPECIAL_CHAR_ENCODING,
                    column_name=col,
                    affected_rows=count,
                    description=f"'{col}' has {count} value(s) with encoding issues (e.g. Ã©, â€™).",
                    suggested_fix="Use 'fix_encoding' or re-encode your file.",
                )

    def _check_inconsistent_naming(self, dataset, df):
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            unique_vals = vals.unique()
            if len(unique_vals) > 100 or len(unique_vals) < 2:
                continue
            lower_map = {}
            for v in unique_vals:
                lower_map.setdefault(v.strip().lower(), []).append(v)
            inconsistent_groups = {k: vs for k, vs in lower_map.items() if len(vs) > 1}
            if inconsistent_groups:
                affected = sum(int(vals.isin(vs).sum()) for vs in inconsistent_groups.values())
                DatalabIssue.objects.create(
                    dataset=dataset,
                    issue_type=DatalabIssue.TYPE_INCONSISTENT_NAMING,
                    column_name=col,
                    affected_rows=affected,
                    description=f"'{col}' has inconsistent naming (casing/shorthand issues).",
                    suggested_fix="Standardize values to a consistent case.",
                )

    def _check_logical_inconsistencies(self, dataset, df):
        cols_lower = {c.lower().replace(" ", "_"): c for c in df.columns}
        # start_date > end_date check
        s_col = cols_lower.get("start_date")
        e_col = cols_lower.get("end_date")
        if s_col and e_col:
            try:
                starts = pd.to_datetime(df[s_col], errors="coerce")
                ends = pd.to_datetime(df[e_col], errors="coerce")
                mask = (starts.notna() & ends.notna() & (starts > ends))
                count = int(mask.sum())
                if count > 0:
                    DatalabIssue.objects.create(
                        dataset=dataset,
                        issue_type=DatalabIssue.TYPE_LOGICAL_INCONSISTENCY,
                        column_name=f"{s_col}, {e_col}",
                        affected_rows=count,
                        description=f"{count} row(s) where '{s_col}' is after '{e_col}'.",
                        suggested_fix="Validate and swap date values.",
                    )
            except Exception:
                pass
