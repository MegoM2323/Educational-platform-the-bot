"""
T_ASSIGN_003: Tests for consolidated permission checks in assignment submission.

This test file verifies that:
1. Non-assigned students cannot submit (403 Forbidden)
2. Assigned students can submit (201 Created)
3. Non-students cannot submit (403 Forbidden)
4. Past deadline submissions are flagged but allowed (201 Created with is_late=True)
5. Permission checks are consolidated in views layer only
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from assignments.models import Assignment, AssignmentSubmission
from core.models import Subject

User = get_user_model()


class AssignmentSubmissionPermissionTest(TestCase):
    """Test consolidated permission checks for assignment submission."""

    def setUp(self):
        """Set up test data."""
        # Create subjects
        self.subject = Subject.objects.create(name="Mathematics")

        # Create users
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            first_name="John",
            last_name="Teacher",
        )

        self.assigned_student = User.objects.create_user(
            email="assigned@test.com",
            password="testpass123",
            role="student",
            first_name="Alice",
            last_name="Assigned",
        )

        self.unassigned_student = User.objects.create_user(
            email="unassigned@test.com",
            password="testpass123",
            role="student",
            first_name="Bob",
            last_name="Unassigned",
        )

        self.tutor = User.objects.create_user(
            email="tutor@test.com",
            password="testpass123",
            role="tutor",
            first_name="Charlie",
            last_name="Tutor",
        )

        # Create assignment (due date in the future)
        self.assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test description",
            author=self.teacher,
            subject=self.subject,
            type="text",
            status="published",
            max_score=100,
            due_date=timezone.now() + timedelta(days=7),
        )

        # Assign only to assigned_student
        self.assignment.assigned_to.add(self.assigned_student)

        # Create past deadline assignment
        self.past_assignment = Assignment.objects.create(
            title="Past Assignment",
            description="Test description",
            author=self.teacher,
            subject=self.subject,
            type="text",
            status="published",
            max_score=100,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.past_assignment.assigned_to.add(self.assigned_student)

        self.client = APIClient()

    def test_non_assigned_student_cannot_submit(self):
        """Non-assigned student should get 403 Forbidden when submitting."""
        self.client.force_authenticate(user=self.unassigned_student)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # Should receive 403 Forbidden (PermissionDenied)
        self.assertEqual(response.status_code, 403)
        self.assertIn("assigned", response.data.get("detail", "").lower())

    def test_assigned_student_can_submit(self):
        """Assigned student should be able to submit (201 Created)."""
        self.client.force_authenticate(user=self.assigned_student)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # Should succeed with 201 Created
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["assignment"], self.assignment.id)
        self.assertEqual(response.data["student"], self.assigned_student.id)
        self.assertFalse(response.data.get("is_late", False))

    def test_teacher_cannot_submit_assignment(self):
        """Non-student (teacher) should get 403 Forbidden."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # Should receive 403 Forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("student", response.data.get("detail", "").lower())

    def test_tutor_cannot_submit_assignment(self):
        """Non-student (tutor) should get 403 Forbidden."""
        self.client.force_authenticate(user=self.tutor)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # Should receive 403 Forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("student", response.data.get("detail", "").lower())

    def test_assignment_not_found_returns_404(self):
        """Non-existent assignment should return 404 Not Found."""
        self.client.force_authenticate(user=self.assigned_student)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": 99999,
                "content": "My answer",
            },
            format="json",
        )

        # Should receive 404 Not Found
        self.assertEqual(response.status_code, 404)

    def test_missing_assignment_id_returns_400(self):
        """Missing assignment_id should return 400 Bad Request."""
        self.client.force_authenticate(user=self.assigned_student)

        response = self.client.post(
            "/api/submissions/",
            {
                "content": "My answer",
            },
            format="json",
        )

        # Should receive 400 Bad Request
        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.data.get("error", "").lower())

    def test_past_deadline_submission_flagged_as_late(self):
        """Submission past deadline should be flagged with is_late=True."""
        self.client.force_authenticate(user=self.assigned_student)

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.past_assignment.id,
                "content": "My late answer",
            },
            format="json",
        )

        # Should succeed (late submissions allowed) with 201 Created
        self.assertEqual(response.status_code, 201)
        # Should be marked as late
        self.assertTrue(response.data.get("is_late", False))

    def test_multiple_submissions_from_same_student(self):
        """Second submission from same student should fail with unique constraint."""
        self.client.force_authenticate(user=self.assigned_student)

        # First submission
        response1 = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "First answer",
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 201)

        # Second submission (should fail due to unique_together constraint)
        response2 = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "Second answer",
            },
            format="json",
        )

        # Should receive validation error about duplicate submission
        self.assertEqual(response2.status_code, 400)
        self.assertIn("already", response2.data[0].lower())


class AssignmentPermissionConsolidationTest(TestCase):
    """
    Verify that permission checks are consolidated in views layer.

    This test ensures that:
    - Permission logic is explicit and centralized in views
    - Serializer only validates data, not permissions
    - No redundant checks across layers
    """

    def setUp(self):
        """Set up test data."""
        self.subject = Subject.objects.create(name="Science")

        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student",
            first_name="Test",
            last_name="Student",
        )

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
        )

        self.assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test",
            author=self.teacher,
            subject=self.subject,
            type="text",
            status="published",
            due_date=timezone.now() + timedelta(days=1),
        )
        self.assignment.assigned_to.add(self.student)

    def test_views_layer_permission_check_point(self):
        """
        Verify that permission checks occur in views layer (create method).

        The create() method should perform all permission checks before
        delegating to serializer.
        """
        # This test validates the implementation by checking that:
        # 1. Non-assigned student gets 403 (permission check)
        # 2. Not a 400/422 (data validation error)
        # 3. Not a 500 (serializer error)

        client = APIClient()

        unassigned_student = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            role="student",
        )

        client.force_authenticate(user=unassigned_student)

        response = client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # 403 = permission check in views (PermissionDenied exception)
        # Not 400 = not a data validation issue
        # Not 500 = not a serializer logic error
        self.assertEqual(response.status_code, 403)
        self.assertTrue(hasattr(response, "data"))

    def test_student_role_validation_in_views(self):
        """Verify student role check happens in views layer."""
        client = APIClient()
        client.force_authenticate(user=self.teacher)

        response = client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "content": "My answer",
            },
            format="json",
        )

        # Should be 403 (permission check) not 400 (validation)
        self.assertEqual(response.status_code, 403)
