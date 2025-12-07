"""
Views for KnowledgeGraph CRUD and Management (T301, T302)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from django.contrib.auth import get_user_model
import logging

from .models import KnowledgeGraph, GraphLesson, Lesson
from .graph_serializers import (
    KnowledgeGraphSerializer,
    GraphLessonSerializer,
    AddLessonToGraphSerializer,
    UpdateLessonPositionSerializer,
    BatchUpdateLessonsSerializer
)
from .permissions import IsTeacherOrAdmin, IsGraphOwner, IsStudentOfGraph

logger = logging.getLogger(__name__)
User = get_user_model()


class GetOrCreateGraphView(APIView):
    """
    GET /api/knowledge-graph/students/{student_id}/subject/{subject_id}/ - получить или создать граф
    POST /api/knowledge-graph/students/{student_id}/subject/{subject_id}/ - создать граф
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, student_id, subject_id):
        """Получить существующий граф или создать новый"""
        try:
            # Проверка что student существует и является студентом
            student = User.objects.filter(id=student_id, role='student').first()
            if not student:
                return Response(
                    {'success': False, 'error': 'Студент не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Проверка что subject существует
            from materials.models import Subject
            subject = Subject.objects.filter(id=subject_id).first()
            if not subject:
                return Response(
                    {'success': False, 'error': 'Предмет не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Получить или создать граф
            graph, created = KnowledgeGraph.objects.get_or_create(
                student=student,
                subject=subject,
                defaults={'created_by': request.user}
            )

            serializer = KnowledgeGraphSerializer(graph)
            return Response({
                'success': True,
                'data': serializer.data,
                'created': created
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in GetOrCreateGraphView.get: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении графа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, student_id, subject_id):
        """Создать новый граф (если не существует)"""
        try:
            # Проверка что student существует и является студентом
            student = User.objects.filter(id=student_id, role='student').first()
            if not student:
                return Response(
                    {'success': False, 'error': 'Студент не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Проверка что subject существует
            from materials.models import Subject
            subject = Subject.objects.filter(id=subject_id).first()
            if not subject:
                return Response(
                    {'success': False, 'error': 'Предмет не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Проверка что граф не существует
            if KnowledgeGraph.objects.filter(student=student, subject=subject).exists():
                return Response(
                    {'success': False, 'error': 'Граф для этого студента и предмета уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создать граф
            graph = KnowledgeGraph.objects.create(
                student=student,
                subject=subject,
                created_by=request.user,
                is_active=True,
                allow_skip=request.data.get('allow_skip', False)
            )

            serializer = KnowledgeGraphSerializer(graph)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error in GetOrCreateGraphView.post: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при создании графа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddLessonToGraphView(APIView):
    """
    POST /api/knowledge-graph/{graph_id}/lessons/ - добавить урок в граф

    Body:
    {
        "lesson_id": 123,
        "position_x": 100,
        "position_y": 200,
        "node_color": "#4F46E5",
        "node_size": 50
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, graph_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by', 'student', 'subject').get(id=graph_id)

            # Проверка прав (только создатель графа)
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может добавлять уроки'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Валидация данных
            serializer = AddLessonToGraphSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            lesson_id = serializer.validated_data['lesson_id']
            position_x = serializer.validated_data['position_x']
            position_y = serializer.validated_data['position_y']
            node_color = serializer.validated_data['node_color']
            node_size = serializer.validated_data['node_size']

            # Получить урок
            lesson = Lesson.objects.get(id=lesson_id)

            # Проверка что урок того же предмета
            if lesson.subject != graph.subject:
                return Response(
                    {'success': False, 'error': 'Урок должен быть по тому же предмету что и граф'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверка что урок еще не добавлен
            if GraphLesson.objects.filter(graph=graph, lesson=lesson).exists():
                return Response(
                    {'success': False, 'error': 'Урок уже добавлен в граф'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создать GraphLesson
            graph_lesson = GraphLesson.objects.create(
                graph=graph,
                lesson=lesson,
                position_x=position_x,
                position_y=position_y,
                node_color=node_color,
                node_size=node_size,
                is_unlocked=False  # По умолчанию заблокирован
            )

            result_serializer = GraphLessonSerializer(graph_lesson)
            return Response({
                'success': True,
                'data': result_serializer.data
            }, status=status.HTTP_201_CREATED)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Lesson.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Урок не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in AddLessonToGraphView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при добавлении урока: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RemoveLessonFromGraphView(APIView):
    """
    DELETE /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/ - удалить урок из графа
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, graph_id, lesson_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может удалять уроки'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Найти GraphLesson
            graph_lesson = GraphLesson.objects.filter(
                graph=graph,
                lesson_id=lesson_id
            ).first()

            if not graph_lesson:
                return Response(
                    {'success': False, 'error': 'Урок не найден в графе'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Удалить (каскадно удалятся зависимости)
            with transaction.atomic():
                graph_lesson.delete()

            return Response({
                'success': True,
                'message': 'Урок успешно удален из графа'
            }, status=status.HTTP_204_NO_CONTENT)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in RemoveLessonFromGraphView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при удалении урока: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateLessonPositionView(APIView):
    """
    PATCH /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/ - обновить позицию урока
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, graph_id, lesson_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может обновлять позиции'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Найти GraphLesson
            graph_lesson = GraphLesson.objects.filter(
                graph=graph,
                lesson_id=lesson_id
            ).first()

            if not graph_lesson:
                return Response(
                    {'success': False, 'error': 'Урок не найден в графе'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Валидация данных
            serializer = UpdateLessonPositionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Обновить поля
            if 'position_x' in serializer.validated_data:
                graph_lesson.position_x = serializer.validated_data['position_x']
            if 'position_y' in serializer.validated_data:
                graph_lesson.position_y = serializer.validated_data['position_y']
            if 'node_color' in serializer.validated_data:
                graph_lesson.node_color = serializer.validated_data['node_color']
            if 'node_size' in serializer.validated_data:
                graph_lesson.node_size = serializer.validated_data['node_size']

            graph_lesson.save()

            result_serializer = GraphLessonSerializer(graph_lesson)
            return Response({
                'success': True,
                'data': result_serializer.data
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in UpdateLessonPositionView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при обновлении позиции: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GraphLessonsListOrAddView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/lessons/ - список уроков в графе
    POST /api/knowledge-graph/{graph_id}/lessons/ - добавить урок в граф

    POST Body:
    {
        "lesson_id": 123,
        "position_x": 100,
        "position_y": 200,
        "node_color": "#4F46E5",
        "node_size": 50
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, graph_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('student', 'created_by').get(id=graph_id)

            # Проверка прав (студент видит свой граф, учитель - созданный им)
            if graph.student != request.user and graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'У вас нет доступа к этому графу'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Получить все уроки с оптимизацией запросов
            graph_lessons = GraphLesson.objects.filter(
                graph=graph
            ).select_related('lesson', 'lesson__created_by', 'lesson__subject').prefetch_related(
                'lesson__elements'
            ).order_by('added_at')

            # Для каждого урока получить прогресс студента
            from .models import LessonProgress
            lessons_data = []

            for gl in graph_lessons:
                lesson_data = GraphLessonSerializer(gl).data

                # Получить прогресс
                progress = LessonProgress.objects.filter(
                    student=graph.student,
                    graph_lesson=gl
                ).first()

                if progress:
                    lesson_data['progress'] = {
                        'status': progress.status,
                        'completion_percent': progress.completion_percent,
                        'total_score': progress.total_score,
                        'max_possible_score': progress.max_possible_score,
                    }
                else:
                    lesson_data['progress'] = {
                        'status': 'not_started',
                        'completion_percent': 0,
                        'total_score': 0,
                        'max_possible_score': gl.lesson.total_max_score,
                    }

                lessons_data.append(lesson_data)

            return Response({
                'success': True,
                'data': lessons_data,
                'count': len(lessons_data)
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GraphLessonsListView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении уроков: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchUpdateLessonsView(APIView):
    """
    PATCH /api/knowledge-graph/{graph_id}/lessons/ - batch обновление позиций

    Body:
    {
        "lessons": [
            {"lesson_id": 1, "position_x": 100, "position_y": 200},
            {"lesson_id": 2, "position_x": 300, "position_y": 400}
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, graph_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может обновлять позиции'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Валидация данных
            serializer = BatchUpdateLessonsSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            lessons_data = serializer.validated_data['lessons']

            # Обновить все уроки в транзакции
            updated_count = 0
            with transaction.atomic():
                for lesson_update in lessons_data:
                    lesson_id = lesson_update['lesson_id']
                    position_x = lesson_update['position_x']
                    position_y = lesson_update['position_y']

                    graph_lesson = GraphLesson.objects.filter(
                        graph=graph,
                        lesson_id=lesson_id
                    ).first()

                    if graph_lesson:
                        graph_lesson.position_x = position_x
                        graph_lesson.position_y = position_y
                        graph_lesson.save(update_fields=['position_x', 'position_y'])
                        updated_count += 1

            return Response({
                'success': True,
                'message': f'Обновлено {updated_count} уроков'
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in BatchUpdateLessonsView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при batch обновлении: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
