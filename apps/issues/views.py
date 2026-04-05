import pandas as pd
import numpy as np
from rest_framework import mixins, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from apps.datasets.models import Dataset
from .models import Issue
from .serializers import IssueSerializer

import re

ERR_UNSUPPORTED_FORMAT = "Unsupported format."

class IssueViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
      GET    /issues/?dataset={id}              — list issues (filter by dataset)
      GET    /issues/{id}/                      — single issue detail
      PATCH  /issues/{id}/                      — update issue fields
      DELETE /issues/{id}/                      — delete single issue
      POST   /issues/diagnose/{dataset_id}/     — run diagnosis scan
      GET    /issues/summary/{dataset_id}/      — issue stats for a dataset
    """
    serializer_class = IssueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Issue.objects.filter(dataset__user=self.request.user)
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        return qs

    # ------------------------------------------------------------------
    # Diagnose endpoint
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

    @action(detail=False, methods=["post"], url_path=r"diagnose/(?P<dataset_pk>\d+)")
    def diagnose(self, request, dataset_pk=None):
        """
        POST /issues/diagnose/{dataset_id}/

        Runs Pandas-based scans and returns issues grouped by column.
        All previous auto-detected issues are replaced on each run.
        """
        try:
            dataset = Dataset.objects.get(pk=dataset_pk, user=request.user)
        except Dataset.DoesNotExist:
            return Response({"detail": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            df = self._load_dataframe(dataset.file.path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            # Clear previous auto-detected issues
            dataset.issues.all().delete()

            # Build dataset overview
            overview = self._build_overview(df)

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

            issues_qs = dataset.issues.all().order_by("column_name", "-detected_at")

            if not issues_qs.exists():
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_SEMANTIC_ERROR,
                    description="Dataset is healthy! No major issues found.",
                    suggested_fix="Your data looks ready for analysis.",
                )
                issues_qs = dataset.issues.all()

            # Group issues by column for display
            grouped = {}
            for issue in issues_qs:
                key = issue.column_name or "__dataset__"
                grouped.setdefault(key, []).append({
                    "id": issue.id,
                    "issue_type": issue.issue_type,
                    "affected_rows": issue.affected_rows,
                    "description": issue.description,
                    "suggested_fix": issue.suggested_fix,
                })

            return Response({
                "dataset_id": dataset.id,
                "overview": overview,
                "total_issues": issues_qs.count(),
                "issues_by_column": grouped,
            })

        except Exception as e:
            return Response({"detail": f"Diagnosis failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path=r"summary/(?P<dataset_pk>\d+)")
    def summary(self, request, dataset_pk=None):
        """
        GET /issues/summary/{dataset_id}/

        Returns issue statistics for a dataset:
        - total count
        - count per issue_type
        - count per column
        """
        try:
            dataset = Dataset.objects.get(pk=dataset_pk, user=request.user)
        except Dataset.DoesNotExist:
            return Response({"detail": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)

        issues_qs = dataset.issues.all()

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

        dataset_level = issues_qs.filter(column_name="").count()

        return Response({
            "dataset_id": dataset.id,
            "total_issues": issues_qs.count(),
            "by_type": by_type,
            "by_column": by_column,
            "dataset_level_issues": dataset_level,
        })

    # ------------------------------------------------------------------
    # Dataset overview helper
    # ------------------------------------------------------------------

    def _build_overview(self, df):
        """Return df.info / shape / dtypes / nulls / duplicates / describe."""
        rows, cols = df.shape

        # Per-column info (dtype, non-null count, null count)
        columns_info = {}
        for col in df.columns:
            non_null = int(df[col].notna().sum())
            columns_info[col] = {
                "dtype": str(df[col].dtype),
                "non_null_count": non_null,
                "null_count": rows - non_null,
            }

        # Statistical summary for numeric columns (describe)
        describe = {}
        desc_df = df.describe()
        for col in desc_df.columns:
            describe[col] = {
                stat: round(float(val), 4) if pd.notna(val) else None
                for stat, val in desc_df[col].items()
            }

        return {
            "shape": {"rows": rows, "columns": cols},
            "duplicate_rows": int(df.duplicated().sum()),
            "total_missing": int(df.isnull().sum().sum()),
            "columns": columns_info,
            "numeric_summary": describe,
        }

    # ------------------------------------------------------------------
    # Scanner helpers
    # ------------------------------------------------------------------

    def _check_missing_values(self, dataset, df):
        for col, count in df.isnull().sum().to_dict().items():
            if count > 0:
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_MISSING_VALUE,
                    column_name=col,
                    affected_rows=int(count),
                    description=f"'{col}' has {count} missing value(s).",
                    suggested_fix="Use the 'handle_na' operation to fill or drop these rows.",
                )

    def _check_duplicates(self, dataset, df):
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            Issue.objects.create(
                dataset=dataset,
                issue_type=Issue.TYPE_DUPLICATE,
                affected_rows=dup_count,
                description=f"Found {dup_count} exact duplicate row(s) across the dataset.",
                suggested_fix="Use the 'drop_duplicates' operation.",
            )

    def _check_type_inconsistencies(self, dataset, df):
        for col in df.columns:
            types = df[col].dropna().apply(type).unique()
            if len(types) > 1:
                type_names = [t.__name__ for t in types]
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_DATA_TYPE,
                    column_name=col,
                    description=f"'{col}' contains mixed types: {', '.join(type_names)}.",
                    suggested_fix="Use the 'astype' operation to standardize this column.",
                )

    def _check_outliers(self, dataset, df):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].std() > 0:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                ocount = int((z_scores > 3).sum())
                if ocount > 0:
                    Issue.objects.create(
                        dataset=dataset,
                        issue_type=Issue.TYPE_OUTLIER,
                        column_name=col,
                        affected_rows=ocount,
                        description=f"'{col}' has {ocount} outlier(s) with Z-score > 3.",
                        suggested_fix="Use 'outlier_clip' to bound these values.",
                    )

    def _check_inconsistent_formatting(self, dataset, df):
        """Detect columns where date-like strings use multiple formats."""
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
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_INCONSISTENT_FORMATTING,
                    column_name=col,
                    description=f"'{col}' has mixed date formats: {fmt_list}.",
                    suggested_fix="Standardize all dates to a single format (e.g. YYYY-MM-DD).",
                )

    def _check_invalid_values(self, dataset, df):
        """Flag negative numbers in columns whose names suggest non-negative values."""
        non_negative_hints = [
            "age", "price", "quantity", "qty", "amount", "count",
            "salary", "income", "revenue", "cost", "weight", "height",
            "population", "score", "rating", "total", "balance",
        ]
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_lower = col.lower().replace("_", " ")
            if any(hint in col_lower for hint in non_negative_hints):
                neg_count = int((df[col].dropna() < 0).sum())
                if neg_count > 0:
                    Issue.objects.create(
                        dataset=dataset,
                        issue_type=Issue.TYPE_INVALID_VALUE,
                        column_name=col,
                        affected_rows=neg_count,
                        description=f"'{col}' has {neg_count} negative value(s), which is unexpected.",
                        suggested_fix="Review and correct these values, or convert to absolute values.",
                    )

    def _check_whitespace_issues(self, dataset, df):
        """Detect leading/trailing whitespace or multiple consecutive spaces."""
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            has_issue = vals.str.contains(r"^\s|\s$|\s{2,}", regex=True)
            count = int(has_issue.sum())
            if count > 0:
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_WHITESPACE_ISSUE,
                    column_name=col,
                    affected_rows=count,
                    description=f"'{col}' has {count} value(s) with leading, trailing, or extra whitespace.",
                    suggested_fix="Use strip() and regex to normalize whitespace.",
                )

    def _check_special_char_encoding(self, dataset, df):
        """Detect non-ASCII characters and common mojibake patterns."""
        mojibake_pattern = re.compile(r"\ufffd|Ã.|â€.|Â.")
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            has_issue = vals.apply(lambda v: bool(mojibake_pattern.search(v)))
            count = int(has_issue.sum())
            if count > 0:
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_SPECIAL_CHAR_ENCODING,
                    column_name=col,
                    affected_rows=count,
                    description=f"'{col}' has {count} value(s) with encoding issues (e.g. Ã©, â€™, ï¿½).",
                    suggested_fix="Re-encode the file as UTF-8, or replace garbled characters.",
                )

    def _check_inconsistent_naming(self, dataset, df):
        """Detect categorical columns where the same value appears in different cases."""
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            vals = df[col].dropna().astype(str)
            if vals.empty:
                continue
            unique_vals = vals.unique()
            # Only check columns that look categorical (not too many unique values)
            if len(unique_vals) > 100 or len(unique_vals) < 2:
                continue
            lower_map = {}
            for v in unique_vals:
                lower_map.setdefault(v.strip().lower(), []).append(v)
            inconsistent_groups = {k: vs for k, vs in lower_map.items() if len(vs) > 1}
            if inconsistent_groups:
                examples = []
                for variants in list(inconsistent_groups.values())[:3]:
                    examples.append(" / ".join(f"'{v}'" for v in variants))
                affected = sum(
                    int(vals.isin(vs).sum())
                    for vs in inconsistent_groups.values()
                )
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_INCONSISTENT_NAMING,
                    column_name=col,
                    affected_rows=affected,
                    description=f"'{col}' has inconsistent naming: {'; '.join(examples)}.",
                    suggested_fix="Standardize values to a consistent case (e.g. Title Case).",
                )

    def _check_logical_inconsistencies(self, dataset, df):
        """Detect logically impossible value combinations."""
        cols_lower = {c.lower().replace(" ", "_"): c for c in df.columns}
        self._check_date_inconsistencies(dataset, df, cols_lower)
        self._check_bound_inconsistencies(dataset, df, cols_lower)

    def _check_date_inconsistencies(self, dataset, df, cols_lower):
        # Check: start_date > end_date
        start_candidates = ["start_date", "start_time", "begin_date", "date_start"]
        end_candidates = ["end_date", "end_time", "finish_date", "date_end"]
        for s_key in start_candidates:
            for e_key in end_candidates:
                s_col = cols_lower.get(s_key)
                e_col = cols_lower.get(e_key)
                if s_col and e_col:
                    try:
                        starts = pd.to_datetime(df[s_col], errors="coerce")
                        ends = pd.to_datetime(df[e_col], errors="coerce")
                        mask = (starts.notna() & ends.notna() & (starts > ends))
                        count = int(mask.sum())
                        if count > 0:
                            Issue.objects.create(
                                dataset=dataset,
                                issue_type=Issue.TYPE_LOGICAL_INCONSISTENCY,
                                column_name=f"{s_col}, {e_col}",
                                affected_rows=count,
                                description=f"{count} row(s) where '{s_col}' is after '{e_col}'.",
                                suggested_fix="Review and swap or correct the date values.",
                            )
                    except Exception:
                        pass

    def _check_bound_inconsistencies(self, dataset, df, cols_lower):
        # Check: min > max columns
        min_candidates = ["min", "minimum", "low", "lower_bound"]
        max_candidates = ["max", "maximum", "high", "upper_bound"]
        for mn_key in min_candidates:
            for mx_key in max_candidates:
                mn_col = cols_lower.get(mn_key)
                mx_col = cols_lower.get(mx_key)
                if mn_col and mx_col:
                    try:
                        mins = pd.to_numeric(df[mn_col], errors="coerce")
                        maxs = pd.to_numeric(df[mx_col], errors="coerce")
                        mask = (mins.notna() & maxs.notna() & (mins > maxs))
                        count = int(mask.sum())
                        if count > 0:
                            Issue.objects.create(
                                dataset=dataset,
                                issue_type=Issue.TYPE_LOGICAL_INCONSISTENCY,
                                column_name=f"{mn_col}, {mx_col}",
                                affected_rows=count,
                                description=f"{count} row(s) where '{mn_col}' exceeds '{mx_col}'.",
                                suggested_fix="Review and correct the min/max values.",
                            )
                    except Exception:
                        pass
