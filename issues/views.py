import pandas as pd
import numpy as np
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datasets.models import Dataset
from .models import Issue
from .serializers import IssueSerializer

ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class IssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing detected data issues.
    Users can only see issues for THEIR datasets.

    Query params:
      GET /issues/?dataset={id}  — filter issues for a specific dataset
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
        if file_format in ["xlsx", "xls"]:
            return pd.read_excel(path)
        if file_format == "json":
            return pd.read_json(path)
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

            self._check_missing_values(dataset, df)
            self._check_duplicates(dataset, df)
            self._check_type_inconsistencies(dataset, df)
            self._check_outliers(dataset, df)

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
                "total_issues": issues_qs.count(),
                "issues_by_column": grouped,
            })

        except Exception as e:
            return Response({"detail": f"Diagnosis failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
