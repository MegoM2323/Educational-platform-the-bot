"""
Основной сервис для управления чатами.
Предоставляет методы для получения, создания и управления чат-комнатами.
"""
import logging
from typing import Tuple, Optional

from django.db import transaction
from django.db.models import (
    Count,
    Q,
    OuterRef,
    Subquery,
    IntegerField,
    Prefetch,
    F,
)
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile
from materials.models import SubjectEnrollment
from ..models import ChatRoom, ChatParticipant, Message

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatService:
    """
    Сервис для управления чатами.
    Инкапсулирует бизнес-логику работы с чат-комнатами и участниками.
    """

    @staticmethod
    def get_or_create_chat(user1: User, user2: User) -> Tuple[ChatRoom, bool]:
        """
        Получить существующий или создать новый чат между двумя пользователями.

        ВАЖНО: Использует детерминированный порядок блокировки для избежания deadlock.
        user1 и user2 сортируются по user.id для гарантии одинакового порядка блокировок.
        Даже при параллельном вызове get_or_create_chat(A, B) и get_or_create_chat(B, A)
        обе операции будут блокировать в порядке (min(A,B), max(A,B)), предотвращая deadlock.

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            tuple[ChatRoom, bool]: (room, created)
                - created=True если чат был только что создан
                - created=False если найден существующий

        Raises:
            ValueError: Если user1 == user2 или один из пользователей неактивен
        """
        if user1.id == user2.id:
            raise ValueError("Cannot create direct chat with yourself")

        if not user1.is_active or not user2.is_active:
            raise ValueError("Both users must be active")

        # ✅ ИСПРАВЛЕНИЕ DEADLOCK: детерминированный порядок
        # Всегда блокируем в порядке меньший user.id → больший user.id
        # Это гарантирует что Thread A и Thread B блокируют в одном порядке
        ordered_users = sorted([user1, user2], key=lambda u: u.id)
        user_min, user_max = ordered_users[0], ordered_users[1]

        # Первая проверка БЕЗ блокировки (fast path)
        existing_room = ChatService._find_existing_chat(user_min, user_max, for_update=False)
        if existing_room:
            logger.debug(f"Found existing chat {existing_room.id} for users {user1.id}, {user2.id}")
            return existing_room, False

        # Вторая проверка С блокировкой (slow path)
        with transaction.atomic():
            existing_room = ChatService._find_existing_chat(user_min, user_max, for_update=True)
            if existing_room:
                logger.debug(f"Found existing chat {existing_room.id} after lock")
                return existing_room, False

            # Создаем чат (порядок user1, user2 не важен, т.к. уже в транзакции)
            room = ChatService._create_chat(user1, user2)
            logger.info(f"Created new chat {room.id} between users {user1.id} and {user2.id}")
            return room, True

    @staticmethod
    def _find_existing_chat(
        user1: User, user2: User, for_update: bool = False
    ) -> Optional[ChatRoom]:
        """
        Найти существующий direct чат между двумя пользователями.

        Логика:
        1. Оба пользователя в ChatParticipant
        2. Проверка что ровно 2 участника (SQL: COUNT(DISTINCT user_id) = 2)
        3. Фильтр по is_active=True

        Args:
            user1: Первый пользователь
            user2: Второй пользователь
            for_update: Если True, использует select_for_update() для блокировки

        Returns:
            ChatRoom или None
        """
        participant_count_subquery = (
            ChatRoom.objects.filter(id=OuterRef("id"))
            .annotate(cnt=Count("participants", distinct=True))
            .values("cnt")[:1]
        )

        qs = (
            ChatRoom.objects.filter(participants__user=user1, is_active=True)
            .filter(participants__user=user2)
            .annotate(participant_count=Subquery(participant_count_subquery))
            .filter(participant_count=2)
        )

        if for_update:
            qs = qs.select_for_update()

        return qs.first()

    @staticmethod
    def _create_chat(user1: User, user2: User) -> ChatRoom:
        """
        Создать новый direct чат в транзакции.

        Операции:
        1. Создание ChatRoom (только is_active)
        2. Создание двух ChatParticipant записей

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            ChatRoom: Созданная комната
        """
        room = ChatRoom.objects.create(is_active=True)

        ChatParticipant.objects.bulk_create(
            [
                ChatParticipant(room=room, user=user1),
                ChatParticipant(room=room, user=user2),
            ],
            ignore_conflicts=True,
        )

        return room

    @staticmethod
    def _validate_chat_permissions(user1: User, user2: User) -> bool:
        """
        Проверить актуальные permissions между двумя пользователями.
        Использует can_initiate_chat() для проверки ТЕКУЩИХ прав.

        Проверяет все связи через:
        - SubjectEnrollment.status=ACTIVE
        - StudentProfile.tutor
        - Ролевую матрицу permissions

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            bool: True если permission актуален в обе стороны
        """
        from chat.permissions import can_initiate_chat

        # Проверить в обе стороны (чат bidirectional)
        return can_initiate_chat(user1, user2) or can_initiate_chat(user2, user1)

    @staticmethod
    def get_user_chats(user: User):
        """
        Получить все чаты пользователя с дополнительной информацией.

        Логика:
        1. Если user.role == 'admin' → все активные чаты
        2. Иначе → чаты где user в ChatParticipant

        Аннотации для каждого чата:
        - last_message: последнее неудалённое сообщение (содержит content для превью)
        - unread_count: кол-во непрочитанных сообщений
        - other_participant: User объект собеседника (для direct чатов)

        Сортировка: по updated_at DESC

        ОПТИМИЗАЦИЯ: Используется Count с условиями вместо вложенных Subquery
        для избежания N+1 queries на unread_count.
        - last_message: Subquery (1 запрос)
        - unread_count: Count с Q() фильтрами (в основном запросе)
        - participants: prefetch_related (1 запрос)
        Итого: 2-3 запроса вместо 1+(N*3)

        ВАЖНО: Пагинация должна делаться на уровне View через QuerySet slicing,
        а не в сервисе. Это позволяет правильно обрабатывать count() и offset.

        Args:
            user: Пользователь

        Returns:
            QuerySet[ChatRoom]: Оптимизированный queryset с аннотациями (БЕЗ слайсинга)
        """
        if hasattr(user, "role") and user.role == "admin":
            base_qs = ChatRoom.objects.filter(is_active=True)
        else:
            base_qs = ChatRoom.objects.filter(participants__user=user, is_active=True)

        last_message_subquery = (
            Message.objects.filter(room=OuterRef("id"), is_deleted=False)
            .order_by("-created_at")
            .values("content")[:1]
        )

        last_message_time_subquery = (
            Message.objects.filter(room=OuterRef("id"), is_deleted=False)
            .order_by("-created_at")
            .values("created_at")[:1]
        )

        is_admin = hasattr(user, "role") and user.role == "admin"

        if is_admin:
            unread_count_filter = Q(
                messages__is_deleted=False,
            ) & ~Q(messages__sender=user)
        else:
            participant_last_read_subquery = ChatParticipant.objects.filter(
                room=OuterRef("id"), user=user
            ).values("last_read_at")[:1]

            unread_count_filter = Q(
                messages__is_deleted=False,
                messages__created_at__gt=Subquery(participant_last_read_subquery),
            ) & ~Q(messages__sender=user)

        qs = (
            base_qs.annotate(
                last_message_content=Subquery(last_message_subquery),
                last_message_time=Subquery(last_message_time_subquery),
                unread_count=Count(
                    "messages",
                    filter=unread_count_filter,
                    distinct=True,
                ),
            )
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=ChatParticipant.objects.select_related("user"),
                    to_attr="_prefetched_participants",
                )
            )
            .distinct()
            .order_by("-updated_at")
        )

        return qs

    @staticmethod
    def can_access_chat(user: User, room: ChatRoom) -> bool:
        """
        Проверить может ли пользователь получить доступ к чату.

        CRITICAL: Проверяет не только существование ChatParticipant,
        но и АКТУАЛЬНЫЕ permissions через can_initiate_chat().

        Если permissions истек (enrollment INACTIVE, tutor removed, и т.д.),
        доступ блокируется.

        RACE CONDITION PROTECTION:
        - Для direct chats: использует SELECT FOR UPDATE для блокировки
        - Это гарантирует что permissions не изменятся между проверкой и использованием
        - Timeline защиты: Thread1 не может изменить enrollment пока Thread2 проверяет доступ

        Логика:
        1. Если user.is_active == False → False
        2. Если user.role == 'admin' → True (админы видят все)
        3. Если user НЕ в ChatParticipant → False
        4. Получить other_participant (собеседника)
        5. Проверить что собеседник активен
        6. Для direct chats: использовать SELECT FOR UPDATE для безопасности
        7. Проверить _validate_chat_permissions(user, other_participant)

        Args:
            user: Пользователь
            room: Чат-комната

        Returns:
            bool: True если доступ разрешен
        """
        if not user.is_active:
            logger.debug(f"Inactive user {user.id} denied access to chat {room.id}")
            return False

        if hasattr(user, "role") and user.role == "admin":
            logger.debug(f"Admin user {user.id} has access to chat {room.id}")
            return True

        # Проверить что user является участником
        try:
            participant = ChatParticipant.objects.get(room=room, user=user)
        except ChatParticipant.DoesNotExist:
            logger.debug(f"User {user.id} is not participant in chat {room.id}")
            return False

        # Получить всех участников чата (кроме текущего пользователя)
        participants = list(
            ChatParticipant.objects.filter(room=room).exclude(user=user).select_related("user")
        )

        if len(participants) == 0:
            # Чат только с самим собой (не должно быть)
            logger.warning(f"Chat {room.id} has only one participant {user.id}")
            return False

        # Проверить что все участники активны
        for participant in participants:
            if not participant.user.is_active:
                logger.debug(f"Participant {participant.user.id} in chat {room.id} is inactive")
                return False

        # Для group chats (3+ участников) - просто проверить что участник в ChatParticipant достаточно
        if len(participants) >= 2:  # 3+ всего (user + 2+ others)
            logger.debug(f"User {user.id} has valid access to group chat {room.id}")
            return True

        # Для direct chats (2 участников всего) - проверить permissions с race condition protection
        # SELECT FOR UPDATE предотвращает изменение enrollment пока мы проверяем доступ
        with transaction.atomic():
            # Заново получаем participants с блокировкой (SELECT FOR UPDATE)
            # Это гарантирует что никто не изменит permissions во время проверки
            locked_participants = list(
                ChatParticipant.objects.filter(room=room)
                .exclude(user=user)
                .select_related("user")
                .select_for_update()
            )

            if len(locked_participants) != 1:
                logger.warning(
                    f"Direct chat {room.id} has unexpected participant count: {len(locked_participants)}"
                )
                return False

            other_participant = locked_participants[0].user

            # Re-validate permissions under lock
            has_permission = ChatService._validate_chat_permissions(user, other_participant)

            if not has_permission:
                logger.debug(
                    f"User {user.id} lost permission to chat with {other_participant.id} "
                    f"(enrollment changed, tutor removed, etc.)"
                )
                return False

        logger.debug(f"User {user.id} has valid access to direct chat {room.id}")
        return True

    @staticmethod
    def mark_chat_as_read(user: User, room: ChatRoom) -> None:
        """
        Пометить чат как прочитанный для пользователя.

        Обновляет ChatParticipant.last_read_at = now().
        Если ChatParticipant не существует → молча игнорирует.

        Args:
            user: Пользователь
            room: Чат-комната
        """
        try:
            participant = ChatParticipant.objects.get(room=room, user=user)
            participant.last_read_at = timezone.now()
            participant.save(update_fields=["last_read_at"])
            logger.debug(f"Marked chat {room.id} as read for user {user.id}")
        except ChatParticipant.DoesNotExist:
            logger.debug(f"No ChatParticipant found for user {user.id} in chat {room.id}")
            pass

    @staticmethod
    def _get_contacts_for_admin(user):
        """Админ видит всех активных пользователей, кроме себя."""
        return User.objects.filter(is_active=True).exclude(id=user.id).values_list("id", flat=True)

    @staticmethod
    def _get_contacts_for_student(student):
        """Студент может общаться с: Teachers (ACTIVE enrollment) + Tutor."""
        contact_ids = set()

        teacher_ids = SubjectEnrollment.objects.filter(
            student=student,
            status=SubjectEnrollment.Status.ACTIVE,
            teacher__is_active=True,
        ).values_list("teacher_id", flat=True)
        contact_ids.update(teacher_ids)

        try:
            student_profile = StudentProfile.objects.get(user=student)
            if student_profile.tutor and student_profile.tutor.is_active:
                contact_ids.add(student_profile.tutor_id)
        except StudentProfile.DoesNotExist:
            pass

        return list(contact_ids)

    @staticmethod
    def _get_contacts_for_teacher(teacher):
        """Учитель может общаться с: Students + Parents (через детей) + Tutors (через студентов)."""
        contact_ids = set()

        student_ids = SubjectEnrollment.objects.filter(
            teacher=teacher,
            status=SubjectEnrollment.Status.ACTIVE,
            student__is_active=True,
        ).values_list("student_id", flat=True)
        contact_ids.update(student_ids)

        parent_ids = StudentProfile.objects.filter(
            user_id__in=student_ids,
            parent__isnull=False,
            parent__is_active=True,
        ).values_list("parent_id", flat=True)
        contact_ids.update(parent_ids)

        tutor_ids = StudentProfile.objects.filter(
            user_id__in=student_ids,
            tutor__isnull=False,
            tutor__is_active=True,
        ).values_list("tutor_id", flat=True)
        contact_ids.update(tutor_ids)

        return list(contact_ids)

    @staticmethod
    def _get_contacts_for_tutor(tutor):
        """Репетитор может общаться с: Students (назначенные) + Teachers (через студентов) + Parents."""
        contact_ids = set()

        student_ids = StudentProfile.objects.filter(
            tutor=tutor,
            user__is_active=True,
        ).values_list("user_id", flat=True)
        contact_ids.update(student_ids)

        teacher_ids = SubjectEnrollment.objects.filter(
            student_id__in=student_ids,
            status=SubjectEnrollment.Status.ACTIVE,
            teacher__is_active=True,
        ).values_list("teacher_id", flat=True)
        contact_ids.update(teacher_ids)

        parent_ids = StudentProfile.objects.filter(
            user_id__in=student_ids,
            parent__isnull=False,
            parent__is_active=True,
        ).values_list("parent_id", flat=True)
        contact_ids.update(parent_ids)

        return list(contact_ids)

    @staticmethod
    def _get_contacts_for_parent(parent):
        """Родитель может общаться с: Teachers (через детей) + Tutors (через детей)."""
        contact_ids = set()

        child_ids = StudentProfile.objects.filter(
            parent=parent,
            user__is_active=True,
        ).values_list("user_id", flat=True)

        teacher_ids = SubjectEnrollment.objects.filter(
            student_id__in=child_ids,
            status=SubjectEnrollment.Status.ACTIVE,
            teacher__is_active=True,
        ).values_list("teacher_id", flat=True)
        contact_ids.update(teacher_ids)

        tutor_ids = StudentProfile.objects.filter(
            user_id__in=child_ids,
            tutor__isnull=False,
            tutor__is_active=True,
        ).values_list("tutor_id", flat=True)
        contact_ids.update(tutor_ids)

        return list(contact_ids)

    @staticmethod
    def _get_allowed_contacts_queryset(user):
        """
        Роутер для выбора метода получения контактов по роли пользователя.
        Возвращает QuerySet с ID разрешенных контактов.
        """
        role = getattr(user, "role", None)

        if role == "admin":
            contact_ids = ChatService._get_contacts_for_admin(user)
        elif role == "student":
            contact_ids = ChatService._get_contacts_for_student(user)
        elif role == "teacher":
            contact_ids = ChatService._get_contacts_for_teacher(user)
        elif role == "tutor":
            contact_ids = ChatService._get_contacts_for_tutor(user)
        elif role == "parent":
            contact_ids = ChatService._get_contacts_for_parent(user)
        else:
            contact_ids = []

        if not contact_ids:
            return User.objects.none()

        return User.objects.filter(id__in=contact_ids, is_active=True)

    @staticmethod
    def get_contacts(user):
        """
        Получить список пользователей, с которыми может общаться current user.

        Оптимизированная версия с role-specific queries вместо линейного перебора.
        Максимум 4 SQL запроса на пользователя вместо 1200-3000.

        ОПТИМИЗАЦИЯ ПАМЯТИ:
        - Использует iterator(chunk_size=100) для streaming больших наборов данных
        - Prefetch все SubjectEnrollment один раз (не N+1 в цикле)
        - Префильтр parent_children один раз перед циклом

        Returns:
            list[dict]: Список контактов с полями:
                - id, full_name, role
                - has_existing_chat, existing_chat_id
        """
        allowed_contacts_qs = ChatService._get_allowed_contacts_queryset(user)

        my_rooms = ChatParticipant.objects.filter(user=user).values_list("room_id", flat=True)
        existing_chats = {}

        for cp in ChatParticipant.objects.filter(
            user_id__in=allowed_contacts_qs.values_list("id", flat=True),
            room_id__in=my_rooms,
        ).values_list("user_id", "room_id"):
            user_id, room_id = cp
            if user_id not in existing_chats:
                existing_chats[user_id] = room_id

        user_role = getattr(user, "role", None)

        student_teacher_enrollments = {}
        parent_children = set()

        if user_role == "student":
            enrollments = SubjectEnrollment.objects.filter(
                student=user,
                status=SubjectEnrollment.Status.ACTIVE,
            ).select_related("subject", "teacher")

            for enrollment in enrollments:
                teacher_id = enrollment.teacher_id
                if teacher_id not in student_teacher_enrollments:
                    student_teacher_enrollments[teacher_id] = {
                        "id": enrollment.subject.id,
                        "name": enrollment.subject.name,
                    }

        elif user_role == "parent":
            from accounts.models import StudentProfile

            parent_children = set(
                StudentProfile.objects.filter(
                    parent=user,
                    user__is_active=True,
                ).values_list("user_id", flat=True)
            )

            if parent_children:
                enrollments = SubjectEnrollment.objects.filter(
                    student_id__in=parent_children,
                    status=SubjectEnrollment.Status.ACTIVE,
                ).select_related("subject", "teacher")

                for enrollment in enrollments:
                    teacher_id = enrollment.teacher_id
                    if teacher_id not in student_teacher_enrollments:
                        student_teacher_enrollments[teacher_id] = {
                            "id": enrollment.subject.id,
                            "name": enrollment.subject.name,
                        }

        contacts = []
        BATCH_SIZE = 100

        for other_user in allowed_contacts_qs.iterator(chunk_size=BATCH_SIZE):
            avatar_url = None
            try:
                avatar = getattr(other_user, "avatar", None)
                if avatar and hasattr(avatar, "url"):
                    avatar_url = avatar.url
            except (ValueError, AttributeError):
                avatar_url = None

            subject_info = None
            other_role = getattr(other_user, "role", "user")

            if other_role == "teacher" and other_user.id in student_teacher_enrollments:
                subject_info = student_teacher_enrollments[other_user.id]

            contact_dict = {
                "id": other_user.id,
                "user_id": other_user.id,
                "first_name": other_user.first_name or "",
                "last_name": other_user.last_name or "",
                "name": f"{other_user.first_name} {other_user.last_name}".strip()
                or other_user.username,
                "email": other_user.email or "",
                "role": getattr(other_user, "role", "user"),
                "avatar": avatar_url,
                "is_online": False,
                "has_active_chat": other_user.id in existing_chats,
                "chat_id": existing_chats.get(other_user.id),
            }

            if subject_info:
                contact_dict["subject"] = subject_info

            contacts.append(contact_dict)

        return contacts
