from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .models import UserFile
from .serializers import UserFileSerializer


class FileUploadView(APIView):
    """
    Handles file uploads.
    Extracts metadata automatically and links file to a session.
    """

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        session_id = request.data.get("session_id")

        if not file_obj:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not session_id:
            return Response(
                {"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create the model instance manually to populate metadata before saving
        # Note: We let the serializer handle the validation/creation usually,
        # but here we want to auto-fill fields from the file object itself.

        try:
            user_file = UserFile.objects.create(
                file=file_obj,
                original_filename=file_obj.name,
                file_size=file_obj.size,
                session_id=session_id,
            )

            serializer = UserFileSerializer(user_file)

            # --- Trigger Data Analysis ---
            try:
                from .data_engine import load_data, generate_summary_stats
                from .models import AnalysisResult

                # Load dataframe
                df = load_data(user_file.file.path)

                # Create summary stats
                stats = generate_summary_stats(df)

                # Save to DB
                AnalysisResult.objects.create(file=user_file, summary_stats=stats)

            except Exception as analysis_error:
                # Log error but don't fail the upload
                print(f"Analysis failed: {analysis_error}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
