from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.conf import settings

from apps.datasets.models import Dataset
from apps.core.data_engine import load_data, generate_summary_stats
from apps.core.ollama_client import stream_frame_problem
from .models import DatasetFrame
from .serializers import DatasetFrameSerializer


class DatasetFrameViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Handles Problem Framing: streaming AI analysis and retrieving saved frames.

    GET  /frames/                    — list all frames for the authenticated user
    GET  /frames/{id}/               — retrieve a single frame
    POST /frames/run/{dataset_id}/   — stream a new Problem Framing for a dataset
    GET  /frames/history/{dataset_id}/ — list all frames for a specific dataset
    """

    serializer_class = DatasetFrameSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DatasetFrame.objects.filter(dataset__user=self.request.user)

    @action(detail=False, methods=["post"], url_path="run/(?P<dataset_id>[^/.]+)")
    def run(self, request, dataset_id=None):
        """
        POST /frames/run/{dataset_id}/
        Streams AI Problem Framing via SSE and saves the result on completion.

        Client receives:
            data: <token>\n\n        — one token at a time
            data: [DONE]\n\n         — stream complete
            data: [ERROR] ...\n\n    — Ollama error
        """
        try:
            dataset = Dataset.objects.get(pk=dataset_id, user=request.user)
        except Dataset.DoesNotExist:
            return Response({"detail": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)

        df = load_data(dataset.file.path)
        stats = generate_summary_stats(df)

        columns = stats.get("columns", [])
        column_names = [col["name"] for col in columns]
        simplified_stats = [
            {
                "name": col["name"],
                "type": col["type"],
                "missing": col["missing"],
                "unique": col["unique"],
            }
            for col in columns
        ]

        model_name = getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")

        def _stream_and_save():
            tokens = []
            try:
                for chunk in stream_frame_problem(column_names, simplified_stats):
                    tokens.append(chunk)
                    yield chunk
                # Save full result once streaming finishes
                full_result = "".join(tokens)
                clean = "\n".join(
                    line[6:].replace("\\n", "\n")
                    for line in full_result.splitlines()
                    if line.startswith("data: ") and line[6:] != "[DONE]"
                )
                DatasetFrame.objects.create(
                    dataset=dataset,
                    model_used=model_name,
                    result=clean,
                )
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"

        response = StreamingHttpResponse(_stream_and_save(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=False, methods=["get"], url_path="history/(?P<dataset_id>[^/.]+)")
    def history(self, request, dataset_id=None):
        """
        GET /frames/history/{dataset_id}/
        Returns all saved Problem Framing results for a dataset, newest first.
        """
        frames = self.get_queryset().filter(dataset_id=dataset_id)
        serializer = self.get_serializer(frames, many=True)
        return Response(serializer.data)
