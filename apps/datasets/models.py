import os
from django.db import models
from django.conf import settings
from .validators import validate_file_size_and_type
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class Dataset(models.Model):
    """
    Model representing a dataset file associated with a user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets",
        null=True,
        blank=True,
    )
    file = models.FileField(
        upload_to="datasets/%Y/%m/%d/", validators=[validate_file_size_and_type]
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_format = models.CharField(max_length=10, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_cleaned = models.BooleanField(default=False)

    uploaded_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 1. Set basic metadata
        if not self.file_name:
            self.file_name = self.file.name
        if not self.file_format:
            self.file_format = os.path.splitext(self.file.name)[1][1:].lower()
        if self.file:
            self.file_size = self.file.size

        super().save(*args, **kwargs)

    def __str__(self):
        owner = self.user.username if self.user else "Unknown"
        return f"{self.file_name} ({owner})"

    class Meta:
        ordering = ["-uploaded_date"]
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"


@receiver(pre_delete, sender=Dataset)
def dataset_delete(sender, instance, **kwargs):
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)
