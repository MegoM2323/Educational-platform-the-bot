"""
Permission classes for chat system.

Handles authorization checks for chat operations:
- Verify user can initiate chat with another user
- Check enrollment and relationship permissions
- Parent access to children's chat rooms
"""

import logging
from django.db import transaction
from rest_framework import permissions
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment
from chat.models import ChatParticipant

logger = logging.getLogger(__name__)


def check_parent_access_to_room(parent_user, room, add_to_participants: bool = True) -> bool:
    """
    Проверяет доступ родителя к комнате чата.
    Родитель имеет доступ если один из его детей является участником.

    При положительной проверке и add_to_participants=True родитель
    автоматически добавляется в участники комнаты.

    Args:
        parent_user: User с ролью parent
        room: ChatRoom объект
        add_to_participants: Добавлять ли родителя в participants (default True)

    Returns:
        bool: True если родитель имеет доступ
    """
    if parent_user.role != 'parent':
        return False

    # Получаем ID всех детей этого родителя
    children_ids = list(StudentProfile.objects.filter(
        parent=parent_user
    ).values_list('user_id', flat=True))

    if not children_ids:
        return False

    # Проверяем, является ли хотя бы один ребёнок участником комнаты
    if not room.participants.filter(id__in=children_ids).exists():
        return False

    # Добавляем родителя в участники для будущих проверок (если нужно)
    if add_to_participants:
        with transaction.atomic():
            room.participants.add(parent_user)
            ChatParticipant.objects.get_or_create(room=room, user=parent_user)
        logger.info(
            f'[check_parent_access_to_room] Parent {parent_user.id} granted access to room {room.id} '
            f'via child relationship and added to participants'
        )
    else:
        logger.info(
            f'[check_parent_access_to_room] Parent {parent_user.id} granted access to room {room.id} '
            f'via child relationship (not added to participants)'
        )

    return True


