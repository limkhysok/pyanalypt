import os
import pandas as pd
from django.db import models
from projects.models import Project
from .validators import validate_file_size_and_type


class ProjectDataset(models.Model):
    """
    Model representing a dataset file associated with a project.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="datasets"
    )
    file = models.FileField(
        upload_to="datasets/%Y/%m/%d/", validators=[validate_file_size_and_type]
    )
    name = models.CharField(max_length=255, blank=True)
    file_format = models.CharField(max_length=10, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleaned_versions",
    )
    is_cleaned = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 1. Set basic metadata
        if not self.name:
            self.name = self.file.name
        if not self.file_format:
            self.file_format = os.path.splitext(self.file.name)[1][1:].lower()

        # 2. Extract Dataframe Shape (Row/Col count)
        if self.file and (self.row_count is None or self.column_count is None):
            try:
                # We use pandas to get the shape
                # Note: For very large files, this should be a background task
                if self.file_format == "csv":
                    # Read only headers for col count, then rows
                    df = pd.read_csv(self.file)
                    self.row_count = len(df)
                    self.column_count = len(df.columns)
                elif self.file_format in ["xlsx", "xls"]:
                    df = pd.read_excel(self.file)
                    self.row_count = len(df)
                    self.column_count = len(df.columns)
                elif self.file_format == "json":
                    df = pd.read_json(self.file)
                    self.row_count = len(df)
                    self.column_count = len(df.columns)
            except Exception:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
