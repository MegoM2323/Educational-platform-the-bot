"""
Сигналы для инвалидации кэша отчётов.

Автоматическое инвалидирование кэша при изменении данных,
которые влияют на отчёты:
- Изменение оценок
- Отправка заданий
- Изменение прогресса студента
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def invalidate_student_reports(student_id: int, report_type: str = "student_progress"):
    """
    Инвалидирует отчёты студента.

    Args:
        student_id: ID студента
        report_type: Тип отчёта для инвалидирования
    """
    try:
        from reports.cache import cache_strategy

        # Инвалидируем кэш для студента и для учителей/родителей
        cache_strategy.invalidate_user_cache(student_id)

        logger.info(
            f"Cache invalidated for student_progress (student_id={student_id})",
            extra={"student_id": student_id, "report_type": report_type},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for student {student_id}: {str(e)}",
            extra={"student_id": student_id, "error": str(e)},
        )


def invalidate_teacher_reports(teacher_id: int, report_type: str = "class_performance"):
    """
    Инвалидирует отчёты учителя.

    Args:
        teacher_id: ID учителя
        report_type: Тип отчёта для инвалидирования
    """
    try:
        from reports.cache import cache_strategy

        cache_strategy.invalidate_user_cache(teacher_id)

        logger.info(
            f"Cache invalidated for teacher reports (teacher_id={teacher_id})",
            extra={"teacher_id": teacher_id, "report_type": report_type},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for teacher {teacher_id}: {str(e)}",
            extra={"teacher_id": teacher_id, "error": str(e)},
        )


# ========== Signals for grade changes ==========

@receiver(post_save, sender='assignments.AssignmentAnswer')
def invalidate_on_grade_change(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении оценки задания.

    Args:
        sender: Model class
        instance: AssignmentAnswer instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    if instance.score is not None:
        # Инвалидируем отчёты студента
        invalidate_student_reports(instance.submission.student_id)

        # Инвалидируем отчёты учителя (если есть)
        if instance.graded_by_id:
            invalidate_teacher_reports(instance.graded_by_id)

        logger.debug(
            f"Cache invalidated: grade changed for submission {instance.submission_id}",
            extra={"submission_id": instance.submission_id, "score": instance.score},
        )


@receiver(post_save, sender='assignments.AssignmentSubmission')
def invalidate_on_submission_change(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при отправке задания.

    Args:
        sender: Model class
        instance: AssignmentSubmission instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    # Инвалидируем отчёты студента
    invalidate_student_reports(instance.student_id, "assignment_completion")

    # Инвалидируем отчёты учителя
    if instance.assignment.created_by_id:
        invalidate_teacher_reports(instance.assignment.created_by_id)

    logger.debug(
        f"Cache invalidated: submission changed {instance.id}",
        extra={"submission_id": instance.id, "student_id": instance.student_id},
    )


# ========== Signals for material progress ==========

@receiver(post_save, sender='materials.MaterialProgress')
def invalidate_on_material_progress(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении прогресса по материалу.

    Args:
        sender: Model class
        instance: MaterialProgress instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    invalidate_student_reports(instance.student_id, "material_study")

    logger.debug(
        f"Cache invalidated: material progress changed {instance.id}",
        extra={"material_id": instance.material_id, "student_id": instance.student_id},
    )


# ========== Signals for knowledge graph progress ==========

@receiver(post_save, sender='knowledge_graph.ElementProgress')
def invalidate_on_element_progress(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении прогресса по элементу.

    Args:
        sender: Model class
        instance: ElementProgress instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    invalidate_student_reports(instance.student_id, "student_progress")

    logger.debug(
        f"Cache invalidated: element progress changed {instance.id}",
        extra={"element_id": instance.element_id, "student_id": instance.student_id},
    )


# ========== Signals for report model changes ==========

@receiver(post_save, sender='reports.Report')
def invalidate_on_report_save(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении отчёта.

    Args:
        sender: Model class
        instance: Report instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    try:
        from reports.cache import cache_strategy

        if instance.author_id:
            cache_strategy.invalidate_user_cache(instance.author_id)

        logger.debug(
            f"Cache invalidated: report saved {instance.id}",
            extra={"report_id": instance.id, "author_id": instance.author_id},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for report {instance.id}: {str(e)}",
            extra={"report_id": instance.id, "error": str(e)},
        )


@receiver(post_delete, sender='reports.Report')
def invalidate_on_report_delete(sender, instance, **kwargs):
    """
    Инвалидирует кэш при удалении отчёта.

    Args:
        sender: Model class
        instance: Report instance
        **kwargs: Additional arguments
    """
    try:
        from reports.cache import cache_strategy

        if instance.author_id:
            cache_strategy.invalidate_user_cache(instance.author_id)

        logger.debug(
            f"Cache invalidated: report deleted {instance.id}",
            extra={"report_id": instance.id, "author_id": instance.author_id},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for deleted report {instance.id}: {str(e)}",
            extra={"report_id": instance.id, "error": str(e)},
        )


@receiver(post_save, sender='reports.StudentReport')
def invalidate_on_student_report_save(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении отчёта студента.

    Args:
        sender: Model class
        instance: StudentReport instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    try:
        from reports.cache import cache_strategy

        # Инвалидируем для учителя
        if instance.teacher_id:
            cache_strategy.invalidate_user_cache(instance.teacher_id)

        # Инвалидируем для студента
        if instance.student_id:
            cache_strategy.invalidate_user_cache(instance.student_id)

        # Инвалидируем для родителя
        if instance.parent_id:
            cache_strategy.invalidate_user_cache(instance.parent_id)

        logger.debug(
            f"Cache invalidated: student report saved {instance.id}",
            extra={"report_id": instance.id, "student_id": instance.student_id},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for student report {instance.id}: {str(e)}",
            extra={"report_id": instance.id, "error": str(e)},
        )


@receiver(post_save, sender='reports.TutorWeeklyReport')
def invalidate_on_tutor_report_save(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении еженедельного отчёта тьютора.

    Args:
        sender: Model class
        instance: TutorWeeklyReport instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    try:
        from reports.cache import cache_strategy

        # Инвалидируем для тьютора
        if instance.tutor_id:
            cache_strategy.invalidate_user_cache(instance.tutor_id)

        # Инвалидируем для студента
        if instance.student_id:
            cache_strategy.invalidate_user_cache(instance.student_id)

        # Инвалидируем для родителя
        if instance.parent_id:
            cache_strategy.invalidate_user_cache(instance.parent_id)

        logger.debug(
            f"Cache invalidated: tutor weekly report saved {instance.id}",
            extra={"report_id": instance.id, "student_id": instance.student_id},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for tutor report {instance.id}: {str(e)}",
            extra={"report_id": instance.id, "error": str(e)},
        )


@receiver(post_save, sender='reports.TeacherWeeklyReport')
def invalidate_on_teacher_report_save(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при изменении еженедельного отчёта учителя.

    Args:
        sender: Model class
        instance: TeacherWeeklyReport instance
        created: Boolean indicating if instance was created
        **kwargs: Additional arguments
    """
    try:
        from reports.cache import cache_strategy

        # Инвалидируем для учителя
        if instance.teacher_id:
            cache_strategy.invalidate_user_cache(instance.teacher_id)

        # Инвалидируем для тьютора
        if instance.tutor_id:
            cache_strategy.invalidate_user_cache(instance.tutor_id)

        # Инвалидируем для студента
        if instance.student_id:
            cache_strategy.invalidate_user_cache(instance.student_id)

        logger.debug(
            f"Cache invalidated: teacher weekly report saved {instance.id}",
            extra={"report_id": instance.id, "student_id": instance.student_id},
        )
    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for teacher report {instance.id}: {str(e)}",
            extra={"report_id": instance.id, "error": str(e)},
        )
