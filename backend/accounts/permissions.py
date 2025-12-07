"""
Константы и функции для управления приватными полями профилей.

Приватные поля скрываются от владельца профиля, но доступны для просмотра
админам и другим ролям согласно бизнес-логике платформы.
"""

# ============= КОНСТАНТЫ ПРИВАТНЫХ ПОЛЕЙ =============

# Приватные поля StudentProfile (видят только teacher, tutor, admin)
STUDENT_PRIVATE_FIELDS = ['goal', 'tutor', 'parent']

# Приватные поля TeacherProfile (видят только admin)
TEACHER_PRIVATE_FIELDS = ['bio', 'experience_years']

# Приватные поля TutorProfile (видят только admin)
TUTOR_PRIVATE_FIELDS = ['bio', 'experience_years']

# Приватные поля ParentProfile (пока нет)
PARENT_PRIVATE_FIELDS = []


# ============= ФУНКЦИИ ПРОВЕРКИ ПРАВ =============

def can_view_private_fields(viewer_user, profile_owner_user, profile_type):
    """
    Проверяет, может ли viewer_user видеть приватные поля профиля profile_owner_user.

    Бизнес-правила:
    - Админы и staff видят всё
    - Владелец профиля НЕ видит свои приватные поля
    - Для студентов: teacher и tutor могут видеть приватные поля
    - Для teacher/tutor: только admin видит приватные поля
    - Для parent: пока нет приватных полей

    Args:
        viewer_user (User): Пользователь, который смотрит профиль
        profile_owner_user (User): Владелец профиля
        profile_type (str): Тип профиля ('student', 'teacher', 'tutor', 'parent')

    Returns:
        bool: True если может видеть приватные поля, False иначе

    Examples:
        >>> # Студент смотрит свой профиль - НЕ видит goal, tutor, parent
        >>> can_view_private_fields(student_user, student_user, 'student')
        False

        >>> # Преподаватель смотрит профиль студента - видит goal, tutor, parent
        >>> can_view_private_fields(teacher_user, student_user, 'student')
        True

        >>> # Преподаватель смотрит свой профиль - НЕ видит bio, experience_years
        >>> can_view_private_fields(teacher_user, teacher_user, 'teacher')
        False

        >>> # Админ смотрит профиль преподавателя - видит bio, experience_years
        >>> can_view_private_fields(admin_user, teacher_user, 'teacher')
        True
    """
    # Админы и staff видят всё
    if viewer_user.is_staff or viewer_user.is_superuser:
        return True

    # Если смотрит на свой профиль - НЕ видит приватные поля
    if viewer_user.id == profile_owner_user.id:
        return False

    # Для студентов: teacher и tutor могут видеть приватные поля
    if profile_type == 'student':
        if viewer_user.role in ['teacher', 'tutor']:
            return True

    # Для teacher/tutor: только admin видит приватные поля
    # (уже обработано выше через is_staff)

    return False


def get_private_fields_for_role(profile_type):
    """
    Возвращает список приватных полей для указанного типа профиля.

    Args:
        profile_type (str): Тип профиля ('student', 'teacher', 'tutor', 'parent')

    Returns:
        list: Список имен приватных полей

    Examples:
        >>> get_private_fields_for_role('student')
        ['goal', 'tutor', 'parent']

        >>> get_private_fields_for_role('teacher')
        ['bio', 'experience_years']
    """
    field_map = {
        'student': STUDENT_PRIVATE_FIELDS,
        'teacher': TEACHER_PRIVATE_FIELDS,
        'tutor': TUTOR_PRIVATE_FIELDS,
        'parent': PARENT_PRIVATE_FIELDS,
    }

    return field_map.get(profile_type, [])


# ============= DRF PERMISSION CLASSES =============

