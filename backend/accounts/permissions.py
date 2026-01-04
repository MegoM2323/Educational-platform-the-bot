"""
Константы и функции для управления приватными полями профилей.

Приватные поля скрываются от владельца профиля, но доступны для просмотра
админам и другим ролям согласно бизнес-логике платформы.
"""

from .models import User

# ============= КОНСТАНТЫ ПРИВАТНЫХ ПОЛЕЙ =============

# Приватные поля StudentProfile (видят только teacher, tutor, admin)
STUDENT_PRIVATE_FIELDS = ["goal", "tutor", "parent"]

# Приватные поля TeacherProfile (видят только admin)
TEACHER_PRIVATE_FIELDS = ["bio", "experience_years"]

# Приватные поля TutorProfile (видят только admin)
TUTOR_PRIVATE_FIELDS = ["bio", "experience_years"]

# Приватные поля ParentProfile (пока нет)
PARENT_PRIVATE_FIELDS: list[str] = []


# ============= ФУНКЦИИ ПРОВЕРКИ ПРАВ =============


def can_view_private_fields(viewer_user, profile_owner_user, profile_type):
    """
    Проверяет, может ли viewer_user видеть приватные поля профиля profile_owner_user.

    Бизнес-правила:
    - Админы и staff видят всё
    - Только активные пользователи могут видеть приватные поля
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
    # Только активные пользователи могут видеть приватные поля
    if not viewer_user.is_active:
        return False

    # Админы и staff видят всё
    if viewer_user.is_staff or viewer_user.is_superuser:
        return True

    # Если смотрит на свой профиль - НЕ видит приватные поля
    if viewer_user.id == profile_owner_user.id:
        return False

    # Для студентов: teacher и tutor могут видеть приватные поля
    if profile_type == User.Role.STUDENT:
        if viewer_user.role in [User.Role.TEACHER, User.Role.TUTOR]:
            return True

    # Для teacher/tutor: только admin видит приватные поля
    # (уже обработано выше через is_staff)

    return False


def get_private_fields_for_role(profile_type):
    """
    Возвращает список приватных полей для указанного типа профиля.

    Args:
        profile_type (str): Тип профиля или User.Role enum значение

    Returns:
        list: Список имен приватных полей

    Examples:
        >>> get_private_fields_for_role(User.Role.STUDENT)
        ['goal', 'tutor', 'parent']

        >>> get_private_fields_for_role(User.Role.TEACHER)
        ['bio', 'experience_years']
    """
    field_map = {
        User.Role.STUDENT: STUDENT_PRIVATE_FIELDS,
        User.Role.TEACHER: TEACHER_PRIVATE_FIELDS,
        User.Role.TUTOR: TUTOR_PRIVATE_FIELDS,
        User.Role.PARENT: PARENT_PRIVATE_FIELDS,
    }

    return field_map.get(profile_type, [])


# ============= DRF PERMISSION CLASSES =============

from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Позволяет редактировать объект только его владельцу.
    Остальные пользователи могут только читать (GET).

    Требует:
    - Пользователь активен (is_active=True)

    Права по ролям:
    - Все активные: GET запросы к объекту
    - Владелец (active): PUT/PATCH/DELETE свой объект
    - Остальные: запрещено редактировать
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект"""
        if not request.user.is_active:
            return False

        # Все могут читать
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Только владелец может редактировать/удалять
        # Проверяем если obj - это User, иначе это Profile (у которого есть .user)
        owner = (
            obj
            if isinstance(obj, type(obj).__bases__[0])
            else getattr(obj, "user", obj)
        )
        return request.user == owner


class IsOwnerProfileOrAdmin(BasePermission):
    """
    Позволяет редактировать профиль только его владельцу или администратору.

    Требует:
    - Пользователь активен (is_active=True)

    Права по ролям:
    - Админ (is_staff/is_superuser): PUT/PATCH/DELETE любой профиль
    - Владелец (active): PUT/PATCH/DELETE свой профиль
    - Все активные: GET любой профиль
    - Остальные (неактивные): запрещено
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект профиля"""
        if not request.user.is_active:
            return False

        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Только владелец может редактировать/удалять
        return request.user == obj.user


