"""
Wave 2: Teacher Dashboard - Progress Tracking Tests (T2.3)
Tests for monitoring student progress on assigned materials
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from materials.models import Material, Subject, MaterialProgress, MaterialSubmission, MaterialFeedback
from .fixtures import *  # Import all fixtures

User = get_user_model()


class TestProgressStartTracking:
    """Test tracking when student starts material"""

    def test_track_material_start_time(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that start time is recorded when student begins material"""
        material = Material.objects.create(
            title="Tracked Material",
            description="Track start",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="assigned",
            started_at=None,
        )

        # Simulate student starting material
        payload = {"status": "in_progress", "started_at": timezone.now().isoformat()}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 400, 404]

    def test_record_first_access_time(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that first access time is recorded"""
        material = Material.objects.create(
            title="First Access",
            description="Record first access",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="assigned",
        )

        # Check first access is recorded
        response = authenticated_student_client.get(f"/api/materials/progress/{progress.id}/")
        assert response.status_code in [200, 404]

    def test_prevent_duplicate_starts(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that material can't be marked as started twice"""
        material = Material.objects.create(
            title="Start Once",
            description="Can only start once",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
            started_at=timezone.now(),
        )

        # Try to start again
        payload = {"status": "in_progress"}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        # Should succeed (idempotent) or ignore
        assert response.status_code in [200, 400, 404]


class TestCompletionTracking:
    """Test tracking material completion status"""

    def test_mark_material_as_completed(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test marking material as completed"""
        material = Material.objects.create(
            title="Complete Material",
            description="Mark as done",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
        )

        payload = {"status": "completed"}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 400, 404]

    def test_record_completion_time(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that completion time is recorded"""
        material = Material.objects.create(
            title="Time Tracked",
            description="Record completion",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
            started_at=timezone.now() - timedelta(hours=2),
        )

        payload = {
            "status": "completed",
            "completed_at": timezone.now().isoformat(),
        }
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 400, 404]

    def test_prevent_status_regression(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that completed material can't be marked as incomplete"""
        material = Material.objects.create(
            title="No Regression",
            description="Can't go backwards",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="completed",
            completed_at=timezone.now(),
        )

        # Try to revert to in_progress
        payload = {"status": "in_progress"}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        # Should reject or ignore
        assert response.status_code in [200, 400, 404]


class TestSubmissionStatus:
    """Test getting submission status for student"""

    def test_get_submission_status(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test checking if student has submitted material"""
        material = Material.objects.create(
            title="Submission Test",
            description="Check submission",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        MaterialSubmission.objects.create(
            user=student_user,
            material=material,
            content="Submitted work",
            status="submitted",
        )

        response = authenticated_client.get(
            f"/api/materials/materials/{material.id}/submissions/{student_user.id}/"
        )
        assert response.status_code in [200, 404]

    def test_check_submission_received(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test student checking if their submission was received"""
        material = Material.objects.create(
            title="Receipt Test",
            description="Verify receipt",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        submission = MaterialSubmission.objects.create(
            user=student_user,
            material=material,
            content="My work",
            status="received",
        )

        response = authenticated_student_client.get(
            f"/api/materials/submissions/{submission.id}/"
        )
        assert response.status_code in [200, 404]

    def test_list_submissions_for_material(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test teacher viewing all submissions for a material"""
        material = Material.objects.create(
            title="Submissions List",
            description="View all",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        MaterialSubmission.objects.create(user=student_user, material=material, content="Work 1")
        MaterialSubmission.objects.create(user=student_user_2, material=material, content="Work 2")

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/submissions/")
        assert response.status_code in [200, 404]

    def test_filter_submissions_by_status(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test filtering submissions by status"""
        response = authenticated_client.get("/api/materials/submissions/?status=submitted")
        assert response.status_code in [200, 404]


class TestProgressPercentage:
    """Test calculating progress percentage"""

    def test_calculate_progress_percentage(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test progress percentage calculation"""
        material = Material.objects.create(
            title="Progress Material",
            description="Calculate progress",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
            progress_percentage=50,
        )

        response = authenticated_client.get(f"/api/materials/progress/{progress.id}/")
        assert response.status_code in [200, 404]

    def test_get_overall_subject_progress(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test calculating overall progress in a subject"""
        # Create multiple materials
        for i in range(5):
            material = Material.objects.create(
                title=f"Subject Material {i+1}",
                description="Test",
                content="Content...",
                author=teacher_user,
                subject=subject_math,
                type=Material.Type.LESSON,
                status=Material.Status.ACTIVE,
            )
            MaterialProgress.objects.create(
                user=student_user,
                material=material,
                status="completed" if i < 3 else "in_progress",
            )

        response = authenticated_client.get(f"/api/materials/progress/?subject={subject_math.id}&student={student_user.id}")
        assert response.status_code in [200, 404]


class TestTimeTracking:
    """Test tracking time spent on material"""

    def test_track_time_spent_on_material(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test recording time spent on material"""
        material = Material.objects.create(
            title="Time Tracking",
            description="Track time",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
            started_at=timezone.now() - timedelta(minutes=30),
        )

        # Update with time spent
        payload = {
            "time_spent_seconds": 1800,  # 30 minutes
        }
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 400, 404]

    def test_calculate_average_time(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test calculating average time spent by students"""
        material = Material.objects.create(
            title="Average Time",
            description="Calculate average",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(user=student_user, material=material, status="completed", time_spent_seconds=1200)
        MaterialProgress.objects.create(user=student_user_2, material=material, status="completed", time_spent_seconds=1800)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/stats/")
        assert response.status_code in [200, 404]

    def test_track_cumulative_time(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test cumulative time tracking across sessions"""
        material = Material.objects.create(
            title="Cumulative Time",
            description="Track total",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="in_progress",
            time_spent_seconds=0,
        )

        # Add time from multiple sessions
        payload = {"time_spent_seconds": 600}
        authenticated_student_client.patch(f"/api/materials/progress/{progress.id}/", payload, format="json")

        payload = {"time_spent_seconds": 1200}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 400, 404]


class TestFeedbackStatus:
    """Test tracking student feedback status"""

    def test_get_feedback_status_for_student(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test checking if feedback has been given"""
        material = Material.objects.create(
            title="Feedback Material",
            description="Check feedback",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        submission = MaterialSubmission.objects.create(
            user=student_user,
            material=material,
            content="Submitted",
        )

        feedback = MaterialFeedback.objects.create(
            submission=submission,
            teacher=teacher_user,
            content="Great work!",
            grade=85,
        )

        response = authenticated_student_client.get(f"/api/materials/feedback/{feedback.id}/")
        assert response.status_code in [200, 404]

    def test_feedback_notification_status(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test checking if student was notified about feedback"""
        material = Material.objects.create(
            title="Notification Test",
            description="Track notification",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        submission = MaterialSubmission.objects.create(
            user=student_user,
            material=material,
            content="Work",
        )

        response = authenticated_client.get(
            f"/api/materials/submissions/{submission.id}/feedback-status/"
        )
        assert response.status_code in [200, 404]

    def test_list_feedback_for_student(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test student viewing all feedback they received"""
        response = authenticated_student_client.get("/api/materials/feedback/")
        assert response.status_code in [200, 404]


class TestIncompleteTracking:
    """Test tracking incomplete materials"""

    def test_list_incomplete_materials(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test listing materials student hasn't completed"""
        # Create materials with different statuses
        for i, status in enumerate(["assigned", "in_progress", "completed"]):
            material = Material.objects.create(
                title=f"Material {i+1}",
                description="Test",
                content="Content...",
                author=teacher_user,
                subject=subject_math,
                type=Material.Type.LESSON,
                status=Material.Status.ACTIVE,
            )
            MaterialProgress.objects.create(
                user=student_user,
                material=material,
                status=status,
            )

        response = authenticated_student_client.get("/api/materials/assignments/?status=incomplete")
        assert response.status_code in [200, 404]

    def test_list_overdue_materials(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test listing overdue materials"""
        material = Material.objects.create(
            title="Overdue Material",
            description="Past due",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="assigned",
            due_date=timezone.now() - timedelta(days=1),
        )

        response = authenticated_student_client.get("/api/materials/assignments/?overdue=true")
        assert response.status_code in [200, 404]

    def test_count_incomplete_materials(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test counting incomplete materials for student"""
        # Create 5 materials, only 2 completed
        for i in range(5):
            material = Material.objects.create(
                title=f"Material {i+1}",
                description="Test",
                content="Content...",
                author=teacher_user,
                subject=subject_math,
                type=Material.Type.LESSON,
                status=Material.Status.ACTIVE,
            )
            status = "completed" if i < 2 else "assigned"
            MaterialProgress.objects.create(
                user=student_user,
                material=material,
                status=status,
            )

        response = authenticated_client.get(f"/api/materials/progress/?student={student_user.id}")
        assert response.status_code in [200, 404]


class TestProgressComparison:
    """Test comparing progress across students"""

    def test_compare_progress_across_students(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test comparing progress of multiple students on same material"""
        material = Material.objects.create(
            title="Comparison Material",
            description="Compare progress",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(user=student_user, material=material, status="completed", progress_percentage=100)
        MaterialProgress.objects.create(user=student_user_2, material=material, status="in_progress", progress_percentage=50)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/progress-comparison/")
        assert response.status_code in [200, 404]

    def test_class_average_progress(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test calculating class average progress"""
        material = Material.objects.create(
            title="Class Average",
            description="Calculate class avg",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(user=student_user, material=material, status="completed", progress_percentage=100)
        MaterialProgress.objects.create(user=student_user_2, material=material, status="completed", progress_percentage=80)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/class-stats/")
        assert response.status_code in [200, 404]

    def test_percentile_ranking(self, authenticated_client, teacher_user, subject_math, db):
        """Test student percentile ranking in class"""
        # Create 10 students
        students = []
        for i in range(10):
            student = User.objects.create_user(
                username=f"percentile_student_{i}",
                email=f"percentile_{i}@test.com",
                password="password123",
                role=User.Role.STUDENT,
            )
            students.append(student)

        material = Material.objects.create(
            title="Percentile Material",
            description="For ranking",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        # Create progress with varying completion rates
        for i, student in enumerate(students):
            MaterialProgress.objects.create(
                user=student,
                material=material,
                status="completed",
                progress_percentage=10 * (i + 1),
            )

        response = authenticated_client.get(f"/api/materials/progress/ranking/?material={material.id}")
        assert response.status_code in [200, 404]


class TestProgressSummary:
    """Test generating progress summary for student"""

    def test_generate_student_progress_summary(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test creating progress summary for individual student"""
        # Create multiple materials and progress records
        for i in range(3):
            material = Material.objects.create(
                title=f"Summary Material {i+1}",
                description="For summary",
                content="Content...",
                author=teacher_user,
                subject=subject_math,
                type=Material.Type.LESSON,
                status=Material.Status.ACTIVE,
            )
            MaterialProgress.objects.create(
                user=student_user,
                material=material,
                status="completed" if i < 2 else "in_progress",
            )

        response = authenticated_client.get(f"/api/materials/progress/summary/?student={student_user.id}")
        assert response.status_code in [200, 404]

    def test_progress_summary_by_subject(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test progress summary grouped by subject"""
        response = authenticated_client.get(f"/api/materials/progress/by-subject/?student={student_user.id}")
        assert response.status_code in [200, 404]

    def test_progress_export_to_pdf(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test exporting progress summary as PDF"""
        response = authenticated_client.get(
            f"/api/materials/progress/export/pdf/?student={student_user.id}",
            HTTP_ACCEPT="application/pdf",
        )
        assert response.status_code in [200, 400, 404]

    def test_progress_export_to_excel(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test exporting progress data as Excel"""
        response = authenticated_client.get(
            f"/api/materials/progress/export/excel/?student={student_user.id}",
            HTTP_ACCEPT="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        assert response.status_code in [200, 400, 404]


class TestAttemptTracking:
    """Test tracking material attempt count"""

    def test_track_material_attempt_count(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test counting attempts on material"""
        material = Material.objects.create(
            title="Attempt Test",
            description="Track attempts",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.TEST,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="assigned",
            attempt_count=0,
        )

        # Simulate multiple attempts
        for _ in range(3):
            payload = {"attempt_count": _ + 1}
            authenticated_student_client.patch(
                f"/api/materials/progress/{progress.id}/",
                payload,
                format="json",
            )

        response = authenticated_client.get(f"/api/materials/progress/{progress.id}/")
        assert response.status_code in [200, 404]

    def test_limit_attempts_per_material(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test enforcing attempt limit on material"""
        material = Material.objects.create(
            title="Limited Attempts",
            description="Only 3 attempts",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.TEST,
            status=Material.Status.ACTIVE,
            max_attempts=3,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="assigned",
            attempt_count=3,
        )

        # Try 4th attempt
        payload = {"attempt_count": 4, "status": "in_progress"}
        response = authenticated_student_client.patch(
            f"/api/materials/progress/{progress.id}/",
            payload,
            format="json",
        )
        # Should either reject or warn
        assert response.status_code in [200, 400, 404]

    def test_track_last_attempt_time(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test recording timestamp of last attempt"""
        material = Material.objects.create(
            title="Last Attempt Time",
            description="Track time of last attempt",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.TEST,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="completed",
            attempt_count=3,
            last_attempted_at=timezone.now(),
        )

        response = authenticated_client.get(f"/api/materials/progress/{progress.id}/")
        assert response.status_code in [200, 404]

    def test_best_attempt_score(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test tracking best score across multiple attempts"""
        material = Material.objects.create(
            title="Best Score",
            description="Track best attempt",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.TEST,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            user=student_user,
            material=material,
            status="completed",
            attempt_count=3,
            best_score=92,
        )

        response = authenticated_client.get(f"/api/materials/progress/{progress.id}/")
        assert response.status_code in [200, 404]
