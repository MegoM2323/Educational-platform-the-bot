"""
API views for lesson management.

Endpoints for creating, retrieving, updating, and deleting lessons.
"""

from datetime import timedelta
from uuid import UUID
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import PermissionDenied, ValidationError
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

try:
    from materials.models import Subject
except ImportError:
    Subject = None


class LessonCreateThrottle(UserRateThrottle):
    """Rate limiting for lesson creation: max 10 lessons per minute."""

    rate = "10/minute"


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
    throttle_classes = [LessonCreateThrottle]

    def get_queryset(self):
        """Get lessons filtered by user role."""
        user = self.request.user

        from accounts.models import User as UserModel

        if not user.is_active:
            return Lesson.objects.none()

        if user.is_staff or user.is_superuser or user.role == UserModel.Role.ADMIN:
            # Admins see all lessons
            queryset = Lesson.objects.all()
        elif user.role == UserModel.Role.TEACHER:
            queryset = Lesson.objects.filter(teacher=user)
        elif user.role == UserModel.Role.STUDENT:
            six_months_ago = timezone.now().date() - timedelta(days=180)
            queryset = Lesson.objects.filter(
                student=user,
                date__gte=six_months_ago,
            )
        elif user.role == UserModel.Role.TUTOR:
            from accounts.models import StudentProfile

            six_months_ago = timezone.now().date() - timedelta(days=180)
            student_ids = StudentProfile.objects.filter(tutor=user).values_list(
                "user_id", flat=True
            )
            queryset = Lesson.objects.filter(
                student_id__in=student_ids,
                date__gte=six_months_ago,
            ).select_related("teacher", "student", "subject")
        elif user.role == UserModel.Role.PARENT:
            from accounts.models import StudentProfile

            six_months_ago = timezone.now().date() - timedelta(days=180)
            children_ids = StudentProfile.objects.filter(parent=user).values_list(
                "user_id", flat=True
            )
            queryset = Lesson.objects.filter(
                student_id__in=children_ids,
                date__gte=six_months_ago,
            ).select_related("teacher", "student", "subject")
        else:
            queryset = Lesson.objects.none()

        queryset = queryset.order_by("date", "start_time")

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

    def retrieve(self, request, pk=None):
        """
        Get a specific lesson by ID (role-aware) with explicit permission check.

        GET /api/scheduling/lessons/{id}/

        Rules:
        - Teachers can view their own lessons
        - Students can view their own lessons
        - Tutors can view lessons for their managed students
        - Parents can view lessons for their children
        - Admins can view all lessons
        - Returns 404 if lesson not in user's queryset
        """
        lesson = self.get_object()
        user = request.user

        # Explicit permission check
        has_access = False

        # Проверка прямого доступа
        if lesson.teacher == user or lesson.student == user:
            has_access = True
        # Admin/staff доступ
        elif user.is_staff or user.role in ("admin", "superuser"):
            has_access = True
        # Tutor доступ к студентам
        elif user.role == "tutor":
            from accounts.models import StudentProfile

            has_access = StudentProfile.objects.filter(
                user=lesson.student, tutor=user
            ).exists()
        # Parent доступ к детям
        elif user.role == "parent":
            from accounts.models import StudentProfile

            has_access = StudentProfile.objects.filter(
                user=lesson.student, parent=user
            ).exists()

        if not has_access:
            raise PermissionDenied("You cannot view this lesson")

        serializer = self.get_serializer(lesson)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new lesson (teacher or admin).

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

        Rules:
        - Teachers can create lessons for their own students (must have SubjectEnrollment)
        - Admins can create lessons for any student
        - start_time must be before end_time
        - Date cannot be in the past
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Only teachers, tutors, and admins can create lessons
        if request.user.role not in ("teacher", "tutor", "admin"):
            return Response(
                {"error": "Only teachers, tutors, and admins can create lessons"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate input
        serializer = LessonCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            student_id = serializer.validated_data.get("student")
            subject_id = serializer.validated_data["subject"]

            # Fetch student (if assigned) and subject objects
            student_obj = None
            if student_id:
                try:
                    student_obj = User.objects.get(id=student_id, role="student")
                except User.DoesNotExist:
                    return Response(
                        {"error": f"Student with id {student_id} not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            try:
                subject_obj = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                return Response(
                    {"error": f"Subject with id {subject_id} not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check teacher authorization (only if student is assigned)
            from accounts.models import User as UserModel

            if request.user.role == UserModel.Role.TEACHER and student_obj:
                # Teachers must have SubjectEnrollment with student
                from materials.models import SubjectEnrollment

                if not SubjectEnrollment.objects.filter(
                    student=student_obj,
                    teacher=request.user,
                    subject=subject_obj,
                    is_active=True,
                ).exists():
                    return Response(
                        {"error": "You do not teach this subject to this student"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # Create lesson (admin or authorized teacher)
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

        except DjangoValidationError as e:
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

    def perform_update(self, serializer):
        """
        Perform update with proper ForeignKey handling.

        Overrides default perform_update to handle:
        - Optional ForeignKey updates (teacher_id, student_id, subject_id)
        - Proper validation before save
        - Skip model-level validation in save()
        """
        lesson = self.get_object()

        # Prepare update data
        update_data = serializer.validated_data.copy()

        # Handle ForeignKey updates
        if "teacher_id" in update_data:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            teacher_id = update_data.pop("teacher_id")
            if teacher_id:
                lesson.teacher = User.objects.get(id=teacher_id, role="teacher")

        if "student_id" in update_data:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            student_id = update_data.pop("student_id")
            if student_id:
                lesson.student = User.objects.get(id=student_id, role="student")

        if "subject_id" in update_data:
            subject_id = update_data.pop("subject_id")
            if subject_id:
                lesson.subject = Subject.objects.get(id=subject_id)

        # Update remaining fields
        for attr, value in update_data.items():
            setattr(lesson, attr, value)

        # Save without skipped validation
        lesson.save()
        return lesson

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

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Cancel a lesson using POST method (alternative to DELETE).

        POST /api/scheduling/lessons/{id}/cancel/

        Rule: Cannot cancel less than 2 hours before lesson start.
        """
        lesson = self.get_object()

        # Only teacher can cancel
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
            from accounts.models import User as UserModel

            if request.user.role == UserModel.Role.TUTOR:
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
                six_months_ago = timezone.now().date() - timedelta(days=180)
                queryset = Lesson.objects.filter(
                    student_id=student_id_int,
                    date__gte=six_months_ago,
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
        from accounts.models import User as UserModel

        has_permission = (
            lesson.teacher == request.user or lesson.student == request.user
        )

        # Check if tutor has access to this lesson (manages the student)
        if not has_permission and request.user.role == UserModel.Role.TUTOR:
            from accounts.models import StudentProfile

            has_permission = StudentProfile.objects.filter(
                user=lesson.student, tutor=request.user
            ).exists()

        # Check if parent has access to this lesson (child is the student)
        if not has_permission and request.user.role == UserModel.Role.PARENT:
            from accounts.models import StudentProfile

            has_permission = StudentProfile.objects.filter(
                user=lesson.student, parent=request.user
            ).exists()

        if not has_permission:
            return Response(
                {"error": "You do not have permission to view this lesson"},
                status=status.HTTP_403_FORBIDDEN,
            )

        history = (
            LessonHistory.objects.filter(lesson=lesson)
            .select_related("performed_by")
            .order_by("-timestamp")
        )
        serializer = LessonHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """
        Get next upcoming lessons for current user (role-aware) with pagination.

        GET /api/scheduling/lessons/upcoming/
        GET /api/scheduling/lessons/upcoming/?limit=20

        Returns upcoming lessons with pagination support.
        """
        limit = int(request.query_params.get("limit", 10))
        queryset = LessonService.get_upcoming_lessons(request.user, limit=limit)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @transaction.atomic
    @action(detail=False, methods=["get", "post"], url_path="check-conflicts")
    def check_conflicts(self, request):
        """
        Check for schedule conflicts for a teacher on a specific date/time.

        GET /api/scheduling/lessons/check-conflicts/?date=2026-01-07&start_time=10:00&end_time=11:00
        OR
        GET /api/scheduling/lessons/check-conflicts/?date=2026-01-07&start_time=10:00&duration_minutes=60

        POST /api/scheduling/lessons/check-conflicts/
        {
            "date": "2026-01-07",
            "start_time": "10:00",
            "end_time": "11:00"
        }
        OR
        {
            "date": "2026-01-07",
            "start_time": "10:00",
            "duration_minutes": 60
        }

        If no teacher_id provided, uses current authenticated user as teacher.

        Returns:
        {
            "has_conflict": false,
            "conflicts": []
        }

        Or if conflicts exist:
        {
            "has_conflict": true,
            "conflicts": [
                {
                    "id": "uuid",
                    "student": "John Doe",
                    "subject": "Math",
                    "start_time": "10:15",
                    "end_time": "11:15"
                }
            ]
        }
        """
        from django.contrib.auth import get_user_model
        from datetime import datetime, time, timedelta

        User = get_user_model()

        # Validate input - get data from query params or POST body
        if request.method == "GET":
            data = request.query_params
        else:
            data = request.data

        teacher_id = data.get("teacher_id")
        date_str = data.get("date")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")
        duration_minutes = data.get("duration_minutes")

        # Валидация teacher_id
        teacher = None
        if not teacher_id:
            teacher = request.user
        else:
            # Валидировать формат (integer или UUID string)
            try:
                # Попробовать интерпретировать как integer (если pk integer)
                try:
                    teacher_id_int = int(teacher_id)
                    teacher = User.objects.filter(
                        id=teacher_id_int, role__in=["teacher", "tutor"]
                    ).first()
                except (ValueError, TypeError):
                    # Может быть UUID string
                    try:
                        uuid_obj = UUID(str(teacher_id))
                        teacher = User.objects.filter(
                            id=uuid_obj, role__in=["teacher", "tutor"]
                        ).first()
                    except (ValueError, TypeError):
                        raise ValidationError("Invalid teacher_id format")

                if not teacher:
                    raise ValidationError("Teacher/Tutor not found with given ID")
            except ValidationError as e:
                return Response(
                    {"error": f"Invalid teacher_id: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Check required date and start_time
        if not date_str or not start_time_str:
            return Response(
                {"error": "date and start_time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate end_time or duration_minutes provided
        if not end_time_str and not duration_minutes:
            return Response(
                {"error": "Either end_time or duration_minutes is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse date and times
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()

            # Calculate end_time from duration_minutes if not provided
            if end_time_str:
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
            else:
                # Calculate end_time from start_time + duration_minutes
                start_dt = datetime.combine(date, start_time)
                end_dt = start_dt + timedelta(minutes=int(duration_minutes))
                end_time = end_dt.time()
        except ValueError:
            return Response(
                {
                    "error": "Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for times"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get all lessons for teacher on that date (not cancelled/completed)
        lessons_on_date = (
            Lesson.objects.select_for_update()
            .filter(
                teacher=teacher,
                date=date,
                status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED],
            )
            .select_related("student", "subject")
        )

        # Check for time conflicts
        conflicts = []
        for lesson in lessons_on_date:
            # Check if time ranges overlap
            # Conflict if: new.start < existing.end AND new.end > existing.start
            if start_time < lesson.end_time and end_time > lesson.start_time:
                conflicts.append(
                    {
                        "id": str(lesson.id),
                        "student": lesson.student.get_full_name(),
                        "subject": lesson.subject.name,
                        "start_time": lesson.start_time.strftime("%H:%M"),
                        "end_time": lesson.end_time.strftime("%H:%M"),
                    }
                )

        return Response(
            {
                "has_conflict": len(conflicts) > 0,
                "conflicts": conflicts,
                "conflict_count": len(conflicts),
            }
        )

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """
        Reschedule an existing lesson to a new date/time.

        POST /api/scheduling/lessons/{lesson_id}/reschedule/
        {
            "date": "2026-01-08",
            "start_time": "14:00",
            "end_time": "15:00"
        }

        Returns the updated lesson.

        Rules:
        - Only teacher who created the lesson can reschedule it
        - Must check for time conflicts first
        - Cannot reschedule lesson that already completed/cancelled
        """
        lesson = self.get_object()

        # Validate input
        data = request.data
        new_date = data.get("date")
        new_start_time = data.get("start_time")
        new_end_time = data.get("end_time")

        if not all([new_date, new_start_time, new_end_time]):
            return Response(
                {"error": "date, start_time, and end_time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_lesson = LessonService.update_lesson(
                lesson=lesson,
                updates={
                    "date": new_date,
                    "start_time": new_start_time,
                    "end_time": new_end_time,
                },
                user=request.user,
            )
            serializer = self.get_serializer(updated_lesson)
            return Response(serializer.data)
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
