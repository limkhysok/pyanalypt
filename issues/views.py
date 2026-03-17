from rest_framework import viewsets, permissions
from .models import Issue
from .serializers import IssueSerializer


class IssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing detected data issues.
    Users can only see issues for THEIR datasets.

    Query params:
      GET /issues/?dataset={id}  — filter issues for a specific dataset
    """
    serializer_class = IssueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Issue.objects.filter(dataset__user=self.request.user)
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        return qs

    def perform_update(self, serializer):
        # Any user edit automatically marks the issue as manually modified.
        serializer.save(is_user_modified=True)
