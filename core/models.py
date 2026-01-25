import uuid
from django.db import models


class UserFile(models.Model):
    """
    Stores metadata and the actual file for uploaded datasets.
    Linked to a session_id to allow anonymous usage.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Size in bytes")

    # Ownership
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
    )
    # session_id maps the file to a specific browser session (for anonymous/guest users)
    session_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.id})"


class AnalysisResult(models.Model):
    """
    Stores the pre-calculated summary statistics (mean, median, etc.)
    using a JSONB column for efficient querying and flexibility.
    """

    file = models.OneToOneField(
        UserFile, on_delete=models.CASCADE, related_name="analysis"
    )
    # summary_stats will use PostgreSQL's JSONB type automatically with Django's JSONField
    summary_stats = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.file.original_filename}"
