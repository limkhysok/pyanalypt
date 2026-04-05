from rest_framework import serializers
from .models import CleaningOperation

class CleaningOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleaningOperation
        fields = "__all__"
        read_only_fields = ("id", "status", "applied_at", "created_at")
