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
            "suggested_fix",
            "detected_at",
        )
        read_only_fields = ("id", "dataset", "row_index", "affected_rows", "detected_at")
