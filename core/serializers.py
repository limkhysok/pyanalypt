from rest_framework import serializers
from .models import UserFile


class UserFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFile
        fields = [
            "id",
            "file",
            "original_filename",
            "file_size",
            "session_id",
            "uploaded_at",
        ]
        read_only_fields = ["id", "original_filename", "file_size", "uploaded_at"]
