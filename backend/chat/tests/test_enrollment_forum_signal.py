"""
Tests для create_forum_chat_on_enrollment signal

Проверяет:
1. Создание FORUM_SUBJECT чата при создании SubjectEnrollment
2. Создание FORUM_TUTOR чата если у студента есть tutor
3. Добавление участников в чаты (student, teacher, tutor)
4. Идемпотентность (не создает дубликатов)
5. Создание ChatParticipant записей для WebSocket
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.factories import (
    StudentFactory,
    TeacherFactory,
    TutorFactory,
    StudentProfileFactory,
)
from materials.factories import (
    SubjectFactory,
    SubjectEnrollmentFactory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def _imports_fixture():
    from materials.models import SubjectEnrollment
    from chat.models import ChatRoom, ChatParticipant

    return SubjectEnrollment, ChatRoom, ChatParticipant


@pytest.mark.django_db
class TestForumChatCreation:
    """Тесты создания FORUM_SUBJECT чата"""

    @pytest.fixture(autouse=True)
    def _setup_imports(self, _imports_fixture):
        self.SubjectEnrollment, self.ChatRoom, self.ChatParticipant = _imports_fixture

    def test_creates_forum_subject_chat_on_enrollment(self):
        """При создании SubjectEnrollment создается FORUM_SUBJECT чат"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Math")

        # До создания enrollment чатов нет
        assert ChatRoom.objects.filter(type=ChatRoom.Type.FORUM_SUBJECT).count() == 0

        # Создаем enrollment - должен сработать signal
        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Проверяем что создался FORUM_SUBJECT чат
        forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        ).first()

        assert forum_chat is not None
        assert forum_chat.type == ChatRoom.Type.FORUM_SUBJECT
        assert forum_chat.enrollment == enrollment
        assert forum_chat.created_by == student

    def test_forum_chat_has_correct_participants(self):
        """FORUM_SUBJECT чат содержит student и teacher как участников"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Physics")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        )

        # Проверяем участников через M2M
        participants = list(forum_chat.participants.all())
        assert len(participants) == 2
        assert student in participants
        assert teacher in participants

        # Проверяем ChatParticipant записи
        chat_participants = ChatParticipant.objects.filter(room=forum_chat)
        assert chat_participants.count() == 2
        assert chat_participants.filter(user=student).exists()
        assert chat_participants.filter(user=teacher).exists()

    def test_forum_chat_name_format(self):
        """Имя FORUM_SUBJECT чата имеет правильный формат"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory(first_name="John", last_name="Doe")
        student = StudentFactory(first_name="Jane", last_name="Smith")
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Chemistry")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        )

        # Format: "{Subject} - {Student} ↔ {Teacher}"
        expected_name = (
            f"{subject.name} - {student.get_full_name()} ↔ {teacher.get_full_name()}"
        )
        assert forum_chat.name == expected_name

    def test_forum_chat_idempotent(self):
        """Повторное создание enrollment не создает дубликаты чатов"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Math")

        # Создаем enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        first_chat_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        ).count()
        assert first_chat_count == 1

        # Обновляем enrollment (save() без created=True)
        enrollment.is_active = False
        enrollment.save()

        # Проверяем что чатов не добавилось
        second_chat_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        ).count()
        assert second_chat_count == 1


@pytest.mark.django_db
class TestForumTutorChatCreation:
    """Тесты создания FORUM_TUTOR чата"""

    @pytest.fixture(autouse=True)
    def _setup_imports(self, _imports_fixture):
        self.SubjectEnrollment, self.ChatRoom, self.ChatParticipant = _imports_fixture

    def test_creates_forum_tutor_chat_if_student_has_tutor(self):
        """Создается FORUM_TUTOR чат если у студента есть tutor"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        tutor = TutorFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10", tutor=tutor)
        subject = SubjectFactory(name="Math")

        # Создаем enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Проверяем создание FORUM_TUTOR чата
        tutor_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        ).first()

        assert tutor_chat is not None
        assert tutor_chat.type == ChatRoom.Type.FORUM_TUTOR
        assert tutor_chat.enrollment == enrollment

    def test_forum_tutor_chat_has_student_and_tutor(self):
        """FORUM_TUTOR чат содержит student и tutor как участников"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        tutor = TutorFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10", tutor=tutor)
        subject = SubjectFactory(name="Physics")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        tutor_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        )

        # Проверяем участников
        participants = list(tutor_chat.participants.all())
        assert len(participants) == 2
        assert student in participants
        assert tutor in participants

        # teacher НЕ должен быть в FORUM_TUTOR чате
        assert teacher not in participants

    def test_no_forum_tutor_chat_if_no_tutor(self):
        """Не создается FORUM_TUTOR чат если у студента нет tutor"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10", tutor=None)
        subject = SubjectFactory(name="Math")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Проверяем что FORUM_TUTOR чат не создался
        tutor_chat_exists = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        ).exists()
        assert tutor_chat_exists is False

    def test_forum_tutor_chat_name_format(self):
        """Имя FORUM_TUTOR чата имеет правильный формат"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory(first_name="John", last_name="Doe")
        tutor = TutorFactory(first_name="Bob", last_name="Tutor")
        student = StudentFactory(first_name="Jane", last_name="Smith")
        StudentProfileFactory(user=student, grade="10", tutor=tutor)
        subject = SubjectFactory(name="Biology")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        tutor_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        )

        # Format: "{Student}" (just student name)
        expected_name = student.get_full_name()
        assert tutor_chat.name == expected_name

    def test_forum_tutor_chat_with_created_by_tutor(self):
        """FORUM_TUTOR чат создается если student.created_by_tutor установлен"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        tutor = TutorFactory()
        student = StudentFactory()
        student.created_by_tutor = tutor
        student.save()
        StudentProfileFactory(user=student, grade="10", tutor=None)
        subject = SubjectFactory(name="Math")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Проверяем что FORUM_TUTOR чат создался
        tutor_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        ).first()

        assert tutor_chat is not None
        assert tutor in tutor_chat.participants.all()


