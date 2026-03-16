import uuid
import io
import pandas as pd
import numpy as np
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.files.base import ContentFile
from django.http import HttpResponse
from .models import ProjectDataset
from .serializers import ProjectDatasetSerializer
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.metrics import silhouette_score, mean_squared_error, r2_score

# Error Messages
ERR_UNSUPPORTED_FORMAT = "Unsupported format."


class CreateDatasetView(generics.CreateAPIView):
    """
    Handle file uploads (Drag and Drop / File Input).
    Expects multipart/form-data.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PasteDatasetView(generics.GenericAPIView):
    """
    Handle raw text paste (CSV or JSON string).
    """

    serializer_class = ProjectDatasetSerializer
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
                "name": file_name,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectDatasetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual datasets (Read, Update, Delete).
    Includes a 'preview' action and 'clean' action for transformations.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProjectDataset.objects.filter(user=self.request.user)

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
                    {"detail": ERR_UNSUPPORTED_FORMAT},
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
            new_name = self._generate_cleaned_name(dataset.name)
            buf = self._save_dataframe_to_buffer(df, dataset.file_format)
            content_file = ContentFile(buf.read(), name=new_name)

            new_dataset = ProjectDataset.objects.create(
                user=dataset.user,
                file=content_file,
                name=new_name,
                parent=dataset,
                is_cleaned=True,
                row_count=len(df),
                column_count=len(df.columns),
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
        col, old_v, new_v = params.get("column"), params.get("old_value"), params.get("new_value")
        if col in df.columns:
            df[col] = df[col].replace(old_v, new_v)
        return df

    def _op_outlier_clip(self, df, params):
        cols = params.get("columns", [])
        low, high = params.get("lower_quantile", 0.05), params.get("upper_quantile", 0.95)
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

    def _generate_cleaned_name(self, original_name):
        return original_name if original_name.startswith("cleaned_") else f"cleaned_{original_name}"

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
            return Response({"detail": "Features required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            df = df.dropna(subset=features + ([target] if target else []))
            if df.empty:
                return Response({"detail": "Empty dataset after dropping NAs."}, status=status.HTTP_400_BAD_REQUEST)

            if not all(pd.api.types.is_numeric_dtype(df[col]) for col in features):
                return Response({"detail": "Features must be numeric."}, status=status.HTTP_400_BAD_REQUEST)

            X = df[features]
            if model_type == "kmeans":
                return self._train_kmeans(dataset, df, X, request.data.get("params", {}))
            if model_type == "linear_regression":
                return self._train_linear_regression(df, X, target)

            return Response({"detail": f"Model '{model_type}' not supported."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"detail": f"Training failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _train_kmeans(self, dataset, df, X, params):
        n_clusters = int(params.get("n_clusters", 3))
        model = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = model.fit_predict(X)
        df["cluster_id"] = clusters

        if len(set(clusters)) > 1:
            score = silhouette_score(X, clusters, random_state=42)
        else:
            score = 0.0

        new_name = f"clustered_{dataset.name}"
        buf = self._save_dataframe_to_buffer(df, dataset.file_format)
        content_file = ContentFile(buf.read(), name=new_name)

        new_dataset = ProjectDataset.objects.create(
            user=dataset.user,
            file=content_file,
            name=new_name,
            parent=dataset,
            is_cleaned=True,
            row_count=len(df),
            column_count=len(df.columns),
            file_format=dataset.file_format,
        )

        return Response({
            "evaluation": {"silhouette_score": round(score, 4), "model": "KMeans", "n_clusters": n_clusters},
            "new_dataset": self._get_preview_response(new_dataset, df)
        })

    def _train_linear_regression(self, df, X, target):
        if not target or not pd.api.types.is_numeric_dtype(df[target]):
            return Response({"detail": "Numeric target required."}, status=status.HTTP_400_BAD_REQUEST)

        y = df[target]
        model = LinearRegression()
        model.fit(X, y)
        predictions = model.predict(X)

        mse, r2 = mean_squared_error(y, predictions), r2_score(y, predictions)
        coeffs = dict(zip(X.columns, model.coef_))

        return Response({
            "evaluation": {
                "model": "Linear Regression",
                "mean_squared_error": round(mse, 4),
                "r2_score": round(r2, 4),
                "coefficients": {k: round(v, 4) for k, v in coeffs.items()},
                "intercept": round(model.intercept_, 4),
            }
        })

    @action(detail=True, methods=["post"])
    def visualize(self, request, pk=None):
        """
        Return structured data for charts.
        Supports: scatter, bar, line, pie
        """
        dataset = self.get_object()
        file_path = dataset.file.path

        chart_type = request.data.get("chart_type", "scatter")
        x_axis, y_axis, category_col = request.data.get("x_axis"), request.data.get("y_axis"), request.data.get("category_col")

        try:
            df = self._load_dataframe(file_path, dataset.file_format)
            if df is None:
                return Response({"detail": ERR_UNSUPPORTED_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

            required_cols = [c for c in [x_axis, y_axis, category_col] if c]
            if not required_cols:
                return Response({"detail": "At least one axis or category column is required."}, status=status.HTTP_400_BAD_REQUEST)

            df = df.dropna(subset=required_cols)
            return Response(self._build_chart_data(df, chart_type, x_axis, y_axis, category_col))

        except Exception as e:
            return Response({"detail": f"Visualization generation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                series.append({"name": str(name), "data": group[[x_axis, y_axis]].values.tolist()})
            return {"series": series}
        return {"series": [{"name": "Data", "data": df[[x_axis, y_axis]].values.tolist()}]}

    def _build_bar(self, df, x_axis, y_axis):
        if not x_axis or not y_axis:
            raise ValueError("x_axis and y_axis are required")
        grouped = df.groupby(x_axis)[y_axis].sum().reset_index()
        return {"xAxis": grouped[x_axis].tolist(), "series": [{"name": y_axis, "data": grouped[y_axis].tolist()}]}

    def _build_pie(self, df, y_axis, category_col):
        if not category_col or not y_axis:
            raise ValueError("category_col and y_axis are required")
        grouped = df.groupby(category_col)[y_axis].sum().reset_index()
        return {"series": [{"data": [{"name": str(row[category_col]), "value": row[y_axis]} for _, row in grouped.iterrows()]}]}

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
                    f'attachment; filename="{dataset.name.split(".")[0]}.csv"'
                )
                response["Content-Type"] = "text/csv"
                df.to_csv(response, index=False)
            elif export_format in ["xlsx", "excel"]:
                response["Content-Disposition"] = (
                    f'attachment; filename="{dataset.name.split(".")[0]}.xlsx"'
                )
                response["Content-Type"] = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                df.to_excel(response, index=False)
            elif export_format == "json":
                response["Content-Disposition"] = (
                    f'attachment; filename="{dataset.name.split(".")[0]}.json"'
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
