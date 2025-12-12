"""
Progress Synchronization Service (T035)
Автоматическая синхронизация прогресса в графе знаний
"""
from django.db.models import Count, Q
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    KnowledgeGraph, GraphLesson, LessonProgress,
    LessonDependency, LessonElement, ElementProgress
)

logger = logging.getLogger(__name__)


class ProgressSyncService:
    """
    Синхронизация прогресса в графе знаний

    Основные функции:
    - Автоматическое завершение уроков когда все элементы пройдены
    - Автоматическая разблокировка зависимых уроков
    - Проверка выполнения всех prerequisites
    """

    @staticmethod
    def complete_lesson(student, graph_lesson):
        """
        Завершить урок и автоматически разблокировать зависимые уроки

        Args:
            student: User объект студента
            graph_lesson: GraphLesson который завершается

        Returns:
            list: список разблокированных GraphLesson объектов

        Raises:
            LessonProgress.DoesNotExist: если прогресс урока не найден
        """
        try:
            with transaction.atomic():
                # Получить прогресс урока
                lesson_progress = LessonProgress.objects.select_for_update().get(
                    student=student,
                    graph_lesson=graph_lesson
                )

                # Отметить как завершенный если еще не завершен
                if lesson_progress.status != 'completed':
                    lesson_progress.status = 'completed'
                    lesson_progress.completed_at = timezone.now()
                    lesson_progress.save(update_fields=['status', 'completed_at'])

                    logger.info(
                        f"Lesson completed: student={student.id}, "
                        f"graph_lesson={graph_lesson.id}, "
                        f"score={lesson_progress.total_score}/{lesson_progress.max_possible_score}"
                    )

                # Найти уроки которые зависят от этого
                unlocked_lessons = ProgressSyncService._unlock_dependent_lessons(
                    student,
                    graph_lesson,
                    lesson_progress
                )

                return unlocked_lessons

        except LessonProgress.DoesNotExist:
            logger.error(
                f"LessonProgress not found: student={student.id}, "
                f"graph_lesson={graph_lesson.id}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Error in complete_lesson: student={student.id}, "
                f"graph_lesson={graph_lesson.id}, error={str(e)}",
                exc_info=True
            )
            raise

    @staticmethod
    def _unlock_dependent_lessons(student, completed_graph_lesson, lesson_progress):
        """
        Разблокировать уроки которые зависят от завершенного урока

        Args:
            student: User объект
            completed_graph_lesson: GraphLesson который только что завершен
            lesson_progress: LessonProgress завершенного урока

        Returns:
            list: список разблокированных GraphLesson объектов
        """
        unlocked_lessons = []

        try:
            # Найти все зависимости где текущий урок - prerequisite
            dependencies = LessonDependency.objects.filter(
                from_lesson=completed_graph_lesson,
                dependency_type='required'
            ).select_related('to_lesson', 'to_lesson__lesson', 'to_lesson__graph')

            for dep in dependencies:
                # Проверить выполнено ли условие по баллам
                if lesson_progress.max_possible_score > 0:
                    score_percent = (
                        lesson_progress.total_score / lesson_progress.max_possible_score
                    ) * 100
                else:
                    score_percent = 100

                if score_percent >= dep.min_score_percent:
                    # Проверить что все другие prerequisites тоже выполнены
                    if ProgressSyncService.check_all_prerequisites_complete(
                        student,
                        dep.to_lesson
                    ):
                        # Разблокировать урок если еще не разблокирован
                        if not dep.to_lesson.is_unlocked:
                            dep.to_lesson.unlock()
                            unlocked_lessons.append(dep.to_lesson)

                            logger.info(
                                f"Lesson unlocked: student={student.id}, "
                                f"graph_lesson={dep.to_lesson.id}, "
                                f"lesson={dep.to_lesson.lesson.title}"
                            )

        except Exception as e:
            logger.error(
                f"Error in _unlock_dependent_lessons: student={student.id}, "
                f"completed_graph_lesson={completed_graph_lesson.id}, error={str(e)}",
                exc_info=True
            )

        return unlocked_lessons

    @staticmethod
    def check_all_prerequisites_complete(student, graph_lesson):
        """
        Проверить что все prerequisites урока завершены

        Args:
            student: User объект студента
            graph_lesson: GraphLesson для проверки

        Returns:
            bool: True если все prerequisites завершены, False иначе
        """
        try:
            # Найти все обязательные зависимости для этого урока
            prerequisites = LessonDependency.objects.filter(
                to_lesson=graph_lesson,
                dependency_type='required'
            ).select_related('from_lesson')

            # Если нет prerequisites - урок доступен сразу
            if not prerequisites.exists():
                return True

            # Проверить что все prerequisites завершены
            for prereq in prerequisites:
                prereq_progress = LessonProgress.objects.filter(
                    student=student,
                    graph_lesson=prereq.from_lesson
                ).first()

                # Если нет прогресса или урок не завершен
                if not prereq_progress or prereq_progress.status != 'completed':
                    return False

                # Проверить минимальный процент баллов
                if prereq_progress.max_possible_score > 0:
                    score_percent = (
                        prereq_progress.total_score / prereq_progress.max_possible_score
                    ) * 100
                else:
                    score_percent = 100

                if score_percent < prereq.min_score_percent:
                    return False

            return True

        except Exception as e:
            logger.error(
                f"Error in check_all_prerequisites_complete: student={student.id}, "
                f"graph_lesson={graph_lesson.id}, error={str(e)}",
                exc_info=True
            )
            return False

    @staticmethod
    def auto_complete_lesson_if_all_elements_done(student, graph_lesson):
        """
        Автоматически отметить урок как завершенный если все обязательные элементы пройдены

        Args:
            student: User объект студента
            graph_lesson: GraphLesson для проверки

        Returns:
            tuple: (was_completed: bool, unlocked_lessons: list)
                was_completed - True если урок был автоматически завершен
                unlocked_lessons - список разблокированных уроков
        """
        try:
            with transaction.atomic():
                # Получить прогресс урока
                lesson_progress = LessonProgress.objects.select_for_update().get(
                    student=student,
                    graph_lesson=graph_lesson
                )

                # Если урок уже завершен, ничего не делаем
                if lesson_progress.status == 'completed':
                    return (False, [])

                # Получить все обязательные элементы урока
                lesson_elements = LessonElement.objects.filter(
                    lesson=graph_lesson.lesson,
                    is_optional=False
                ).select_related('element')

                # Если нет обязательных элементов, не завершаем автоматически
                if not lesson_elements.exists():
                    return (False, [])

                # Получить прогресс по всем элементам
                element_progresses = ElementProgress.objects.filter(
                    student=student,
                    graph_lesson=graph_lesson,
                    element__in=[le.element for le in lesson_elements]
                )

                # Подсчитать завершенные элементы
                completed_count = element_progresses.filter(
                    status='completed'
                ).count()

                # Если все обязательные элементы завершены
                if completed_count == lesson_elements.count():
                    # Обновить прогресс урока
                    lesson_progress.update_progress()

                    # Завершить урок и разблокировать зависимые
                    unlocked_lessons = ProgressSyncService.complete_lesson(
                        student,
                        graph_lesson
                    )

                    logger.info(
                        f"Lesson auto-completed: student={student.id}, "
                        f"graph_lesson={graph_lesson.id}, "
                        f"unlocked={len(unlocked_lessons)} lessons"
                    )

                    return (True, unlocked_lessons)

                return (False, [])

        except LessonProgress.DoesNotExist:
            logger.warning(
                f"LessonProgress not found for auto-complete: student={student.id}, "
                f"graph_lesson={graph_lesson.id}"
            )
            return (False, [])
        except Exception as e:
            logger.error(
                f"Error in auto_complete_lesson_if_all_elements_done: "
                f"student={student.id}, graph_lesson={graph_lesson.id}, error={str(e)}",
                exc_info=True
            )
            return (False, [])

    @staticmethod
    def initialize_lesson_unlocks(knowledge_graph):
        """
        Инициализировать разблокировку уроков без dependencies

        Вызывается при создании графа знаний, чтобы разблокировать
        первые уроки (которые не имеют prerequisites)

        Args:
            knowledge_graph: KnowledgeGraph объект

        Returns:
            int: количество разблокированных уроков
        """
        try:
            unlocked_count = 0

            # Найти все уроки в графе
            graph_lessons = GraphLesson.objects.filter(
                graph=knowledge_graph
            ).select_related('lesson')

            for graph_lesson in graph_lessons:
                # Проверить есть ли у урока обязательные зависимости
                has_required_deps = LessonDependency.objects.filter(
                    to_lesson=graph_lesson,
                    dependency_type='required'
                ).exists()

                # Если нет обязательных зависимостей - разблокировать
                if not has_required_deps and not graph_lesson.is_unlocked:
                    graph_lesson.unlock()
                    unlocked_count += 1

                    logger.info(
                        f"Initial lesson unlocked: graph={knowledge_graph.id}, "
                        f"graph_lesson={graph_lesson.id}, "
                        f"lesson={graph_lesson.lesson.title}"
                    )

            return unlocked_count

        except Exception as e:
            logger.error(
                f"Error in initialize_lesson_unlocks: graph={knowledge_graph.id}, "
                f"error={str(e)}",
                exc_info=True
            )
            return 0
