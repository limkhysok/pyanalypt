import pandas as pd


def load_data(file_path):
    """
    Loads data from a file path into a Pandas DataFrame.
    Supports CSV and Excel files.
    """
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            df = pd.read_excel(file_path)
        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        else:
            raise ValueError("Unsupported file format")

        # Standardize: clean column names
        df = clean_columns(df)
        return df
    except Exception as e:
        raise ValueError(f"Error loading file: {str(e)}")


def clean_columns(df):
    """
    Standardizes column names: lowercase, spaces to underscores.
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
    Generates summary statistics for the DataFrame.
    Returns a dictionary suitable for JSON serialization.
    """
    summary = {
        "total_rows": len(df),
        "columns": [],
        "missing_values": df.isnull().sum().to_dict(),
    }

    for col in df.columns:
        col_data = df[col]
        col_type = (
            "numeric" if pd.api.types.is_numeric_dtype(col_data) else "categorical"
        )

        col_summary = {
            "name": col,
            "type": col_type,
            "missing": int(df[col].isnull().sum()),
            "unique": int(df[col].nunique()),
        }

        if col_type == "numeric":
            # Drop NaNs for stats calculation
            valid_data = col_data.dropna()
            if not valid_data.empty:
                col_summary.update(
                    {
                        "min": float(valid_data.min()),
                        "max": float(valid_data.max()),
                        "mean": float(valid_data.mean()),
                        "median": float(valid_data.median()),
                        "std": float(valid_data.std()),
                    }
                )
        else:
            # For categorical, maybe top 5 values?
            top_values = col_data.value_counts().head(5).to_dict()
            col_summary["top_values"] = top_values

        summary["columns"].append(col_summary)

    return summary
