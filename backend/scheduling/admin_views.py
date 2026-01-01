"""
Admin views for schedule management.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import datetime

from django.contrib.auth import get_user_model
from accounts.permissions import IsAdminUser
from scheduling.admin_schedule_service import AdminScheduleService
from scheduling.serializers import AdminLessonSerializer, LessonCreateSerializer, LessonSerializer
from scheduling.views import LessonPagination
from scheduling.services.lesson_service import LessonService
from materials.models import Subject

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_schedule_view(request):
    """
    Get all lessons for admin with optional filters.

    Query parameters:
    - teacher_id: Filter by teacher UUID
    - subject_id: Filter by subject UUID
    - student_id: Filter by student UUID
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    - status: Filter by status (pending, confirmed, completed, cancelled)

    Returns:
    - List of all lessons matching filters
    - Includes teacher_name, student_name, subject_name
    - Ordered by date descending
    """
    try:
        # Parse query parameters
        teacher_id = request.GET.get("teacher_id")
        subject_id = request.GET.get("subject_id")
        student_id = request.GET.get("student_id")
        date_from_str = request.GET.get("date_from")
        date_to_str = request.GET.get("date_to")
        status_filter = request.GET.get("status")

        # Convert date strings to date objects
        date_from = None
        date_to = None

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "error": "Invalid date_from format. Use YYYY-MM-DD",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "error": "Invalid date_to format. Use YYYY-MM-DD",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Validate date range
        if date_from and date_to and date_from > date_to:
            return Response(
                {
                    "success": False,
                    "error": "date_from must be before or equal to date_to",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get filtered lessons (already optimized with select_related)
        lessons = AdminScheduleService.get_all_lessons(
            teacher_id=teacher_id,
            subject_id=subject_id,
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            status=status_filter,
        )

        # Оптимизация: получаем count из queryset ДО сериализации
        # Это выполняет COUNT(*) запрос вместо загрузки всех записей в память
        total_count = lessons.count()

        # Применяем пагинацию для оптимизации при большом количестве записей
        paginator = LessonPagination()
        page = paginator.paginate_queryset(lessons, request)

        if page is not None:
            # Сериализуем только текущую страницу
            serializer = AdminLessonSerializer(page, many=True)
            # Возвращаем пагинированный ответ с count, next, previous, results
            return Response(
                {
                    "success": True,
                    "count": total_count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "results": serializer.data,
                }
            )

        # Fallback если пагинация отключена (например, для совместимости)
        serializer = AdminLessonSerializer(lessons, many=True)
        return Response(
            {"success": True, "count": total_count, "results": serializer.data}
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_schedule_stats_view(request):
    """
    Get schedule statistics for admin dashboard.

    Returns:
    - Total lessons count
    - Today's lessons count
    - Week ahead lessons count
    - Lessons by status counts
    """
    try:
        stats = AdminScheduleService.get_schedule_stats()
        return Response({"success": True, "stats": stats})
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_schedule_filters_view(request):
    """
    Get filter options for schedule (teachers, subjects, students).

    Returns:
    - List of teachers with id and name
    - List of subjects with id and name
    - List of students with id and name
    """
    try:
        teachers = AdminScheduleService.get_teachers_list()
        subjects = AdminScheduleService.get_subjects_list()
        students = AdminScheduleService.get_students_list()

        return Response(
            {
                "success": True,
                "teachers": teachers,
                "subjects": subjects,
                "students": students,
            }
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_create_lesson_view(request):
    """
    Create a new lesson as admin.

    Admin can create lessons on behalf of any teacher.

    Request body:
    - teacher: teacher user ID (required)
    - student: student user ID (required)
    - subject: subject ID (required)
    - date: lesson date YYYY-MM-DD (required)
    - start_time: start time HH:MM:SS (required)
    - end_time: end time HH:MM:SS (required)
    - description: optional description
    - telemost_link: optional video call link

    Returns:
    - Created lesson data with teacher_name, student_name, subject_name
    """
    try:
        # Extract data from request
        teacher_id = request.data.get("teacher")
        student_id = request.data.get("student")
        subject_id = request.data.get("subject")
        date_str = request.data.get("date")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        description = request.data.get("description", "")
        telemost_link = request.data.get("telemost_link", "")

        # Validate required fields
        if not all([teacher_id, student_id, subject_id, date_str, start_time, end_time]):
            return Response(
                {
                    "success": False,
                    "error": "Missing required fields: teacher, student, subject, date, start_time, end_time",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get teacher
        try:
            teacher = User.objects.get(id=teacher_id, role="teacher")
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": f"Teacher with id {teacher_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get student
        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": f"Student with id {student_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get subject
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response(
                {"success": False, "error": f"Subject with id {subject_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parse date
        try:
            lesson_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse times
        try:
            from datetime import time as dt_time

            start_parts = start_time.split(":")
            end_parts = end_time.split(":")
            start_time_obj = dt_time(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]) if len(start_parts) > 2 else 0)
            end_time_obj = dt_time(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]) if len(end_parts) > 2 else 0)
        except (ValueError, IndexError):
            return Response(
                {"success": False, "error": "Invalid time format. Use HH:MM or HH:MM:SS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create lesson using LessonService
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=lesson_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            description=description,
            telemost_link=telemost_link,
        )

        logger.info(
            f"[admin_create_lesson] Admin {request.user.id} created lesson {lesson.id} "
            f"for teacher {teacher.id} and student {student.id}"
        )

        # Serialize and return
        serializer = AdminLessonSerializer(lesson)
        return Response(
            {"success": True, **serializer.data},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"[admin_create_lesson] Error: {str(e)}", exc_info=True)
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
