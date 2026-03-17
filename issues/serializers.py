from rest_framework import serializers
from .models import Issue


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = (
            "id",
            "dataset",
            "issue_type",
            "column_name",
            "row_index",
            "description",
            "severity",
            "suggested_fix",
            "is_resolved",
            "detected_at",
        )
        read_only_fields = ("id", "dataset", "detected_at")
