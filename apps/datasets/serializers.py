from rest_framework import serializers
from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "user",
            "file",
            "file_name",
            "file_format",
            "file_size",
            "uploaded_date",
            "updated_date",
        )
        read_only_fields = (
            "id",
            "user",
            "file_format",
            "file_size",
            "uploaded_date",
            "updated_date",
        )
