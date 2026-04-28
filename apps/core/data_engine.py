import io
import logging

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _df_cache_key(dataset_id):
    return f"df:{dataset_id}"


def get_cached_dataframe(dataset_id, file_path, file_format):
    """
    Return a DataFrame from cache (Redis in prod, LocMemCache in dev), or load
    from disk on a miss and populate the cache with a 2-hour TTL.
    Falls back gracefully if the cache is unavailable.
    """
    key = _df_cache_key(dataset_id)
    blob = cache.get(key)
    if blob is not None:
        try:
            return pd.read_parquet(io.BytesIO(blob))
        except Exception:
            logger.warning("df cache deserialize failed for dataset %s — reloading", dataset_id)

    df = load_dataframe(file_path, file_format)
    if df is not None:
        try:
            buf = io.BytesIO()
            df.to_parquet(buf, index=True)
            cache.set(key, buf.getvalue(), timeout=settings.DATAFRAME_CACHE_TTL)
        except Exception:
            logger.warning("df cache set failed for dataset %s — serving uncached", dataset_id)
    return df


def invalidate_dataframe_cache(dataset_id):
    """Remove the cached DataFrame for a dataset (call after file mutation or deletion)."""
    cache.delete(_df_cache_key(dataset_id))


def load_dataframe(file_path, file_format):
    """
    Load a file into a DataFrame using the explicit file_format field.
    Supports: csv, xlsx, xls, json, parquet.
    Returns None on failure instead of raising, so callers can return 400.
    """
    try:
        fmt = file_format.lower()
        if fmt == "csv":
            return pd.read_csv(file_path)
        if fmt in ("xlsx", "xls"):
            return pd.read_excel(file_path)
        if fmt == "json":
            return pd.read_json(file_path)
        if fmt == "parquet":
            return pd.read_parquet(file_path)
    except Exception:
        logger.exception("Failed to load dataframe: %s (%s)", file_path, file_format)
    return None


SUPPORTED_CASTS = {
    "datetime",
    "numeric",
    "float",
    "integer",
    "string",
    "boolean",
    "category",
}


def validate_cast(series, target):
    """
    Check if casting 'series' to 'target' is safe or contains risks.
    Returns (status, message) where status is 'safe', 'warning', or 'error'.
    """
    if target == "integer" and pd.api.types.is_float_dtype(series):
        if (series.dropna() % 1 != 0).any():
            return (
                "warning",
                "Column contains decimal values that will be truncated during conversion.",
            )

    if target == "string":
        null_count = int(series.isna().sum())
        if null_count > 0:
            return (
                "warning",
                f"{null_count} null value(s) will become the literal string 'nan'.",
            )

    if target == "boolean":
        # Check if values are logically boolean (0/1, True/False, or strings thereof)
        # We allow common representations, otherwise warn about logical mismatch.
        valid_bool_values = {True, False, "0", "1", "True", "False", "true", "false"}
        # Convert to set for fast lookup, filtering out strings if they aren't in the list
        unique_vals = set(series.dropna().unique())
        # If any unique value is not in our set of "logical booleans"
        if not unique_vals.issubset(valid_bool_values):
            return (
                "warning",
                "Column contains values other than 0, 1, or True/False. Results may be unexpected.",
            )

    if target in ("numeric", "float", "integer", "datetime"):
        # Dry run to see how many new NaNs are created (parsing failures)
        original_nulls = int(series.isna().sum())
        try:
            # We use a copy for the dry run
            casted = apply_cast(series.copy(), target)
            new_nulls = int(casted.isna().sum())
            if new_nulls > original_nulls:
                diff = new_nulls - original_nulls
                pct = round((diff / len(series)) * 100, 1)
                return (
                    "warning",
                    f"Conversion failed for {diff} values ({pct}% of rows). These will become NULL.",
                )
        except Exception as e:
            return "error", f"Cast is fundamentally incompatible: {str(e)}"

    return "safe", "Conversion is safe."


def apply_cast(series, target):
    """Apply a single dtype cast to a pandas Series. Used by cast_columns view and apply_stored_casts."""
    if target == "datetime":
        return pd.to_datetime(series, errors="coerce")
    if target in ("numeric", "float"):
        return pd.to_numeric(series, errors="coerce")
    if target == "integer":
        return pd.to_numeric(series, errors="coerce").astype("Int64")
    if target == "string":
        return series.astype(str)
    if target == "boolean":
        return series.astype(bool)
    if target == "category":
        return series.astype("category")
    return series


