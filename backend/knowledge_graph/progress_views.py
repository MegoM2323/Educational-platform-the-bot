"""
Views for Element and Lesson Progress (T401, T402)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
import logging

from .models import Element, ElementProgress, LessonProgress, GraphLesson
from .progress_serializers import (
    ElementProgressSerializer,
    SaveElementProgressSerializer,
    LessonProgressSerializer,
    UpdateLessonStatusSerializer
)
from .dependency_service import PrerequisiteChecker

logger = logging.getLogger(__name__)


class SaveElementProgressView(APIView):
    """
    POST /api/knowledge-graph/elements/{element_id}/progress/ - сохранить ответ на элемент

    Body:
    {
        "answer": <varies by element type>,
        "graph_lesson_id": 123
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, element_id):
        try:
            # Получить элемент
            element = Element.objects.get(id=element_id)

            # Получить graph_lesson_id
            graph_lesson_id = request.data.get('graph_lesson_id')
            if not graph_lesson_id:
                return Response(
                    {'success': False, 'error': 'graph_lesson_id обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получить GraphLesson
            graph_lesson = GraphLesson.objects.select_related('graph', 'lesson').get(id=graph_lesson_id)

            # Проверка что студент принадлежит графу
            if graph_lesson.graph.student != request.user:
                return Response(
                    {'success': False, 'error': 'Вы не являетесь студентом этого графа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Проверка что элемент принадлежит уроку
            if not graph_lesson.lesson.elements.filter(id=element_id).exists():
                return Response(
                    {'success': False, 'error': 'Элемент не принадлежит этому уроку'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Валидация ответа
            serializer = SaveElementProgressSerializer(
                data=request.data,
                context={'element': element}
            )
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            answer = serializer.validated_data['answer']

            # Рассчитать балл
            score = self._calculate_score(element, answer)

            # Создать или обновить прогресс
            with transaction.atomic():
                progress, created = ElementProgress.objects.get_or_create(
                    student=request.user,
                    element=element,
                    graph_lesson=graph_lesson,
                    defaults={
                        'max_score': element.max_score,
                        'status': 'not_started'
                    }
                )

                # Обновить данные
                if created or progress.status == 'not_started':
                    progress.start()

                progress.complete(answer=answer, score=score)

                # Обновить прогресс урока
                lesson_progress, _ = LessonProgress.objects.get_or_create(
                    student=request.user,
                    graph_lesson=graph_lesson,
                    defaults={
                        'total_elements': graph_lesson.lesson.elements.count(),
                        'max_possible_score': graph_lesson.lesson.total_max_score
                    }
                )

                if lesson_progress.status == 'not_started':
                    lesson_progress.start()

                lesson_progress.update_progress()

                # Проверить разблокировку следующих уроков
                lesson_progress.check_unlock_next()

            result_serializer = ElementProgressSerializer(progress)
            return Response({
                'success': True,
                'data': result_serializer.data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Element.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except GraphLesson.DoesNotExist:
            return Response(
                {'success': False, 'error': 'GraphLesson не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in SaveElementProgressView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при сохранении прогресса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _calculate_score(self, element, answer):
        """
        Рассчитать балл за ответ

        Args:
            element: Element объект
            answer: Dict с ответом

        Returns:
            int: количество баллов
        """
        element_type = element.element_type
        max_score = element.max_score

        # Текстовая задача - требует ручной проверки учителем
        if element_type == 'text_problem':
            return None  # Будет проверено учителем

        # Быстрый вопрос - автоматическая проверка
        elif element_type == 'quick_question':
            correct_answer = element.content.get('correct_answer')
            user_choice = answer.get('choice')

            if user_choice == correct_answer:
                return max_score
            else:
                return 0

        # Теория - просто просмотр
        elif element_type == 'theory':
            if answer.get('viewed'):
                return max_score
            return 0

        # Видео - проверка что досмотрел
        elif element_type == 'video':
            watched_until = answer.get('watched_until', 0)
            video_duration = element.content.get('duration', 0)

            if video_duration > 0:
                watch_percent = (watched_until / video_duration) * 100
                if watch_percent >= 90:  # Досмотрел 90% видео
                    return max_score
                else:
                    return int((watch_percent / 100) * max_score)
            else:
                return max_score

        return 0


class GetElementProgressView(APIView):
    """
    GET /api/knowledge-graph/elements/{element_id}/progress/{student_id}/ - получить прогресс студента
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, element_id, student_id):
        try:
            # Получить элемент
            element = Element.objects.get(id=element_id)

            # Проверка прав: учитель или сам студент
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(id=student_id, role='student')

            if request.user != student and request.user.role != 'teacher' and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'У вас нет прав для просмотра прогресса этого студента'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Получить graph_lesson_id (optional)
            graph_lesson_id = request.query_params.get('graph_lesson_id')

            if graph_lesson_id:
                # Прогресс по конкретному GraphLesson
                progress = ElementProgress.objects.filter(
                    student=student,
                    element=element,
                    graph_lesson_id=graph_lesson_id
                ).select_related('element', 'student').first()

                if not progress:
                    return Response({
                        'success': True,
                        'data': None,
                        'message': 'Прогресс не найден'
                    }, status=status.HTTP_200_OK)

                serializer = ElementProgressSerializer(progress)
                return Response({
                    'success': True,
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                # Все прогрессы студента по этому элементу
                progress_list = ElementProgress.objects.filter(
                    student=student,
                    element=element
                ).select_related('element', 'student', 'graph_lesson')

                serializer = ElementProgressSerializer(progress_list, many=True)
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'count': progress_list.count()
                }, status=status.HTTP_200_OK)

        except Element.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GetElementProgressView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении прогресса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetLessonProgressView(APIView):
    """
    GET /api/knowledge-graph/lessons/{lesson_id}/progress/{student_id}/ - получить прогресс по уроку
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id, student_id):
        try:
            # Проверка прав
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(id=student_id, role='student')

            if request.user != student and request.user.role != 'teacher' and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'У вас нет прав для просмотра прогресса этого студента'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Получить graph_lesson_id
            graph_lesson_id = request.query_params.get('graph_lesson_id')
            if not graph_lesson_id:
                return Response(
                    {'success': False, 'error': 'graph_lesson_id обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получить GraphLesson
            graph_lesson = GraphLesson.objects.select_related('lesson', 'graph').get(id=graph_lesson_id)

            # Получить прогресс
            progress = LessonProgress.objects.filter(
                student=student,
                graph_lesson=graph_lesson
            ).select_related('student', 'graph_lesson', 'graph_lesson__lesson').first()

            if not progress:
                # Прогресс еще не начат
                return Response({
                    'success': True,
                    'data': {
                        'status': 'not_started',
                        'completion_percent': 0,
                        'percentage': 0,
                        'completed_elements': 0,
                        'total_elements': graph_lesson.lesson.elements.count(),
                        'total_score': 0,
                        'max_possible_score': graph_lesson.lesson.total_max_score,
                        'can_start': None
                    }
                }, status=status.HTTP_200_OK)

            # Проверить prerequisite
            can_start_result = PrerequisiteChecker.can_start_lesson(student, graph_lesson)

            serializer = LessonProgressSerializer(progress)
            data = serializer.data
            data['can_start'] = can_start_result

            return Response({
                'success': True,
                'data': data
            }, status=status.HTTP_200_OK)

        except GraphLesson.DoesNotExist:
            return Response(
                {'success': False, 'error': 'GraphLesson не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GetLessonProgressView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении прогресса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateLessonStatusView(APIView):
    """
    PATCH /api/knowledge-graph/lessons/{lesson_id}/progress/{student_id}/ - обновить статус урока
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, lesson_id, student_id):
        try:
            # Проверка прав (только студент может обновлять свой статус)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(id=student_id, role='student')

            if request.user != student:
                return Response(
                    {'success': False, 'error': 'Вы можете обновлять только свой прогресс'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Получить graph_lesson_id
            graph_lesson_id = request.data.get('graph_lesson_id')
            if not graph_lesson_id:
                return Response(
                    {'success': False, 'error': 'graph_lesson_id обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получить GraphLesson
            graph_lesson = GraphLesson.objects.select_related('lesson', 'graph').get(id=graph_lesson_id)

            # Проверка prerequisite
            can_start_result = PrerequisiteChecker.can_start_lesson(student, graph_lesson)
            if not can_start_result['can_start']:
                return Response(
                    {
                        'success': False,
                        'error': 'Не выполнены prerequisite для этого урока',
                        'details': can_start_result
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Валидация данных
            serializer = UpdateLessonStatusSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            new_status = serializer.validated_data['status']

            # Получить или создать прогресс
            with transaction.atomic():
                progress, created = LessonProgress.objects.get_or_create(
                    student=student,
                    graph_lesson=graph_lesson,
                    defaults={
                        'total_elements': graph_lesson.lesson.elements.count(),
                        'max_possible_score': graph_lesson.lesson.total_max_score,
                        'status': 'not_started'
                    }
                )

                # Обновить статус
                if new_status == 'in_progress' and progress.status == 'not_started':
                    progress.start()
                elif new_status == 'completed':
                    # Проверка что все элементы завершены
                    if progress.completion_percent < 100:
                        return Response(
                            {'success': False, 'error': 'Невозможно завершить урок - не все элементы выполнены'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    progress.status = 'completed'
                    progress.completed_at = timezone.now()
                    progress.save(update_fields=['status', 'completed_at'])

                    # Разблокировать следующие уроки
                    progress.check_unlock_next()
                else:
                    progress.status = new_status
                    progress.save(update_fields=['status'])

            result_serializer = LessonProgressSerializer(progress)
            return Response({
                'success': True,
                'data': result_serializer.data
            }, status=status.HTTP_200_OK)

        except GraphLesson.DoesNotExist:
            return Response(
                {'success': False, 'error': 'GraphLesson не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in UpdateLessonStatusView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при обновлении статуса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
