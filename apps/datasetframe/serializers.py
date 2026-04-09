from rest_framework import serializers
from .models import DatasetFrame


class DatasetFrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetFrame
        fields = ["id", "dataset", "model_used", "result", "created_at"]
        read_only_fields = ["id", "model_used", "result", "created_at"]
