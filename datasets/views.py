import uuid
import pandas as pd
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.files.base import ContentFile
from projects.models import Project
from .models import ProjectDataset
from .serializers import ProjectDatasetSerializer


class CreateDatasetView(generics.CreateAPIView):
    """
    Handle file uploads (Drag and Drop / File Input).
    Expects multipart/form-data.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Check ownership of the project
        project = serializer.validated_data["project"]
        if project.user != self.request.user:
            raise permissions.exceptions.PermissionDenied(
                "You do not own this project."
            )
        serializer.save()


class PasteDatasetView(generics.GenericAPIView):
    """
    Handle raw text paste (CSV or JSON string).
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project_id = request.data.get("project")
        raw_data = request.data.get("raw_data")
        file_name = request.data.get("name", f"pasted_data_{uuid.uuid4().hex[:8]}")
        data_format = request.data.get("format", "csv").lower()

        if not project_id:
            return Response(
                {"detail": "Project ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not raw_data:
            return Response(
                {"detail": "Raw data is empty."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create a virtual file from the raw string
        file_extension = ".json" if data_format == "json" else ".csv"
        if not file_name.endswith(file_extension):
            file_name += file_extension

        content_file = ContentFile(raw_data.encode("utf-8"), name=file_name)

        # Save via serializer
        serializer = self.get_serializer(
            data={"project": project.id, "file": content_file, "name": file_name}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectDatasetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual datasets (Read, Update, Delete).
    Includes a 'preview' action to see columns and first 10 rows.
    """

    serializer_class = ProjectDatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProjectDataset.objects.filter(project__user=self.request.user)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        dataset = self.get_object()
        file_path = dataset.file.path

        # Get dynamic row limit from query params (default 10, max 1000)
        try:
            row_limit = int(request.query_params.get("rows", 10))
            if row_limit <= 0:
                row_limit = 10
            row_limit = min(row_limit, 1000)  # Safety cap
        except (ValueError, TypeError):
            row_limit = 10

        try:
            if dataset.file_format == "csv":
                df = pd.read_csv(file_path, nrows=row_limit)
            elif dataset.file_format in ["xlsx", "xls"]:
                df = pd.read_excel(file_path, nrows=row_limit)
            elif dataset.file_format == "json":
                df = pd.read_json(file_path).head(row_limit)
            else:
                return Response(
                    {"detail": "Unsupported preview for this format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract dtypes and summary
            dtypes = df.dtypes.apply(lambda x: str(x)).to_dict()
            summary = {}
            # Numeric summary
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if not numeric_cols.empty:
                full_stats = df[numeric_cols].describe().to_dict()
                summary = full_stats

            preview_data = {
                "columns": list(df.columns),
                "rows": df.where(pd.notnull(df), None).to_dict(orient="records"),
                "metadata": {
                    "dtypes": dtypes,
                    "shape": [dataset.row_count, dataset.column_count],
                },
                "summary": summary,
                "total_rows_hint": dataset.row_count,  # Backwards compatibility
            }
            return Response(preview_data)

        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
