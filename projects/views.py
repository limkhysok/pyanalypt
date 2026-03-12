from rest_framework import viewsets, permissions
from rest_framework.response import Response
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

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to update last_accessed_at whenever
        a user opens/reads a specific project.
        """
        instance = self.get_object()
        instance.mark_accessed()  # Update last_accessed_at timestamp
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
