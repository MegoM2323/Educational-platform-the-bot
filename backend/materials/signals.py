from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Material, MaterialProgress, SubjectEnrollment, SubjectPayment, MaterialSubmission
from notifications.notification_service import NotificationService
from .cache_utils import DashboardCacheManager

User = get_user_model()


@receiver(post_save, sender=Material)
@receiver(post_delete, sender=Material)
def invalidate_material_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении материалов"""
    try:
        cache_manager = DashboardCacheManager()
        
        # Инвалидируем кэш для всех студентов, которым назначен материал
        for student in instance.assigned_to.all():
            cache_manager.invalidate_student_cache(student.id)
        
        # Инвалидируем кэш преподавателя
        cache_manager.invalidate_teacher_cache(instance.author.id)
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=MaterialProgress)
@receiver(post_delete, sender=MaterialProgress)
def invalidate_progress_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении прогресса"""
    try:
        cache_manager = DashboardCacheManager()
        
        # Инвалидируем кэш студента
        cache_manager.invalidate_student_cache(instance.student.id)
        
        # Инвалидируем кэш преподавателя материала
        cache_manager.invalidate_teacher_cache(instance.material.author.id)
        
        # Инвалидируем кэш родителя студента
        try:
            parent_profile = instance.student.parent_profile
            if parent_profile:
                cache_manager.invalidate_parent_cache(parent_profile.parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=SubjectEnrollment)
@receiver(post_delete, sender=SubjectEnrollment)
def invalidate_enrollment_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении зачислений"""
    try:
        cache_manager = DashboardCacheManager()
        
        # Инвалидируем кэш студента
        cache_manager.invalidate_student_cache(instance.student.id)
        
        # Инвалидируем кэш преподавателя
        cache_manager.invalidate_teacher_cache(instance.teacher.id)
        
        # Инвалидируем кэш родителя
        try:
            parent_profile = instance.student.parent_profile
            if parent_profile:
                cache_manager.invalidate_parent_cache(parent_profile.parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=SubjectPayment)
@receiver(post_delete, sender=SubjectPayment)
def invalidate_payment_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении платежей"""
    try:
        cache_manager = DashboardCacheManager()
        
        # Инвалидируем кэш родителя
        try:
            parent_profile = instance.enrollment.student.parent_profile
            if parent_profile:
                cache_manager.invalidate_parent_cache(parent_profile.parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=MaterialSubmission)
def notify_teacher_on_submission(sender, instance, created, **kwargs):
    """Уведомление преподавателя о новом домашнем задании"""
    if not created:
        return
    try:
        teacher = instance.material.author
        student = instance.student
        NotificationService().notify_homework_submitted(
            teacher=teacher,
            submission_id=instance.id,
            student=student,
        )
    except Exception:
        pass


@receiver(post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении пользователя"""
    try:
        cache_manager = DashboardCacheManager()
        
        if instance.role == User.Role.STUDENT:
            cache_manager.invalidate_student_cache(instance.id)
            
            # Инвалидируем кэш родителя
            try:
                parent_profile = instance.parent_profile
                if parent_profile:
                    cache_manager.invalidate_parent_cache(parent_profile.parent.id)
            except:
                pass
                
        elif instance.role == User.Role.TEACHER:
            cache_manager.invalidate_teacher_cache(instance.id)
            
        elif instance.role == User.Role.PARENT:
            cache_manager.invalidate_parent_cache(instance.id)
    except Exception:
        pass  # Игнорируем ошибки Redis
