from django.db import models
from apps.datasets.models import Dataset


class DatasetFrame(models.Model):
    """
    Stores AI-generated Problem Framing results for a dataset.
    Each run of the 'Problem Framing' feature creates one record.
    """

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="frames",
    )
    model_used = models.CharField(max_length=100)
    result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Frame for {self.dataset.file_name} ({self.model_used}) @ {self.created_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dataset Frame"
        verbose_name_plural = "Dataset Frames"
