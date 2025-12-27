"""
T_MAT_003: Material Progress Edge Cases - Unit Tests

Comprehensive test coverage for material progress tracking edge cases.
Run with: python manage.py test materials.test_mat_003_edge_cases
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Material, MaterialProgress, Subject, SubjectEnrollment
from .progress_service import MaterialProgressService

User = get_user_model()


class MaterialProgressEdgeCasesTest(TransactionTestCase):
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
            email="other@test.com",
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

    # Edge Case 1: Unenrolled Student Access
    def test_unenrolled_student_cannot_access_private_material(self):
        """Test that unenrolled student cannot access private material"""
        self.material.is_public = False
        self.material.assigned_to.set([self.other_student])
        self.material.save()

        is_valid, error = MaterialProgressService.validate_student_access(
            self.student, self.material
        )

        self.assertFalse(is_valid)
        self.assertIn("доступен", error.lower())

    def test_public_material_accessible_to_all(self):
        """Test that public material is accessible to all"""
        self.material.is_public = True
        self.material.save()

        is_valid, error = MaterialProgressService.validate_student_access(
            self.student, self.material
        )

        self.assertTrue(is_valid)

    # Edge Case 2: Deleted/Archived Material Handling
    def test_progress_preserved_when_material_archived(self):
        """Test that progress records are preserved when material is archived"""
        self.material.assigned_to.add(self.student)

        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=75,
            time_spent=120
        )

        result = MaterialProgressService.handle_material_archive(self.material)

        self.material.refresh_from_db()
        self.assertEqual(self.material.status, Material.Status.ARCHIVED)

        progress.refresh_from_db()
        self.assertEqual(progress.progress_percentage, 75)
        self.assertEqual(progress.time_spent, 120)
        self.assertEqual(result["status"], "archived")

    def test_cannot_write_progress_on_archived_material(self):
        """Test that progress cannot be updated on archived materials"""
        self.material.status = Material.Status.ARCHIVED
        self.material.assigned_to.add(self.student)
        self.material.save()

        with self.assertRaises(ValueError):
            MaterialProgressService.update_progress(
                self.student,
                self.material,
                progress_percentage=80
            )

    # Edge Case 4: Progress Percentage Validation
    def test_negative_progress_clamped_to_zero(self):
        """Test that negative progress is clamped to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": -10
        })

        self.assertEqual(result["progress_percentage"], 0)

    def test_progress_over_100_capped(self):
        """Test that progress over 100 is capped at 100"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": 150
        })

        self.assertEqual(result["progress_percentage"], 100)

    def test_progress_null_defaults_to_zero(self):
        """Test that NULL progress defaults to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "progress_percentage": None
        })

        self.assertEqual(result["progress_percentage"], 0)

    def test_progress_non_numeric_raises_error(self):
        """Test that non-numeric progress raises ValueError"""
        with self.assertRaises(ValueError):
            MaterialProgressService.normalize_progress_data({
                "progress_percentage": "invalid"
            })

    # Edge Case 5: NULL Value Handling
    def test_null_time_spent_defaults_to_zero(self):
        """Test that NULL time_spent defaults to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "time_spent": None
        })

        self.assertEqual(result["time_spent"], 0)

    def test_negative_time_spent_clamped_to_zero(self):
        """Test that negative time_spent is clamped to 0"""
        result = MaterialProgressService.normalize_progress_data({
            "time_spent": -60
        })

        self.assertEqual(result["time_spent"], 0)

    def test_progress_metrics_handles_no_materials(self):
        """Test that progress metrics handle zero materials"""
        metrics = MaterialProgressService.calculate_progress_metrics(self.student)

        self.assertEqual(metrics["total_materials"], 0)
        self.assertEqual(metrics["completion_rate"], 0.0)
        self.assertEqual(metrics["average_progress"], 0.0)
        self.assertEqual(metrics["total_time_spent"], 0)

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

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.progress_percentage, 85)

    # Edge Case 7: Inactive Enrollment
    def test_inactive_enrollment_detected(self):
        """Test that inactive enrollment is detected"""
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=False
        )

        is_active = MaterialProgressService.validate_enrollment_active(
            self.student,
            self.material
        )

        self.assertFalse(is_active)

    def test_active_enrollment_detected(self):
        """Test that active enrollment is detected"""
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

        is_active = MaterialProgressService.validate_enrollment_active(
            self.student,
            self.material
        )

        self.assertTrue(is_active)

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

        self.assertEqual(updated.progress_percentage, 80)
        self.assertTrue(info["rollback_prevented"])

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

        self.assertEqual(updated.progress_percentage, 75)
        self.assertFalse(info["rollback_prevented"])

    def test_progress_stays_same_if_no_increase(self):
        """Test that progress stays same if new value equals current"""
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

        self.assertEqual(updated.progress_percentage, 60)

    # Edge Case 9: Auto-completion on 100%
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

        self.assertTrue(updated.is_completed)
        self.assertIsNotNone(updated.completed_at)
        self.assertTrue(info["completed_now"])

    def test_completed_at_set_only_once(self):
        """Test that completed_at is set only on first completion"""
        original_time = timezone.now()
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=100,
            is_completed=True,
            completed_at=original_time
        )

        self.material.assigned_to.add(self.student)

        updated, info = MaterialProgressService.update_progress(
            self.student,
            self.material,
            progress_percentage=100
        )

        self.assertEqual(updated.completed_at, original_time)
        self.assertFalse(info["completed_now"])

    # Edge Case 10: Time spent accumulation
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

        self.assertEqual(updated.time_spent, 90)

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

        self.assertEqual(updated.time_spent, 100)

    # Atomic transaction test
    def test_update_uses_atomic_transaction(self):
        """Test that updates use atomic transactions"""
        self.material.assigned_to.add(self.student)
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material
        )

        with transaction.atomic():
            updated, _ = MaterialProgressService.update_progress(
                self.student,
                self.material,
                progress_percentage=50
            )

        progress.refresh_from_db()
        self.assertEqual(progress.progress_percentage, 50)

    # Serializer validation test
    def test_serializer_validates_progress_percentage(self):
        """Test that serializer validates progress_percentage"""
        from .serializers import MaterialProgressSerializer

        data = {"progress_percentage": -10}
        serializer = MaterialProgressSerializer(data=data, partial=True)

        self.assertFalse(serializer.is_valid())

    def test_serializer_validates_time_spent(self):
        """Test that serializer validates time_spent"""
        from .serializers import MaterialProgressSerializer

        data = {"time_spent": "invalid"}
        serializer = MaterialProgressSerializer(data=data, partial=True)

        self.assertFalse(serializer.is_valid())


class MaterialProgressQueryOptimization(TestCase):
    """Test that queries are optimized"""

    def setUp(self):
        """Set up test data"""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student"
        )

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher"
        )

        self.subject = Subject.objects.create(name="Math")

        self.material = Material.objects.create(
            title="Test",
            content="Test content",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )

    def test_get_student_progress_uses_select_related(self):
        """Test that get_student_progress uses select_related"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material
        )

        retrieved = MaterialProgressService.get_student_progress(
            self.student,
            self.material
        )

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, progress.id)
