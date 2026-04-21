import io
import re
import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)

SQLITE_MEMORY = ":memory:"


def load_dataframe(file_path, file_format):
    """
    Load a file into a DataFrame using the explicit file_format field.
    Supports: csv, xlsx, xls, json, parquet, sql.
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
        if fmt == "sql":
            return _load_sql(file_path)
    except Exception:
        logger.exception("Failed to load dataframe: %s (%s)", file_path, file_format)
    return None


def _load_sql(file_path):
    conn = sqlite3.connect(SQLITE_MEMORY)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            return None
        table_name = tables[0][0]
        if not re.match(r"^[A-Za-z_]\w*$", table_name):
            return None
        return pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
    finally:
        conn.close()


SUPPORTED_CASTS = {"datetime", "numeric", "float", "integer", "string", "boolean", "category"}


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
    SQL files are not supported for round-trip saves.
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
                col_summary.update({
                    "min": float(valid.min()),
                    "max": float(valid.max()),
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                    "std": float(valid.std()),
                })
        else:
            col_summary["top_values"] = col_data.value_counts().head(5).to_dict()

        summary["columns"].append(col_summary)

    return summary
