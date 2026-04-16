import os
from django.core.exceptions import ValidationError


def validate_file_size_and_type(value):
    """
    Validation for datasets:
    - Size limit: 25MB
    - Formats: CSV, XLSX, JSON, Parquet
    """
    # 25MB Limit
    filesize = value.size
    if filesize > 25 * 1024 * 1024:
        raise ValidationError("The maximum file size that can be uploaded is 25MB")

    # Extension Check
    ext = os.path.splitext(value.name)[1]
    valid_extensions = [".csv", ".xlsx", ".json", ".parquet", ".sql"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("Unsupported file extension. Use CSV, XLSX, JSON, Parquet, or SQL.")
