from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.contrib.auth import get_user_model

from chat.models import ChatRoom, Message

User = get_user_model()


class Command(BaseCommand):
    help = "Создает тестовые чаты с сообщениями"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Удалить существующие тестовые чаты перед созданием",
        )

    @transaction.atomic()
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_test_chats()

        self._create_test_chats()
        self.stdout.write(self.style.SUCCESS("✓ Тестовые чаты успешно созданы"))

    def _clear_test_chats(self):
        """Удаляет существующие тестовые чаты"""
        test_rooms = ChatRoom.objects.filter(
            name__in=[
                "Teacher-Student Chat",
                "Parent-Tutor Chat",
                "Group Chat",
            ]
        )
        count = test_rooms.count()
        test_rooms.delete()
        self.stdout.write(f"✓ Удалено {count} тестовых чатов")

    def _create_test_chats(self):
        """Создает тестовые чаты с сообщениями"""

        users = self._get_or_create_users()

        self.stdout.write(self.style.HTTP_INFO("Создание ChatRoom'ов..."))

        teacher_student_room = self._create_or_get_chat_room(
            name="Teacher-Student Chat",
            chat_type=ChatRoom.Type.DIRECT,
            created_by=users["teacher"],
            participants=[users["teacher"], users["student"]],
        )

        parent_tutor_room = self._create_or_get_chat_room(
            name="Parent-Tutor Chat",
            chat_type=ChatRoom.Type.DIRECT,
            created_by=users["parent"],
            participants=[users["parent"], users["tutor"]],
        )

        group_room = self._create_or_get_chat_room(
            name="Group Chat",
            chat_type=ChatRoom.Type.GROUP,
            created_by=users["teacher"],
            participants=[users["teacher"], users["student"], users["student2"]],
        )

        self.stdout.write(self.style.SUCCESS("✓ ChatRoom'ы созданы"))

        self.stdout.write(self.style.HTTP_INFO("Создание сообщений..."))

        self._create_messages_for_teacher_student(teacher_student_room, users)
        self._create_messages_for_parent_tutor(parent_tutor_room, users)
        self._create_messages_for_group(group_room, users)

        self.stdout.write(self.style.SUCCESS("✓ Сообщения созданы"))

        self._print_summary(teacher_student_room, parent_tutor_room, group_room)

    def _get_or_create_users(self):
        """Получает или создает тестовых пользователей"""
        users = {}

        user_data = [
            {
                "email": "teacher@test.com",
                "username": "teacher",
                "role": User.Role.TEACHER,
                "first_name": "Иван",
                "last_name": "Учитель",
            },
            {
                "email": "student@test.com",
                "username": "student",
                "role": User.Role.STUDENT,
                "first_name": "Петр",
                "last_name": "Студент",
            },
            {
                "email": "student2@test.com",
                "username": "student2",
                "role": User.Role.STUDENT,
                "first_name": "Мария",
                "last_name": "Студент",
            },
            {
                "email": "parent@test.com",
                "username": "parent",
                "role": User.Role.PARENT,
                "first_name": "Елена",
                "last_name": "Родитель",
            },
            {
                "email": "tutor@test.com",
                "username": "tutor",
                "role": User.Role.TUTOR,
                "first_name": "Алексей",
                "last_name": "Тьютор",
            },
        ]

        for data in user_data:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "role": data["role"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "is_active": True,
                },
            )
            key = data["username"]
            users[key] = user

            if created:
                self.stdout.write(f"  ✓ Создан пользователь: {user.email} ({user.role})")
            else:
                self.stdout.write(f"  - Пользователь существует: {user.email}")

        return users

    def _create_or_get_chat_room(self, name, chat_type, created_by, participants):
        """Создает или получает существующую ChatRoom"""
        room, created = ChatRoom.objects.get_or_create(
            name=name,
            defaults={
                "type": chat_type,
                "created_by": created_by,
                "description": f"Тестовый чат: {name}",
                "is_active": True,
            },
        )

        if not created:
            existing_participants = set(room.participants.all())
            new_participants = set(participants)

            to_add = new_participants - existing_participants
            for participant in to_add:
                room.participants.add(participant)

        else:
            room.participants.set(participants)
            self.stdout.write(f"  ✓ Создана ChatRoom: {name}")

        return room

    def _create_messages_for_teacher_student(self, room, users):
        """Создает 7 сообщений в чате Teacher-Student"""
        if room.messages.exists():
            self.stdout.write(f"  - Сообщения в '{room.name}' уже существуют ({room.messages.count()})")
            return

        base_time = timezone.now() - timedelta(days=5)

        messages_data = [
            {
                "sender": users["teacher"],
                "content": "Привет! Как дела с домашним заданием?",
                "offset_minutes": 0,
            },
            {
                "sender": users["student"],
                "content": "Привет! Почти готов, есть вопрос по третьему заданию",
                "offset_minutes": 15,
            },
            {
                "sender": users["teacher"],
                "content": "Давай обсудим. В чем сложность?",
                "offset_minutes": 20,
            },
            {
                "sender": users["student"],
                "content": "Не понимаю как применить формулу в этом контексте",
                "offset_minutes": 35,
            },
            {
                "sender": users["teacher"],
                "content": "Попробуй сначала разобраться с основами. Посмотри урок 5",
                "offset_minutes": 50,
            },
            {
                "sender": users["student"],
                "content": "Спасибо, посмотрю!",
                "offset_minutes": 65,
            },
            {
                "sender": users["teacher"],
                "content": "Если остались вопросы - пиши",
                "offset_minutes": 75,
            },
        ]

        for msg_data in messages_data:
            created_at = base_time + timedelta(minutes=msg_data["offset_minutes"])
            msg, created = Message.objects.get_or_create(
                room=room,
                sender=msg_data["sender"],
                content=msg_data["content"],
                defaults={
                    "message_type": Message.Type.TEXT,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )
            if not created:
                Message.objects.filter(id=msg.id).update(created_at=created_at, updated_at=created_at)

        self.stdout.write(f"  ✓ Создано 7 сообщений в '{room.name}'")

    def _create_messages_for_parent_tutor(self, room, users):
        """Создает 7 сообщений в чате Parent-Tutor"""
        if room.messages.exists():
            self.stdout.write(f"  - Сообщения в '{room.name}' уже существуют ({room.messages.count()})")
            return

        base_time = timezone.now() - timedelta(days=3)

        messages_data = [
            {
                "sender": users["parent"],
                "content": "Здравствуйте! Как успехи в учебе?",
                "offset_minutes": 0,
            },
            {
                "sender": users["tutor"],
                "content": "Добрый день! Успехи хорошие, учится прилежно",
                "offset_minutes": 30,
            },
            {
                "sender": users["parent"],
                "content": "Спасибо за информацию. А есть ли сложности?",
                "offset_minutes": 45,
            },
            {
                "sender": users["tutor"],
                "content": "Небольшие трудности с письменным выражением мыслей",
                "offset_minutes": 60,
            },
            {
                "sender": users["parent"],
                "content": "Что вы рекомендуете?",
                "offset_minutes": 90,
            },
            {
                "sender": users["tutor"],
                "content": "Рекомендую больше практики в написании эссе и пересказов",
                "offset_minutes": 120,
            },
            {
                "sender": users["parent"],
                "content": "Хорошо, спасибо за совет!",
                "offset_minutes": 150,
            },
        ]

        for msg_data in messages_data:
            created_at = base_time + timedelta(minutes=msg_data["offset_minutes"])
            msg, created = Message.objects.get_or_create(
                room=room,
                sender=msg_data["sender"],
                content=msg_data["content"],
                defaults={
                    "message_type": Message.Type.TEXT,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )
            if not created:
                Message.objects.filter(id=msg.id).update(created_at=created_at, updated_at=created_at)

        self.stdout.write(f"  ✓ Создано 7 сообщений в '{room.name}'")

    def _create_messages_for_group(self, room, users):
        """Создает 6 сообщений в групповом чате"""
        if room.messages.exists():
            self.stdout.write(f"  - Сообщения в '{room.name}' уже существуют ({room.messages.count()})")
            return

        base_time = timezone.now() - timedelta(days=1)

        messages_data = [
            {
                "sender": users["teacher"],
                "content": "Привет всем! Как дела?",
                "offset_minutes": 0,
            },
            {
                "sender": users["student"],
                "content": "Привет! Все хорошо",
                "offset_minutes": 10,
            },
            {
                "sender": users["student2"],
                "content": "И у меня все в порядке!",
                "offset_minutes": 20,
            },
            {
                "sender": users["teacher"],
                "content": "Отлично! Напоминаю о сроках сдачи проекта",
                "offset_minutes": 45,
            },
            {
                "sender": users["student"],
                "content": "Когда дедлайн?",
                "offset_minutes": 60,
            },
            {
                "sender": users["teacher"],
                "content": "На следующий четверг. Еще неделя!",
                "offset_minutes": 70,
            },
        ]

        for msg_data in messages_data:
            created_at = base_time + timedelta(minutes=msg_data["offset_minutes"])
            msg, created = Message.objects.get_or_create(
                room=room,
                sender=msg_data["sender"],
                content=msg_data["content"],
                defaults={
                    "message_type": Message.Type.TEXT,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )
            if not created:
                Message.objects.filter(id=msg.id).update(created_at=created_at, updated_at=created_at)

        self.stdout.write(f"  ✓ Создано 6 сообщений в '{room.name}'")

    def _print_summary(self, teacher_student_room, parent_tutor_room, group_room):
        """Выводит итоговую статистику"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write("=" * 60)

        rooms = [teacher_student_room, parent_tutor_room, group_room]
        total_messages = 0

        for room in rooms:
            msg_count = room.messages.filter(is_deleted=False).count()
            participant_count = room.participants.count()
            total_messages += msg_count

            self.stdout.write(
                f"\n{room.name}:"
                f"\n  Тип: {room.get_type_display()}"
                f"\n  Участников: {participant_count}"
                f"\n  Сообщений: {msg_count}"
            )

        self.stdout.write(f"\nВсего сообщений: {total_messages}")
        self.stdout.write("=" * 60 + "\n")
