from rest_framework import serializers
from .models import DatalabIssue, WrangleOperation


class DatalabIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatalabIssue
        fields = "__all__"


class WrangleOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WrangleOperation
        fields = "__all__"
