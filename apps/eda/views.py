from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.data_engine import (
    CORRELATION_METHODS,
    OUTLIER_METHODS,
    apply_stored_casts,
    eda_correlation,
    eda_crosstab,
    eda_distribution,
    eda_missing_heatmap,
    eda_outlier_summary,
    eda_pairwise,
    eda_value_counts,
    get_cached_dataframe,
)
from apps.datasets.models import Dataset

_DEFAULT_BINS = 20
_MAX_BINS = 100
_DEFAULT_SAMPLE = 500
_MAX_SAMPLE = 5000
_DEFAULT_TOP_N = 20
_MAX_TOP_N = 100
_MAX_CROSSTAB_CARDINALITY = 50


def _load_df(dataset_id, request):
    """
    Fetch Dataset, verify ownership, load and apply casts.
    Returns (error_response, None) on failure or (None, (df, dataset)).
    """
    try:
        dataset = Dataset.objects.get(pk=dataset_id, user=request.user)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset not found."}, status=404), None

    df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
    if df is None:
        return Response({"error": "Could not load dataset file."}, status=500), None

    if dataset.column_casts:
        df = apply_stored_casts(df, dataset.column_casts)

    return None, (df, dataset)


def _parse_columns_param(raw, df, require_numeric=False):
    """
    Validate a list of column names against df.
    Returns (error_str, None) or (None, validated_list).
    """
    if not raw or not isinstance(raw, list):
        return "columns must be a non-empty list.", None

    missing = [c for c in raw if c not in df.columns]
    if missing:
        return f"Columns not found: {missing}", None

    if require_numeric:
        non_numeric = [c for c in raw if not hasattr(df[c], "dtype") or
                       df[c].dtype.kind not in "iufcb"]
        if non_numeric:
            return f"Columns must be numeric: {non_numeric}", None

    return None, raw


class EDAViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/correlation")
    def correlation(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        columns_raw = request.query_params.getlist("columns")
        method = request.query_params.get("method", "pearson")

        if method not in CORRELATION_METHODS:
            return Response(
                {"error": f"method must be one of {CORRELATION_METHODS}."},
                status=400,
            )

        if columns_raw:
            col_err, columns = _parse_columns_param(columns_raw, df, require_numeric=True)
            if col_err:
                return Response({"error": col_err}, status=400)
        else:
            columns = df.select_dtypes(include="number").columns.tolist()
            if not columns:
                return Response({"error": "No numeric columns found."}, status=400)

        data = eda_correlation(df, columns, method=method)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/distribution")
    def distribution(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        columns_raw = request.query_params.getlist("columns")
        try:
            bins = int(request.query_params.get("bins", _DEFAULT_BINS))
        except (ValueError, TypeError):
            return Response({"error": "bins must be an integer."}, status=400)

        if not (1 <= bins <= _MAX_BINS):
            return Response({"error": f"bins must be between 1 and {_MAX_BINS}."}, status=400)

        if columns_raw:
            col_err, columns = _parse_columns_param(columns_raw, df, require_numeric=True)
            if col_err:
                return Response({"error": col_err}, status=400)
        else:
            columns = df.select_dtypes(include="number").columns.tolist()
            if not columns:
                return Response({"error": "No numeric columns found."}, status=400)

        data = eda_distribution(df, columns, bins=bins)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/value-counts")
    def value_counts(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        columns_raw = request.query_params.getlist("columns")
        try:
            top_n = int(request.query_params.get("top_n", _DEFAULT_TOP_N))
        except (ValueError, TypeError):
            return Response({"error": "top_n must be an integer."}, status=400)

        if not (1 <= top_n <= _MAX_TOP_N):
            return Response({"error": f"top_n must be between 1 and {_MAX_TOP_N}."}, status=400)

        if columns_raw:
            col_err, columns = _parse_columns_param(columns_raw, df)
            if col_err:
                return Response({"error": col_err}, status=400)
        else:
            columns = df.columns.tolist()

        data = eda_value_counts(df, columns, top_n=top_n)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/crosstab")
    def crosstab(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        col_a = request.query_params.get("col_a")
        col_b = request.query_params.get("col_b")

        if not col_a or not col_b:
            return Response({"error": "col_a and col_b are required."}, status=400)

        missing = [c for c in (col_a, col_b) if c not in df.columns]
        if missing:
            return Response({"error": f"Columns not found: {missing}"}, status=400)

        for col_name, col in ((col_a, df[col_a]), (col_b, df[col_b])):
            if col.nunique() > _MAX_CROSSTAB_CARDINALITY:
                return Response(
                    {
                        "error": (
                            f"'{col_name}' has {col.nunique()} unique values — "
                            f"crosstab is limited to {_MAX_CROSSTAB_CARDINALITY}."
                        )
                    },
                    status=400,
                )

        normalize_raw = request.query_params.get("normalize", "false").lower()
        normalize = normalize_raw in ("true", "1", "yes")

        data = eda_crosstab(df, col_a, col_b, normalize=normalize)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/outlier-summary")
    def outlier_summary(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        method = request.query_params.get("method", "iqr")
        if method not in OUTLIER_METHODS:
            return Response(
                {"error": f"method must be one of {OUTLIER_METHODS}."},
                status=400,
            )

        try:
            threshold = float(request.query_params.get("threshold", 1.5))
        except (ValueError, TypeError):
            return Response({"error": "threshold must be a number."}, status=400)

        if threshold <= 0:
            return Response({"error": "threshold must be > 0."}, status=400)

        data = eda_outlier_summary(df, method=method, threshold=threshold)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/missing-heatmap")
    def missing_heatmap(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        data = eda_missing_heatmap(df)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<dataset_id>[^/.]+)/pairwise")
    def pairwise(self, request, dataset_id=None):
        err, result = _load_df(dataset_id, request)
        if err:
            return err
        df, _ = result

        col_x = request.query_params.get("col_x")
        col_y = request.query_params.get("col_y")

        if not col_x or not col_y:
            return Response({"error": "col_x and col_y are required."}, status=400)

        missing = [c for c in (col_x, col_y) if c not in df.columns]
        if missing:
            return Response({"error": f"Columns not found: {missing}"}, status=400)

        try:
            sample = int(request.query_params.get("sample", _DEFAULT_SAMPLE))
        except (ValueError, TypeError):
            return Response({"error": "sample must be an integer."}, status=400)

        if not (1 <= sample <= _MAX_SAMPLE):
            return Response({"error": f"sample must be between 1 and {_MAX_SAMPLE}."}, status=400)

        data = eda_pairwise(df, col_x, col_y, sample=sample)
        return Response(data)
