"""
Test Suite T002: Parent Synchronization Issues in Forum Chats

Tests for sync_parent_participants signal to verify:
1. Parent is added to ALL student chats when assigned
2. Parent is REMOVED from chats when unassigned (CURRENTLY FAILS)
3. Parent is UPDATED when changed (CURRENTLY FAILS)
4. No race conditions between create_forum_chat_on_enrollment and sync_parent_participants
"""

import pytest
from uuid import uuid4
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile, ParentProfile
from chat.models import ChatRoom, ChatParticipant, Message
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestParentSyncIssues:
    """T002: Parent synchronization in forum chats"""

    @pytest.fixture
    def parent1(self):
        """First parent user"""
        username = f"parent1_t002_{uuid4().hex[:8]}"
        email = f"parent1_{uuid4().hex[:8]}@t002.test"
        parent = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)
        return parent

    @pytest.fixture
    def parent2(self):
        """Second parent user"""
        username = f"parent2_t002_{uuid4().hex[:8]}"
        email = f"parent2_{uuid4().hex[:8]}@t002.test"
        parent = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)
        return parent

    @pytest.fixture
    def student(self):
        """Student without parent initially"""
        username = f"student_t002_{uuid4().hex[:8]}"
        email = f"student_{uuid4().hex[:8]}@t002.test"
        student = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def teacher(self):
        """Teacher user"""
        username = f"teacher_t002_{uuid4().hex[:8]}"
        email = f"teacher_{uuid4().hex[:8]}@t002.test"
        teacher = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123",
            role=User.Role.TEACHER,
        )
        return teacher

    @pytest.fixture
    def subject(self):
        """Math subject"""
        return Subject.objects.create(name=f"Math_T002_{uuid4().hex[:8]}")

    @pytest.fixture
    def enrollment(self, student, teacher, subject):
        """Subject enrollment (creates forum via signal)"""
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        return enrollment

    @pytest.fixture
    def forum(self, enrollment):
        """Forum chat created by signal"""
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )
        return forum

    def test_01_scenario_parent_added_after_enrollment(self, student, teacher, subject, parent1):
        """
        Scenario 1: Enrollment exists BEFORE parent is assigned
        ---
        Timeline:
        1. StudentProfile created (no parent)
        2. SubjectEnrollment created → forum created (parent not added)
        3. Parent assigned to StudentProfile
        4. CHECK: Parent should be in forum

        Expected: sync_parent_participants adds parent to forum
        """
        # Create enrollment first (forum is created by signal)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent is NOT in forum initially
        assert parent1 not in forum.participants.all()
        assert not ChatParticipant.objects.filter(
            room=forum, user=parent1
        ).exists()

        # Now assign parent to student
        student_profile = student.student_profile
        student_profile.parent = parent1
        student_profile.save()

        # Verify parent was added to forum
        forum.refresh_from_db()
        assert parent1 in forum.participants.all(), (
            "FAIL: Parent not added to forum after assignment"
        )
        assert ChatParticipant.objects.filter(
            room=forum, user=parent1
        ).exists(), (
            "FAIL: ChatParticipant record not created for parent"
        )

    def test_02_scenario_parent_removed_from_chats(self, student, parent1, teacher, subject):
        """
        Scenario 2: Parent is REMOVED from chats when unassigned
        ---
        Timeline:
        1. StudentProfile created WITH parent
        2. SubjectEnrollment created → forum created (parent added)
        3. Parent is REMOVED from StudentProfile (parent = None)
        4. CHECK: Parent should be REMOVED from forum

        Expected: sync_parent_participants removes parent from forum
        Status: CURRENTLY FAILS - parent is not removed
        """
        # Create student WITH parent
        student.student_profile.parent = parent1
        student.student_profile.save()

        # Create enrollment (forum created with parent as participant)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent is in forum
        assert parent1 in forum.participants.all()
        assert ChatParticipant.objects.filter(
            room=forum, user=parent1
        ).exists()

        # Now REMOVE parent from student
        student_profile = student.student_profile
        student_profile.parent = None
        student_profile.save()

        # CHECK: Parent should be REMOVED from forum
        forum.refresh_from_db()

        # This assertion will FAIL because current implementation doesn't remove parent
        assert parent1 not in forum.participants.all(), (
            "FAIL: Parent not removed from forum after unassignment. "
            "sync_parent_participants only adds, doesn't remove!"
        )
        assert not ChatParticipant.objects.filter(
            room=forum, user=parent1
        ).exists(), (
            "FAIL: ChatParticipant record not deleted for removed parent"
        )

    def test_03_scenario_parent_changed_to_different_parent(self, student, parent1, parent2, teacher, subject):
        """
        Scenario 3: Parent is CHANGED to different parent
        ---
        Timeline:
        1. StudentProfile created with parent1
        2. SubjectEnrollment created → forum created (parent1 added)
        3. Parent is CHANGED to parent2
        4. CHECK: parent1 should be REMOVED, parent2 should be ADDED

        Expected: sync_parent_participants updates parent
        Status: CURRENTLY FAILS - parent1 not removed, only parent2 added
        """
        # Create student WITH parent1
        student.student_profile.parent = parent1
        student.student_profile.save()

        # Create enrollment (forum created with parent1 as participant)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent1 is in forum
        assert parent1 in forum.participants.all()
        participants_count_before = forum.participants.count()

        # Now CHANGE parent from parent1 to parent2
        student_profile = student.student_profile
        student_profile.parent = parent2
        student_profile.save()

        # CHECK: parent1 should be REMOVED, parent2 should be ADDED
        forum.refresh_from_db()
        participants_count_after = forum.participants.count()

        # This will FAIL - parent1 not removed
        assert parent1 not in forum.participants.all(), (
            "FAIL: Old parent1 not removed from forum when changed to parent2"
        )
        assert parent2 in forum.participants.all(), (
            "FAIL: New parent2 not added to forum"
        )
        # If parent1 was properly removed, count should stay same
        # But since removal doesn't work, count will increase
        assert participants_count_after == participants_count_before, (
            "FAIL: Parent count increased instead of staying same "
            "(old parent not removed)"
        )

    def test_04_multiple_enrollments_parent_sync(self, student, parent1, teacher, subject):
        """
        Scenario 4: Parent is added to ALL student chats (multiple enrollments)
        ---
        Timeline:
        1. StudentProfile created (no parent)
        2. SubjectEnrollment 1 created → forum1 created (parent not added)
        3. SubjectEnrollment 2 created → forum2 created (parent not added)
        4. Parent assigned to StudentProfile
        5. CHECK: Parent should be in BOTH forum1 AND forum2

        Expected: sync_parent_participants finds all student chats and adds parent to all
        Status: Should WORK correctly
        """
        # Create first enrollment
        enrollment1 = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        forum1 = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment1,
        )

        # Create second enrollment with different subject
        subject2 = Subject.objects.create(name=f"English_T002_{uuid4().hex[:8]}")
        enrollment2 = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject2,
        )
        forum2 = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment2,
        )

        # Verify parent is NOT in either forum
        assert parent1 not in forum1.participants.all()
        assert parent1 not in forum2.participants.all()

        # Now assign parent
        student_profile = student.student_profile
        student_profile.parent = parent1
        student_profile.save()

        # Verify parent is in BOTH forums
        forum1.refresh_from_db()
        forum2.refresh_from_db()
        assert parent1 in forum1.participants.all(), (
            "FAIL: Parent not added to forum1"
        )
        assert parent1 in forum2.participants.all(), (
            "FAIL: Parent not added to forum2"
        )

    def test_05_concurrent_enrollment_and_parent_assignment(self, student, parent1, teacher, subject):
        """
        Scenario 5: Enrollment and parent assignment happen at same time
        ---
        Timeline:
        1. StudentProfile created WITH parent
        2. SubjectEnrollment created → signal fires
        3. Parent sync signal fires
        4. CHECK: Parent should be in forum (only once, no duplicates)

        Expected: Both signals handle correctly, no race condition
        Status: Should WORK - both use ignore_conflicts
        """
        # Assign parent first
        student.student_profile.parent = parent1
        student.student_profile.save()

        # Create enrollment (both signals fire)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent is in forum
        assert parent1 in forum.participants.all()

        # Verify no duplicate ChatParticipant records
        parent_participant_count = ChatParticipant.objects.filter(
            room=forum, user=parent1
        ).count()
        assert parent_participant_count == 1, (
            f"FAIL: Duplicate ChatParticipant records (count={parent_participant_count})"
        )


