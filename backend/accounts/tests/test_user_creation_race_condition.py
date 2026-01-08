"""
Tests for user profile creation race conditions.

Tests verify that creating user profiles safely handles concurrent signal and view operations.
Scenario: Signal creates empty profile, then view updates with data via get_or_create.
"""
import pytest
from django.contrib.auth import get_user_model
from faker import Faker

from accounts.models import StudentProfile, TeacherProfile, TutorProfile

User = get_user_model()
fake = Faker()


@pytest.mark.django_db
class TestUserCreationRaceCondition:
    """Tests that profile creation safely handles race conditions (signal vs view)"""

    def test_signal_and_view_race_condition_student(self):
        """get_or_create safely handles concurrent StudentProfile updates"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.STUDENT,
        )

        # Simulate signal creating empty profile (or first request)
        StudentProfile.objects.create(user=user)
        assert StudentProfile.objects.filter(user=user).exists()
        student_profile = StudentProfile.objects.get(user=user)
        assert student_profile.grade is None

        # Simulate second concurrent request updating with data via get_or_create
        profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={"grade": 5, "goal": "Learn Python"},
        )

        if not created:
            profile.grade = 5
            profile.goal = "Learn Python"
            profile.save(update_fields=["grade", "goal"])

        # Verify data updated
        profile.refresh_from_db()
        assert profile.grade == 5
        assert profile.goal == "Learn Python"
        # Verify only one profile exists (no duplicate)
        assert StudentProfile.objects.filter(user=user).count() == 1

    def test_signal_and_view_race_condition_teacher(self):
        """get_or_create safely handles concurrent TeacherProfile updates"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.TEACHER,
        )

        # Simulate signal/first request creating empty profile
        TeacherProfile.objects.create(user=user)
        assert TeacherProfile.objects.filter(user=user).exists()

        # Second concurrent request updates via get_or_create
        profile, created = TeacherProfile.objects.get_or_create(
            user=user,
            defaults={"subject": "Math"},
        )

        if not created:
            profile.subject = "Math"
            profile.save(update_fields=["subject"])

        profile.refresh_from_db()
        assert profile.subject == "Math"
        assert TeacherProfile.objects.filter(user=user).count() == 1

    def test_signal_and_view_race_condition_tutor(self):
        """get_or_create safely handles concurrent TutorProfile updates"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.TUTOR,
        )

        # Simulate signal/first request creating empty profile
        TutorProfile.objects.create(user=user)
        assert TutorProfile.objects.filter(user=user).exists()

        # Second concurrent request updates via get_or_create
        profile, created = TutorProfile.objects.get_or_create(
            user=user,
            defaults={"specialization": "Physics"},
        )

        if not created:
            profile.specialization = "Physics"
            profile.save(update_fields=["specialization"])

        profile.refresh_from_db()
        assert profile.specialization == "Physics"
        assert TutorProfile.objects.filter(user=user).count() == 1

    def test_student_profile_no_duplicate_on_multiple_updates(self):
        """Verify that multiple updates via get_or_create do not create duplicates"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.STUDENT,
        )

        # First update
        profile1, created1 = StudentProfile.objects.get_or_create(
            user=user,
            defaults={"grade": 5, "goal": "First goal"},
        )
        if not created1:
            profile1.grade = 5
            profile1.goal = "First goal"
            profile1.save(update_fields=["grade", "goal"])

        # Second update
        profile2, created2 = StudentProfile.objects.get_or_create(
            user=user,
            defaults={"grade": 6, "goal": "Second goal"},
        )
        if not created2:
            profile2.grade = 6
            profile2.goal = "Second goal"
            profile2.save(update_fields=["grade", "goal"])

        # Still only one profile
        assert StudentProfile.objects.filter(user=user).count() == 1
        profile_final = StudentProfile.objects.get(user=user)
        assert profile_final.grade == 6
        assert profile_final.goal == "Second goal"

    def test_teacher_profile_no_duplicate_on_multiple_updates(self):
        """Verify multiple updates preserve single TeacherProfile"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.TEACHER,
        )

        # First update
        profile1, created1 = TeacherProfile.objects.get_or_create(
            user=user,
            defaults={"subject": "Math", "experience_years": 5},
        )
        if not created1:
            profile1.subject = "Math"
            profile1.experience_years = 5
            profile1.save(update_fields=["subject", "experience_years"])

        # Second update
        profile2, created2 = TeacherProfile.objects.get_or_create(
            user=user,
            defaults={"subject": "Physics", "experience_years": 10},
        )
        if not created2:
            profile2.subject = "Physics"
            profile2.experience_years = 10
            profile2.save(update_fields=["subject", "experience_years"])

        # Still only one profile
        assert TeacherProfile.objects.filter(user=user).count() == 1
        profile_final = TeacherProfile.objects.get(user=user)
        assert profile_final.subject == "Physics"
        assert profile_final.experience_years == 10

    def test_tutor_profile_no_duplicate_on_multiple_updates(self):
        """Verify multiple updates preserve single TutorProfile"""
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            role=User.Role.TUTOR,
        )

        # First update
        profile1, created1 = TutorProfile.objects.get_or_create(
            user=user,
            defaults={"specialization": "Math"},
        )
        if not created1:
            profile1.specialization = "Math"
            profile1.save(update_fields=["specialization"])

        # Second update
        profile2, created2 = TutorProfile.objects.get_or_create(
            user=user,
            defaults={"specialization": "Physics"},
        )
        if not created2:
            profile2.specialization = "Physics"
            profile2.save(update_fields=["specialization"])

        # Still only one profile
        assert TutorProfile.objects.filter(user=user).count() == 1
        profile_final = TutorProfile.objects.get(user=user)
        assert profile_final.specialization == "Physics"
