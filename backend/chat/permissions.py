import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accounts.models import User

logger = logging.getLogger(__name__)


def can_initiate_chat(user1: "User", user2: "User") -> bool:
    """
    Check if user1 can initiate a chat with user2.

    Implements permission matrix from CHAT_ARCHITECTURE_SIMPLIFIED.md:
    - admin: can chat with anyone
    - student + teacher: need active SubjectEnrollment
    - student + tutor: need StudentProfile.tutor == tutor
    - teacher + tutor: need common student
    - students cannot chat with each other

    Args:
        user1: User initiating the chat
        user2: User receiving the chat invitation

    Returns:
        bool: True if chat can be initiated, False otherwise
    """
    try:
        # 1. Admin can always initiate chat
        if user1.role == "admin":
            return True

        # 2. Students cannot chat with each other
        if user1.role == "student" and user2.role == "student":
            return False

        # 3. Student + Teacher (bidirectional)
        if (user1.role == "student" and user2.role == "teacher") or (
            user1.role == "teacher" and user2.role == "student"
        ):
            student = user1 if user1.role == "student" else user2
            teacher = user1 if user1.role == "teacher" else user2

            from materials.models import SubjectEnrollment

            return SubjectEnrollment.objects.filter(
                student=student,
                teacher=teacher,
                status=SubjectEnrollment.Status.ACTIVE,
            ).exists()

        # 4. Student + Tutor (bidirectional)
        if (user1.role == "student" and user2.role == "tutor") or (
            user1.role == "tutor" and user2.role == "student"
        ):
            student = user1 if user1.role == "student" else user2
            tutor = user1 if user1.role == "tutor" else user2

            from accounts.models import StudentProfile

            return StudentProfile.objects.filter(
                user=student,
                tutor=tutor,
            ).exists()

        # 5. Teacher + Tutor (bidirectional)
        if (user1.role == "teacher" and user2.role == "tutor") or (
            user1.role == "tutor" and user2.role == "teacher"
        ):
            teacher = user1 if user1.role == "teacher" else user2
            tutor = user1 if user1.role == "tutor" else user2

            from materials.models import SubjectEnrollment
            from accounts.models import StudentProfile

            tutor_students = StudentProfile.objects.filter(
                tutor=tutor,
            ).values_list("user_id", flat=True)

            return SubjectEnrollment.objects.filter(
                student_id__in=tutor_students,
                teacher=teacher,
                status=SubjectEnrollment.Status.ACTIVE,
            ).exists()

        # 6. Parent + Teacher (bidirectional)
        if (user1.role == "parent" and user2.role == "teacher") or (
            user1.role == "teacher" and user2.role == "parent"
        ):
            parent = user1 if user1.role == "parent" else user2
            teacher = user1 if user1.role == "teacher" else user2

            from accounts.models import StudentProfile
            from materials.models import SubjectEnrollment

            parent_children = StudentProfile.objects.filter(parent=parent).values_list(
                "user_id", flat=True
            )

            return SubjectEnrollment.objects.filter(
                student_id__in=parent_children,
                teacher=teacher,
                status=SubjectEnrollment.Status.ACTIVE,
            ).exists()

        # 7. Parent + Tutor (bidirectional)
        if (user1.role == "parent" and user2.role == "tutor") or (
            user1.role == "tutor" and user2.role == "parent"
        ):
            parent = user1 if user1.role == "parent" else user2
            tutor = user1 if user1.role == "tutor" else user2

            from accounts.models import StudentProfile

            return StudentProfile.objects.filter(
                parent=parent,
                tutor=tutor,
            ).exists()

        # 8. Parent + Student - FORBIDDEN
        if (user1.role == "parent" and user2.role == "student") or (
            user1.role == "student" and user2.role == "parent"
        ):
            return False

        return False

    except Exception as e:
        logger.debug(f"[can_initiate_chat] Error checking chat initiation: {e}")
        return False
