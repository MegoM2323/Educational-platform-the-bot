"""
Parent views for lesson scheduling system.

Provides API endpoints for parents to view schedules of their children.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Prefetch

from accounts.models import User, StudentProfile
from .models import Lesson
from .permissions import IsParent
from .serializers import LessonSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def get_child_schedule(request, child_id):
    """
    Получить расписание конкретного ребёнка (для родителя).

    GET /api/scheduling/parent/children/{child_id}/schedule/

    Query params:
        date_from: Filter lessons from this date (YYYY-MM-DD)
        date_to: Filter lessons until this date (YYYY-MM-DD)
        subject_id: Filter by subject ID
        status: Filter by lesson status

    Args:
        request: HTTP request with authenticated parent
        child_id: ID ребёнка (студента)

    Returns:
        Response with student info, lessons, and total count

    Raises:
        404: Ребёнок не найден
        403: Ребёнок не принадлежит этому родителю
    """
    # Проверить что ребёнок существует и имеет роль student
    child = get_object_or_404(User, id=child_id, role=User.Role.STUDENT)

    # Проверить что ребёнок принадлежит этому родителю
    try:
        student_profile = StudentProfile.objects.get(user=child, parent=request.user)
    except StudentProfile.DoesNotExist:
        return Response(
            {"error": "Child not assigned to you"}, status=status.HTTP_403_FORBIDDEN
        )

    # Получить уроки ребёнка с оптимизацией запросов
    lessons = (
        Lesson.objects.filter(student=child)
        .select_related("teacher", "student", "subject")
        .order_by("date", "start_time")
    )

    # Применить фильтры
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")
    subject_id = request.query_params.get("subject_id")
    lesson_status = request.query_params.get("status")

    if date_from:
        lessons = lessons.filter(date__gte=date_from)
    if date_to:
        lessons = lessons.filter(date__lte=date_to)
    if subject_id:
        lessons = lessons.filter(subject_id=subject_id)
    if lesson_status:
        lessons = lessons.filter(status=lesson_status)

    # Вычисляем count до сериализации для эффективности
    total_count = lessons.count()

    # Сериализовать уроки используя LessonSerializer
    serializer = LessonSerializer(lessons, many=True)

    return Response(
        {
            "student": {
                "id": str(child.id),
                "name": child.get_full_name(),
                "email": child.email,
            },
            "lessons": serializer.data,
            "total_lessons": total_count,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsParent])
def get_all_children_schedules(request):
    """
    Получить расписания всех детей этого родителя.

    GET /api/scheduling/parent/schedule/

    Args:
        request: HTTP request with authenticated parent

    Returns:
        Response with all children, their lessons, and statistics
    """
    # Оптимизация N+1: Создаём Prefetch объект для уроков детей.
    # Это позволяет загрузить все уроки всех детей одним запросом вместо
    # отдельного запроса для каждого ребёнка (было N+1 queries, стало 2 queries).
    # Уроки сортируются по дате и времени начала.
    lessons_prefetch = Prefetch(
        "student_lessons",
        queryset=Lesson.objects.select_related("teacher", "subject").order_by(
            "date", "start_time"
        ),
        to_attr="prefetched_lessons",
    )

    # Получить всех детей этого родителя с оптимизацией.
    # prefetch_related загружает уроки одним дополнительным запросом.
    children = (
        User.objects.filter(
            role=User.Role.STUDENT, student_profile__parent=request.user
        )
        .select_related("student_profile")
        .prefetch_related(lessons_prefetch)
    )

    children_data = []
    for child in children:
        # Используем предзагруженные уроки (to_attr='prefetched_lessons')
        # вместо дополнительного запроса Lesson.objects.filter(student=child)
        lessons_list = []
        for lesson in child.prefetched_lessons:
            lessons_list.append(
                {
                    "id": str(lesson.id),
                    "teacher": lesson.teacher.get_full_name(),
                    "teacher_id": str(lesson.teacher.id),
                    "subject": lesson.subject.name if lesson.subject else None,
                    "subject_id": str(lesson.subject.id) if lesson.subject else None,
                    "date": lesson.date,
                    "start_time": lesson.start_time,
                    "end_time": lesson.end_time,
                    "status": lesson.status,
                }
            )

        children_data.append(
            {
                "id": str(child.id),
                "name": child.get_full_name(),
                "lessons": lessons_list,
            }
        )

    return Response(
        {
            "children": children_data,
            "total_children": len(children),
        }
    )
