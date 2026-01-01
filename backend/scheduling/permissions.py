"""
Permissions for lesson scheduling system.

Defines role-based access control for lesson management.
"""

from rest_framework import permissions

from accounts.models import User
from accounts.permissions import (
    IsTeacher as BaseIsTeacher,
    IsStudent as BaseIsStudent,
    IsTutor as BaseIsTutor,
    IsParent as BaseIsParent,
)


IsTeacher = BaseIsTeacher
IsStudent = BaseIsStudent
IsTutor = BaseIsTutor
IsParent = BaseIsParent


class IsParentOfStudent(permissions.BasePermission):
    """
    Permission check for parent accessing their child's data.

    Проверяет, что пользователь является родителем и имеет право
    доступа к данным конкретного ребёнка (студента).
    """
    message = "You can only view your own children's data."

    def has_permission(self, request, view):
        """Проверяет, что пользователь является родителем."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.PARENT
        )

    def has_object_permission(self, request, view, obj):
        """Проверяет, что родитель имеет доступ к данным ребёнка."""
        from accounts.models import StudentProfile

        # Проверяем, что obj является экземпляром User
        if not isinstance(obj, User):
            return False

        # Проверяем, что obj - студент
        if obj.role != User.Role.STUDENT:
            return False

        # Проверяем, что студент принадлежит этому родителю
        try:
            profile = StudentProfile.objects.get(user=obj)
            return profile.parent == request.user
        except StudentProfile.DoesNotExist:
            return False


class IsTeacherOrStudent(permissions.BasePermission):
    """
    Permission for teachers and students.
    """

    def has_permission(self, request, view):
        """Check if user is teacher or student."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.Role.TEACHER, User.Role.STUDENT]
        )