import uuid
import io
import pandas as pd
import numpy as np
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.files.base import ContentFile
from projects.models import Project
from .models import ProjectDataset
from .serializers import ProjectDatasetSerializer


class CreateDatasetView(generics.CreateAPIView):
    """
    Handle file uploads (Drag and Drop / File Input).
    Expects multipart/form-data.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Check ownership of the project
        project = serializer.validated_data["project"]
        if project.user != self.request.user:
            raise permissions.exceptions.PermissionDenied(
                "You do not own this project."
            )
        serializer.save()


class PasteDatasetView(generics.GenericAPIView):
    """
    Handle raw text paste (CSV or JSON string).
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project_id = request.data.get("project")
        raw_data = request.data.get("raw_data")
        file_name = request.data.get("name", f"pasted_data_{uuid.uuid4().hex[:8]}")
        data_format = request.data.get("format", "csv").lower()

        if not project_id:
            return Response(
                {"detail": "Project ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not raw_data:
            return Response(
                {"detail": "Raw data is empty."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create a virtual file from the raw string
        file_extension = ".json" if data_format == "json" else ".csv"
        if not file_name.endswith(file_extension):
            file_name += file_extension

        content_file = ContentFile(raw_data.encode("utf-8"), name=file_name)

        # Save via serializer
        serializer = self.get_serializer(
            data={"project": project.id, "file": content_file, "name": file_name}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectDatasetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual datasets (Read, Update, Delete).
    Includes a 'preview' action and 'clean' action for transformations.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProjectDataset.objects.filter(project__user=self.request.user)

    def _get_preview_response(self, dataset, df, row_limit=10):
        """Helper to generate preview structure from a dataframe."""
        preview_df = df.head(row_limit)
        dtypes = df.dtypes.apply(lambda x: str(x)).to_dict()
        summary = {}

        # Numeric summary
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if not numeric_cols.empty:
            summary = df[numeric_cols].describe().to_dict()

        return {
            "columns": list(df.columns),
            "rows": preview_df.where(pd.notnull(preview_df), None).to_dict(
                orient="records"
            ),
            "metadata": {
                "dtypes": dtypes,
                "shape": [len(df), len(df.columns)],
            },
            "summary": summary,
            "total_rows_hint": len(df),
            "dataset_id": dataset.id,
            "name": dataset.name,
        }

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        dataset = self.get_object()
        file_path = dataset.file.path

        try:
            row_limit = int(request.query_params.get("rows", 10))
            row_limit = min(max(row_limit, 1), 1000)
        except (ValueError, TypeError):
            row_limit = 10

        try:
            if dataset.file_format == "csv":
                df = pd.read_csv(
                    file_path, nrows=row_limit + 100
                )  # Read slightly more for context
            elif dataset.file_format in ["xlsx", "xls"]:
                df = pd.read_excel(file_path, nrows=row_limit + 100)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path).head(row_limit + 100)
            else:
                return Response(
                    {"detail": "Unsupported format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(self._get_preview_response(dataset, df, row_limit))

        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def clean(self, request, pk=None):
        """
        Apply data cleaning transformations.
        Expects a pipeline of operations.
        """
        dataset = self.get_object()
        pipeline = request.data.get("pipeline", [])
        file_path = dataset.file.path

        try:
            # Load full dataframe for pipeline processing
            if dataset.file_format == "csv":
                df = pd.read_csv(file_path)
            elif dataset.file_format in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path)
            else:
                return Response(
                    {"detail": "Unsupported format for cleaning."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Apply transformations
            for step in pipeline:
                op = step.get("operation")
                params = step.get("params", {})

                if op == "handle_na":
                    cols = params.get("columns", "all")
                    strategy = params.get("strategy", "drop")
                    target_cols = df.columns if cols == "all" else cols

                    if strategy == "drop":
                        df = df.dropna(subset=target_cols)
                    elif strategy == "fill_zero":
                        df[target_cols] = df[target_cols].fillna(0)
                    elif strategy == "fill_mean":
                        for c in target_cols:
                            if pd.api.types.is_numeric_dtype(df[c]):
                                df[c] = df[c].fillna(df[c].mean())
                    elif strategy == "fill_median":
                        for c in target_cols:
                            if pd.api.types.is_numeric_dtype(df[c]):
                                df[c] = df[c].fillna(df[c].median())

                elif op == "drop_duplicates":
                    cols = params.get("columns", "all")
                    subset = None if cols == "all" else cols
                    df = df.drop_duplicates(subset=subset)

                elif op == "astype":
                    col = params.get("column")
                    target_type = params.get("target_type")
                    if col in df.columns:
                        try:
                            if target_type == "int":
                                df[col] = (
                                    pd.to_numeric(df[col], errors="coerce")
                                    .fillna(0)
                                    .astype(int)
                                )
                            elif target_type == "float":
                                df[col] = pd.to_numeric(
                                    df[col], errors="coerce"
                                ).astype(float)
                            elif target_type == "string":
                                df[col] = df[col].astype(str)
                            elif target_type == "datetime":
                                df[col] = pd.to_datetime(df[col], errors="coerce")
                        except Exception as e:
                            return Response(
                                {
                                    "detail": f"Type conversion failed for column '{col}': {str(e)}"
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                elif op == "drop_columns":
                    cols = params.get("columns", [])
                    # Safety: don't drop everything
                    if len(cols) < len(df.columns):
                        df = df.drop(columns=[c for c in cols if c in df.columns])

                elif op == "rename_columns":
                    mapping = params.get("mapping", {})
                    df = df.rename(columns=mapping)

                elif op == "trim_strings":
                    cols = params.get("columns", "all")
                    target_cols = df.columns if cols == "all" else cols
                    for c in target_cols:
                        if pd.api.types.is_object_dtype(df[c]):
                            df[c] = df[c].astype(str).str.strip()

                elif op == "case_convert":
                    cols = params.get("columns", [])
                    case_type = params.get("case", "lower")
                    for c in cols:
                        if c in df.columns and pd.api.types.is_object_dtype(df[c]):
                            if case_type == "lower":
                                df[c] = df[c].astype(str).str.lower()
                            elif case_type == "upper":
                                df[c] = df[c].astype(str).str.upper()
                            elif case_type == "title":
                                df[c] = df[c].astype(str).str.title()

                elif op == "replace_value":
                    col = params.get("column")
                    old_v = params.get("old_value")
                    new_v = params.get("new_value")
                    if col in df.columns:
                        df[col] = df[col].replace(old_v, new_v)

                elif op == "outlier_clip":
                    cols = params.get("columns", [])
                    low = params.get("lower_quantile", 0.05)
                    high = params.get("upper_quantile", 0.95)
                    for c in cols:
                        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                            q_low = df[c].quantile(low)
                            q_high = df[c].quantile(high)
                            df[c] = df[c].clip(lower=q_low, upper=q_high)

                elif op == "round_numeric":
                    cols = params.get("columns", [])
                    decimals = params.get("decimals", 2)
                    for c in cols:
                        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                            df[c] = df[c].round(decimals)

            # Save cleaned version as a new dataset
            new_name = f"cleaned_{dataset.name}"
            # Ensure it doesn't get recursive 'cleaned_cleaned_'
            if dataset.name.startswith("cleaned_"):
                new_name = dataset.name

            buf = io.BytesIO()
            if dataset.file_format == "csv":
                df.to_csv(buf, index=False)
            elif dataset.file_format in ["xlsx", "xls"]:
                df.to_excel(buf, index=False)
            elif dataset.file_format == "json":
                df.to_json(buf)
            buf.seek(0)

            content_file = ContentFile(buf.read(), name=new_name)

            new_dataset = ProjectDataset.objects.create(
                project=dataset.project,
                file=content_file,
                name=new_name,
                parent=dataset,
                is_cleaned=True,
                row_count=len(df),
                column_count=len(df.columns),
                file_format=dataset.file_format,
            )

            # Return the preview of the NEW dataset
            return Response(self._get_preview_response(new_dataset, df))

        except Exception as e:
            return Response(
                {"detail": f"Cleaning failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def analyze(self, request, pk=None):
        """
        Perform smart analysis: Correlation Matrix and Missing Value Analysis.
        """
        dataset = self.get_object()
        file_path = dataset.file.path

        try:
            # Load full dataframe
            if dataset.file_format == "csv":
                df = pd.read_csv(file_path)
            elif dataset.file_format in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path)
            else:
                return Response(
                    {"detail": "Unsupported format for analysis."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 1. Correlation Matrix (Numeric only)
            numeric_df = df.select_dtypes(include=[np.number])
            # Drop columns with zero variance (all same values)
            numeric_df = numeric_df.loc[:, (numeric_df.nunique() > 1)]

            corr_matrix = {}
            if not numeric_df.empty:
                # Use spearman to capture non-linear but monotonic relationships
                corr_data = numeric_df.corr(method="spearman").round(3)
                corr_matrix = corr_data.to_dict()

            # 2. Missing Value Distribution
            null_counts = df.isnull().sum()
            null_pct = (null_counts / len(df) * 100).round(2)
            missing_analysis = {
                col: {"count": int(count), "percentage": float(null_pct[col])}
                for col, count in null_counts.to_dict().items()
            }

            # 3. Quick Outlier Detection (Z-Score method for numeric)
            outliers = {}
            for col in numeric_df.columns:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_count = int((z_scores > 3).sum())
                if outlier_count > 0:
                    outliers[col] = outlier_count

            analysis_result = {
                "correlations": corr_matrix,
                "missing_values": missing_analysis,
                "outlier_summary": outliers,
                "metadata": {
                    "analyzed_at": uuid.uuid4().hex[:8],
                    "numeric_cols_count": len(numeric_df.columns),
                },
            }

            return Response(analysis_result)

        except Exception as e:
            return Response(
                {"detail": f"Analysis failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
