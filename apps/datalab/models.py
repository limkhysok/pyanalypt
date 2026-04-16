from django.db import models
from apps.datasets.models import Dataset


class DatalabIssue(models.Model):
    """
    Represents a data quality issue found during EDA (Exploratory Data Analysis).
    """

    TYPE_MISSING_VALUE = "MISSING_VALUE"
    TYPE_DUPLICATE = "DUPLICATE"
    TYPE_OUTLIER = "OUTLIER"
    TYPE_SEMANTIC_ERROR = "SEMANTIC_ERROR"
    TYPE_DATA_TYPE = "DATA_TYPE"
    TYPE_INCONSISTENT_FORMATTING = "INCONSISTENT_FORMATTING"
    TYPE_INVALID_VALUE = "INVALID_VALUE"
    TYPE_WHITESPACE_ISSUE = "WHITESPACE_ISSUE"
    TYPE_SPECIAL_CHAR_ENCODING = "SPECIAL_CHAR_ENCODING"
    TYPE_INCONSISTENT_NAMING = "INCONSISTENT_NAMING"
    TYPE_LOGICAL_INCONSISTENCY = "LOGICAL_INCONSISTENCY"

    TYPE_CHOICES = [
        (TYPE_MISSING_VALUE, "Missing Value"),
        (TYPE_DUPLICATE, "Duplicate Row"),
        (TYPE_OUTLIER, "Outlier"),
        (TYPE_SEMANTIC_ERROR, "Semantic Error"),
        (TYPE_DATA_TYPE, "Data Type"),
        (TYPE_INCONSISTENT_FORMATTING, "Inconsistent Formatting"),
        (TYPE_INVALID_VALUE, "Invalid Value"),
        (TYPE_WHITESPACE_ISSUE, "Whitespace Issue"),
        (TYPE_SPECIAL_CHAR_ENCODING, "Special Characters & Encoding"),
        (TYPE_INCONSISTENT_NAMING, "Inconsistent Naming"),
        (TYPE_LOGICAL_INCONSISTENCY, "Logical Inconsistency"),
    ]

    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="datalab_issues"
    )
    issue_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    column_name = models.CharField(max_length=255, blank=True, default="")
    row_index = models.IntegerField(null=True, blank=True)
    affected_rows = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    suggested_fix = models.TextField(blank=True, default="")
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.issue_type}] in {self.column_name or 'dataset'}"

    class Meta:
        ordering = ["-detected_at"]
        verbose_name = "Datalab Issue"
        verbose_name_plural = "Datalab Issues"


class WrangleOperation(models.Model):
    """
    Represents a Data Wrangling operation applied to a dataset.
    """

    OPERATION_CHOICES = [
        ("FILL_NA", "Fill missing values"),
        ("DROP_ROWS", "Drop rows"),
        ("DROP_DUPLICATES", "Drop duplicates"),
        ("CLIP_OUTLIERS", "Clip outliers"),
        ("REMOVE_OUTLIERS", "Remove outliers"),
        ("CAST_COLUMN", "Cast column type"),
        ("STANDARDIZE_FORMAT", "Standardize format"),
        ("REPLACE_VALUES", "Replace values"),
        ("STRIP_WHITESPACE", "Strip whitespace"),
        ("FIX_ENCODING", "Fix encoding"),
        ("STANDARDIZE_CASE", "Standardize case"),
        ("RENAME_COLUMN", "Rename column"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPLIED", "Applied"),
        ("FAILED", "Failed"),
        ("REVERTED", "Reverted"),
    ]

    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="wrangle_ops"
    )
    issue = models.ForeignKey(
        DatalabIssue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wrangle_ops",
    )
    operation_type = models.CharField(max_length=32, choices=OPERATION_CHOICES)
    column_name = models.CharField(max_length=255, blank=True, default="")
    parameters = models.JSONField(default=dict, blank=True)
    rows_affected = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.operation_type} on {self.column_name or 'dataset'} ({self.status})"
        )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Wrangle Operation"
        verbose_name_plural = "Wrangle Operations"