def apply_stored_casts(df, column_casts):
    """
    Re-apply user-defined dtype overrides after loading from a flat file.
    column_casts is a dict of {column_name: target_type} stored on the Dataset model.
    Silently skips columns that no longer exist or fail to cast.
    """
    for col, target in column_casts.items():
        if col not in df.columns:
            continue
        try:
            df[col] = apply_cast(df[col], target)
        except Exception:
            logger.warning("apply_stored_casts: failed to cast %s → %s", col, target)
    return df


def save_dataframe(df, file_path, file_format):
    """
    Write a DataFrame back to disk in its original format.
    Returns True on success, False on failure or unsupported format.
    """
    fmt = file_format.lower()
    try:
        if fmt == "csv":
            df.to_csv(file_path, index=False)
        elif fmt in ("xlsx", "xls"):
            df.to_excel(file_path, index=False)
        elif fmt == "json":
            df.to_json(file_path, orient="records", indent=2)
        elif fmt == "parquet":
            df.to_parquet(file_path, index=False)
        else:
            return False
        return True
    except Exception:
        logger.exception("Failed to save dataframe: %s (%s)", file_path, file_format)
        return False


def update_cell(df, row_index, column, value):
    """
    Write a new value into df.at[row_index, column] with type-safe coercion.
    None sets the cell to NaN. Raises ValueError on dtype mismatch.
    Returns (updated_df, coerced_value).
    """
    dtype = df[column].dtype

    if value is None:
        df.at[row_index, column] = np.nan
        return df, None

    try:
        if pd.api.types.is_integer_dtype(dtype):
            coerced = int(value)
        elif pd.api.types.is_float_dtype(dtype):
            coerced = float(value)
        elif pd.api.types.is_bool_dtype(dtype):
            sv = str(value).lower()
            if sv in ("true", "1"):
                coerced = True
            elif sv in ("false", "0"):
                coerced = False
            else:
                raise ValueError(f"Cannot convert '{value}' to boolean.")
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            coerced = pd.to_datetime(value)
        else:
            coerced = str(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Cannot assign '{value}' to column '{column}' (dtype: {dtype})."
        ) from exc

    df.at[row_index, column] = coerced
    return df, coerced


def rename_column(df, old_name, new_name):
    """Rename a single column header. Returns the modified DataFrame."""
    return df.rename(columns={old_name: new_name})


def replace_values(df, replacements, columns=None):
    """
    Replace specific values across columns. None in replacements maps to np.nan.
    columns=None applies to all columns. Returns (updated_df, cells_replaced_count).
    """
    target_cols = columns if columns is not None else df.columns.tolist()
    pandas_replacements = {k: (np.nan if v is None else v) for k, v in replacements.items()}

    cells_replaced = 0
    for col in target_cols:
        if col not in df.columns:
            continue
        cells_replaced += int(df[col].isin(replacements.keys()).sum())
        df[col] = df[col].replace(pandas_replacements)

    return df, cells_replaced


def drop_nulls(df, axis, how="any", subset=None, thresh_pct=None):
    """
    Drop rows or columns containing nulls.

    axis="rows"    — drop rows where any/all values are null (how), optionally scoped to subset.
    axis="columns" — drop columns whose null % exceeds thresh_pct (0-100).

    Returns (updated_df, stats_dict).
    """
    if axis == "rows":
        rows_before = len(df)
        df = df.dropna(axis=0, how=how, subset=subset)
        return df, {
            "rows_before": rows_before,
            "rows_after": len(df),
            "rows_dropped": rows_before - len(df),
        }

    # axis == "columns"
    total_rows = len(df)
    if total_rows == 0:
        return df, {"columns_before": len(df.columns), "columns_after": len(df.columns), "columns_dropped": []}

    null_pcts = df.isnull().sum() / total_rows * 100
    cols_to_drop = null_pcts[null_pcts > thresh_pct].index.tolist()
    cols_before = len(df.columns)
    df = df.drop(columns=cols_to_drop)
    return df, {
        "columns_before": cols_before,
        "columns_after": len(df.columns),
        "columns_dropped": cols_to_drop,
    }


FILL_STRATEGIES = {"constant", "mean", "median", "mode", "ffill", "bfill"}


