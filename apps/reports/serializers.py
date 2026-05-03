from rest_framework import serializers

from .models import Report, ReportItem


class ReportItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        fields = ["id", "order", "chart_type", "chart_params", "chart_image", "annotation", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReportSerializer(serializers.ModelSerializer):
    items      = ReportItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Report
        fields = ["id", "dataset", "goal", "title", "description", "created_at", "updated_at", "item_count", "items"]
        read_only_fields = ["id", "created_at", "updated_at", "item_count"]


class ReportListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Report
        fields = ["id", "dataset", "goal", "title", "description", "created_at", "updated_at", "item_count"]
        read_only_fields = ["id", "created_at", "updated_at", "item_count"]
