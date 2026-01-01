"""
API views for lesson management.

Endpoints for creating, retrieving, updating, and deleting lessons.
"""

from typing import Optional
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import ValidationError as DjangoValidationError

from scheduling.models import Lesson, LessonHistory
from scheduling.serializers import (
    LessonSerializer,
    LessonCreateSerializer,
    LessonUpdateSerializer,
    LessonHistorySerializer,
)
from scheduling.services.lesson_service import LessonService
from scheduling.permissions import IsTeacher, IsStudent
from materials.models import Subject


class LessonPagination(PageNumberPagination):
    """
    Пагинация для списка уроков.

    Параметры:
    - page_size: 50 элементов на страницу по умолчанию
    - max_page_size: максимум 100 элементов на страницу
    - page_size_query_param: клиент может запросить размер через ?page_size=N
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class LessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for lesson management.

    Provides endpoints for creating, listing, retrieving, updating, and deleting lessons.
    Role-based access control: teachers create, students/tutors view.
    """

    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LessonPagination

    def get_queryset(self):
        """Get lessons filtered by user role."""
        user = self.request.user

        if user.role == "teacher":
            # Teachers see their created lessons
            queryset = Lesson.objects.filter(teacher=user)
        elif user.role == "student":
            # Students see their own lessons
            queryset = Lesson.objects.filter(student=user)
        elif user.role == "tutor":
            # Tutors see lessons for their students
            from accounts.models import StudentProfile

            student_ids = StudentProfile.objects.filter(tutor=user).values_list(
                "user_id", flat=True
            )

            queryset = Lesson.objects.filter(student_id__in=student_ids)
        elif user.role == "parent":
            # Parents see lessons for their children
            from accounts.models import StudentProfile

            children_ids = StudentProfile.objects.filter(parent=user).values_list(
                "user_id", flat=True
            )
            queryset = Lesson.objects.filter(student_id__in=children_ids)
        else:
            # Other roles see nothing
            queryset = Lesson.objects.none()

        # Always optimize queries
        queryset = queryset.select_related("teacher", "student", "subject").order_by(
            "date", "start_time"
        )

        return queryset

    def list(self, request, *args, **kwargs):
        """
        List lessons for current user with pagination.

        GET /api/scheduling/lessons/
        GET /api/scheduling/lessons/?page=2
        GET /api/scheduling/lessons/?page_size=25

        Returns paginated lessons filtered by user role via get_queryset().
        Response structure:
        {
            "count": 150,
            "next": "http://api/scheduling/lessons/?page=2",
            "previous": null,
            "results": [...]
        }
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Применяем пагинацию
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback если пагинация отключена
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new lesson (teacher only).

        POST /api/scheduling/lessons/
        {
            "student_id": 123,
            "subject_id": 1,
            "date": "2024-12-20",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "description": "Optional description",
            "telemost_link": "https://telemost.yandex.ru/..."
        }
        """
        # Only teachers can create lessons
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can create lessons"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate input
        serializer = LessonCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            # Use service to create lesson
            student_id = serializer.validated_data["student"]
            subject_id = serializer.validated_data["subject"]

            # Fetch actual objects
            from django.contrib.auth import get_user_model

            User = get_user_model()

            student_obj = User.objects.get(id=student_id, role="student")
            subject_obj = Subject.objects.get(id=subject_id)

            lesson = LessonService.create_lesson(
                teacher=request.user,
                student=student_obj,
                subject=subject_obj,
                date=serializer.validated_data["date"],
                start_time=serializer.validated_data["start_time"],
                end_time=serializer.validated_data["end_time"],
                description=serializer.validated_data.get("description", ""),
                telemost_link=serializer.validated_data.get("telemost_link", ""),
            )

            # Return created lesson
            output_serializer = LessonSerializer(lesson)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        except (DjangoValidationError, User.DoesNotExist, Subject.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Full update of a lesson (teacher only, before lesson starts).

        PUT /api/scheduling/lessons/{id}/
        {
            "date": "2024-12-21",
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "description": "Updated description",
            "telemost_link": "https://telemost.yandex.ru/..."
        }
        """
        lesson = self.get_object()

        # Only teacher can update
        if lesson.teacher != request.user:
            return Response(
                {"error": "Only the teacher who created this lesson can update it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate input
        serializer = LessonUpdateSerializer(
            data=request.data, context={"lesson": lesson}
        )
        serializer.is_valid(raise_exception=True)

        try:
            # Use service to update lesson
            updated_lesson = LessonService.update_lesson(
                lesson=lesson, updates=serializer.validated_data, user=request.user
            )

            # Return updated lesson
            output_serializer = LessonSerializer(updated_lesson)
            return Response(output_serializer.data)

        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """
        Partial update of a lesson (teacher only, before lesson starts).

        PATCH /api/scheduling/lessons/{id}/
        {
            "date": "2024-12-21",  # Optional
            "start_time": "11:00:00",  # Optional
            "end_time": "12:00:00",  # Optional
            "description": "Updated description",  # Optional
            "telemost_link": "https://telemost.yandex.ru/..."  # Optional
        }
        """
        lesson = self.get_object()

        # Only teacher can update
        if lesson.teacher != request.user:
            return Response(
                {"error": "Only the teacher who created this lesson can update it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate input (partial=True allows optional fields)
        serializer = LessonUpdateSerializer(
            data=request.data, partial=True, context={"lesson": lesson}
        )
        serializer.is_valid(raise_exception=True)

        try:
            # Use service to update lesson
            updated_lesson = LessonService.update_lesson(
                lesson=lesson, updates=serializer.validated_data, user=request.user
            )

            # Return updated lesson
            output_serializer = LessonSerializer(updated_lesson)
            return Response(output_serializer.data)

        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        Delete (cancel) a lesson (teacher only).

        DELETE /api/scheduling/lessons/{id}/

        Rule: Cannot cancel less than 2 hours before lesson start.
        """
        lesson = self.get_object()

        # Only teacher can delete
        if lesson.teacher != request.user:
            return Response(
                {"error": "Only the teacher who created this lesson can cancel it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Use service to delete lesson
            LessonService.delete_lesson(lesson=lesson, user=request.user)

            # 204 No Content - must not have response body
            return Response(status=status.HTTP_204_NO_CONTENT)

        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="my-schedule")
    def my_schedule(self, request):
        """
        Get current user's schedule (role-aware) with pagination.

        GET /api/scheduling/lessons/my-schedule/
        GET /api/scheduling/lessons/my-schedule/?page=2
        GET /api/scheduling/lessons/my-schedule/?page_size=25

        Query params:
        - date_from: filter by start date (YYYY-MM-DD)
        - date_to: filter by end date (YYYY-MM-DD)
        - status: filter by lesson status
        - subject_id: filter by subject

        Returns:
        - Teacher: lessons they created
        - Student: their lessons
        - Tutor: lessons for managed students
        """
        queryset = self.get_queryset()

        # Apply date filters if provided
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        status_filter = request.query_params.get("status")
        subject_id = request.query_params.get("subject_id")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        # Применяем пагинацию
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback если пагинация отключена
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def student_schedule(self, request):
        """
        Get lessons for a specific student (tutor or parent) with pagination.

        GET /api/scheduling/lessons/student_schedule/?student_id={student_id}
        GET /api/scheduling/lessons/student_schedule/?student_id={student_id}&page=2
        GET /api/scheduling/lessons/student_schedule/?student_id={student_id}&page_size=25

        Query params:
        - student_id: required, ID of the student
        - date_from: filter by start date (YYYY-MM-DD)
        - date_to: filter by end date (YYYY-MM-DD)
        - status: filter by lesson status
        - subject_id: filter by subject

        Only tutors can access their students' schedules.
        Parents can access their children's schedules.
        """
        # Only tutors and parents can access
        if request.user.role not in ["tutor", "parent"]:
            return Response(
                {"error": "Only tutors and parents can view student schedules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация формата student_id (должен быть целым числом)
        try:
            student_id_int = int(student_id)
        except ValueError:
            return Response(
                {"error": "Invalid student_id format. Expected integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if request.user.role == "tutor":
                # Use service to get lessons (validates tutor manages student)
                queryset = LessonService.get_tutor_student_lessons(
                    tutor=request.user, student_id=student_id_int
                )
            else:
                # Parent role - verify parent relationship
                from accounts.models import StudentProfile

                if not StudentProfile.objects.filter(
                    user_id=student_id_int, parent=request.user
                ).exists():
                    return Response(
                        {"error": "You can only view schedules for your children"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                queryset = Lesson.objects.filter(
                    student_id=student_id_int
                ).select_related("teacher", "student", "subject")

            # Apply filters
            date_from = request.query_params.get("date_from")
            date_to = request.query_params.get("date_to")
            status_filter = request.query_params.get("status")
            subject_id = request.query_params.get("subject_id")

            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if subject_id:
                queryset = queryset.filter(subject_id=subject_id)

            # Применяем пагинацию
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            # Fallback если пагинация отключена
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """
        Get history of changes for a lesson.

        GET /api/scheduling/lessons/{id}/history/
        """
        lesson = self.get_object()

        # Verify permission to view history
        # Teacher, student, tutor, or parent of student
        has_permission = (
            lesson.teacher == request.user or lesson.student == request.user
        )

        # Check if tutor has access to this lesson (manages the student)
        if not has_permission and request.user.role == "tutor":
            from accounts.models import StudentProfile

            has_permission = StudentProfile.objects.filter(
                user=lesson.student, tutor=request.user
            ).exists()

        # Check if parent has access to this lesson (child is the student)
        if not has_permission and request.user.role == "parent":
            from accounts.models import StudentProfile

            has_permission = StudentProfile.objects.filter(
                user=lesson.student, parent=request.user
            ).exists()

        if not has_permission:
            return Response(
                {"error": "You do not have permission to view this lesson"},
                status=status.HTTP_403_FORBIDDEN,
            )

        history = LessonHistory.objects.filter(lesson=lesson).order_by("-timestamp")
        serializer = LessonHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """
        Get next upcoming lessons for current user (role-aware).

        GET /api/scheduling/lessons/upcoming/

        Returns up to 10 upcoming lessons.
        """
        queryset = LessonService.get_upcoming_lessons(request.user, limit=10)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
