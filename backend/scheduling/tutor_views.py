"""
Tutor views for lesson scheduling system.

Provides API endpoints for tutors to view schedules of their assigned students.
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
from .permissions import IsTutor


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTutor])
def get_student_schedule(request, student_id):
    """
    Получить расписание конкретного студента (для тьютора).

    GET /api/scheduling/tutor/students/{student_id}/schedule/

    Query params:
        date_from: Filter lessons from this date (YYYY-MM-DD)
        date_to: Filter lessons until this date (YYYY-MM-DD)
        subject_id: Filter by subject ID
        status: Filter by lesson status

    Args:
        request: HTTP request with authenticated tutor
        student_id: ID студента

    Returns:
        Response with student info, lessons, and total count

    Raises:
        404: Студент не найден
        403: Студент не назначен этому тьютору
    """
    # Проверить что студент существует и имеет роль student
    student = get_object_or_404(User, id=student_id, role=User.Role.STUDENT)

    # Проверить что студент принадлежит этому тьютору
    try:
        student_profile = StudentProfile.objects.get(user=student, tutor=request.user)
    except StudentProfile.DoesNotExist:
        return Response(
            {"error": "Student not assigned to you"}, status=status.HTTP_403_FORBIDDEN
        )

    # Получить уроки студента с оптимизацией запросов
    lessons = (
        Lesson.objects.filter(student=student)
        .select_related("teacher", "subject")
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

    # Сериализовать уроки
    lessons_list = list(lessons)
    lessons_data = []
    for lesson in lessons_list:
        lessons_data.append(
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
                "description": lesson.description,
                "telemost_link": lesson.telemost_link,
            }
        )

    return Response(
        {
            "student": {
                "id": str(student.id),
                "name": student.get_full_name(),
                "email": student.email,
            },
            "lessons": lessons_data,
            "total_lessons": len(lessons_data),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTutor])
def get_all_student_schedules(request):
    """
    Получить расписания всех студентов этого тьютора.

    GET /api/scheduling/tutor/schedule/

    Args:
        request: HTTP request with authenticated tutor

    Returns:
        Response with all students, their lessons, and statistics
    """
    # Оптимизация N+1: Создаём Prefetch объект для уроков студентов
    lessons_prefetch = Prefetch(
        "student_lessons",
        queryset=Lesson.objects.select_related("teacher", "subject").order_by(
            "date", "start_time"
        ),
        to_attr="prefetched_lessons",
    )

    # Получить всех студентов этого тьютора с оптимизацией
    # Удален select_related("student_profile") т.к. он не используется в response
    students = (
        User.objects.filter(role=User.Role.STUDENT, student_profile__tutor=request.user)
        .distinct()
        .prefetch_related(lessons_prefetch)
    )

    students_data = []
    for student in students:
        # Используем предзагруженные уроки вместо дополнительного запроса
        lessons_list = []
        for lesson in student.prefetched_lessons:
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

        students_data.append(
            {
                "id": str(student.id),
                "name": student.get_full_name(),
                "email": student.email,
                "lessons_count": len(lessons_list),
                "next_lesson": _get_next_lesson_data(student.prefetched_lessons),
                "lessons": lessons_list,
            }
        )

    return Response(
        {
            "students": students_data,
            "total_students": len(students),
        }
    )


def _get_next_lesson_data(lessons):
    """
    Получить данные следующего предстоящего урока.

    Args:
        lessons: QuerySet уроков, отсортированных по date и start_time

    Returns:
        dict с данными следующего урока или None если нет предстоящих уроков
    """
    now = timezone.now()
    today = now.date()

    for lesson in lessons:
        # Проверяем что урок в будущем
        if lesson.date > today:
            return {
                "id": str(lesson.id),
                "teacher": lesson.teacher.get_full_name(),
                "teacher_id": str(lesson.teacher.id),
                "date": lesson.date,
                "start_time": lesson.start_time,
            }
        elif lesson.date == today:
            # Если урок сегодня, проверяем время
            lesson_time = timezone.datetime.combine(lesson.date, lesson.start_time)
            lesson_time = (
                timezone.make_aware(lesson_time)
                if not timezone.is_aware(lesson_time)
                else lesson_time
            )
            if lesson_time > now:
                return {
                    "id": str(lesson.id),
                    "teacher": lesson.teacher.get_full_name(),
                    "teacher_id": str(lesson.teacher.id),
                    "date": lesson.date,
                    "start_time": lesson.start_time,
                }

    return None
