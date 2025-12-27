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

from accounts.models import User, StudentProfile
from .models import Lesson
from .permissions import IsTutor


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTutor])
def get_student_schedule(request, student_id):
    """
    Получить расписание конкретного студента (для тьютора).

    GET /api/scheduling/tutor/students/{student_id}/schedule/

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
    student = get_object_or_404(User, id=student_id, role='student')
    student_profile = get_object_or_404(StudentProfile, user=student)

    # Проверить что студент принадлежит этому тьютору
    if student_profile.tutor_id != request.user.id:
        return Response(
            {'error': 'Student not assigned to you'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Получить уроки студента с оптимизацией запросов
    lessons = Lesson.objects.filter(
        student=student
    ).select_related('teacher', 'subject').order_by('date', 'start_time')

    # Сериализовать уроки
    lessons_data = []
    for lesson in lessons:
        lessons_data.append({
            'id': str(lesson.id),
            'teacher': lesson.teacher.get_full_name(),
            'teacher_id': lesson.teacher.id,
            'subject': lesson.subject.name if lesson.subject else None,
            'subject_id': lesson.subject.id if lesson.subject else None,
            'date': lesson.date,
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'status': lesson.status,
            'description': lesson.description,
            'telemost_link': lesson.telemost_link,
        })

    return Response({
        'student': {
            'id': student.id,
            'name': student.get_full_name(),
            'email': student.email,
        },
        'lessons': lessons_data,
        'total_lessons': len(lessons),
    })


@api_view(['GET'])
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
    # Получить всех студентов этого тьютора с оптимизацией
    students = User.objects.filter(
        role='student',
        student_profile__tutor=request.user
    ).select_related('student_profile').prefetch_related('student_lessons')

    students_data = []
    for student in students:
        # Получить уроки студента с оптимизацией
        lessons = Lesson.objects.filter(
            student=student
        ).select_related('teacher', 'subject').order_by('date', 'start_time')

        # Сериализовать уроки
        lessons_list = []
        for lesson in lessons:
            lessons_list.append({
                'id': str(lesson.id),
                'teacher': lesson.teacher.get_full_name(),
                'teacher_id': lesson.teacher.id,
                'subject': lesson.subject.name if lesson.subject else None,
                'subject_id': lesson.subject.id if lesson.subject else None,
                'date': lesson.date,
                'start_time': lesson.start_time,
                'end_time': lesson.end_time,
                'status': lesson.status,
            })

        students_data.append({
            'id': student.id,
            'name': student.get_full_name(),
            'email': student.email,
            'lessons_count': lessons.count(),
            'next_lesson': _get_next_lesson_data(lessons),
            'lessons': lessons_list,
        })

    return Response({
        'students': students_data,
        'total_students': len(students),
    })


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
                'id': str(lesson.id),
                'teacher': lesson.teacher.get_full_name(),
                'teacher_id': lesson.teacher.id,
                'date': lesson.date,
                'start_time': lesson.start_time,
            }
        elif lesson.date == today:
            # Если урок сегодня, проверяем время
            lesson_time = timezone.datetime.combine(lesson.date, lesson.start_time)
            lesson_time = timezone.make_aware(lesson_time) if not timezone.is_aware(lesson_time) else lesson_time
            if lesson_time > now:
                return {
                    'id': str(lesson.id),
                    'teacher': lesson.teacher.get_full_name(),
                    'teacher_id': lesson.teacher.id,
                    'date': lesson.date,
                    'start_time': lesson.start_time,
                }

    return None