from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Позволяет редактировать объект только его владельцу.
    Остальные пользователи могут только читать (GET).

    Проверяет:
    - GET запросы: доступны всем аутентифицированным пользователям
    - PUT/PATCH/DELETE: только владельцу объекта
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект"""
        # Все могут читать
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Только владелец может редактировать/удалять
        # Проверяем если obj - это User, иначе это Profile (у которого есть .user)
        owner = obj if isinstance(obj, type(obj).__bases__[0]) else getattr(obj, 'user', obj)
        return request.user == owner


class IsOwnerProfileOrAdmin(BasePermission):
    """
    Позволяет редактировать профиль только его владельцу или администратору.

    Проверяет:
    - Владелец профиля может редактировать свой профиль
    - Админ/staff может редактировать любой профиль
    - Остальные могут только читать
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект профиля"""
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Только владелец может редактировать/удалять
        return request.user == obj.user


class IsTutorOrAdmin(BasePermission):
    """
    Позволяет выполнять действия только тьютору или администратору.

    Проверяет:
    - Пользователь имеет роль 'tutor' или 'admin'
    - Остальные ролям запрещено
    """

    def has_permission(self, request, view):
        """Проверяет глобальные права пользователя"""
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.role == 'tutor' or request.user.is_staff or request.user.is_superuser)
        )


class TutorCanManageStudentProfiles(BasePermission):
    """
    Позволяет тьютору управлять профилями только своих студентов.

    Бизнес-правила:
    - Студент может редактировать ТОЛЬКО свой профиль
    - Тьютор может редактировать профили своих студентов (через StudentProfile.tutor)
    - Учитель может редактировать ТОЛЬКО свой профиль
    - Админ может редактировать ВСЕ профили

    Проверяет:
    - Если пользователь - админ: всегда True
    - Если пользователь - тьютор: может редактировать студентов, назначенных ему
    - Если пользователь редактирует свой профиль: всегда True (если не в blacklist роли)
    - Остальные: False
    """

    def has_permission(self, request, view):
        """Проверяет глобальные права (для list operations)"""
        # Все остальные операции проверяются в has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект профиля студента"""
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Если это студент - может редактировать только свой профиль
        if request.user.role == 'student':
            return request.user == obj.user

        # Если это тьютор - может редактировать профили своих студентов
        if request.user.role == 'tutor':
            # Проверяем что студент назначен тьютору
            from .models import StudentProfile
            if isinstance(obj, StudentProfile):
                return obj.tutor == request.user

        # Если это учитель, родитель или другая роль - может редактировать только свой профиль
        if hasattr(obj, 'user'):
            return request.user == obj.user

        return False


class CanViewOwnProfileOnly(BasePermission):
    """
    Позволяет просматривать только свой профиль (строгое ограничение).

    Используется для protect endpoints где мы хотим разрешить только доступ к собственному профилю.
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет имеет ли пользователь доступ к профилю"""
        # Админы могут видеть все
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Остальные - только свой профиль
        if hasattr(obj, 'user'):
            return request.user == obj.user

        return request.user == obj


class IsStudentOwner(BasePermission):
    """
    Позволяет только студентам редактировать свой профиль,
    или тьюторам редактировать профили своих студентов.
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет имеет ли пользователь доступ к профилю студента"""
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        from .models import StudentProfile

        # Это должен быть StudentProfile
        if not isinstance(obj, StudentProfile):
            return False

        # Студент может редактировать только свой профиль
        if request.user.role == 'student':
            return request.user == obj.user

        # Тьютор может редактировать профили своих студентов
        if request.user.role == 'tutor':
            return obj.tutor == request.user

        return False


class IsStaffOrAdmin(BasePermission):
    """
    Разрешение для пользователей с правами администратора или staff.
    Также разрешает тьюторам (роль TUTOR).

    Бизнес-правила:
    - Админ (is_superuser или is_staff) имеет полный доступ
    - Пользователь с ролью TUTOR также имеет доступ (тьютор - это тип администратора)
    - Остальные пользователи не имеют доступа
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет глобальные права пользователя"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return (
            request.user.is_staff or
            request.user.is_superuser or
            getattr(request.user, 'role', None) == 'tutor'
        )


class IsAdminUser(BasePermission):
    """
    Разрешение только для пользователей с правами администратора.

    Бизнес-правила:
    - Только пользователи с is_staff=True или is_superuser=True имеют доступ
    - Возвращает 403 Forbidden для всех остальных пользователей
    - Используется для admin-only endpoints (schedule, chat management)

    Примечание: Этот класс отличается от IsStaffOrAdmin тем, что НЕ включает тьюторов.
    Только настоящие админы (staff/superuser) имеют доступ к админской панели.
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь имеет права администратора"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.is_staff or request.user.is_superuser
