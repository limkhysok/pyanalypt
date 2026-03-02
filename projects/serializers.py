from rest_framework import serializers
from .models import Project
from datasets.serializers import ProjectDatasetSerializer


class ProjectSerializer(serializers.ModelSerializer):
    datasets = ProjectDatasetSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "category",
            "status",
            "color_code",
            "thumbnail",
            "is_favorite",
            "created_at",
            "updated_at",
            "last_accessed_at",
            "settings",
            "datasets",
        )
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
            "last_accessed_at",
        )

    def create(self, validated_data):
        # Automatically set the user to the currently logged in user
        if "request" in self.context:
            validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
