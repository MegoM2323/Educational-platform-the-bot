"""
Views for Dependency Management (T303)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
import logging

from .models import LessonDependency, GraphLesson, KnowledgeGraph
from .dependency_serializers import DependencySerializer, AddDependencySerializer
from .dependency_service import DependencyCycleDetector, PrerequisiteChecker

logger = logging.getLogger(__name__)


class DependenciesView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/dependencies/ - получить зависимости урока
    POST /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/dependencies/ - добавить зависимость

    POST Body:
    {
        "prerequisite_lesson_id": 123,
        "dependency_type": "required",
        "min_score_percent": 80
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, graph_id, lesson_id):
        """Получить все зависимости урока"""
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('student', 'created_by').get(id=graph_id)

            # Проверка прав
            if graph.student != request.user and graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'У вас нет доступа к этому графу'},
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

            # Получить все зависимости где этот урок является зависимым (incoming)
            incoming_deps = LessonDependency.objects.filter(
                to_lesson=graph_lesson
            ).select_related('from_lesson', 'from_lesson__lesson', 'to_lesson', 'to_lesson__lesson')

            # Получить все зависимости где этот урок является prerequisite (outgoing)
            outgoing_deps = LessonDependency.objects.filter(
                from_lesson=graph_lesson
            ).select_related('from_lesson', 'from_lesson__lesson', 'to_lesson', 'to_lesson__lesson')

            incoming_serializer = DependencySerializer(incoming_deps, many=True)
            outgoing_serializer = DependencySerializer(outgoing_deps, many=True)

            return Response({
                'success': True,
                'data': {
                    'incoming': incoming_serializer.data,  # Prerequisite для этого урока
                    'outgoing': outgoing_serializer.data,  # Уроки зависящие от этого
                }
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in DependenciesView.get: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении зависимостей: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, graph_id, lesson_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by').get(id=graph_id)

            # Проверка прав (только создатель графа)
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может добавлять зависимости'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Найти зависимый урок (to_lesson)
            to_lesson = GraphLesson.objects.filter(
                graph=graph,
                lesson_id=lesson_id
            ).first()

            if not to_lesson:
                return Response(
                    {'success': False, 'error': 'Урок не найден в графе'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Валидация данных
            serializer = AddDependencySerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            prerequisite_lesson_id = serializer.validated_data['prerequisite_lesson_id']
            dependency_type = serializer.validated_data['dependency_type']
            min_score_percent = serializer.validated_data['min_score_percent']

            # Найти prerequisite урок (from_lesson)
            from_lesson = GraphLesson.objects.filter(
                id=prerequisite_lesson_id,
                graph=graph
            ).first()

            if not from_lesson:
                return Response(
                    {'success': False, 'error': 'Prerequisite урок не найден в этом графе'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Проверка что уроки не совпадают
            if from_lesson == to_lesson:
                return Response(
                    {'success': False, 'error': 'Урок не может зависеть от самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверка что зависимость не существует
            if LessonDependency.objects.filter(
                graph=graph,
                from_lesson=from_lesson,
                to_lesson=to_lesson
            ).exists():
                return Response(
                    {'success': False, 'error': 'Такая зависимость уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверка на циклы
            cycle_detector = DependencyCycleDetector(graph)
            if cycle_detector.has_cycle(from_lesson.id, to_lesson.id):
                return Response(
                    {'success': False, 'error': 'Добавление этой зависимости создаст цикл в графе'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создать зависимость
            with transaction.atomic():
                dependency = LessonDependency.objects.create(
                    graph=graph,
                    from_lesson=from_lesson,
                    to_lesson=to_lesson,
                    dependency_type=dependency_type,
                    min_score_percent=min_score_percent
                )

            result_serializer = DependencySerializer(dependency)
            return Response({
                'success': True,
                'data': result_serializer.data
            }, status=status.HTTP_201_CREATED)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in DependenciesView.post: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при добавлении зависимости: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RemoveDependencyView(APIView):
    """
    DELETE /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/dependencies/{dependency_id}/ - удалить зависимость
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, graph_id, lesson_id, dependency_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может удалять зависимости'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Найти зависимость
            dependency = LessonDependency.objects.filter(
                id=dependency_id,
                graph=graph,
                to_lesson__lesson_id=lesson_id
            ).first()

            if not dependency:
                return Response(
                    {'success': False, 'error': 'Зависимость не найдена'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Удалить
            dependency.delete()

            # FIX T008: HTTP 204 No Content не должен содержать тело ответа
            return Response(status=status.HTTP_204_NO_CONTENT)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in RemoveDependencyView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при удалении зависимости: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckPrerequisitesView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/can-start/ - проверить может ли студент начать урок
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, graph_id, lesson_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('student').get(id=graph_id)

            # Проверка что это студент графа
            if graph.student != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'У вас нет доступа к этому графу'},
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

            # Проверить prerequisite
            result = PrerequisiteChecker.can_start_lesson(graph.student, graph_lesson)

            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in CheckPrerequisitesView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при проверке prerequisite: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
