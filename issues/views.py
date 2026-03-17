from rest_framework import viewsets, permissions
from .models import Issue
from .serializers import IssueSerializer


class IssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing detected data issues.
    Users can only see issues for THEIR datasets.
    """
    serializer_class = IssueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter issues by the datasets owned by the user
        return Issue.objects.filter(dataset__user=self.request.user)