def _apply_fill(series, strategy, value=None):
    """
    Apply one fill strategy to a single Series.
    Returns the filled Series, or None if the column should be skipped.
    """
    if strategy == "constant":
        return series.fillna(value)
    if strategy in ("mean", "median"):
        if not pd.api.types.is_numeric_dtype(series):
            return None
        fill_val = series.mean() if strategy == "mean" else series.median()
        return series.fillna(fill_val)
    if strategy == "mode":
        mode_vals = series.mode()
        return None if mode_vals.empty else series.fillna(mode_vals.iloc[0])
    if strategy == "ffill":
        return series.ffill()
    if strategy == "bfill":
        return series.bfill()
    return series


def fill_nulls(df, strategy, columns=None, value=None):
    """
    Fill null values using the given strategy across target columns.
    mean/median silently skip non-numeric columns (reported in skipped_columns).
    Returns (updated_df, cells_filled, skipped_columns).
    """
    target_cols = columns if columns is not None else df.columns.tolist()
    cells_filled = 0
    skipped_columns = []

    for col in target_cols:
        if col not in df.columns:
            continue
        null_before = int(df[col].isna().sum())
        if null_before == 0:
            continue
        filled = _apply_fill(df[col], strategy, value)
        if filled is None:
            skipped_columns.append(col)
            continue
        df[col] = filled
        cells_filled += null_before - int(df[col].isna().sum())

    return df, cells_filled, skipped_columns


def normalize_columns(df):
    """
    Standardize column names to lowercase_with_underscores.
    Opt-in — not applied automatically by load_dataframe.
    """
    df.columns = (
        df.columns.astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
    )
    return df


SUPPORTED_FORMULAS = ("divide", "multiply", "add", "subtract")


def fill_derived(df, target, formula, operand_a, operand_b):
    """
    Fill nulls in `target` by computing `operand_a <formula> operand_b`.
    Only fills rows where target is null AND both operands are non-null (and
    non-zero for the denominator when formula is 'divide').
    Returns (df, cells_filled).
    """
    mask = df[target].isnull() & df[operand_a].notnull() & df[operand_b].notnull()

    if formula == "divide":
        mask = mask & (df[operand_b] != 0)
        result = df.loc[mask, operand_a] / df.loc[mask, operand_b]
    elif formula == "multiply":
        result = df.loc[mask, operand_a] * df.loc[mask, operand_b]
    elif formula == "add":
        result = df.loc[mask, operand_a] + df.loc[mask, operand_b]
    else:  # subtract
        result = df.loc[mask, operand_a] - df.loc[mask, operand_b]

    cells_filled = int(mask.sum())
    if cells_filled > 0:
        if pd.api.types.is_integer_dtype(df[target].dtype):
            result = result.round().astype("Int64")
        df.loc[mask, target] = result

    return df, cells_filled


def validate_formula(df, result_column, formula, operand_a, operand_b, tolerance=0.01):
    """
    Check whether result_column ≈ operand_a <formula> operand_b within tolerance.
    Only inspects rows where all three columns are non-null (and denominator != 0
    for divide). Returns a dict with error counts and up to 5 sample error rows.
    """
    mask = (
        df[result_column].notnull()
        & df[operand_a].notnull()
        & df[operand_b].notnull()
    )
    if formula == "divide":
        mask = mask & (df[operand_b] != 0)

    checked = df[mask]
    checked_count = len(checked)

    if checked_count == 0:
        return {
            "total_rows": len(df),
            "checked_rows": 0,
            "error_rows": 0,
            "error_pct": 0.0,
            "tolerance": tolerance,
            "sample_errors": [],
        }

    if formula == "divide":
        calculated = checked[operand_a] / checked[operand_b]
    elif formula == "multiply":
        calculated = checked[operand_a] * checked[operand_b]
    elif formula == "add":
        calculated = checked[operand_a] + checked[operand_b]
    else:  # subtract
        calculated = checked[operand_a] - checked[operand_b]

    diff = (calculated - checked[result_column]).abs()
    error_mask = diff > tolerance
    error_rows = checked[error_mask]
    error_count = len(error_rows)

    sample = []
    for idx, row in error_rows.head(5).iterrows():
        sample.append({
            "row_index": int(idx),
            operand_a: (row[operand_a].item() if hasattr(row[operand_a], "item") else row[operand_a]),
            operand_b: (row[operand_b].item() if hasattr(row[operand_b], "item") else row[operand_b]),
            result_column: (row[result_column].item() if hasattr(row[result_column], "item") else row[result_column]),
            "calculated": round(float(calculated[idx]), 4),
            "diff": round(float(diff[idx]), 4),
        })

    return {
        "total_rows": len(df),
        "checked_rows": checked_count,
        "error_rows": error_count,
        "error_pct": round(error_count / checked_count * 100, 1) if checked_count > 0 else 0.0,
        "tolerance": tolerance,
        "sample_errors": sample,
    }


