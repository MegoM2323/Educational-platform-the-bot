"""
Django signals for automatic progress updates (T402)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ElementProgress, LessonProgress


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
