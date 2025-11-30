"""
Permissions for lesson scheduling system.

Defines role-based access control for lesson management.
"""

from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Permission for teachers only.
    """

    def has_permission(self, request, view):
        """Check if user is a teacher."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'teacher'
        )


class IsStudent(permissions.BasePermission):
    """
    Permission for students only.
    """

    def has_permission(self, request, view):
        """Check if user is a student."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'student'
        )


class IsTutor(permissions.BasePermission):
    """
    Permission for tutors only.
    """

    def has_permission(self, request, view):
        """Check if user is a tutor."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'tutor'
        )


class IsTeacherOrStudent(permissions.BasePermission):
    """
    Permission for teachers and students.
    """

    def has_permission(self, request, view):
        """Check if user is teacher or student."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['teacher', 'student']
        )