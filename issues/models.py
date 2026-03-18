from django.db import models
from datasets.models import Dataset


class Issue(models.Model):
    # ISSUE TYPES
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

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="issues")
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
        verbose_name = "Issue"
        verbose_name_plural = "Issues"