@pytest.mark.django_db
class TestEnrollmentSignalEdgeCases:
    """Тесты граничных случаев"""

    @pytest.fixture(autouse=True)
    def _setup_imports(self, _imports_fixture):
        self.SubjectEnrollment, self.ChatRoom, self.ChatParticipant = _imports_fixture

    def test_signal_skips_if_enrollment_updated_not_created(self):
        """Signal не триггерится при update enrollment"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Math")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Запоминаем количество чатов
        initial_chat_count = ChatRoom.objects.count()

        # Обновляем enrollment
        enrollment.is_active = False
        enrollment.save()

        # Количество чатов не должно измениться
        assert ChatRoom.objects.count() == initial_chat_count

    def test_signal_handles_student_without_profile(self):
        """Signal работает если у студента нет StudentProfile"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        # Не создаем StudentProfile
        subject = SubjectFactory(name="Math")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # FORUM_SUBJECT чат должен создаться
        forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        ).first()
        assert forum_chat is not None

        # FORUM_TUTOR чат не должен создаться (нет StudentProfile)
        tutor_chat_exists = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        ).exists()
        assert tutor_chat_exists is False

    def test_creates_both_forum_chats_correctly(self):
        """Создаются оба чата (FORUM_SUBJECT + FORUM_TUTOR) при наличии tutor"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        tutor = TutorFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10", tutor=tutor)
        subject = SubjectFactory(name="History")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        # Проверяем что созданы оба чата
        forum_subject_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        ).first()
        forum_tutor_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment=enrollment
        ).first()

        assert forum_subject_chat is not None
        assert forum_tutor_chat is not None

        # Проверяем участников в FORUM_SUBJECT
        assert set(forum_subject_chat.participants.all()) == {student, teacher}

        # Проверяем участников в FORUM_TUTOR
        assert set(forum_tutor_chat.participants.all()) == {student, tutor}

    def test_multiple_enrollments_create_separate_chats(self):
        """Разные enrollments создают отдельные чаты"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject1 = SubjectFactory(name="Math")
        subject2 = SubjectFactory(name="Physics")

        enrollment1 = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject1, is_active=True
        )
        enrollment2 = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject2, is_active=True
        )

        # Проверяем что созданы 2 отдельных чата
        chat1 = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment1
        ).first()
        chat2 = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment2
        ).first()

        assert chat1 is not None
        assert chat2 is not None
        assert chat1.id != chat2.id
        assert "Math" in chat1.name
        assert "Physics" in chat2.name

    def test_chat_participant_unread_count_initialized(self):
        """ChatParticipant записи создаются с unread_count=0"""
        SubjectEnrollment, ChatRoom, ChatParticipant = (
            self.SubjectEnrollment,
            self.ChatRoom,
            self.ChatParticipant,
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        StudentProfileFactory(user=student, grade="10")
        subject = SubjectFactory(name="Math")

        enrollment = SubjectEnrollment.objects.create(
            student=student, teacher=teacher, subject=subject, is_active=True
        )

        forum_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=enrollment
        )

        # Проверяем ChatParticipant для student
        student_participant = ChatParticipant.objects.get(room=forum_chat, user=student)
        assert student_participant.unread_count == 0
        assert student_participant.joined_at is not None

        # Проверяем ChatParticipant для teacher
        teacher_participant = ChatParticipant.objects.get(room=forum_chat, user=teacher)
        assert teacher_participant.unread_count == 0
        assert teacher_participant.joined_at is not None
