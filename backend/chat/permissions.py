"""
Permission classes for chat system.

Handles authorization checks for chat operations:
- Verify user can initiate chat with another user
- Check enrollment and relationship permissions
"""

import logging
from rest_framework import permissions
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment

logger = logging.getLogger(__name__)


class CanInitiateChat(permissions.BasePermission):
    """
    Permission check for initiating chats.

    Rules:
    - Student can chat with their assigned teachers (via SubjectEnrollment)
    - Student can chat with their tutor
    - Teacher can chat with their enrolled students
    - Tutor can chat with their assigned students
    - Tutor can chat with teachers of their assigned students
    - Parent can chat with child's teachers and tutor
    - Admin/staff can chat with anyone

    Prevents:
    - Students chatting with random students
    - Teachers chatting with unenrolled students
    - Tutors chatting with unassigned students
    - Users chatting with themselves
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if requester can initiate chat with obj (contact user).

        Args:
            request: HTTP request
            view: View instance
            obj: Contact user (User instance)

        Returns:
            bool: True if relationship allows chat initiation
        """
        requester = request.user
        contact_user = obj

        # Cannot chat with yourself
        if requester.id == contact_user.id:
            return False

        # Admin/staff can chat with anyone
        if requester.is_staff or requester.is_superuser:
            return True

        # For subject-based chats, we need enrollment validation
        # This is handled by can_chat_with() static method
        # For direct permission check, verify basic relationship exists
        can_chat, _, _ = self.can_chat_with(requester, contact_user)
        return can_chat

    @staticmethod
    def can_chat_with(requester, contact_user, subject_id=None):
        """
        Check if requester can initiate chat with contact_user.

        Args:
            requester: User initiating the chat
            contact_user: User to chat with
            subject_id: Optional subject ID for FORUM_SUBJECT chats

        Returns:
            tuple: (can_chat: bool, chat_type: str, enrollment: SubjectEnrollment or None)
        """
        # Same user cannot chat with themselves
        if requester.id == contact_user.id:
            logger.warning(f"User {requester.id} tried to chat with themselves")
            return False, None, None

        # Check student-teacher relationship
        if requester.role == 'student' and contact_user.role == 'teacher':
            if subject_id:
                # Verify student is enrolled with this teacher for this subject
                enrollment = SubjectEnrollment.objects.filter(
                    student=requester,
                    teacher=contact_user,
                    subject_id=subject_id,
                    is_active=True
                ).first()

                if enrollment:
                    return True, 'FORUM_SUBJECT', enrollment

            # No subject_id or not enrolled
            logger.warning(
                f"Student {requester.id} not enrolled with teacher {contact_user.id} "
                f"for subject {subject_id}"
            )
            return False, None, None

        # Check teacher-student relationship (reverse)
        if requester.role == 'teacher' and contact_user.role == 'student':
            if subject_id:
                enrollment = SubjectEnrollment.objects.filter(
                    student=contact_user,
                    teacher=requester,
                    subject_id=subject_id,
                    is_active=True
                ).first()

                if enrollment:
                    return True, 'FORUM_SUBJECT', enrollment

            logger.warning(
                f"Teacher {requester.id} not assigned to student {contact_user.id} "
                f"for subject {subject_id}"
            )
            return False, None, None

        # Check student-tutor relationship
        if requester.role == 'student' and contact_user.role == 'tutor':
            try:
                student_profile = StudentProfile.objects.get(user=requester)
                if student_profile.tutor_id == contact_user.id:
                    # Get any enrollment for this student (for FORUM_TUTOR type)
                    # Use subject_id if provided, otherwise get first enrollment
                    enrollment = SubjectEnrollment.objects.filter(
                        student=requester
                    ).first()

                    if subject_id:
                        # Prefer enrollment with specified subject
                        specific_enrollment = SubjectEnrollment.objects.filter(
                            student=requester,
                            subject_id=subject_id
                        ).first()
                        if specific_enrollment:
                            enrollment = specific_enrollment

                    if enrollment:
                        return True, 'FORUM_TUTOR', enrollment

            except StudentProfile.DoesNotExist:
                pass

            logger.warning(
                f"Student {requester.id} does not have tutor {contact_user.id}"
            )
            return False, None, None

        # Check tutor-student relationship (reverse)
        if requester.role == 'tutor' and contact_user.role == 'student':
            try:
                student_profile = StudentProfile.objects.get(user=contact_user)
                if student_profile.tutor_id == requester.id:
                    enrollment = SubjectEnrollment.objects.filter(
                        student=contact_user
                    ).first()

                    if subject_id:
                        specific_enrollment = SubjectEnrollment.objects.filter(
                            student=contact_user,
                            subject_id=subject_id
                        ).first()
                        if specific_enrollment:
                            enrollment = specific_enrollment

                    if enrollment:
                        return True, 'FORUM_TUTOR', enrollment

            except StudentProfile.DoesNotExist:
                pass

            logger.warning(
                f"Tutor {requester.id} not assigned to student {contact_user.id}"
            )
            return False, None, None

        # Check tutor-teacher relationship
        # Tutor can chat with teachers of their assigned students
        if requester.role == 'tutor' and contact_user.role == 'teacher':
            # Find if teacher teaches any of tutor's students
            enrollment = SubjectEnrollment.objects.filter(
                student__student_profile__tutor=requester,
                teacher=contact_user,
                is_active=True
            ).first()

            if enrollment:
                # Return FORUM_TUTOR type (tutor chatting about their student)
                return True, 'FORUM_TUTOR', enrollment

            logger.warning(
                f"Tutor {requester.id} - Teacher {contact_user.id} "
                f"doesn't teach any of tutor's students"
            )
            return False, None, None

        # Check teacher-tutor relationship (reverse)
        # Teacher can chat with tutor of their students
        if requester.role == 'teacher' and contact_user.role == 'tutor':
            # Find if tutor supervises any of teacher's students
            enrollment = SubjectEnrollment.objects.filter(
                student__student_profile__tutor=contact_user,
                teacher=requester,
                is_active=True
            ).first()

            if enrollment:
                return True, 'FORUM_TUTOR', enrollment

            logger.warning(
                f"Teacher {requester.id} - Tutor {contact_user.id} "
                f"doesn't supervise any of teacher's students"
            )
            return False, None, None

        # Check parent-teacher relationship
        # Parent can chat with teachers of their child
        if requester.role == 'parent' and contact_user.role == 'teacher':
            # Find if teacher teaches parent's child
            enrollment = SubjectEnrollment.objects.filter(
                student__student_profile__parent=requester,
                teacher=contact_user,
                is_active=True
            ).first()

            if enrollment:
                # Use FORUM_SUBJECT type (parent observing child-teacher chat)
                return True, 'FORUM_SUBJECT', enrollment

            logger.warning(
                f"Parent {requester.id} - Teacher {contact_user.id} "
                f"doesn't teach parent's child"
            )
            return False, None, None

        # Check teacher-parent relationship (reverse)
        if requester.role == 'teacher' and contact_user.role == 'parent':
            enrollment = SubjectEnrollment.objects.filter(
                student__student_profile__parent=contact_user,
                teacher=requester,
                is_active=True
            ).first()

            if enrollment:
                return True, 'FORUM_SUBJECT', enrollment

            logger.warning(
                f"Teacher {requester.id} - Parent {contact_user.id} "
                f"is not parent of any student"
            )
            return False, None, None

        # Check parent-tutor relationship
        # Parent can chat with tutor of their child
        if requester.role == 'parent' and contact_user.role == 'tutor':
            # Find if tutor supervises parent's child
            student_profile = StudentProfile.objects.filter(
                parent=requester,
                tutor=contact_user
            ).first()

            if student_profile:
                # Get an enrollment for this student
                enrollment = SubjectEnrollment.objects.filter(
                    student=student_profile.user
                ).first()

                if enrollment:
                    return True, 'FORUM_TUTOR', enrollment

            logger.warning(
                f"Parent {requester.id} - Tutor {contact_user.id} "
                f"is not tutor of parent's child"
            )
            return False, None, None

        # Check tutor-parent relationship (reverse)
        if requester.role == 'tutor' and contact_user.role == 'parent':
            student_profile = StudentProfile.objects.filter(
                parent=contact_user,
                tutor=requester
            ).first()

            if student_profile:
                enrollment = SubjectEnrollment.objects.filter(
                    student=student_profile.user
                ).first()

                if enrollment:
                    return True, 'FORUM_TUTOR', enrollment

            logger.warning(
                f"Tutor {requester.id} - Parent {contact_user.id} "
                f"is not parent of tutor's student"
            )
            return False, None, None

        # No valid relationship found
        logger.warning(
            f"No valid relationship between {requester.role} {requester.id} "
            f"and {contact_user.role} {contact_user.id}"
        )
        return False, None, None
