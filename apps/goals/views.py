import re

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.core.data_engine import get_cached_dataframe
from apps.core.ollama_client import stream_suggest_questions

from .models import AnalysisGoal, AnalysisQuestion
from .serializers import (
    AnalysisGoalListSerializer,
    AnalysisGoalSerializer,
    AnalysisQuestionSerializer,
)

_MAX_QUESTIONS = 20


class AnalysisGoalViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return AnalysisGoal.objects.filter(dataset__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return AnalysisGoalListSerializer
        return AnalysisGoalSerializer

    @action(detail=True, methods=["post"])
    def suggest(self, request, pk=None):
        """
        POST /api/v1/goals/{id}/suggest/
        Streams Q1, Q2... questions from Ollama based on dataset columns
        and problem_statement. Saves generated questions with source="ai"
        on completion.
        """
        goal = self.get_object()
        dataset = goal.dataset
        df = get_cached_dataframe(dataset.id, dataset.file.path, dataset.file_format)
        columns = list(df.columns)

        def _stream_and_save():
            raw_chunks = []
            try:
                for chunk in stream_suggest_questions(columns, goal.problem_statement):
                    raw_chunks.append(chunk)
                    yield chunk

                # Reconstruct full text from SSE chunks
                full_text = "".join(
                    line[6:].replace("\\n", "\n")
                    for line in "".join(raw_chunks).splitlines()
                    if line.startswith("data: ")
                    and "[DONE]" not in line
                    and "[ERROR]" not in line
                )

                # Parse Qn: lines into individual questions
                parsed = []
                for line in full_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    cleaned = re.sub(r"^Q\d+[\.:]\s*", "", line)
                    if cleaned:
                        parsed.append(cleaned)

                current_count = goal.questions.count()
                AnalysisQuestion.objects.bulk_create([
                    AnalysisQuestion(
                        goal=goal,
                        order=current_count + i,
                        question=q,
                        source="ai",
                    )
                    for i, q in enumerate(parsed)
                ])
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"

        response = StreamingHttpResponse(_stream_and_save(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AnalysisQuestionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_goal(self, request, goal_pk):
        try:
            return AnalysisGoal.objects.get(pk=goal_pk, dataset__user=request.user)
        except AnalysisGoal.DoesNotExist:
            raise NotFound("Goal not found.")

    def create(self, request, goal_pk=None):
        """POST /api/v1/goals/{goal_pk}/questions/"""
        goal = self._get_goal(request, goal_pk)
        if goal.questions.count() >= _MAX_QUESTIONS:
            return Response(
                {"detail": f"A goal may have at most {_MAX_QUESTIONS} questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        s = AnalysisQuestionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(goal=goal, source="manual")
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, goal_pk=None, pk=None):
        """PATCH /api/v1/goals/{goal_pk}/questions/{pk}/"""
        goal = self._get_goal(request, goal_pk)
        try:
            question = AnalysisQuestion.objects.get(pk=pk, goal=goal)
        except AnalysisQuestion.DoesNotExist:
            raise NotFound("Question not found.")
        s = AnalysisQuestionSerializer(question, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, goal_pk=None, pk=None):
        """DELETE /api/v1/goals/{goal_pk}/questions/{pk}/"""
        goal = self._get_goal(request, goal_pk)
        try:
            question = AnalysisQuestion.objects.get(pk=pk, goal=goal)
        except AnalysisQuestion.DoesNotExist:
            raise NotFound("Question not found.")
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
