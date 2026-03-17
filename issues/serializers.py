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
            "affected_rows",
            "description",
            "severity",
            "suggested_fix",
            "detected_by",
            "is_user_modified",
            "is_resolved",
            "detected_at",
        )
        read_only_fields = ("id", "dataset", "detected_by", "affected_rows", "is_user_modified", "detected_at")