def fix_formula_errors(df, target, formula, operand_a, operand_b, tolerance=0.01):
    """
    Find rows where target != operand_a <formula> operand_b (beyond tolerance)
    and overwrite target with the recomputed value.
    Only touches rows where all three columns are non-null (and denominator != 0
    for divide). Returns (df, cells_fixed).
    """
    mask = (
        df[target].notnull()
        & df[operand_a].notnull()
        & df[operand_b].notnull()
    )
    if formula == "divide":
        mask = mask & (df[operand_b] != 0)

    checked = df[mask]
    if checked.empty:
        return df, 0

    if formula == "divide":
        calculated = checked[operand_a] / checked[operand_b]
    elif formula == "multiply":
        calculated = checked[operand_a] * checked[operand_b]
    elif formula == "add":
        calculated = checked[operand_a] + checked[operand_b]
    else:  # subtract
        calculated = checked[operand_a] - checked[operand_b]

    diff = (calculated - checked[target]).abs()
    error_idx = diff[diff > tolerance].index
    cells_fixed = len(error_idx)

    if cells_fixed > 0:
        result = calculated[error_idx]
        if pd.api.types.is_integer_dtype(df[target].dtype):
            result = result.round().astype("Int64")
        df.loc[error_idx, target] = result

    return df, cells_fixed


def describe_dataframe(df):
    described = df.describe(include='all')
    result = {}
    for col in described.columns:
        col_stats = {}
        for stat, val in described[col].items():
            if pd.isna(val):
                continue
            col_stats[stat] = val.item() if hasattr(val, "item") else val
        result[col] = col_stats
    return result


OUTLIER_METHODS = ("iqr", "zscore")
OUTLIER_IMPUTE_STRATEGIES = ("mean", "median", "mode")
COLUMN_TRANSFORMS = ("log", "sqrt", "cbrt")


def _outlier_bounds(series, method, threshold):
    """
    Compute (lower, upper) bounds and a boolean outlier mask for a non-null Series.
    series must already have NaN dropped (use df[col].dropna() before calling).
    """
    if method == "iqr":
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr_val = q3 - q1
        lower = float(q1 - threshold * iqr_val)
        upper = float(q3 + threshold * iqr_val)
        return (series < lower) | (series > upper), lower, upper
    # zscore
    mean = float(series.mean())
    std = float(series.std())
    if std == 0:
        return pd.Series(False, index=series.index), mean, mean
    z = (series - mean) / std
    return z.abs() > threshold, mean - threshold * std, mean + threshold * std


def detect_outliers(df, columns, method="iqr", threshold=1.5):
    """
    Return per-column outlier stats and up to 5 sample rows. Read-only.
    """
    total_rows = len(df)
    result = {}
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            result[col] = {
                "outlier_count": 0, "outlier_pct": 0.0,
                "lower_bound": None, "upper_bound": None,
                "sample_outliers": [],
            }
            continue
        mask, lower, upper = _outlier_bounds(valid, method, threshold)
        full_mask = pd.Series(False, index=df.index)
        full_mask[valid.index] = mask.values
        count = int(full_mask.sum())
        sample_rows = []
        for idx in full_mask[full_mask].head(5).index:
            val = df.at[idx, col]
            sample_rows.append({
                "row_index": int(idx),
                col: val.item() if hasattr(val, "item") else val,
            })
        result[col] = {
            "outlier_count": count,
            "outlier_pct": round(count / total_rows * 100, 1) if total_rows else 0.0,
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "min": round(float(valid.min()), 4),
            "max": round(float(valid.max()), 4),
            "mean": round(float(valid.mean()), 4),
            "median": round(float(valid.median()), 4),
            "sample_outliers": sample_rows,
        }
    return result


def trim_outliers(df, columns, method="iqr", threshold=1.5):
    """
    Drop rows where any of the given columns has an outlier value.
    Returns (df, rows_dropped).
    """
    drop_mask = pd.Series(False, index=df.index)
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            continue
        mask, _, _ = _outlier_bounds(valid, method, threshold)
        full_mask = pd.Series(False, index=df.index)
        full_mask[valid.index] = mask.values
        drop_mask |= full_mask
    rows_before = len(df)
    df = df[~drop_mask]
    return df, rows_before - len(df)


