import logging
from typing import TYPE_CHECKING

from django.core.cache import cache

if TYPE_CHECKING:
    from accounts.models import User

logger = logging.getLogger(__name__)


def can_initiate_chat(user1: "User", user2: "User") -> bool:
    """
    Check if user1 can initiate a chat with user2.

    Unified permission matrix for all role combinations:

    ALLOWED (CAN initiate chat):
    1.  Admin -> Anyone (always allowed)
    2.  Student -> Teacher (if ACTIVE SubjectEnrollment exists)
    3.  Student -> Tutor (if StudentProfile.tutor is set and tutor is_active)
    4.  Teacher -> Student (if ACTIVE SubjectEnrollment exists)
    5.  Teacher -> Parent (if parent has child with ACTIVE enrollment with this teacher)
    6.  Teacher -> Tutor (if common student with ACTIVE enrollment)
    7.  Tutor -> Student (if StudentProfile.tutor is set and tutor is_active)
    8.  Tutor -> Teacher (if common student with ACTIVE enrollment)
    9.  Tutor -> Parent (if parent has child with this tutor and tutor is_active)
    10. Parent -> Teacher (ONLY if parent has child with ACTIVE enrollment with this teacher)
    11. Parent -> Tutor (ONLY if parent has child with this tutor and tutor is_active)

    FORBIDDEN (CANNOT initiate chat):
    - Student ↔ Student (mutual)
    - Student ↔ Parent (mutual)
    - Teacher ↔ Teacher (mutual)
    - Parent ↔ Parent (mutual)
    - Tutor ↔ Tutor (mutual)

    Args:
        user1: User initiating the chat
        user2: User receiving the chat invitation

    Returns:
        bool: True if chat can be initiated, False otherwise
    """
    cache_key = f"chat_permission:{min(user1.id, user2.id)}:{max(user1.id, user2.id)}"

    result = cache.get(cache_key)
    if result is not None:
        return result

    try:
        if not user1.is_active or not user2.is_active:
            result = False
        elif user1.role == "admin":
            result = True
        elif user2.role == "admin":
            result = True
        elif user1.role == "student":
            result = _check_student_can_chat_with(user1, user2)
        elif user1.role == "teacher":
            result = _check_teacher_can_chat_with(user1, user2)
        elif user1.role == "tutor":
            result = _check_tutor_can_chat_with(user1, user2)
        elif user1.role == "parent":
            result = _check_parent_can_chat_with(user1, user2)
        else:
            result = False

    except Exception as e:
        logger.debug(f"[can_initiate_chat] Error checking chat initiation: {e}")
        result = False

    cache.set(cache_key, result, timeout=300)
    return result


def _check_student_can_chat_with(student: "User", other: "User") -> bool:
    if other.role == "student":
        return False

    if other.role == "parent":
        return False

    if other.role == "teacher":
        from materials.models import SubjectEnrollment

        return SubjectEnrollment.objects.filter(
            student=student,
            teacher=other,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    if other.role == "tutor":
        if not other.is_active:
            return False

        from accounts.models import StudentProfile

        return StudentProfile.objects.filter(
            user=student,
            tutor=other,
            tutor__is_active=True,
        ).exists()

    return False


def _check_teacher_can_chat_with(teacher: "User", other: "User") -> bool:
    if other.role == "teacher":
        return False

    if other.role == "student":
        from materials.models import SubjectEnrollment

        return SubjectEnrollment.objects.filter(
            student=other,
            teacher=teacher,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    if other.role == "parent":
        from accounts.models import StudentProfile
        from materials.models import SubjectEnrollment

        parent_children = StudentProfile.objects.filter(
            parent=other,
            parent__is_active=True,
        ).values_list("user_id", flat=True)

        return SubjectEnrollment.objects.filter(
            student_id__in=parent_children,
            teacher=teacher,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    if other.role == "tutor":
        from materials.models import SubjectEnrollment
        from accounts.models import StudentProfile

        tutor_students = StudentProfile.objects.filter(
            tutor=other,
            tutor__is_active=True,
        ).values_list("user_id", flat=True)

        return SubjectEnrollment.objects.filter(
            student_id__in=tutor_students,
            teacher=teacher,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    return False


def _check_tutor_can_chat_with(tutor: "User", other: "User") -> bool:
    if other.role == "tutor":
        return False

    if other.role == "student":
        from accounts.models import StudentProfile

        return StudentProfile.objects.filter(
            user=other,
            tutor=tutor,
            tutor__is_active=True,
        ).exists()

    if other.role == "teacher":
        from materials.models import SubjectEnrollment
        from accounts.models import StudentProfile

        tutor_students = StudentProfile.objects.filter(
            tutor=tutor,
            tutor__is_active=True,
        ).values_list("user_id", flat=True)

        return SubjectEnrollment.objects.filter(
            student_id__in=tutor_students,
            teacher=other,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    if other.role == "parent":
        from accounts.models import StudentProfile

        return StudentProfile.objects.filter(
            parent=other,
            tutor=tutor,
            parent__is_active=True,
            tutor__is_active=True,
        ).exists()

    return False


def _check_parent_can_chat_with(parent: "User", other: "User") -> bool:
    if other.role == "parent":
        return False

    if other.role == "student":
        return False

    if other.role == "teacher":
        from accounts.models import StudentProfile
        from materials.models import SubjectEnrollment

        parent_children = StudentProfile.objects.filter(
            parent=parent,
            parent__is_active=True,
        ).values_list("user_id", flat=True)

        return SubjectEnrollment.objects.filter(
            student_id__in=parent_children,
            teacher=other,
            status=SubjectEnrollment.Status.ACTIVE,
        ).exists()

    if other.role == "tutor":
        from accounts.models import StudentProfile

        return StudentProfile.objects.filter(
            parent=parent,
            tutor=other,
            parent__is_active=True,
            tutor__is_active=True,
        ).exists()

    return False
