import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text="The individual owner of this project.",
    )

    # Details
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=False, blank=True)
    description = models.TextField(blank=True, null=True)

    # Organization
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. Sales, Marketing, Research",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    # Visuals/UX
    color_code = models.CharField(
        max_length=7, default="#4F46E5", help_text="HEX color for UI cards"
    )
    thumbnail = models.URLField(blank=True, null=True, help_text="Cover image URL")
    is_favorite = models.BooleanField(default=False)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(default=timezone.now)

    # Settings (flexible storage for individual project preferences)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_favorite", "-last_accessed_at"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def mark_accessed(self):
        """Update last accessed time without triggering full updated_at change."""
        self.last_accessed_at = timezone.now()
        self.save(update_fields=["last_accessed_at"])