class TestParentSyncDjangoTest(TestCase):
    """Django TestCase version for better transaction handling"""

    def setUp(self):
        """Setup test data"""
        self.parent1 = User.objects.create_user(
            username=f"parent1_{uuid4().hex[:8]}",
            email=f"parent1_{uuid4().hex[:8]}@test.com",
            password="pass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=self.parent1)

        self.parent2 = User.objects.create_user(
            username=f"parent2_{uuid4().hex[:8]}",
            email=f"parent2_{uuid4().hex[:8]}@test.com",
            password="pass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=self.parent2)

        self.student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=self.student)

        self.teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )

        self.subject = Subject.objects.create(name=f"Math_{uuid4().hex[:8]}")

    def test_parent_removal_from_chats(self):
        """
        Test that parent is removed from chats when unassigned.
        This test FAILS with current implementation.
        """
        # Assign parent and create enrollment
        self.student.student_profile.parent = self.parent1
        self.student.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Verify parent is in forum
        self.assertIn(self.parent1, forum.participants.all())

        # Remove parent
        self.student.student_profile.parent = None
        self.student.student_profile.save()

        # This FAILS - parent is still in forum
        forum.refresh_from_db()
        self.assertNotIn(
            self.parent1,
            forum.participants.all(),
            "Parent not removed from forum when unassigned"
        )

    def test_parent_change_updates_chats(self):
        """
        Test that parent is properly updated when changed.
        This test FAILS with current implementation.
        """
        # Assign parent1 and create enrollment
        self.student.student_profile.parent = self.parent1
        self.student.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
        )
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # Change to parent2
        self.student.student_profile.parent = self.parent2
        self.student.student_profile.save()

        # This FAILS - parent1 is still in forum
        forum.refresh_from_db()
        self.assertNotIn(
            self.parent1,
            forum.participants.all(),
            "Old parent not removed when changed"
        )
        self.assertIn(
            self.parent2,
            forum.participants.all(),
            "New parent not added"
        )