def check_teacher_access_to_room(teacher_user, room, add_to_participants: bool = True) -> bool:
    """
    Проверяет доступ учителя к комнате чата через enrollment.
    Учитель имеет доступ если он назначен учителем в enrollment этого чата.

    При положительной проверке и add_to_participants=True учитель
    автоматически добавляется в участники комнаты.

    Args:
        teacher_user: User с ролью teacher
        room: ChatRoom объект
        add_to_participants: Добавлять ли учителя в participants (default True)

    Returns:
        bool: True если учитель имеет доступ
    """
    if teacher_user.role != 'teacher':
        return False

    # Проверяем через enrollment: учитель должен быть назначен в enrollment этого чата
    if not room.enrollment:
        return False

    if room.enrollment.teacher_id != teacher_user.id:
        return False

    # Добавляем учителя в участники для будущих проверок (если нужно)
    if add_to_participants:
        with transaction.atomic():
            room.participants.add(teacher_user)
            ChatParticipant.objects.get_or_create(room=room, user=teacher_user)
        logger.info(
            f'[check_teacher_access_to_room] Teacher {teacher_user.id} granted access to room {room.id} '
            f'via enrollment relationship and added to participants'
        )
    else:
        logger.info(
            f'[check_teacher_access_to_room] Teacher {teacher_user.id} granted access to room {room.id} '
            f'via enrollment relationship (not added to participants)'
        )

    return True


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
            # Check TWO ways a tutor can be linked to a student:
            # 1. Via StudentProfile.tutor (direct assignment)
            # 2. Via User.created_by_tutor (tutor who created the student)
            is_tutor_linked = False

            try:
                student_profile = StudentProfile.objects.get(user=requester)
                if student_profile.tutor_id == contact_user.id:
                    is_tutor_linked = True
            except StudentProfile.DoesNotExist:
                pass

            # Also check if tutor created this student
            if not is_tutor_linked and requester.created_by_tutor_id == contact_user.id:
                is_tutor_linked = True

            if is_tutor_linked:
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

            logger.warning(
                f"Student {requester.id} does not have tutor {contact_user.id}"
            )
            return False, None, None

        # Check tutor-student relationship (reverse)
        if requester.role == 'tutor' and contact_user.role == 'student':
            # Check TWO ways a tutor can be linked to a student:
            # 1. Via StudentProfile.tutor (direct assignment)
            # 2. Via User.created_by_tutor (tutor who created the student)
            is_tutor_linked = False

            try:
                student_profile = StudentProfile.objects.get(user=contact_user)
                if student_profile.tutor_id == requester.id:
                    is_tutor_linked = True
            except StudentProfile.DoesNotExist:
                pass

            # Also check if tutor created this student
            if not is_tutor_linked and contact_user.created_by_tutor_id == requester.id:
                is_tutor_linked = True

            if is_tutor_linked:
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

            logger.warning(
                f"Tutor {requester.id} not assigned to student {contact_user.id}"
            )
            return False, None, None

        # Check tutor-teacher relationship
        # Tutor can chat with teachers of their assigned students
        if requester.role == 'tutor' and contact_user.role == 'teacher':
            # Find if teacher teaches any of tutor's students
            # Check both StudentProfile.tutor and User.created_by_tutor
            from django.db.models import Q
            enrollment = SubjectEnrollment.objects.filter(
                Q(student__student_profile__tutor=requester) |
                Q(student__created_by_tutor=requester),
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
            # Check both StudentProfile.tutor and User.created_by_tutor
            from django.db.models import Q
            enrollment = SubjectEnrollment.objects.filter(
                Q(student__student_profile__tutor=contact_user) |
                Q(student__created_by_tutor=contact_user),
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
            # Check both StudentProfile.tutor and User.created_by_tutor
            from django.db.models import Q
            student_profile = StudentProfile.objects.filter(
                parent=requester
            ).filter(
                Q(tutor=contact_user) | Q(user__created_by_tutor=contact_user)
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
            # Check both StudentProfile.tutor and User.created_by_tutor
            from django.db.models import Q
            student_profile = StudentProfile.objects.filter(
                parent=contact_user
            ).filter(
                Q(tutor=requester) | Q(user__created_by_tutor=requester)
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


class IsMessageAuthor(permissions.BasePermission):
    """
    Permission check for message author.

    Только автор может редактировать/удалять свои сообщения.
    Staff и superuser имеют полный доступ.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user is the author of the message.

        Args:
            request: HTTP request
            view: View instance
            obj: Message instance (должен иметь поле sender)

        Returns:
            bool: True if user is author or staff/superuser
        """
        # Staff/superuser can always access
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if user is sender
        is_author = obj.sender == request.user

        if not is_author:
            logger.warning(
                f"Permission denied: User {request.user.id} attempted to "
                f"modify message {getattr(obj, 'id', 'unknown')} "
                f"owned by user {getattr(obj.sender, 'id', 'unknown')}"
            )

        return is_author


class CanModerateChat(permissions.BasePermission):
    """
    Permission for chat moderation actions (delete any message, ban, mute).

    A user can moderate if:
    1. Is staff/superuser
    2. Is ChatParticipant with is_admin=True for this chat
    3. Is teacher role
    4. Is tutor role for FORUM_TUTOR chats
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can moderate chat.

        Args:
            request: HTTP request
            view: View instance
            obj: Message or ChatParticipant instance (must have room attribute)

        Returns:
            bool: True if user can moderate this chat
        """
        user = request.user

        # Staff/superuser can always moderate
        if user.is_staff or user.is_superuser:
            return True

        # Get room from object (obj can be Message or ChatParticipant)
        room = getattr(obj, 'room', None)
        if not room:
            logger.warning(
                f"CanModerateChat: Object {type(obj).__name__} has no room attribute"
            )
            return False

        # Check if user is room admin
        try:
            participant = ChatParticipant.objects.get(room=room, user=user)
            if participant.is_admin:
                return True
        except ChatParticipant.DoesNotExist:
            logger.warning(
                f"CanModerateChat: User {user.id} is not a participant in room {room.id}"
            )
            return False

        # Teachers can moderate their chats
        if user.role == 'teacher':
            return True

        # Tutors can moderate FORUM_TUTOR chats
        from chat.models import ChatRoom
        if user.role == 'tutor' and room.type == ChatRoom.Type.FORUM_TUTOR:
            return True

        logger.warning(
            f"CanModerateChat: Permission denied for user {user.id} "
            f"(role={user.role}) in room {room.id}"
        )
        return False
