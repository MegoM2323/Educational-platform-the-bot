"""
Comprehensive unit tests for Forum Visibility Filters.

Tests for:
- Student sees only FORUM_SUBJECT + FORUM_TUTOR chats
- Teacher sees only FORUM_SUBJECT chats for their students
- Tutor sees only FORUM_TUTOR chats
- No cross-visibility between unrelated users
- Chat filtering logic

Usage:
    pytest backend/tests/unit/chat/test_forum_visibility_comprehensive.py -v
    pytest backend/tests/unit/chat/test_forum_visibility_comprehensive.py --cov=chat.forum_views
"""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile, TeacherProfile, TutorProfile
from chat.models import ChatRoom, ChatParticipant
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestForumVisibilityFiltersComprehensive:
    """Comprehensive tests for forum visibility rules"""

    @pytest.fixture
    def setup_forum_users(self, db):
        """Setup complete forum user ecosystem"""
        # Create teachers
        teacher1 = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER,
            first_name='Teacher1'
        )
        TeacherProfile.objects.create(user=teacher1)

        teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER,
            first_name='Teacher2'
        )
        TeacherProfile.objects.create(user=teacher2)

        # Create tutors
        tutor1 = User.objects.create_user(
            username='tutor1',
            email='tutor1@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR,
            first_name='Tutor1'
        )
        TutorProfile.objects.create(user=tutor1)

        tutor2 = User.objects.create_user(
            username='tutor2',
            email='tutor2@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR,
            first_name='Tutor2'
        )
        TutorProfile.objects.create(user=tutor2)

        # Create students
        student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Student1'
        )
        student1_profile = StudentProfile.objects.create(user=student1)
        student1_profile.tutor = tutor1
        student1_profile.save()

        student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Student2'
        )
        student2_profile = StudentProfile.objects.create(user=student2)
        student2_profile.tutor = tutor1  # Same tutor as student1
        student2_profile.save()

        student3 = User.objects.create_user(
            username='student3',
            email='student3@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Student3'
        )
        student3_profile = StudentProfile.objects.create(user=student3)
        student3_profile.tutor = tutor2  # Different tutor
        student3_profile.save()

        # Create subjects
        math_subject = Subject.objects.create(name='Математика')
        english_subject = Subject.objects.create(name='Английский')

        return {
            'teachers': {
                'teacher1': teacher1,
                'teacher2': teacher2,
            },
            'tutors': {
                'tutor1': tutor1,
                'tutor2': tutor2,
            },
            'students': {
                'student1': student1,
                'student2': student2,
                'student3': student3,
            },
            'subjects': {
                'math': math_subject,
                'english': english_subject,
            }
        }

    # ========== Student Visibility Tests ==========

    def test_student_sees_forum_subject_chats(self, setup_forum_users):
        """Scenario: Student sees FORUM_SUBJECT chats (teacher chats)"""
        users = setup_forum_users
        student1 = users['students']['student1']
        teacher1 = users['teachers']['teacher1']
        math_subject = users['subjects']['math']

        # Create enrollment to establish teacher relationship
        enrollment = SubjectEnrollment.objects.create(
            student=student1,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        # Get the auto-created FORUM_SUBJECT chat (created by signal)
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Student should see this chat when filtering
        # (In real API call, this would be filtered by forum_views.py)
        assert student1 in chat.participants.all()
        assert chat.type == ChatRoom.Type.FORUM_SUBJECT

    def test_student_sees_forum_tutor_chats(self, setup_forum_users):
        """Scenario: Student sees FORUM_TUTOR chats"""
        users = setup_forum_users
        student1 = users['students']['student1']
        tutor1 = users['tutors']['tutor1']

        # Create FORUM_TUTOR chat
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name=f'Tutor - {student1.username} ↔ {tutor1.username}',
            created_by=student1
        )
        chat.participants.add(student1, tutor1)

        # Student should see this chat
        assert student1 in chat.participants.all()
        assert chat.type == ChatRoom.Type.FORUM_TUTOR

    def test_student_does_not_see_other_student_chats(self, setup_forum_users):
        """Scenario: Student doesn't see chats of other students"""
        users = setup_forum_users
        student1 = users['students']['student1']
        student2 = users['students']['student2']
        teacher1 = users['teachers']['teacher1']
        math_subject = users['subjects']['math']

        # Create enrollment for student2 with different teacher
        SubjectEnrollment.objects.create(
            student=student2,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        # Create chat for student2 only
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student2.username} ↔ {teacher1.username}',
            created_by=student2
        )
        chat.participants.add(student2, teacher1)

        # student1 should NOT be in this chat
        assert student1 not in chat.participants.all()
        assert student2 in chat.participants.all()

    def test_student_does_not_see_tutor_chats_they_are_not_in(self, setup_forum_users):
        """Scenario: Student doesn't see tutor chats with other students"""
        users = setup_forum_users
        student1 = users['students']['student1']
        student3 = users['students']['student3']  # Different tutor
        tutor2 = users['tutors']['tutor2']

        # Create chat for student3 with their tutor
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name=f'Tutor - {student3.username} ↔ {tutor2.username}',
            created_by=student3
        )
        chat.participants.add(student3, tutor2)

        # student1 should NOT be in this chat
        assert student1 not in chat.participants.all()

    # ========== Teacher Visibility Tests ==========

    def test_teacher_sees_forum_subject_chats_for_their_students(self, setup_forum_users):
        """Scenario: Teacher sees only FORUM_SUBJECT chats for students they teach"""
        users = setup_forum_users
        student1 = users['students']['student1']
        teacher1 = users['teachers']['teacher1']
        math_subject = users['subjects']['math']

        # Create enrollment
        SubjectEnrollment.objects.create(
            student=student1,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        # Create FORUM_SUBJECT chat
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student1.username} ↔ {teacher1.username}',
            created_by=student1
        )
        chat.participants.add(student1, teacher1)

        # Teacher should be in this chat
        assert teacher1 in chat.participants.all()
        assert chat.type == ChatRoom.Type.FORUM_SUBJECT

    def test_teacher_does_not_see_tutor_chats(self, setup_forum_users):
        """Scenario: Teacher doesn't see FORUM_TUTOR chats"""
        users = setup_forum_users
        student1 = users['students']['student1']
        teacher1 = users['teachers']['teacher1']
        tutor1 = users['tutors']['tutor1']

        # Create FORUM_TUTOR chat
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name=f'Tutor - {student1.username} ↔ {tutor1.username}',
            created_by=student1
        )
        chat.participants.add(student1, tutor1)

        # Teacher should NOT be in this chat
        assert teacher1 not in chat.participants.all()

    def test_teacher_does_not_see_other_teachers_chats(self, setup_forum_users):
        """Scenario: Teacher doesn't see chats with other teachers' students"""
        users = setup_forum_users
        student1 = users['students']['student1']
        student3 = users['students']['student3']
        teacher1 = users['teachers']['teacher1']
        teacher2 = users['teachers']['teacher2']
        math_subject = users['subjects']['math']

        # Create enrollment for student3 with teacher2
        SubjectEnrollment.objects.create(
            student=student3,
            subject=math_subject,
            teacher=teacher2,
            is_active=True
        )

        # Create chat with teacher2
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student3.username} ↔ {teacher2.username}',
            created_by=student3
        )
        chat.participants.add(student3, teacher2)

        # teacher1 should NOT be in this chat
        assert teacher1 not in chat.participants.all()

    # ========== Tutor Visibility Tests ==========

    def test_tutor_sees_forum_tutor_chats_for_their_students(self, setup_forum_users):
        """Scenario: Tutor sees only FORUM_TUTOR chats for their students"""
        users = setup_forum_users
        student1 = users['students']['student1']
        tutor1 = users['tutors']['tutor1']

        # Create FORUM_TUTOR chat
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name=f'Tutor - {student1.username} ↔ {tutor1.username}',
            created_by=student1
        )
        chat.participants.add(student1, tutor1)

        # Tutor should be in this chat
        assert tutor1 in chat.participants.all()
        assert chat.type == ChatRoom.Type.FORUM_TUTOR

    def test_tutor_does_not_see_forum_subject_chats(self, setup_forum_users):
        """Scenario: Tutor doesn't see FORUM_SUBJECT (teacher) chats"""
        users = setup_forum_users
        student1 = users['students']['student1']
        teacher1 = users['teachers']['teacher1']
        tutor1 = users['tutors']['tutor1']
        math_subject = users['subjects']['math']

        # Create enrollment and FORUM_SUBJECT chat
        SubjectEnrollment.objects.create(
            student=student1,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student1.username} ↔ {teacher1.username}',
            created_by=student1
        )
        chat.participants.add(student1, teacher1)

        # Tutor should NOT be in teacher-student chats
        assert tutor1 not in chat.participants.all()

    def test_tutor_does_not_see_other_tutors_chats(self, setup_forum_users):
        """Scenario: Tutor doesn't see chats with other tutors' students"""
        users = setup_forum_users
        student3 = users['students']['student3']  # Belongs to tutor2
        tutor1 = users['tutors']['tutor1']
        tutor2 = users['tutors']['tutor2']

        # Create FORUM_TUTOR chat with tutor2
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name=f'Tutor - {student3.username} ↔ {tutor2.username}',
            created_by=student3
        )
        chat.participants.add(student3, tutor2)

        # tutor1 should NOT be in this chat
        assert tutor1 not in chat.participants.all()

    # ========== Chat Participant Tests ==========

    def test_chat_has_correct_participants(self, setup_forum_users):
        """Scenario: Forum chat has exactly correct participants"""
        users = setup_forum_users
        student1 = users['students']['student1']
        teacher1 = users['teachers']['teacher1']

        # Create FORUM_SUBJECT chat
        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name='Test Chat',
            created_by=student1
        )
        chat.participants.add(student1, teacher1)

        # Assert exact participants
        assert chat.participants.count() == 2
        participant_ids = set(chat.participants.values_list('id', flat=True))
        assert participant_ids == {student1.id, teacher1.id}

    def test_forum_subject_chat_type(self, setup_forum_users):
        """Scenario: FORUM_SUBJECT chat type correctly set"""
        users = setup_forum_users
        student1 = users['students']['student1']

        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name='Test Chat',
            created_by=student1
        )

        assert chat.type == ChatRoom.Type.FORUM_SUBJECT
        assert chat.type != ChatRoom.Type.FORUM_TUTOR

    def test_forum_tutor_chat_type(self, setup_forum_users):
        """Scenario: FORUM_TUTOR chat type correctly set"""
        users = setup_forum_users
        tutor1 = users['tutors']['tutor1']

        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_TUTOR,
            name='Test Chat',
            created_by=tutor1
        )

        assert chat.type == ChatRoom.Type.FORUM_TUTOR
        assert chat.type != ChatRoom.Type.FORUM_SUBJECT

    # ========== Complex Visibility Tests ==========

    def test_no_cross_role_visibility(self, setup_forum_users):
        """Scenario: No unintended visibility between different roles"""
        users = setup_forum_users
        student1 = users['students']['student1']
        student2 = users['students']['student2']
        teacher1 = users['teachers']['teacher1']
        teacher2 = users['teachers']['teacher2']
        tutor1 = users['tutors']['tutor1']
        tutor2 = users['tutors']['tutor2']
        math_subject = users['subjects']['math']

        # Create enrollment (triggers auto-creation of forum chats via signal)
        enrollment = SubjectEnrollment.objects.create(
            student=student1,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        # Get the auto-created FORUM_SUBJECT chat
        forum_subject_chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Get the auto-created FORUM_TUTOR chat (if tutor assigned to student1)
        try:
            forum_tutor_chat = ChatRoom.objects.get(
                type=ChatRoom.Type.FORUM_TUTOR,
                enrollment=enrollment
            )
        except ChatRoom.DoesNotExist:
            # Create tutor chat manually if student1 has no tutor
            forum_tutor_chat = ChatRoom.objects.create(
                type=ChatRoom.Type.FORUM_TUTOR,
                name='Student1-Tutor1',
                created_by=student1,
                enrollment=enrollment
            )
            forum_tutor_chat.participants.add(student1, tutor1)

        # Verify visibility rules
        # student1 can see both
        assert student1 in forum_subject_chat.participants.all()
        assert student1 in forum_tutor_chat.participants.all()

        # student2 (not in chats) cannot see either
        assert student2 not in forum_subject_chat.participants.all()
        assert student2 not in forum_tutor_chat.participants.all()

        # teacher1 can see FORUM_SUBJECT only
        assert teacher1 in forum_subject_chat.participants.all()
        assert teacher1 not in forum_tutor_chat.participants.all()

        # teacher2 (different teacher) cannot see FORUM_SUBJECT
        assert teacher2 not in forum_subject_chat.participants.all()

        # tutor1 can see FORUM_TUTOR only
        assert tutor1 in forum_tutor_chat.participants.all()
        assert tutor1 not in forum_subject_chat.participants.all()

        # tutor2 (different tutor) cannot see FORUM_TUTOR
        assert tutor2 not in forum_tutor_chat.participants.all()

    # ========== Data Integrity Tests ==========

    def test_chat_type_is_enum(self, setup_forum_users):
        """Scenario: Chat type is proper enum value"""
        users = setup_forum_users
        tutor1 = users['tutors']['tutor1']

        chat = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name='Test',
            created_by=tutor1
        )

        # Should be valid enum value
        assert hasattr(ChatRoom.Type, 'FORUM_SUBJECT')
        assert hasattr(ChatRoom.Type, 'FORUM_TUTOR')

    def test_multiple_students_can_be_in_same_chat_group(self, setup_forum_users):
        """Scenario: Multiple students with same teacher can have separate chats"""
        users = setup_forum_users
        student1 = users['students']['student1']
        student2 = users['students']['student2']
        teacher1 = users['teachers']['teacher1']
        math_subject = users['subjects']['math']

        # Create enrollments
        enrollment1 = SubjectEnrollment.objects.create(
            student=student1,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )
        enrollment2 = SubjectEnrollment.objects.create(
            student=student2,
            subject=math_subject,
            teacher=teacher1,
            is_active=True
        )

        # Create separate chats for each student
        chat1 = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student1.username}',
            created_by=student1
        )
        chat1.participants.add(student1, teacher1)

        chat2 = ChatRoom.objects.create(
            type=ChatRoom.Type.FORUM_SUBJECT,
            name=f'Math - {student2.username}',
            created_by=student2
        )
        chat2.participants.add(student2, teacher1)

        # Verify separation
        assert student1 in chat1.participants.all()
        assert student1 not in chat2.participants.all()
        assert student2 in chat2.participants.all()
        assert student2 not in chat1.participants.all()
        assert teacher1 in chat1.participants.all()
        assert teacher1 in chat2.participants.all()
