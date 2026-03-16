from rest_framework import serializers
from .models import ProjectDataset


class ProjectDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDataset
        fields = (
            "id",
            "user",
            "file",
            "name",
            "file_format",
            "row_count",
            "column_count",
            "uploaded_at",
        )
        read_only_fields = (
            "id",
            "user",
            "file_format",
            "row_count",
            "column_count",
            "uploaded_at",
        )
