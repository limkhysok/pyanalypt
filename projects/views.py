from rest_framework import viewsets, permissions
from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing project instances.
    Only the owner of the project can access it.
    """

    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter projects so users only see their own data
        return Project.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Additional safety to ensure user is set correctly
        serializer.save(user=self.request.user)
