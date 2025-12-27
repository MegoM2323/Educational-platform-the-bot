"""
Разрешения для Invoice API endpoints.

Бизнес-правила:
- Только тьюторы могут создавать и управлять счетами
- Только родители могут оплачивать счета
- Каждая роль видит только свои счета
"""

from rest_framework.permissions import BasePermission


class IsTutorOrParent(BasePermission):
    """
    Позволяет выполнять действия только тьютору или родителю.

    Бизнес-правила:
    - Тьюторы: могут создавать и управлять счетами для своих студентов
    - Родители: могут просматривать и оплачивать счета своих детей
    - Админы: имеют полный доступ
    """

    def has_permission(self, request, view):
        """Проверяет глобальные права пользователя"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        # Админы имеют полный доступ
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Разрешено только тьюторам и родителям
        return request.user.role in ['tutor', 'parent']


class IsTutorForStudent(BasePermission):
    """
    Позволяет тьютору управлять счетами только для своих студентов.

    Бизнес-правила:
    - Тьютор может создавать счета только для студентов, назначенных ему
    - Проверка через StudentProfile.tutor
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет права на объект Invoice"""
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Только тьютор может управлять
        if request.user.role != 'tutor':
            return False

        # Проверяем что счет принадлежит этому тьютору
        return obj.tutor == request.user


class IsParentOfStudent(BasePermission):
    """
    Позволяет родителю видеть и оплачивать счета только для своих детей.

    Бизнес-правила:
    - Родитель может просматривать счета только для своих детей
    - Проверка через StudentProfile.parent
    """

    def has_object_permission(self, request, view, obj):
        """Проверяет права на объект Invoice"""
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Только родитель может просматривать
        if request.user.role != 'parent':
            return False

        # Проверяем что счет выставлен родителю этого студента
        return obj.parent == request.user
