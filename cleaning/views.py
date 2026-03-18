
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CleaningOperation
from .serializers import CleaningOperationSerializer

class CleaningOperationViewSet(viewsets.ModelViewSet):
    queryset = CleaningOperation.objects.all()
    serializer_class = CleaningOperationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CleaningOperation.objects.filter(dataset__user=user)
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        return qs

    @action(detail=True, methods=["post"])
    def revert(self, request, pk=None):
        """POST /cleaning/{id}/revert/ — revert a cleaning operation."""
        op = self.get_object()
        if op.status != "APPLIED":
            return Response({"detail": "Only applied operations can be reverted."}, status=status.HTTP_400_BAD_REQUEST)
        # Placeholder: actual revert logic needed
        op.status = "REVERTED"
        op.save(update_fields=["status"])
        return Response({"detail": "Operation reverted (not actually implemented)."})

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """POST /cleaning/preview/ — preview the effect of a cleaning operation (not applied)."""
        # Placeholder: actual preview logic needed
        return Response({"detail": "Preview not implemented yet."}, status=status.HTTP_501_NOT_IMPLEMENTED)