def impute_outliers(df, columns, method="iqr", threshold=1.5, strategy="median"):
    """
    Replace outlier values in each column with mean, median, or mode.
    Returns (df, cells_imputed).
    """
    cells_imputed = 0
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            continue
        mask, _, _ = _outlier_bounds(valid, method, threshold)
        full_mask = pd.Series(False, index=df.index)
        full_mask[valid.index] = mask.values
        count = int(full_mask.sum())
        if count == 0:
            continue
        if strategy == "mean":
            fill_val = valid.mean()
        elif strategy == "median":
            fill_val = valid.median()
        else:  # mode
            mode_vals = valid.mode()
            if mode_vals.empty:
                continue
            fill_val = mode_vals.iloc[0]
        if pd.api.types.is_integer_dtype(df[col].dtype):
            fill_val = round(float(fill_val))
        df.loc[full_mask, col] = fill_val
        cells_imputed += count
    return df, cells_imputed


def cap_outliers(df, columns, lower_pct=5.0, upper_pct=95.0):
    """
    Winsorize: values below lower_pct percentile are set to that percentile;
    values above upper_pct percentile are set to that percentile.
    Returns (df, cells_capped).
    """
    cells_capped = 0
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            continue
        lower = float(valid.quantile(lower_pct / 100))
        upper = float(valid.quantile(upper_pct / 100))
        below = df[col].notna() & (df[col] < lower)
        above = df[col].notna() & (df[col] > upper)
        count = int(below.sum()) + int(above.sum())
        if count == 0:
            continue
        df.loc[below, col] = lower
        df.loc[above, col] = upper
        cells_capped += count
    return df, cells_capped


def transform_column(df, columns, function="log"):
    """
    Apply a mathematical transformation to numeric columns.
    log: natural log (values must be > 0)
    sqrt: square root (values must be >= 0)
    cbrt: cube root (works with negative values)
    Returns (df, transformed_columns, skipped_columns).
    """
    transformed = []
    skipped = []
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            skipped.append({"column": col, "reason": "no non-null values"})
            continue
        if function == "log":
            if (valid <= 0).any():
                skipped.append({"column": col, "reason": "log requires all values > 0"})
                continue
            df[col] = np.log(df[col])
        elif function == "sqrt":
            if (valid < 0).any():
                skipped.append({"column": col, "reason": "sqrt requires all values >= 0"})
                continue
            df[col] = np.sqrt(df[col])
        else:  # cbrt
            df[col] = np.cbrt(df[col])
        transformed.append(col)
    return df, transformed, skipped


FILTER_OPERATORS = ("eq", "ne", "gt", "gte", "lt", "lte", "contains", "not_contains", "isnull", "notnull")
STRING_OPERATIONS = ("strip", "lower", "upper", "title")
SCALE_METHODS = ("minmax", "zscore")
DATETIME_FEATURES = ("year", "month", "day", "weekday", "hour", "minute")
ENCODE_STRATEGIES = ("label", "onehot")


def drop_columns(df, columns):
    """Drop specified columns from df. Returns (df, dropped_list)."""
    to_drop = [c for c in columns if c in df.columns]
    return df.drop(columns=to_drop), to_drop


def add_column(df, new_name, formula, operand_a, operand_b):
    """
    Create a new column by applying formula to operand_a and operand_b.
    divide replaces denominator zeros with NaN.
    Returns the modified df.
    """
    if formula == "divide":
        df[new_name] = df[operand_a] / df[operand_b].replace(0, np.nan)
    elif formula == "multiply":
        df[new_name] = df[operand_a] * df[operand_b]
    elif formula == "add":
        df[new_name] = df[operand_a] + df[operand_b]
    else:  # subtract
        df[new_name] = df[operand_a] - df[operand_b]
    return df


def filter_rows(df, column, operator, value=None):
    """
    Keep only rows matching the condition column <operator> value.
    isnull/notnull do not require value.
    Returns (df, rows_before, rows_after).
    """
    rows_before = len(df)
    col = df[column]
    if operator == "eq":
        mask = col == value
    elif operator == "ne":
        mask = col != value
    elif operator == "gt":
        mask = col > value
    elif operator == "gte":
        mask = col >= value
    elif operator == "lt":
        mask = col < value
    elif operator == "lte":
        mask = col <= value
    elif operator == "contains":
        mask = col.astype(str).str.contains(str(value), na=False, regex=False)
    elif operator == "not_contains":
        mask = ~col.astype(str).str.contains(str(value), na=False, regex=False)
    elif operator == "isnull":
        mask = col.isna()
    else:  # notnull
        mask = col.notna()
    df = df[mask].reset_index(drop=True)
    return df, rows_before, len(df)