class IsTutorOrAdmin(BasePermission):
    """
    Позволяет выполнять действия только тьютору или администратору.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован

    Права по ролям:
    - Admin (is_staff/is_superuser): полный доступ
    - Tutor (role=TUTOR, active): доступ для управления студентами
    - Остальные: запрещено
    """

    def has_permission(self, request, view):
        """Проверяет глобальные права пользователя"""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (
                request.user.role == User.Role.TUTOR
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class TutorCanManageStudentProfiles(BasePermission):
    """
    Позволяет управлять студентами только их владельцам, тьюторам и администраторам.

    Требует:
    - Пользователь активен (is_active=True)

    Право по ролям:
    - Admin (is_staff/is_superuser): PUT/PATCH/DELETE любой профиль
    - Student (role=STUDENT, active): PUT/PATCH/DELETE только свой профиль
    - Tutor (role=TUTOR, active): PUT/PATCH/DELETE профили своих студентов (через StudentProfile.tutor)
    - Teacher/Parent: PUT/PATCH/DELETE только свой профиль
    - Все активные: GET любой профиль
    - Неактивные: запрещено
    """

    def has_permission(self, request, view):
        """Проверяет глобальные права (для list operations)"""
        # Все остальные операции проверяются в has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        """Проверяет есть ли у пользователя права на объект профиля студента"""
        if not request.user.is_active:
            return False

        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Если это студент - может редактировать только свой профиль
        if request.user.role == User.Role.STUDENT:
            return request.user == obj.user

        # Если это тьютор - может редактировать профили своих студентов
        if request.user.role == User.Role.TUTOR:
            # Проверяем что студент назначен тьютору
            from .models import StudentProfile

            if isinstance(obj, StudentProfile):
                return obj.tutor == request.user

        # Если это учитель, родитель или другая роль - может редактировать только свой профиль
        if hasattr(obj, "user"):
            return request.user == obj.user

        return False


class CanViewOwnProfileOnly(BasePermission):
    """
    Позволяет просматривать только свой профиль (строгое ограничение).

    Требует:
    - Пользователь активен (is_active=True)

    Права по ролям:
    - Admin (is_staff/is_superuser): GET любой профиль
    - Все активные: GET свой профиль
    - Неактивные: запрещено
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет имеет ли пользователь доступ к профилю"""
        if not request.user.is_active:
            return False

        # Админы могут видеть все
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Остальные - только свой профиль
        if hasattr(obj, "user"):
            return request.user == obj.user

        return request.user == obj


class IsStudentOwner(BasePermission):
    """
    Позволяет только студентам редактировать свой профиль,
    или тьюторам редактировать профили своих студентов.

    Требует:
    - Пользователь активен (is_active=True)
    - Объект является StudentProfile

    Права по ролям:
    - Admin (is_staff/is_superuser): PUT/PATCH/DELETE любой StudentProfile
    - Student (role=STUDENT, active): PUT/PATCH/DELETE свой StudentProfile, НЕ может менять role field
    - Tutor (role=TUTOR, active): PUT/PATCH/DELETE StudentProfile только своих студентов, НЕ может менять role field
    - Остальные: запрещено
    - Все активные: GET любой StudentProfile
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет имеет ли пользователь доступ к профилю студента"""
        if not request.user.is_active:
            return False

        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Все могут читать
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        from .models import StudentProfile

        # Это должен быть StudentProfile
        if not isinstance(obj, StudentProfile):
            return False

        # Студент может редактировать только свой профиль (но не role field)
        if request.user.role == User.Role.STUDENT:
            if request.user != obj.user:
                return False
            # Студент НЕ может менять role field (это контролируется в сериализаторе)
            return True

        # Тьютор может редактировать профили своих студентов (но не role field)
        if request.user.role == User.Role.TUTOR:
            if obj.tutor != request.user:
                return False
            # Тьютор НЕ может менять role field (это контролируется в сериализаторе)
            return True

        return False


class IsStaffOrAdmin(BasePermission):
    """
    Разрешение ТОЛЬКО для пользователей с правами администратора или staff.
    НЕ включает тьюторов - они используют IsTutorOrAdmin для управления студентами.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован

    Права по ролям:
    - Admin (is_staff=True или is_superuser=True): полный доступ
    - Остальные (включая TUTOR): запрещено
    - Неактивные: запрещено

    Примечание:
    - Используется для admin-only операций (создание/удаление users, system management)
    - Тьютор получает доступ ТОЛЬКО к управлению своими студентами через IsTutorOrAdmin/TutorCanManageStudentProfiles
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет глобальные права пользователя"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.is_staff or request.user.is_superuser


class IsAdminUserOnly(BasePermission):
    """
    Разрешение ТОЛЬКО для пользователей с правами администратора (более строгое, чем IsStaffOrAdmin).

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован
    - is_staff=True или is_superuser=True

    Права по ролям:
    - Admin (is_staff=True или is_superuser=True): полный доступ
    - Все остальные (включая TUTOR): запрещено
    - Неактивные: запрещено

    Примечание:
    - Это наиболее строгое разрешение для admin-only операций
    - Используется для защиты критических операций (удаление users, system configuration)
    - Отличается от IsStaffOrAdmin: оба требуют is_staff, но IsAdminUserOnly может быть еще строже
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь имеет права администратора"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.is_staff or request.user.is_superuser


class IsStudent(BasePermission):
    """
    Разрешение только для студентов.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован
    - role=STUDENT

    Права по ролям:
    - Student (role=STUDENT, active): полный доступ
    - Все остальные (Admin, Teacher, Tutor, Parent): запрещено
    - Неактивные: запрещено

    Используется для:
    - Student-only endpoints
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь студент"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.role == User.Role.STUDENT


class IsTeacher(BasePermission):
    """
    Разрешение только для учителей.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован
    - role=TEACHER

    Права по ролям:
    - Teacher (role=TEACHER, active): полный доступ
    - Все остальные (Admin, Student, Tutor, Parent): запрещено
    - Неактивные: запрещено

    Используется для:
    - Teacher-only endpoints
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь учитель"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.role == User.Role.TEACHER


class IsTutor(BasePermission):
    """
    Разрешение только для тьюторов.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован
    - role=TUTOR

    Права по ролям:
    - Tutor (role=TUTOR, active): полный доступ
    - Все остальные (Admin, Student, Teacher, Parent): запрещено
    - Неактивные: запрещено

    Используется для:
    - Tutor-only endpoints
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь тьютор"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.role == User.Role.TUTOR


class IsParent(BasePermission):
    """
    Разрешение только для родителей.

    Требует:
    - Пользователь активен (is_active=True)
    - Пользователь аутентифицирован
    - role=PARENT

    Права по ролям:
    - Parent (role=PARENT, active): полный доступ
    - Все остальные (Admin, Student, Teacher, Tutor): запрещено
    - Неактивные: запрещено

    Используется для:
    - Parent-only endpoints
    """

    def has_permission(self, request, view) -> bool:
        """Проверяет что пользователь родитель"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        return request.user.role == User.Role.PARENT


# Backward compatibility alias
IsAdminUser = IsAdminUserOnly
