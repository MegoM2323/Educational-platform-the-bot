"""
Admin views for schedule management.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import datetime

from accounts.permissions import IsAdminUser
from scheduling.admin_schedule_service import AdminScheduleService
from scheduling.serializers import AdminLessonSerializer
from scheduling.views import LessonPagination


@api_view(['GET'])
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
        teacher_id = request.GET.get('teacher_id')
        subject_id = request.GET.get('subject_id')
        student_id = request.GET.get('student_id')
        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')
        status_filter = request.GET.get('status')

        # Convert date strings to date objects
        date_from = None
        date_to = None

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'success': False, 'error': 'Invalid date_from format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'success': False, 'error': 'Invalid date_to format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate date range
        if date_from and date_to and date_from > date_to:
            return Response(
                {'success': False, 'error': 'date_from must be before or equal to date_to'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get filtered lessons (already optimized with select_related)
        lessons = AdminScheduleService.get_all_lessons(
            teacher_id=teacher_id,
            subject_id=subject_id,
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            status=status_filter
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
            return Response({
                'success': True,
                'count': total_count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': serializer.data
            })

        # Fallback если пагинация отключена (например, для совместимости)
        serializer = AdminLessonSerializer(lessons, many=True)
        return Response({
            'success': True,
            'count': total_count,
            'results': serializer.data
        })

    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
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
        return Response({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
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

        return Response({
            'success': True,
            'teachers': teachers,
            'subjects': subjects,
            'students': students
        })
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )