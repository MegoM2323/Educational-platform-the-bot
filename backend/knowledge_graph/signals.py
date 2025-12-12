"""
Django signals for automatic progress updates (T402, T035)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ElementProgress, LessonProgress, GraphLesson, LessonDependency
from .progress_sync_service import ProgressSyncService


@receiver(post_save, sender=ElementProgress)
def update_lesson_progress_on_element_complete(sender, instance, created, **kwargs):
    """
    Автоматически обновлять прогресс урока когда элемент завершен

    Срабатывает при:
    - Завершении элемента (status = 'completed')
    - Обновлении ответа на элемент

    Действия:
    - Пересчитать completion_percentage урока
    - Обновить total_score урока
    - Если все элементы завершены, установить status = 'completed'
    - Разблокировать зависимые уроки
    """
    # Проверяем что элемент завершен
    if instance.status == 'completed':
        try:
            # Получить или создать прогресс урока
            lesson_progress, _ = LessonProgress.objects.get_or_create(
                student=instance.student,
                graph_lesson=instance.graph_lesson,
                defaults={
                    'total_elements': instance.graph_lesson.lesson.elements.count(),
                    'max_possible_score': instance.graph_lesson.lesson.total_max_score,
                }
            )

            # Если урок еще не начат, начать его
            if lesson_progress.status == 'not_started':
                lesson_progress.start()

            # Обновить прогресс урока
            lesson_progress.update_progress()

            # Если урок завершен, проверить разблокировку следующих
            if lesson_progress.status == 'completed':
                lesson_progress.check_unlock_next()

        except Exception as e:
            # Логирование ошибки но не блокируем операцию
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in update_lesson_progress_on_element_complete signal: {e}", exc_info=True)


@receiver(post_save, sender=GraphLesson)
def auto_unlock_lesson_without_dependencies(sender, instance, created, **kwargs):
    """
    Автоматически разблокировать урок если у него нет обязательных prerequisites

    Срабатывает при:
    - Добавлении урока в граф (created=True)

    Действия:
    - Проверить есть ли обязательные зависимости
    - Если нет - разблокировать урок
    """
    if created:
        try:
            # Проверить есть ли обязательные зависимости
            has_required_deps = LessonDependency.objects.filter(
                to_lesson=instance,
                dependency_type='required'
            ).exists()

            # Если нет обязательных зависимостей - разблокировать
            if not has_required_deps and not instance.is_unlocked:
                instance.unlock()

                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Auto-unlocked lesson without dependencies: "
                    f"graph={instance.graph.id}, graph_lesson={instance.id}, "
                    f"lesson={instance.lesson.title}"
                )

        except Exception as e:
            # Логирование ошибки но не блокируем операцию
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in auto_unlock_lesson_without_dependencies signal: {e}", exc_info=True)
