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

from .models import SubjectEnrollment, SubjectSubscription, TeacherSubject
from accounts.models import User

logger = logging.getLogger(__name__)


class IsTutor(BasePermission):
    """Разрешение для тьюторов - проверяет role == TUTOR"""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.TUTOR
        )


class IsTeacher(BasePermission):
    """Разрешение для учителей - проверяет role == TEACHER"""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.TEACHER
        )


class IsTutorOrTeacher(BasePermission):
    """Разрешение для тьюторов или учителей"""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in [User.Role.TUTOR, User.Role.TEACHER]
        )


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

        # Проверка что пользователь активен
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: user_id={user.id}")
            return False

        # Админы имеют доступ ко всему
        if user.is_staff or user.is_superuser:
            return True

        # Учителя видят свои материалы
        if user.role == User.Role.TEACHER:
            return (
                obj.author == user
                or TeacherSubject.objects.filter(
                    teacher=user,
                    subject=obj.subject,
                    is_active=True,
                ).exists()
            )

        # Тьюторы видят материалы предметов своих студентов
        if user.role == User.Role.TUTOR:
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
        if user.role == User.Role.STUDENT:
            # Публичные материалы доступны всем активным студентам
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

                    # Проверка статуса и срока действия через подписку
                    if hasattr(enrollment, "subscription") and enrollment.subscription:
                        subscription = enrollment.subscription
                        # Проверяем и статус подписки, и дату истечения
                        if (
                            hasattr(subscription, "status")
                            and subscription.status != SubjectSubscription.Status.ACTIVE
                        ):
                            logger.warning(
                                f"Student subscription inactive: student_id={user.id}, "
                                f"subject_id={obj.subject.id}, status={subscription.status}"
                            )
                            return False
                        if (
                            subscription.expires_at
                            and timezone.now() > subscription.expires_at
                        ):
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
        Teachers/tutors могут видеть (GET) ответы, но НЕ отправлять новые.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Проверка что пользователь активен
        if not request.user.is_active:
            logger.warning(
                f"Inactive user attempted submission: user_id={request.user.id}"
            )
            return False

        # Только студенты могут отправлять ответы (POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.user.role != User.Role.STUDENT:
                logger.warning(
                    f"Non-student attempted submission: user_id={request.user.id}, "
                    f"role={request.user.role}, method={request.method}"
                )
                return False

        # GET разрешен для authenticated пользователей (проверка has_object_permission уточнит)
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

        # Проверка что пользователь активен
        if not user.is_active:
            logger.warning(
                f"Inactive user attempted submission access: user_id={user.id}"
            )
            return False

        # Админы имеют полный доступ
        if user.is_staff or user.is_superuser:
            return True

        # Студенты видят только свои ответы, могут их отправлять и удалять
        if user.role == User.Role.STUDENT:
            is_owner = obj.student == user
            if request.method == "DELETE":
                # Студент может удалять только свои ответы
                return is_owner
            # GET, POST, PUT, PATCH - проверяем что это его ответ
            return is_owner

        # Учителя видят ответы на свои материалы, но НЕ могут их изменять/удалять
        if user.role == User.Role.TEACHER:
            material = obj.material
            # Учитель может просматривать ответы на свои материалы (GET only)
            if request.method == "GET":
                return material.author == user
            # Но не может отправлять, изменять или удалять ответы
            logger.warning(
                f"Teacher attempted to modify/delete answer: teacher_id={user.id}, "
                f"material_id={material.id}, method={request.method}"
            )
            return False

        # Для тьютора проверяем что это его студент
        if user.role == User.Role.TUTOR:
            material = obj.material
            # Тьютор может просматривать ответы на материалы своих студентов (GET only)
            if request.method == "GET":
                return material.subject in [
                    enrollment.subject
                    for enrollment in SubjectEnrollment.objects.filter(
                        student=obj.student,
                        is_active=True,
                        student__student_profile__tutor=user,
                    )
                ]
            # Но не может отправлять, изменять или удалять ответы
            logger.warning(
                f"Tutor attempted to modify/delete answer: tutor_id={user.id}, "
                f"material_id={material.id}, method={request.method}"
            )
            return False

        return False


class ChildBelongsToParent(BasePermission):
    """
    Разрешение для проверки что ребенок (student) принадлежит родителю.

    Проверяет что:
    - Пользователь аутентифицирован
    - Пользователь имеет роль PARENT
    - Ребенок с child_id принадлежит этому родителю (через StudentProfile.parent)

    Используется в parent dashboard endpoints:
    - GET /api/materials/parent/children/{child_id}/subjects/
    - GET /api/materials/parent/children/{child_id}/progress/
    - POST /api/materials/parent/children/{child_id}/payment/{enrollment_id}/
    """

    def has_permission(self, request, view):
        """Проверка что пользователь аутентифицирован"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            logger.warning(
                f"Inactive parent attempted access: user_id={request.user.id}"
            )
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Проверка что ребенок принадлежит родителю.

        Args:
            request: HTTP request
            view: View instance
            obj: User instance (student)

        Returns:
            bool: True if child belongs to parent
        """
        user = request.user

        if not user.is_active:
            return False

        # Админы имеют доступ ко всему
        if user.is_staff or user.is_superuser:
            return True

        # Проверяем что это студент
        if obj.role != User.Role.STUDENT:
            logger.warning(
                f"Parent attempted to access non-student: user_id={user.id}, "
                f"target_id={obj.id}, target_role={obj.role}"
            )
            return False

        # Проверяем что студент принадлежит этому родителю
        try:
            from accounts.models import StudentProfile

            student_profile = StudentProfile.objects.get(user=obj)
            if student_profile.parent == user:
                return True

            logger.warning(
                f"Parent attempted unauthorized child access: parent_id={user.id}, "
                f"student_id={obj.id}, actual_parent_id={student_profile.parent_id}"
            )
            return False
        except StudentProfile.DoesNotExist:
            logger.warning(f"Student profile not found: student_id={obj.id}")
            return False
