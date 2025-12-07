"""
Custom permissions for knowledge graph app
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Позволяет редактировать объект только его владельцу.
    Остальные могут только читать.
    """

    def has_object_permission(self, request, view, obj):
        # Чтение доступно всем
        if request.method in SAFE_METHODS:
            return True

        # Запись только владельцу
        return obj.created_by == request.user


class IsTeacherOrAdmin(BasePermission):
    """
    Позволяет доступ только учителям и администраторам
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.role == 'teacher' or request.user.is_staff or request.user.is_superuser)
        )


class IsGraphOwner(BasePermission):
    """
    Проверяет что пользователь является создателем графа
    """

    def has_object_permission(self, request, view, obj):
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Только создатель графа
        return obj.created_by == request.user


class IsStudentOfGraph(BasePermission):
    """
    Проверяет что пользователь является студентом в графе
    """

    def has_object_permission(self, request, view, obj):
        # Админы могут всё
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Студент может видеть свой граф
        return obj.student == request.user
