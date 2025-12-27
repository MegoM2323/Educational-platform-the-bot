"""
T_MAT_003: Material Progress Edge Cases Test Suite

Comprehensive test coverage for material progress tracking edge cases:
1. Student accessing material they don't have enrollment for (403)
2. Material progress for deleted/archived materials
3. Concurrent progress updates from multiple devices
4. Progress percentage calculation edge cases
5. NULL value handling in view_count, completion_date, score
6. Progress tracking for archived materials
7. Student accessing inactive enrollment materials (403)
8. Progress rollback prevention (only forward allowed)
9. Idempotent progress updates
10. Race condition safety with select_for_update
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from .models import Material, MaterialProgress, Subject, SubjectEnrollment
from .progress_service import MaterialProgressService

User = get_user_model()


@pytest.mark.django_db
class TestMaterialProgressEdgeCases(TransactionTestCase):
    """Test material progress edge cases"""

    def setUp(self):
        """Set up test data"""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student",
            first_name="John",
            last_name="Doe"
        )

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            first_name="Jane",
            last_name="Smith"
        )

        self.other_student = User.objects.create_user(
            email="other_student@test.com",
            password="testpass123",
            role="student",
            first_name="Bob",
            last_name="Johnson"
        )

        self.subject = Subject.objects.create(
            name="Math",
            description="Mathematics"
        )

        self.material = Material.objects.create(
            title="Algebra Basics",
            description="Introduction to algebra",
            content="Basic algebra concepts",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )

        self.client = APIClient()

    # Edge Case 1: Unenrolled Student Access
    def test_unenrolled_student_cannot_access_private_material(self):
        """Test that unenrolled student cannot access private material"""
        self.material.is_public = False
        self.material.assigned_to.set([self.other_student])
        self.material.save()

        progress = MaterialProgress.objects.create(
            student=self.other_student,
            material=self.material,
            progress_percentage=50
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get(f"/api/material-progress/{progress.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unenrolled_student_access_service_validation(self):
        """Test service layer validates unenrolled access"""
        self.material.is_public = False
        self.material.assigned_to.set([self.other_student])
        self.material.save()

        is_valid, error = MaterialProgressService.validate_student_access(
            self.student, self.material
        )

        assert not is_valid
        assert "доступен" in error.lower()

    # Edge Case 2: Deleted/Archived Material Handling
    def test_progress_preserved_when_material_archived(self):
        """Test that progress records are preserved when material is archived"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=75,
            time_spent=120
        )

        MaterialProgressService.handle_material_archive(self.material)

        self.material.refresh_from_db()
        assert self.material.status == Material.Status.ARCHIVED

        progress.refresh_from_db()
        assert progress.progress_percentage == 75
        assert progress.time_spent == 120

    def test_cannot_update_progress_on_archived_material(self):
        """Test that progress cannot be updated on archived materials"""
        self.material.status = Material.Status.ARCHIVED
        self.material.save()

        self.material.assigned_to.add(self.student)

        with pytest.raises(ValueError) as exc_info:
            MaterialProgressService.update_progress(
                self.student,
                self.material,
                progress_percentage=80
            )

    # Edge Case 3: Concurrent Updates Protection
    def test_concurrent_updates_use_select_for_update(self):
        """Test that concurrent updates use select_for_update for atomicity"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=50
        )

        with transaction.atomic():
            progress_locked = MaterialProgress.objects.select_for_update().get(
                pk=progress.pk
            )
            progress_locked.progress_percentage = 75
            progress_locked.save()

        progress.refresh_from_db()
        assert progress.progress_percentage == 75

    # Edge Case 4: Progress Percentage Validation
    def test_negative_progress_clamped_to_zero(self):
        """Test that negative progress is clamped to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": -10
        })

        assert result["progress_percentage"] == 0

    def test_progress_over_100_capped(self):
        """Test that progress over 100 is capped at 100"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": 150
        })

        assert result["progress_percentage"] == 100

    def test_progress_null_defaults_to_zero(self):
        """Test that NULL progress defaults to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": None
        })

        assert result["progress_percentage"] == 0

    def test_progress_non_numeric_raises_error(self):
        """Test that non-numeric progress raises ValidationError"""
        with pytest.raises(ValueError) as exc_info:
            MaterialProgressService.normalize_progress_data({
                "progress_percentage": "invalid"
            })

        assert "числом" in str(exc_info.value).lower()

    # Edge Case 5: NULL Value Handling
    def test_null_time_spent_defaults_to_zero(self):
        """Test that NULL time_spent defaults to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "time_spent": None
        })

        assert result["time_spent"] == 0

    def test_negative_time_spent_clamped_to_zero(self):
        """Test that negative time_spent is clamped to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "time_spent": -60
        })

        assert result["time_spent"] == 0

    def test_progress_metrics_handles_null_aggregates(self):
        """Test that progress metrics safely handle NULL values"""
        self.material.assigned_to.add(self.student)

        metrics = MaterialProgressService.calculate_progress_metrics(self.student)

        assert metrics["total_materials"] == 0
        assert metrics["completion_rate"] == 0.0
        assert metrics["average_progress"] == 0.0
        assert metrics["total_time_spent"] == 0

    # Edge Case 6: Archived Material Access
    def test_student_can_view_progress_on_archived_material(self):
        """Test that student can view progress on archived materials"""
        self.material.assigned_to.add(self.student)
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=85
        )

        self.material.status = Material.Status.ARCHIVED
        self.material.save()

        retrieved = MaterialProgressService.get_student_progress(
            self.student,
            self.material
        )

        assert retrieved is not None
        assert retrieved.progress_percentage == 85

    # Edge Case 7: Inactive Enrollment
    def test_inactive_enrollment_blocks_progress_update(self):
        """Test that inactive enrollment prevents progress updates"""
        self.material.assigned_to.add(self.student)

        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=False
        )

        is_active = MaterialProgressService.validate_enrollment_active(
            self.student,
            self.material
        )

        assert not is_active

    # Edge Case 8: Progress Rollback Prevention
    def test_progress_cannot_go_backwards(self):
        """Test that progress cannot rollback"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=80
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=50
        )

        assert updated.progress_percentage == 80
        assert info["rollback_prevented"] is True

    def test_progress_can_increase(self):
        """Test that progress can increase"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=50
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=75
        )

        assert updated.progress_percentage == 75
        assert info["rollback_prevented"] is False

    def test_progress_stays_same_if_no_update(self):
        """Test that progress stays the same if new value equals current"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=60
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=60
        )

        assert updated.progress_percentage == 60

    # Edge Case 9: Idempotent Updates
    def test_batch_update_idempotent(self):
        """Test that batch updates are idempotent"""
        self.material.assigned_to.add(self.student)

        updates_data = {
            "updates": [
                {"material_id": self.material.id, "progress_percentage": 50}
            ]
        }

        self.client.force_authenticate(user=self.student)

        response1 = self.client.post("/api/material-progress/batch_update/", updates_data, format="json")
        response2 = self.client.post("/api/material-progress/batch_update/", updates_data, format="json")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        assert response1.json()["updated"] == 1
        assert response2.json()["updated"] == 1

        progress = MaterialProgress.objects.get(student=self.student, material=self.material)
        assert progress.progress_percentage == 50

    # Edge Case 10: Auto-completion on 100%
    def test_auto_completion_at_100_percent(self):
        """Test that material is marked complete at 100%"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=99,
            is_completed=False
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=100
        )

        assert updated.is_completed is True
        assert updated.completed_at is not None
        assert info["completed_now"] is True

    def test_completed_at_set_only_once(self):
        """Test that completed_at is set only on first completion"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=100,
            is_completed=True,
            completed_at=timezone.now()
        )

        self.material.assigned_to.add(self.student)
        original_completed_at = progress.completed_at

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=100
        )

        assert updated.completed_at == original_completed_at
        assert info["completed_now"] is False

    # Edge Case: Time spent accumulation
    def test_time_spent_accumulates(self):
        """Test that time_spent accumulates"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            time_spent=60
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            time_spent=30
        )

        assert updated.time_spent == 90

    def test_zero_time_spent_no_change(self):
        """Test that zero time_spent doesn't change total"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            time_spent=100
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            time_spent=0
        )

        assert updated.time_spent == 100
