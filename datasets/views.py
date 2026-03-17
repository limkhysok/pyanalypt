import uuid
import io
import pandas as pd
import numpy as np
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.files.base import ContentFile
from django.http import HttpResponse
from .models import Dataset
from .serializers import DatasetSerializer
from issues.models import Issue
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.metrics import silhouette_score, mean_squared_error, r2_score
import json
from google import genai
from django.conf import settings

# Error Messages
ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class CreateDatasetView(generics.CreateAPIView):
    """
    Handle file uploads (Drag and Drop / File Input).
    Expects multipart/form-data.
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PasteDatasetView(generics.GenericAPIView):
    """
    Handle raw text paste (CSV or JSON string).
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        raw_data = request.data.get("raw_data")
        file_name = request.data.get("name", f"pasted_data_{uuid.uuid4().hex[:8]}")
        data_format = request.data.get("format", "csv").lower()

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
            data={
                "file": content_file,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DatasetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual datasets (Read, Update, Delete).
    Includes a 'preview' action and 'clean' action for transformations.
    """

    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(user=self.request.user)

    def _get_preview_response(self, dataset, df, row_limit=10):
        """Helper to generate preview structure from a dataframe."""
        preview_df = df.head(row_limit)
        dtypes = df.dtypes.apply(lambda x: str(x)).to_dict()
        summary = {}

        # Numeric summary
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if not numeric_cols.empty:
            # describe().to_json ensures numpy types are handled
            summary_json = df[numeric_cols].describe().to_json()
            summary = json.loads(summary_json)

        # rows to_json handles NaNs (converts to null) and numpy types
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
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(self._get_preview_response(dataset, df, row_limit))

        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        """Include preview data in detail view if requested."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Load first 100 rows by default for detail view
        try:
            df = self._load_dataframe(instance.file.path, instance.file_format)
            if df is not None:
                data["data_preview"] = self._get_preview_response(
                    instance, df, row_limit=50
                )
        except Exception:
            data["data_preview"] = None

        return Response(data)

    @action(detail=True, methods=["patch"])
    def update_cell(self, request, pk=None):
        """Manual edit: change a single value in the dataset."""
        dataset = self.get_object()
        row_idx = request.data.get("row_index")
        col_name = request.data.get("column_name")
        new_val = request.data.get("value")

        if row_idx is None or not col_name:
            return Response(
                {"detail": "row_index and column_name required."}, status=400
            )

        try:
            df = self._load_dataframe(dataset.file.path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=400)

            if col_name not in df.columns:
                return Response(
                    {"detail": f"Column '{col_name}' not found."}, status=400
                )

            # Simple manual update
            df.at[int(row_idx), col_name] = new_val

            # Save back to file
            buf = self._save_dataframe_to_buffer(df, dataset.file_format)
            dataset.file.save(dataset.file.name, ContentFile(buf.read()), save=False)
            dataset.save()

            return Response(self._get_preview_response(dataset, df))

        except Exception as e:
            return Response({"detail": f"Failed to update cell: {str(e)}"}, status=500)

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
            # Load full dataframe
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response(
                    {"detail": f"{ERR_UNSUPPORTED_FORMAT} for cleaning."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Apply transformations
            df = self._apply_cleaning_operations(df, pipeline)

            # Save cleaned version
            new_file_name = self._generate_cleaned_name(dataset.file_name)
            buf = self._save_dataframe_to_buffer(df, dataset.file_format)
            content_file = ContentFile(buf.read(), name=new_file_name)

            new_dataset = Dataset.objects.create(
                user=dataset.user,
                file=content_file,
                file_name=new_file_name,
                parent=dataset,
                is_cleaned=True,
                file_format=dataset.file_format,
            )

            return Response(self._get_preview_response(new_dataset, df))

        except Exception as e:
            return Response(
                {"detail": f"Cleaning failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _load_dataframe(self, path, file_format):
        if file_format == "csv":
            return pd.read_csv(path)
        if file_format in ["xlsx", "xls"]:
            return pd.read_excel(path)
        if file_format == "json":
            return pd.read_json(path)
        return None

    def _apply_cleaning_operations(self, df, pipeline):
        for step in pipeline:
            op = step.get("operation")
            params = step.get("params", {})
            df = self._execute_operation(df, op, params)
        return df

    def _execute_operation(self, df, op, params):
        if op == "handle_na":
            return self._op_handle_na(df, params)
        if op == "drop_duplicates":
            return self._op_drop_duplicates(df, params)
        if op == "astype":
            return self._op_astype(df, params)
        if op == "drop_columns":
            return self._op_drop_columns(df, params)
        if op == "rename_columns":
            return df.rename(columns=params.get("mapping", {}))
        if op == "trim_strings":
            return self._op_trim_strings(df, params)
        if op == "case_convert":
            return self._op_case_convert(df, params)
        if op == "replace_value":
            return self._op_replace_value(df, params)
        if op == "outlier_clip":
            return self._op_outlier_clip(df, params)
        if op == "round_numeric":
            return self._op_round_numeric(df, params)
        return df

    def _op_handle_na(self, df, params):
        cols = params.get("columns", "all")
        strategy = params.get("strategy", "drop")
        target_cols = df.columns if cols == "all" else cols
        if strategy == "drop":
            return df.dropna(subset=target_cols)
        if strategy == "fill_zero":
            df[target_cols] = df[target_cols].fillna(0)
        elif strategy == "fill_mean":
            for c in target_cols:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].mean())
        elif strategy == "fill_median":
            for c in target_cols:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].median())
        return df

    def _op_drop_duplicates(self, df, params):
        cols = params.get("columns", "all")
        subset = None if cols == "all" else cols
        return df.drop_duplicates(subset=subset)

    def _op_astype(self, df, params):
        col, target_type = params.get("column"), params.get("target_type")
        if col not in df.columns:
            return df
        if target_type == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        elif target_type == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
        elif target_type == "string":
            df[col] = df[col].astype(str)
        elif target_type == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def _op_drop_columns(self, df, params):
        cols = params.get("columns", [])
        if len(cols) < len(df.columns):
            return df.drop(columns=[c for c in cols if c in df.columns])
        return df

    def _op_trim_strings(self, df, params):
        cols = params.get("columns", "all")
        target_cols = df.columns if cols == "all" else cols
        for c in target_cols:
            if pd.api.types.is_object_dtype(df[c]):
                df[c] = df[c].astype(str).str.strip()
        return df

    def _op_case_convert(self, df, params):
        cols, case_type = params.get("columns", []), params.get("case", "lower")
        for c in cols:
            if c in df.columns and pd.api.types.is_object_dtype(df[c]):
                if case_type == "lower":
                    df[c] = df[c].astype(str).str.lower()
                elif case_type == "upper":
                    df[c] = df[c].astype(str).str.upper()
                elif case_type == "title":
                    df[c] = df[c].astype(str).str.title()
        return df

    def _op_replace_value(self, df, params):
        col, old_v, new_v = (
            params.get("column"),
            params.get("old_value"),
            params.get("new_value"),
        )
        if col in df.columns:
            df[col] = df[col].replace(old_v, new_v)
        return df

    def _op_outlier_clip(self, df, params):
        cols = params.get("columns", [])
        low, high = (
            params.get("lower_quantile", 0.05),
            params.get("upper_quantile", 0.95),
        )
        for c in cols:
            if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                q_low, q_high = df[c].quantile(low), df[c].quantile(high)
                df[c] = df[c].clip(lower=q_low, upper=q_high)
        return df

    def _op_round_numeric(self, df, params):
        cols, decimals = params.get("columns", []), params.get("decimals", 2)
        for c in cols:
            if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
                df[c] = df[c].round(decimals)
        return df

    def _generate_cleaned_name(self, original_file_name):
        return (
            original_file_name
            if original_file_name.startswith("cleaned_")
            else f"cleaned_{original_file_name}"
        )

    def _save_dataframe_to_buffer(self, df, file_format):
        buf = io.BytesIO()
        if file_format == "csv":
            df.to_csv(buf, index=False)
        elif file_format in ["xlsx", "xls"]:
            df.to_excel(buf, index=False)
        elif file_format == "json":
            df.to_json(buf)
        buf.seek(0)
        return buf

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
                    {"detail": f"{ERR_UNSUPPORTED_FORMAT} for analysis."},
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

    @action(detail=True, methods=["get"])
    def query(self, request, pk=None):
        """
        Analyst manual identification of issues by filtering.
        Example: ?column=price&operator=lt&value=0
        """
        dataset = self.get_object()
        file_path = dataset.file.path

        col = request.query_params.get("column")
        op = request.query_params.get("operator", "eq")
        val = request.query_params.get("value")

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=400)

            if col and val:
                df = self._apply_query_filter(df, col, op, val)

            return Response(self._get_preview_response(dataset, df))
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)

    def _apply_query_filter(self, df, col, op, val):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")

        try:
            # Handle numeric conversion if needed
            if pd.api.types.is_numeric_dtype(df[col]):
                query_val = float(val)
            else:
                query_val = val

            if op == "eq":
                return df[df[col] == query_val]
            elif op == "gt":
                return df[df[col] > query_val]
            elif op == "lt":
                return df[df[col] < query_val]
            elif op == "contains":
                return df[df[col].astype(str).str.contains(val, case=False)]
        except (ValueError, TypeError):
            raise ValueError("Invalid filter values for the selected column type.")

        return df

    @action(detail=True, methods=["post"])
    def diagnose(self, request, pk=None):
        """
        POST /datasets/{id}/diagnose/
        Body: {"method": "pandas"} | {"method": "gemini"} | {"method": "both"} (default)

        Runs detector scans safely and returns issues grouped by column.
        Existing issues are replaced only for detectors that run successfully.
        """
        dataset = self.get_object()
        method = request.data.get("method", "both").lower()

        if method not in ("pandas", "gemini", "both"):
            return Response(
                {"detail": "Invalid method. Choose 'pandas', 'gemini', or 'both'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            df = self._load_dataframe(dataset.file.path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=400)

            warnings = []
            any_scan_succeeded = False

            if method in ("pandas", "both"):
                # Refresh only Pandas-generated auto issues.
                dataset.issues.filter(
                    is_user_modified=False,
                    detected_by=Issue.DETECTED_BY_PANDAS,
                ).delete()
                self._check_missing_values(dataset, df)
                self._check_duplicates(dataset, df)
                self._check_type_inconsistencies(dataset, df)
                self._check_outliers(dataset, df)
                any_scan_succeeded = True

            if method in ("gemini", "both"):
                ai_ok, ai_error = self._run_ai_diagnostic(dataset, df)
                if ai_ok:
                    any_scan_succeeded = True
                elif ai_error:
                    warnings.append(ai_error)

            issues_qs = dataset.issues.all().order_by("column_name", "-detected_at")

            if any_scan_succeeded and not issues_qs.exists():
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_SEMANTIC_ERROR,
                    description="Dataset is healthy! No major issues found.",
                    severity=Issue.SEVERITY_LOW,
                    suggested_fix="Your data looks ready for analysis.",
                    detected_by=Issue.DETECTED_BY_PANDAS,
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
                    "severity": issue.severity,
                    "suggested_fix": issue.suggested_fix,
                    "detected_by": issue.detected_by,
                    "is_user_modified": issue.is_user_modified,
                    "is_resolved": issue.is_resolved,
                })

            return Response({
                "dataset_id": dataset.id,
                "method": method,
                "total_issues": issues_qs.count(),
                "issues_by_column": grouped,
                "warnings": warnings,
            })

        except Exception as e:
            return Response({"detail": f"Diagnosis failed: {str(e)}"}, status=500)

    def _check_missing_values(self, dataset, df):
        for col, count in df.isnull().sum().to_dict().items():
            if count > 0:
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_MISSING_VALUE,
                    column_name=col,
                    affected_rows=int(count),
                    description=f"'{col}' has {count} missing value(s).",
                    severity=Issue.SEVERITY_MEDIUM,
                    suggested_fix="Use the 'handle_na' operation to fill or drop these rows.",
                    detected_by=Issue.DETECTED_BY_PANDAS,
                )

    def _check_duplicates(self, dataset, df):
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            Issue.objects.create(
                dataset=dataset,
                issue_type=Issue.TYPE_DUPLICATE,
                affected_rows=dup_count,
                description=f"Found {dup_count} exact duplicate row(s) across the dataset.",
                severity=Issue.SEVERITY_LOW,
                suggested_fix="Use the 'drop_duplicates' operation.",
                detected_by=Issue.DETECTED_BY_PANDAS,
            )

    def _check_type_inconsistencies(self, dataset, df):
        for col in df.columns:
            types = df[col].dropna().apply(type).unique()
            if len(types) > 1:
                type_names = [t.__name__ for t in types]
                Issue.objects.create(
                    dataset=dataset,
                    issue_type=Issue.TYPE_TYPE_MISMATCH,
                    column_name=col,
                    description=f"'{col}' contains mixed types: {', '.join(type_names)}.",
                    severity=Issue.SEVERITY_HIGH,
                    suggested_fix="Use the 'astype' operation to standardize this column.",
                    detected_by=Issue.DETECTED_BY_PANDAS,
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
                        severity=Issue.SEVERITY_LOW,
                        suggested_fix="Use 'outlier_clip' to bound these values.",
                        detected_by=Issue.DETECTED_BY_PANDAS,
                    )

    def _run_ai_diagnostic(self, dataset, df):
        if not settings.GOOGLE_AI_API_KEY:
            return False, "Gemini scan skipped: GOOGLE_AI_API_KEY is not configured."
        try:
            client = genai.Client(api_key=settings.GOOGLE_AI_API_KEY)
            sample_data = df.head(10).to_csv(index=False)
            prompt = (
                f"Analyze this dataset schema and 10-row sample for 'dirty data' or semantic errors. "
                f"Columns: {list(df.columns)}\n\n{sample_data}\n\n"
                "Provide a bulleted list of potential issues per column. Be concise."
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            # Replace only Gemini-generated auto issues after a successful AI call.
            dataset.issues.filter(
                is_user_modified=False,
                detected_by=Issue.DETECTED_BY_GEMINI,
            ).delete()

            Issue.objects.create(
                dataset=dataset,
                issue_type=Issue.TYPE_SEMANTIC_ERROR,
                description="Gemini AI Semantic Analysis",
                suggested_fix=response.text,
                severity=Issue.SEVERITY_LOW,
                detected_by=Issue.DETECTED_BY_GEMINI,
            )
            return True, None
        except Exception as e:
            err = str(e)
            print(f"AI Diagnostic failed: {err}")
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                return False, "Gemini quota exceeded. Existing Gemini issues were kept unchanged."
            return False, "Gemini scan failed. Existing Gemini issues were kept unchanged."

    @action(detail=True, methods=["post"])
    def train(self, request, pk=None):
        """
        Train a Machine Learning model.
        Supports: 'kmeans', 'linear_regression'
        """
        dataset = self.get_object()
        file_path = dataset.file.path
        model_type = request.data.get("model_type", "kmeans")
        features, target = request.data.get("features", []), request.data.get("target")

        if not features:
            return Response(
                {"detail": "Features required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response(
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            df = df.dropna(subset=features + ([target] if target else []))
            if df.empty:
                return Response(
                    {"detail": "Empty dataset after dropping NAs."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not all(pd.api.types.is_numeric_dtype(df[col]) for col in features):
                return Response(
                    {"detail": "Features must be numeric."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            X = df[features]
            if model_type == "kmeans":
                return self._train_kmeans(
                    dataset, df, X, request.data.get("params", {})
                )
            if model_type == "linear_regression":
                return self._train_linear_regression(df, X, target)

            return Response(
                {"detail": f"Model '{model_type}' not supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"detail": f"Training failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _train_kmeans(self, dataset, df, X, params):
        n_clusters = int(params.get("n_clusters", 3))
        model = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = model.fit_predict(X)
        df["cluster_id"] = clusters

        if len(set(clusters)) > 1:
            score = silhouette_score(X, clusters, random_state=42)
        else:
            score = 0.0

        new_file_name = f"clustered_{dataset.file_name}"
        buf = self._save_dataframe_to_buffer(df, dataset.file_format)
        content_file = ContentFile(buf.read(), name=new_file_name)

        new_dataset = Dataset.objects.create(
            user=dataset.user,
            file=content_file,
            file_name=new_file_name,
            parent=dataset,
            is_cleaned=True,
            file_format=dataset.file_format,
        )

        return Response(
            {
                "evaluation": {
                    "silhouette_score": round(score, 4),
                    "model": "KMeans",
                    "n_clusters": n_clusters,
                },
                "new_dataset": self._get_preview_response(new_dataset, df),
            }
        )

    def _train_linear_regression(self, df, X, target):
        if not target or not pd.api.types.is_numeric_dtype(df[target]):
            return Response(
                {"detail": "Numeric target required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        y = df[target]
        model = LinearRegression()
        model.fit(X, y)
        predictions = model.predict(X)

        mse, r2 = mean_squared_error(y, predictions), r2_score(y, predictions)
        coeffs = dict(zip(X.columns, model.coef_))

        return Response(
            {
                "evaluation": {
                    "model": "Linear Regression",
                    "mean_squared_error": round(mse, 4),
                    "r2_score": round(r2, 4),
                    "coefficients": {k: round(v, 4) for k, v in coeffs.items()},
                    "intercept": round(model.intercept_, 4),
                }
            }
        )

    @action(detail=True, methods=["post"])
    def visualize(self, request, pk=None):
        """
        Return structured data for charts.
        Supports: scatter, bar, line, pie
        """
        dataset = self.get_object()
        file_path = dataset.file.path

        chart_type = request.data.get("chart_type", "scatter")
        x_axis, y_axis, category_col = (
            request.data.get("x_axis"),
            request.data.get("y_axis"),
            request.data.get("category_col"),
        )

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response(
                    {"detail": ERR_UNSUPPORTED_FORMAT},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            required_cols = [c for c in [x_axis, y_axis, category_col] if c]
            if not required_cols:
                return Response(
                    {"detail": "At least one axis or category column is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            df = df.dropna(subset=required_cols)
            return Response(
                self._build_chart_data(df, chart_type, x_axis, y_axis, category_col)
            )

        except Exception as e:
            return Response(
                {"detail": f"Visualization generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _build_chart_data(self, df, chart_type, x_axis, y_axis, category_col):
        if chart_type in ["scatter", "line"]:
            return self._build_scatter_line(df, x_axis, y_axis, category_col)
        if chart_type == "bar":
            return self._build_bar(df, x_axis, y_axis)
        if chart_type == "pie":
            return self._build_pie(df, y_axis, category_col)
        raise ValueError("Unsupported chart type")

    def _build_scatter_line(self, df, x_axis, y_axis, category_col):
        if not x_axis or not y_axis:
            raise ValueError("x_axis and y_axis are required")
        if category_col:
            series = []
            for name, group in df.groupby(category_col):
                series.append(
                    {"name": str(name), "data": group[[x_axis, y_axis]].values.tolist()}
                )
            return {"series": series}
        return {
            "series": [{"name": "Data", "data": df[[x_axis, y_axis]].values.tolist()}]
        }

    def _build_bar(self, df, x_axis, y_axis):
        if not x_axis or not y_axis:
            raise ValueError("x_axis and y_axis are required")
        grouped = df.groupby(x_axis)[y_axis].sum().reset_index()
        return {
            "xAxis": grouped[x_axis].tolist(),
            "series": [{"name": y_axis, "data": grouped[y_axis].tolist()}],
        }

    def _build_pie(self, df, y_axis, category_col):
        if not category_col or not y_axis:
            raise ValueError("category_col and y_axis are required")
        grouped = df.groupby(category_col)[y_axis].sum().reset_index()
        return {
            "series": [
                {
                    "data": [
                        {"name": str(row[category_col]), "value": row[y_axis]}
                        for _, row in grouped.iterrows()
                    ]
                }
            ]
        }

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """
        Export the dataset to a requested format (csv, json, excel).
        """
        dataset = self.get_object()
        file_path = dataset.file.path
        export_format = request.query_params.get("format", dataset.file_format).lower()

        try:
            if dataset.file_format == "csv":
                df = pd.read_csv(file_path)
            elif dataset.file_format in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path)
            else:
                return Response(
                    {"detail": "Unsupported input format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response = HttpResponse()
            if export_format == "csv":
                response["Content-Disposition"] = (
                    f'attachment; filename="{dataset.file_name.split(".")[0]}.csv"'
                )
                response["Content-Type"] = "text/csv"
                df.to_csv(response, index=False)
            elif export_format in ["xlsx", "excel"]:
                response["Content-Disposition"] = (
                    f'attachment; filename="{dataset.file_name.split(".")[0]}.xlsx"'
                )
                response["Content-Type"] = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                df.to_excel(response, index=False)
            elif export_format == "json":
                response["Content-Disposition"] = (
                    f'attachment; filename="{dataset.file_name.split(".")[0]}.json"'
                )
                response["Content-Type"] = "application/json"
                df.to_json(response, orient="records")
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
