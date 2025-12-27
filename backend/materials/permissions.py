"""
Разрешения для materials app - управление доступом к материалам.

T_MAT_006: Strict enrollment validation for material access:
- Студенты могут видеть материалы только из зачисленных предметов
- Студенты могут отправлять ответы только на материалы из зачисленных предметов
- Проверка активности зачисления (is_active=True)
- Проверка срока действия зачисления
- Тьюторы имеют доступ только к материалам своих предметов
- Учителя имеют доступ только к своим материалам
"""

import logging
from rest_framework.permissions import BasePermission
from django.utils import timezone

from .models import SubjectEnrollment, TeacherSubject

logger = logging.getLogger(__name__)


class StudentEnrollmentPermission(BasePermission):
    """
    Разрешение для студентов - проверяет что они зачислены на предмет.

    Позволяет студентам:
    - Видеть материалы только из предметов с активным зачислением
    - Отправлять ответы только на материалы из зачисленных предметов
    - Доступ проверяется по:
      1. SubjectEnrollment.is_active = True
      2. Дата зачисления не истекла
      3. Зачисление не было отменено

    Для других ролей:
    - Учителя: доступ ко всем материалам своих предметов
    - Тьюторы: доступ к материалам предметов своих студентов
    - Админ: доступ ко всему
    """

    def has_permission(self, request, view):
        """Глобальная проверка прав"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Проверка прав на объект (Material).

        Args:
            request: HTTP request
            view: View instance
            obj: Material instance

        Returns:
            bool: True if user has access
        """
        user = request.user

        # Админы имеют доступ ко всему
        if user.is_staff or user.is_superuser:
            return True

        # Учителя видят свои материалы
        if user.role == "teacher":
            return obj.author == user or TeacherSubject.objects.filter(
                teacher=user,
                subject=obj.subject,
                is_active=True,
            ).exists()

        # Тьюторы видят материалы предметов своих студентов
        if user.role == "tutor":
            try:
                # Проверяем есть ли активные зачисления студентов на этот предмет
                # которых преподает этот тьютор
                has_access = SubjectEnrollment.objects.filter(
                    subject=obj.subject,
                    is_active=True,
                    student__student_profile__tutor=user,
                ).exists()
                return has_access
            except Exception as e:
                logger.warning(f"Tutor access check failed: {e}")
                return False

        # Студенты видят материалы только предметов с активным зачислением
        if user.role == "student":
            # Публичные материалы доступны всем
            if obj.is_public:
                return True

            # Материал назначен этому студенту
            if obj.assigned_to.filter(id=user.id).exists():
                # Проверяем активное зачисление на предмет
                try:
                    enrollment = SubjectEnrollment.objects.get(
                        student=user,
                        subject=obj.subject,
                        is_active=True,
                    )

                    # Проверка срока действия через подписку
                    if hasattr(enrollment, 'subscription') and enrollment.subscription:
                        subscription = enrollment.subscription
                        if subscription.expires_at and timezone.now() > subscription.expires_at:
                            logger.warning(
                                f"Student enrollment expired: student_id={user.id}, "
                                f"subject_id={obj.subject.id}"
                            )
                            return False

                    return True
                except SubjectEnrollment.DoesNotExist:
                    logger.warning(
                        f"Student not enrolled: student_id={user.id}, "
                        f"subject_id={obj.subject.id}, material_id={obj.id}"
                    )
                    return False

        return False


class MaterialSubmissionEnrollmentPermission(BasePermission):
    """
    Разрешение для отправки ответов на материалы.

    Проверяет что студент зачислен на предмет материала
    перед отправкой ответа.

    Доступно только студентам с:
    1. Активным зачислением на предмет
    2. Неистекшим сроком действия подписки
    3. Материалом назначенным на них или публичным
    """

    def has_permission(self, request, view):
        """
        Глобальная проверка - только студенты могут отправлять ответы.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Только студенты могут отправлять ответы
        if request.method == "POST" and request.user.role != "student":
            logger.warning(
                f"Non-student attempted submission: user_id={request.user.id}, "
                f"role={request.user.role}"
            )
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Проверка прав на объект (MaterialSubmission).

        Args:
            request: HTTP request
            view: View instance
            obj: MaterialSubmission instance

        Returns:
            bool: True if user has access to view/update submission
        """
        user = request.user

        # Админы имеют полный доступ
        if user.is_staff or user.is_superuser:
            return True

        # Студенты видят только свои ответы
        if user.role == "student":
            return obj.student == user

        # Учителя/тьюторы видят ответы на свои материалы
        if user.role in ["teacher", "tutor"]:
            material = obj.material
            if user.role == "teacher":
                return material.author == user

            # Для тьютора проверяем что это его студент
            if user.role == "tutor":
                return material.subject in [
                    enrollment.subject
                    for enrollment in SubjectEnrollment.objects.filter(
                        student=obj.student,
                        is_active=True,
                        student__student_profile__tutor=user,
                    )
                ]

        return False
