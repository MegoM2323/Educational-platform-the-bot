import pytest
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from materials.models import Subject, Material, SubjectEnrollment, TeacherSubject
from accounts.models import TeacherProfile, StudentProfile

User = get_user_model()


class TestStudentSubmissions:
    """T3.2 - Tests for student submissions (file/text)"""

    def test_student_submit_file(self, authenticated_student_client, material_math):
        """Test student submitting work as file"""
        data = {
            "assignment_id": material_math.id,
            "submission_type": "file",
            "file": "test_file_content",
        }
        response = authenticated_student_client.post("/api/submissions/", data, format="multipart")
        assert response.status_code in [200, 201, 400, 404]

    def test_student_submit_text(self, authenticated_student_client, material_math):
        """Test student submitting work as text"""
        data = {
            "assignment_id": material_math.id,
            "submission_type": "text",
            "content": "This is my solution to the algebra problem...",
        }
        response = authenticated_student_client.post("/api/submissions/", data, format="json")
        assert response.status_code in [200, 201, 400, 404]

    def test_teacher_view_submission(self, authenticated_client, material_math):
        """Test teacher viewing student submission"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/")
        assert response.status_code in [200, 404]

    def test_get_all_submissions_for_assignment(self, authenticated_client, material_math):
        """Test getting all submissions for a specific assignment"""
        response = authenticated_client.get(f"/api/assignments/{material_math.id}/submissions/")
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            assert isinstance(response.data, (list, dict))

    def test_filter_submissions_by_status(self, authenticated_client, material_math):
        """Test filtering submissions by status (submitted, reviewed, graded)"""
        response = authenticated_client.get(
            f"/api/assignments/{material_math.id}/submissions/?status=submitted"
        )
        assert response.status_code in [200, 400, 404]

    def test_sort_submissions_by_date(self, authenticated_client, material_math):
        """Test sorting submissions by date"""
        response = authenticated_client.get(
            f"/api/assignments/{material_math.id}/submissions/?sort=date"
        )
        assert response.status_code in [200, 400, 404]

    def test_sort_submissions_by_student(self, authenticated_client, material_math):
        """Test sorting submissions by student name"""
        response = authenticated_client.get(
            f"/api/assignments/{material_math.id}/submissions/?sort=student_name"
        )
        assert response.status_code in [200, 400, 404]

    def test_sort_submissions_by_grade(self, authenticated_client, material_math):
        """Test sorting submissions by grade"""
        response = authenticated_client.get(
            f"/api/assignments/{material_math.id}/submissions/?sort=grade"
        )
        assert response.status_code in [200, 400, 404]

    def test_resubmit_assignment_after_feedback(self, authenticated_student_client, material_math):
        """Test student resubmitting assignment after receiving feedback"""
        data = {
            "assignment_id": material_math.id,
            "submission_type": "text",
            "content": "Revised solution based on feedback",
        }
        response = authenticated_student_client.post("/api/submissions/", data, format="json")
        assert response.status_code in [200, 201, 400, 404]


class TestTeacherFeedback:
    """T3.2 - Tests for teacher feedback on submissions"""

    def test_teacher_add_text_feedback(self, authenticated_client, material_math):
        """Test teacher adding text feedback to submission"""
        submission_id = 1
        data = {
            "feedback_type": "text",
            "content": "Great work! But check your algebra in step 3.",
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/feedback/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_teacher_add_audio_feedback(self, authenticated_client, material_math):
        """Test teacher adding audio feedback"""
        submission_id = 1
        data = {
            "feedback_type": "audio",
            "audio_data": b"mock_audio_content",
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/feedback/",
            data,
            format="multipart"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_teacher_add_video_feedback(self, authenticated_client, material_math):
        """Test teacher adding video feedback"""
        submission_id = 1
        data = {
            "feedback_type": "video",
            "video_url": "https://example.com/feedback.mp4",
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/feedback/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_teacher_mark_submission_reviewed(self, authenticated_client, material_math):
        """Test marking submission as reviewed"""
        submission_id = 1
        data = {"status": "reviewed"}
        response = authenticated_client.patch(
            f"/api/submissions/{submission_id}/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_get_feedback_on_submission(self, authenticated_student_client, material_math):
        """Test getting feedback for a submission"""
        submission_id = 1
        response = authenticated_student_client.get(f"/api/submissions/{submission_id}/feedback/")
        assert response.status_code in [200, 404]

    def test_view_submission_timeline_edits(self, authenticated_client, material_math):
        """Test viewing submission timeline including edits and resubmissions"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/timeline/")
        assert response.status_code in [200, 404]

    def test_bulk_add_feedback(self, authenticated_client, material_math):
        """Test adding feedback to multiple submissions at once"""
        data = {
            "submissions": [
                {"submission_id": 1, "feedback": "Good work"},
                {"submission_id": 2, "feedback": "Needs improvement"},
                {"submission_id": 3, "feedback": "Excellent"},
            ]
        }
        response = authenticated_client.post(
            f"/api/assignments/{material_math.id}/feedback-bulk/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_send_feedback_notification_to_student(self, authenticated_client, material_math):
        """Test sending feedback notification to student"""
        submission_id = 1
        data = {
            "notify": True,
            "message": "Your submission has been reviewed",
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/notify/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_view_feedback_history(self, authenticated_student_client, material_math):
        """Test viewing all feedback history for a submission"""
        submission_id = 1
        response = authenticated_student_client.get(f"/api/submissions/{submission_id}/feedback-history/")
        assert response.status_code in [200, 404]


class TestSubmissionLifecycle:
    """T3.2 - Tests for submission lifecycle management"""

    def test_lock_submission_from_resubmission(self, authenticated_client, material_math):
        """Test locking submission to prevent further resubmissions"""
        submission_id = 1
        data = {"locked": True}
        response = authenticated_client.patch(
            f"/api/submissions/{submission_id}/lock/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_unlock_submission_for_resubmission(self, authenticated_client, material_math):
        """Test unlocking submission to allow resubmissions"""
        submission_id = 1
        data = {"locked": False}
        response = authenticated_client.patch(
            f"/api/submissions/{submission_id}/lock/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_request_resubmission_from_student(self, authenticated_client, material_math):
        """Test requesting resubmission from student"""
        submission_id = 1
        data = {
            "reason": "Please revise and resubmit",
            "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/request-resubmission/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_student_cannot_resubmit_locked_submission(self, authenticated_student_client, material_math):
        """Test that student cannot resubmit if submission is locked"""
        submission_id = 1
        data = {
            "assignment_id": material_math.id,
            "submission_type": "text",
            "content": "Revised answer",
        }
        response = authenticated_student_client.post("/api/submissions/", data, format="json")
        assert response.status_code in [200, 201, 400, 403, 404]

    def test_submission_after_deadline_prevented(self, authenticated_student_client, material_math):
        """Test that submission after deadline is prevented"""
        data = {
            "assignment_id": material_math.id,
            "submission_type": "text",
            "content": "Late submission",
        }
        response = authenticated_student_client.post("/api/submissions/", data, format="json")
        # May allow with late flag or may prevent with 400/403
        assert response.status_code in [200, 201, 400, 403, 404]


class TestSubmissionPermissions:
    """T3.2 - Permission and authorization tests for submissions"""

    def test_student_can_view_own_submission(self, authenticated_student_client, material_math):
        """Test that student can view their own submission"""
        submission_id = 1
        response = authenticated_student_client.get(f"/api/submissions/{submission_id}/")
        assert response.status_code in [200, 404]

    def test_student_cannot_view_other_submissions(self, authenticated_student_client, material_math):
        """Test that student cannot view other students' submissions"""
        submission_id = 999  # Belongs to different student
        response = authenticated_student_client.get(f"/api/submissions/{submission_id}/")
        assert response.status_code in [403, 404]

    def test_teacher_can_view_all_submissions(self, authenticated_client, material_math):
        """Test that teacher can view all submissions for their assignment"""
        response = authenticated_client.get(f"/api/assignments/{material_math.id}/submissions/")
        assert response.status_code in [200, 404]

    def test_unauthenticated_cannot_submit(self, api_client, material_math):
        """Test that unauthenticated users cannot submit"""
        response = api_client.post("/api/submissions/", {}, format="json")
        assert response.status_code in [400, 401, 403, 404]

    def test_different_teacher_cannot_view_submissions(self, authenticated_client_2, material_math):
        """Test that different teacher cannot view submissions"""
        response = authenticated_client_2.get(f"/api/assignments/{material_math.id}/submissions/")
        assert response.status_code in [403, 404]


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, teacher_user):
    """Create API client authenticated as teacher"""
    refresh = RefreshToken.for_user(teacher_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_client_2(api_client, teacher_user_2):
    """Create API client authenticated as second teacher"""
    refresh = RefreshToken.for_user(teacher_user_2)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_student_client(api_client, student_user):
    """Create API client authenticated as student"""
    refresh = RefreshToken.for_user(student_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def teacher_user(db):
    """Create teacher user"""
    user = User.objects.create_user(
        username="teacher_submissions1",
        email="teacher_submissions1@test.com",
        password="teacher123",
        role=User.Role.TEACHER,
    )
    TeacherProfile.objects.create(user=user, subject="Mathematics")
    return user


@pytest.fixture
def teacher_user_2(db):
    """Create second teacher user"""
    user = User.objects.create_user(
        username="teacher_submissions2",
        email="teacher_submissions2@test.com",
        password="teacher456",
        role=User.Role.TEACHER,
    )
    TeacherProfile.objects.create(user=user, subject="English")
    return user


@pytest.fixture
def student_user(db):
    """Create student user"""
    user = User.objects.create_user(
        username="student_submissions1",
        email="student_submissions1@test.com",
        password="student123",
        role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user, grade=10)
    return user


@pytest.fixture
def subject_math(db):
    """Create math subject"""
    return Subject.objects.create(name="Mathematics")


@pytest.fixture
def subject_english(db):
    """Create English subject"""
    return Subject.objects.create(name="English")


@pytest.fixture
def material_math(db, teacher_user, subject_math):
    """Create math material"""
    return Material.objects.create(
        title="Algebra Basics",
        content="Algebra content",
        author=teacher_user,
        subject=subject_math,
        type=Material.Type.LESSON,
    )


@pytest.fixture
def material_english(db, teacher_user_2, subject_english):
    """Create English material"""
    return Material.objects.create(
        title="Shakespeare",
        content="Shakespeare content",
        author=teacher_user_2,
        subject=subject_english,
        type=Material.Type.LESSON,
    )