def clean_string_column(df, columns, operation):
    """
    Apply a string operation (strip/lower/upper/title) to object/string columns.
    Returns (df, cells_changed).
    """
    cells_changed = 0
    for col in columns:
        before = df[col].copy()
        if operation == "strip":
            df[col] = df[col].str.strip()
        elif operation == "lower":
            df[col] = df[col].str.lower()
        elif operation == "upper":
            df[col] = df[col].str.upper()
        elif operation == "title":
            df[col] = df[col].str.title()
        changed = df[col].compare(before)
        cells_changed += len(changed)
    return df, cells_changed


def scale_columns(df, columns, method="minmax"):
    """
    Scale numeric columns in-place.
    minmax → [0, 1]; zscore → mean=0, std=1.
    Returns (df, scaled_columns, skipped_columns).
    """
    scaled = []
    skipped = []
    for col in columns:
        valid = df[col].dropna()
        if valid.empty:
            skipped.append({"column": col, "reason": "no non-null values"})
            continue
        if method == "minmax":
            col_min, col_max = float(valid.min()), float(valid.max())
            if col_min == col_max:
                skipped.append({"column": col, "reason": "all values identical — cannot min-max scale"})
                continue
            df[col] = (df[col] - col_min) / (col_max - col_min)
        else:  # zscore
            mean, std = float(valid.mean()), float(valid.std())
            if std == 0:
                skipped.append({"column": col, "reason": "std is 0 — cannot z-score scale"})
                continue
            df[col] = (df[col] - mean) / std
        scaled.append(col)
    return df, scaled, skipped


def extract_datetime_features(df, column, features):
    """
    Extract datetime sub-fields from a datetime column into new columns named {column}_{feature}.
    Returns (df, added_columns).
    """
    series = pd.to_datetime(df[column], errors="coerce")
    added = []
    attr_map = {
        "year": series.dt.year,
        "month": series.dt.month,
        "day": series.dt.day,
        "weekday": series.dt.weekday,
        "hour": series.dt.hour,
        "minute": series.dt.minute,
    }
    for feat in features:
        if feat not in attr_map:
            continue
        new_col = f"{column}_{feat}"
        df[new_col] = attr_map[feat]
        added.append(new_col)
    return df, added


def encode_columns(df, columns, strategy="label"):
    """
    Encode categorical columns.
    label  — replaces values with integer codes (0-based); returns mapping per column.
    onehot — adds binary indicator columns and drops the original.
    Returns (df, result_info).
    result_info is a list of dicts per column describing what was done.
    """
    result_info = []
    for col in columns:
        if strategy == "label":
            codes, uniques = pd.factorize(df[col])
            df[col] = codes
            result_info.append({
                "column": col,
                "strategy": "label",
                "mapping": {str(k): int(v) for v, k in enumerate(uniques)},
            })
        else:  # onehot
            dummies = pd.get_dummies(df[col], prefix=col, dtype=int)
            new_cols = list(dummies.columns)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
            result_info.append({
                "column": col,
                "strategy": "onehot",
                "new_columns": new_cols,
            })
    return df, result_info


def normalize_column_names(df):
    """Rename all columns to lowercase_snake_case. Returns (df, rename_map)."""
    old_names = list(df.columns)
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    rename_map = {old: new for old, new in zip(old_names, df.columns) if old != new}
    return df, rename_map


def generate_summary_stats(df):
    """
    Per-column summary statistics suitable for JSON serialization.
    """
    summary = {
        "total_rows": len(df),
        "missing_values": df.isnull().sum().to_dict(),
        "columns": [],
    }

    for col in df.columns:
        col_data = df[col]
        is_numeric = pd.api.types.is_numeric_dtype(col_data)

        col_summary = {
            "name": col,
            "type": "numeric" if is_numeric else "categorical",
            "missing": int(col_data.isnull().sum()),
            "unique": int(col_data.nunique()),
        }

        if is_numeric:
            valid = col_data.dropna()
            if not valid.empty:
                col_summary.update(
                    {
                        "min": float(valid.min()),
                        "max": float(valid.max()),
                        "mean": float(valid.mean()),
                        "median": float(valid.median()),
                        "std": float(valid.std()),
                    }
                )
        else:
            col_summary["top_values"] = {
                (k.item() if isinstance(k, np.generic) else k): int(v)
                for k, v in col_data.value_counts().head(5).items()
            }

        summary["columns"].append(col_summary)

    return summary
