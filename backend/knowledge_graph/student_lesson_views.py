"""
Views for Student Lesson Viewer (T014)
API endpoints для прохождения уроков студентом
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import logging

from scheduling.permissions import IsStudent
from .models import (
    GraphLesson,
    LessonElement,
    Element,
    ElementProgress,
    LessonProgress,
    LessonDependency,
)
from .progress_serializers import ElementProgressSerializer, LessonProgressSerializer
from .progress_sync_service import ProgressSyncService

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def get_student_lesson(request, graph_lesson_id):
    """
    Получить урок для студента с элементами и прогрессом

    GET /api/knowledge-graph/student/lessons/{graph_lesson_id}/

    Response:
    {
        "lesson": {
            "id": 1,
            "title": "Урок 1",
            "description": "Описание",
            "total_elements": 5
        },
        "elements": [
            {
                "id": 1,
                "order": 0,
                "title": "Элемент 1",
                "type": "text_problem",
                "content": {...},
                "status": "not_started",
                "score": null,
                "max_score": 100
            }
        ],
        "progress": {
            "status": "not_started",
            "completion_percent": 0,
            "total_score": 0,
            "completed_at": null
        },
        "next_element_id": 1
    }
    """
    try:
        # Получить GraphLesson (404 если не существует)
        graph_lesson = get_object_or_404(
            GraphLesson.objects.select_related("lesson", "graph"), id=graph_lesson_id
        )

        # Проверить доступ студента (403 если не принадлежит)
        if graph_lesson.graph.student != request.user:
            return Response(
                {"success": False, "error": "Доступ запрещен"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lesson = graph_lesson.lesson

        # Получить элементы урока в правильном порядке
        lesson_elements = (
            LessonElement.objects.filter(lesson=lesson).select_related("element").order_by("order")
        )

        # Получить или создать прогресс урока
        lesson_progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            graph_lesson=graph_lesson,
            defaults={
                "total_elements": lesson_elements.count(),
                "max_possible_score": lesson.total_max_score,
            },
        )

        # FIX N+1: Bulk fetch существующих прогрессов + bulk_create для отсутствующих
        element_ids = [le.element_id for le in lesson_elements]
        existing_progress = ElementProgress.objects.filter(
            student=request.user,
            element_id__in=element_ids,
            graph_lesson=graph_lesson,
        )
        progress_map = {ep.element_id: ep for ep in existing_progress}

        elements_to_create = []
        for lesson_elem in lesson_elements:
            element = lesson_elem.element
            if element.id not in progress_map:
                elements_to_create.append(
                    ElementProgress(
                        student=request.user,
                        element=element,
                        graph_lesson=graph_lesson,
                        max_score=element.max_score,
                        status="not_started",
                    )
                )

        if elements_to_create:
            created = ElementProgress.objects.bulk_create(elements_to_create)
            for ep in created:
                progress_map[ep.element_id] = ep

        # Собрать данные по элементам с прогрессом
        elements_data = []
        next_element_id = None

        for lesson_elem in lesson_elements:
            element = lesson_elem.element
            elem_progress = progress_map[element.id]

            elements_data.append(
                {
                    "id": element.id,
                    "order": lesson_elem.order,
                    "title": element.title,
                    "description": element.description,
                    "type": element.element_type,
                    "content": element.content,
                    "status": elem_progress.status,
                    "score": elem_progress.score,
                    "max_score": elem_progress.max_score,
                    "attempts": elem_progress.attempts,
                    "time_spent_seconds": elem_progress.time_spent_seconds,
                    "is_optional": lesson_elem.is_optional,
                    "custom_instructions": lesson_elem.custom_instructions,
                }
            )

            # Найти первый незавершенный элемент
            if next_element_id is None and elem_progress.status != "completed":
                next_element_id = element.id

        return Response(
            {
                "success": True,
                "data": {
                    "lesson": {
                        "id": lesson.id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "total_elements": lesson_elements.count(),
                        "total_duration_minutes": lesson.total_duration_minutes,
                    },
                    "elements": elements_data,
                    "progress": {
                        "status": lesson_progress.status,
                        "completion_percent": lesson_progress.completion_percent,
                        "completed_elements": lesson_progress.completed_elements,
                        "total_elements": lesson_progress.total_elements,
                        "total_score": lesson_progress.total_score,
                        "max_possible_score": lesson_progress.max_possible_score,
                        "started_at": lesson_progress.started_at,
                        "completed_at": lesson_progress.completed_at,
                        "total_time_spent_seconds": lesson_progress.total_time_spent_seconds,
                    },
                    "next_element_id": next_element_id,
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in get_student_lesson: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Ошибка при получении урока: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def start_element(request, element_id):
    """
    Начать прохождение элемента

    POST /api/knowledge-graph/student/elements/{element_id}/start/
    Body: { "graph_lesson_id": 123 }

    Response:
    {
        "success": true,
        "data": {
            "progress": {
                "status": "in_progress",
                "started_at": "2025-12-11T10:00:00Z",
                "attempts": 1
            }
        }
    }
    """
    try:
        element = get_object_or_404(Element, id=element_id)

        # Получить graph_lesson_id
        graph_lesson_id = request.data.get("graph_lesson_id")
        if not graph_lesson_id:
            return Response(
                {"success": False, "error": "graph_lesson_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверить доступ к GraphLesson
        graph_lesson = get_object_or_404(
            GraphLesson, id=graph_lesson_id, graph__student=request.user
        )

        # Проверить что элемент принадлежит уроку
        if not graph_lesson.lesson.elements.filter(id=element_id).exists():
            return Response(
                {"success": False, "error": "Элемент не принадлежит этому уроку"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получить или создать прогресс элемента
        elem_progress, created = ElementProgress.objects.get_or_create(
            student=request.user,
            element=element,
            graph_lesson=graph_lesson,
            defaults={"max_score": element.max_score, "status": "not_started"},
        )

        # Начать элемент если еще не начат
        if elem_progress.status == "not_started":
            elem_progress.start()

        # Автоматически начать урок если еще не начат
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            student=request.user,
            graph_lesson=graph_lesson,
            defaults={
                "total_elements": graph_lesson.lesson.elements.count(),
                "max_possible_score": graph_lesson.lesson.total_max_score,
            },
        )

        if lesson_progress.status == "not_started":
            lesson_progress.start()

        return Response(
            {
                "success": True,
                "data": {
                    "progress": {
                        "status": elem_progress.status,
                        "started_at": elem_progress.started_at,
                        "attempts": elem_progress.attempts,
                    }
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in start_element: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Ошибка при начале элемента: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def submit_element_answer(request, element_id):
    """
    Отправить ответ на элемент

    POST /api/knowledge-graph/student/elements/{element_id}/submit/
    Body: {
        "graph_lesson_id": 123,
        "answer": {...}  // Формат зависит от типа элемента
    }

    Response:
    {
        "success": true,
        "data": {
            "is_correct": true,
            "score": 100,
            "progress": {
                "status": "completed",
                "score": 100,
                "completed_at": "2025-12-11T10:05:00Z"
            }
        }
    }
    """
    try:
        element = get_object_or_404(Element, id=element_id)

        # Получить graph_lesson_id и answer
        graph_lesson_id = request.data.get("graph_lesson_id")
        answer = request.data.get("answer")

        if not graph_lesson_id:
            return Response(
                {"success": False, "error": "graph_lesson_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if answer is None:
            return Response(
                {"success": False, "error": "answer обязателен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверить доступ к GraphLesson
        graph_lesson = get_object_or_404(
            GraphLesson, id=graph_lesson_id, graph__student=request.user
        )

        # Получить прогресс элемента
        elem_progress = get_object_or_404(
            ElementProgress,
            student=request.user,
            element=element,
            graph_lesson=graph_lesson,
        )

        # Проверить ответ и вычислить балл
        is_correct, score = _evaluate_answer(element, answer)

        # Сохранить ответ с использованием transaction
        with transaction.atomic():
            # Для quick_question: неверный ответ оставляет status='in_progress' (разрешает retry)
            if element.element_type == "quick_question" and is_correct is False:
                # Сохранить ответ, но НЕ завершать элемент (можно повторить)
                # Примечание: attempts уже увеличен в start(), здесь не дублируем
                elem_progress.answer = answer
                elem_progress.score = 0
                elem_progress.status = "in_progress"
                elem_progress.save(update_fields=["answer", "score", "status"])
            else:
                # Для правильных ответов или других типов элементов: завершить нормально
                elem_progress.complete(answer=answer, score=score)

            # Обновить прогресс урока
            lesson_progress = LessonProgress.objects.get(
                student=request.user, graph_lesson=graph_lesson
            )
            lesson_progress.update_progress()

            # Автоматически завершить урок если все элементы пройдены
            (
                was_auto_completed,
                unlocked_lessons,
            ) = ProgressSyncService.auto_complete_lesson_if_all_elements_done(
                request.user, graph_lesson
            )

        # Определить можно ли повторить попытку
        can_retry = element.element_type == "quick_question" and is_correct is False

        return Response(
            {
                "success": True,
                "data": {
                    "is_correct": is_correct,
                    "score": score,
                    "can_retry": can_retry,
                    "progress": {
                        "status": elem_progress.status,
                        "score": elem_progress.score,
                        "completed_at": elem_progress.completed_at,
                        "time_spent_seconds": elem_progress.time_spent_seconds,
                        "attempts": elem_progress.attempts,
                    },
                    "lesson_auto_completed": was_auto_completed,
                    "unlocked_lessons": [
                        {
                            "id": ul.id,
                            "lesson_id": ul.lesson.id,
                            "title": ul.lesson.title,
                        }
                        for ul in unlocked_lessons
                    ]
                    if was_auto_completed
                    else [],
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in submit_element_answer: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Ошибка при отправке ответа: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def complete_lesson(request, graph_lesson_id):
    """
    Завершить урок (если все элементы пройдены)

    POST /api/knowledge-graph/student/lessons/{graph_lesson_id}/complete/

    Response:
    {
        "success": true,
        "data": {
            "lesson_progress": {
                "status": "completed",
                "score": 450,
                "completed_at": "2025-12-11T11:00:00Z"
            },
            "unlocked_lessons": [
                {"id": 5, "title": "Урок 5"}
            ]
        }
    }
    """
    try:
        # Проверить доступ к GraphLesson
        graph_lesson = get_object_or_404(
            GraphLesson, id=graph_lesson_id, graph__student=request.user
        )

        # Получить прогресс урока
        lesson_progress = get_object_or_404(
            LessonProgress, student=request.user, graph_lesson=graph_lesson
        )

        # Проверить что все обязательные элементы завершены
        lesson_elements = LessonElement.objects.filter(lesson=graph_lesson.lesson).select_related(
            "element"
        )

        required_elements = [le for le in lesson_elements if not le.is_optional]

        completed_count = ElementProgress.objects.filter(
            student=request.user,
            graph_lesson=graph_lesson,
            element__in=[le.element for le in required_elements],
            status="completed",
        ).count()

        if completed_count < len(required_elements):
            return Response(
                {
                    "success": False,
                    "error": "Не все обязательные элементы завершены",
                    "details": {
                        "completed": completed_count,
                        "required": len(required_elements),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Завершить урок и разблокировать зависимые (через ProgressSyncService)
        unlocked_lessons = ProgressSyncService.complete_lesson(request.user, graph_lesson)

        # Обновить прогресс для ответа
        lesson_progress.refresh_from_db()

        return Response(
            {
                "success": True,
                "data": {
                    "lesson_progress": {
                        "status": lesson_progress.status,
                        "completion_percent": lesson_progress.completion_percent,
                        "total_score": lesson_progress.total_score,
                        "completed_at": lesson_progress.completed_at,
                    },
                    "unlocked_lessons": [
                        {
                            "id": ul.id,
                            "lesson_id": ul.lesson.id,
                            "title": ul.lesson.title,
                        }
                        for ul in unlocked_lessons
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in complete_lesson: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Ошибка при завершении урока: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================
# Helper Functions
# ============================================


def _evaluate_answer(element, answer):
    """
    Проверить ответ (зависит от типа элемента)

    Args:
        element: Element объект
        answer: JSON ответ студента

    Returns:
        tuple: (is_correct: bool, score: int)
    """
    element_type = element.element_type
    max_score = element.max_score

    # Текстовая задача - требует ручной проверки учителем
    if element_type == "text_problem":
        # Проверяем что есть текст ответа
        if isinstance(answer, dict) and "text" in answer and answer["text"]:
            # Сохраняем ответ, но оценку поставит учитель
            return (None, None)  # None означает "ждет проверки"
        else:
            return (False, 0)

    # Быстрый вопрос - автоматическая проверка
    elif element_type == "quick_question":
        correct_answer = element.content.get("correct_answer")
        user_choice = answer.get("choice") if isinstance(answer, dict) else None

        if user_choice == correct_answer:
            return (True, max_score)
        else:
            return (False, 0)

    # Теория - просто просмотр
    elif element_type == "theory":
        viewed = answer.get("viewed") if isinstance(answer, dict) else False
        if viewed:
            return (True, max_score)
        return (False, 0)

    # Видео - проверка что досмотрел
    elif element_type == "video":
        watched_until = answer.get("watched_until", 0) if isinstance(answer, dict) else 0
        video_duration = element.content.get("duration", 0)

        if video_duration > 0:
            watch_percent = (watched_until / video_duration) * 100
            if watch_percent >= 90:  # Досмотрел 90% видео
                return (True, max_score)
            else:
                # Частичный балл за просмотр
                partial_score = int((watch_percent / 100) * max_score)
                return (False, partial_score)
        else:
            # Если длительность не указана, засчитываем как просмотренное
            return (True, max_score)

    # Неизвестный тип элемента
    return (False, 0)
