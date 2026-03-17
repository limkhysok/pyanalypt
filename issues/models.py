from django.db import models
from datasets.models import Dataset


class Issue(models.Model):
    # SEVERITY LEVELS
    SEVERITY_LOW = "LOW"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_CHOICES = [
        (SEVERITY_LOW, "Low"),
        (SEVERITY_MEDIUM, "Medium"),
        (SEVERITY_HIGH, "High"),
    ]

    # ISSUE TYPES
    TYPE_MISSING_VALUE = "MISSING_VALUE"
    TYPE_DUPLICATE = "DUPLICATE"
    TYPE_OUTLIER = "OUTLIER"
    TYPE_SEMANTIC_ERROR = "SEMANTIC_ERROR"
    TYPE_TYPE_MISMATCH = "TYPE_MISMATCH"
    TYPE_CHOICES = [
        (TYPE_MISSING_VALUE, "Missing Value"),
        (TYPE_DUPLICATE, "Duplicate Row"),
        (TYPE_OUTLIER, "Outlier"),
        (TYPE_SEMANTIC_ERROR, "Semantic Error"),
        (TYPE_TYPE_MISMATCH, "Type Mismatch"),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="issues")
    issue_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    column_name = models.CharField(max_length=255, blank=True, default="")
    row_index = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_LOW)
    suggested_fix = models.TextField(blank=True, default="")
    
    is_resolved = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.issue_type}] in {self.column_name or 'dataset'}"

    class Meta:
        ordering = ["-detected_at"]
        verbose_name = "Issue"
        verbose_name_plural = "Issues"
