from django.db import models
from apps.datasets.models import Dataset
from apps.issues.models import Issue


class CleaningOperation(models.Model):
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
        Dataset, on_delete=models.CASCADE, related_name="cleaning_ops"
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleaning_ops",
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
        verbose_name = "Cleaning Operation"
        verbose_name_plural = "Cleaning Operations"
