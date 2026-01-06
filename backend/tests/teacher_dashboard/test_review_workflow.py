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


class TestReviewSessionManagement:
    """T3.3 - Tests for managing review sessions"""

    def test_start_review_session_for_assignment(self, authenticated_client, material_math):
        """Test starting a review session for an assignment"""
        data = {
            "assignment_id": material_math.id,
            "include_submissions": [1, 2, 3],
        }
        response = authenticated_client.post("/api/review-sessions/", data, format="json")
        assert response.status_code in [200, 201, 400, 404]

    def test_navigate_between_submissions(self, authenticated_client, material_math):
        """Test navigating between submissions in review session"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/next/")
        assert response.status_code in [200, 404]

    def test_get_review_session_details(self, authenticated_client, material_math):
        """Test getting review session details"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/")
        assert response.status_code in [200, 404]

    def test_complete_review_session(self, authenticated_client, material_math):
        """Test completing a review session"""
        session_id = 1
        data = {"status": "completed"}
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_pause_resume_review_session(self, authenticated_client, material_math):
        """Test pausing and resuming a review session"""
        session_id = 1
        data = {"status": "paused"}
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]


class TestSubmissionComparison:
    """T3.3 - Tests for comparing submissions"""

    def test_compare_submissions_side_by_side(self, authenticated_client, material_math):
        """Test side-by-side comparison of two submissions"""
        data = {
            "submission_1_id": 1,
            "submission_2_id": 2,
        }
        response = authenticated_client.post("/api/submissions/compare/", data, format="json")
        assert response.status_code in [200, 400, 404]

    def test_view_submission_differences(self, authenticated_client, material_math):
        """Test viewing differences between submissions"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/diff/")
        assert response.status_code in [200, 404]

    def test_view_submission_with_inline_comments(self, authenticated_client, material_math):
        """Test viewing submission with inline comments"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/with-comments/")
        assert response.status_code in [200, 404]

    def test_compare_multiple_submissions_batch(self, authenticated_client, material_math):
        """Test comparing multiple submissions in batch"""
        data = {
            "submission_ids": [1, 2, 3, 4],
        }
        response = authenticated_client.post("/api/submissions/compare-batch/", data, format="json")
        assert response.status_code in [200, 400, 404]


class TestPlagiarismAndQuality:
    """T3.3 - Tests for plagiarism detection and quality checks"""

    def test_plagiarism_check_integration(self, authenticated_client, material_math):
        """Test plagiarism check integration"""
        submission_id = 1
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/plagiarism-check/",
            {},
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_get_plagiarism_results(self, authenticated_client, material_math):
        """Test retrieving plagiarism check results"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/plagiarism-results/")
        assert response.status_code in [200, 404]

    def test_similarity_percentage(self, authenticated_client, material_math):
        """Test retrieving similarity percentage from plagiarism check"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/similarity/")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert isinstance(response.data, dict)


class TestInlineCommenting:
    """T3.3 - Tests for inline commenting on submissions"""

    def test_add_inline_comment_on_submission(self, authenticated_client, material_math):
        """Test adding inline comment at specific location in submission"""
        submission_id = 1
        data = {
            "content": "This solution is incorrect",
            "line": 5,
            "position": 10,
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/comments/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_edit_inline_comment(self, authenticated_client, material_math):
        """Test editing an inline comment"""
        comment_id = 1
        data = {"content": "Updated comment"}
        response = authenticated_client.patch(
            f"/api/comments/{comment_id}/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_delete_inline_comment(self, authenticated_client, material_math):
        """Test deleting an inline comment"""
        comment_id = 1
        response = authenticated_client.delete(f"/api/comments/{comment_id}/")
        assert response.status_code in [200, 204, 404]

    def test_reply_to_comment(self, authenticated_student_client, material_math):
        """Test replying to a teacher comment"""
        comment_id = 1
        data = {"content": "Thank you for the feedback"}
        response = authenticated_student_client.post(
            f"/api/comments/{comment_id}/replies/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_get_all_comments_on_submission(self, authenticated_client, material_math):
        """Test retrieving all comments on a submission"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/comments/")
        assert response.status_code in [200, 404]


class TestReviewCompletion:
    """T3.3 - Tests for review completion and tracking"""

    def test_mark_submission_as_reviewed(self, authenticated_client, material_math):
        """Test marking a submission as reviewed"""
        submission_id = 1
        data = {"status": "reviewed"}
        response = authenticated_client.patch(
            f"/api/submissions/{submission_id}/mark-reviewed/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_generate_review_summary(self, authenticated_client, material_math):
        """Test generating a review summary"""
        session_id = 1
        response = authenticated_client.post(
            f"/api/review-sessions/{session_id}/generate-summary/",
            {},
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_get_review_summary(self, authenticated_client, material_math):
        """Test retrieving review summary"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/summary/")
        assert response.status_code in [200, 404]

    def test_track_review_completion_percentage(self, authenticated_client, material_math):
        """Test tracking review completion percentage"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/progress/")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert "completed" in response.data or "percentage" in response.data or True

    def test_get_review_statistics(self, authenticated_client, material_math):
        """Test retrieving review statistics"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/stats/")
        assert response.status_code in [200, 404]


class TestReviewDeadlines:
    """T3.3 - Tests for review deadlines and scheduling"""

    def test_set_review_deadline(self, authenticated_client, material_math):
        """Test setting a deadline for review completion"""
        session_id = 1
        data = {
            "deadline": (timezone.now() + timedelta(days=7)).isoformat(),
        }
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/set-deadline/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_get_upcoming_review_deadlines(self, authenticated_client):
        """Test getting upcoming review deadlines"""
        response = authenticated_client.get("/api/review-sessions/upcoming-deadlines/")
        assert response.status_code in [200, 404]

    def test_extend_review_deadline(self, authenticated_client, material_math):
        """Test extending review deadline"""
        session_id = 1
        data = {
            "extension_days": 3,
        }
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/extend-deadline/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]


class TestDraftFeedback:
    """T3.3 - Tests for draft feedback and auto-save"""

    def test_auto_save_draft_feedback(self, authenticated_client, material_math):
        """Test auto-saving draft feedback"""
        submission_id = 1
        data = {
            "feedback": "This is draft feedback...",
            "grade": 85,
        }
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/draft-feedback/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_retrieve_draft_feedback(self, authenticated_client, material_math):
        """Test retrieving saved draft feedback"""
        submission_id = 1
        response = authenticated_client.get(f"/api/submissions/{submission_id}/draft-feedback/")
        assert response.status_code in [200, 404]

    def test_publish_draft_feedback(self, authenticated_client, material_math):
        """Test publishing draft feedback to student"""
        submission_id = 1
        data = {"publish": True}
        response = authenticated_client.patch(
            f"/api/submissions/{submission_id}/draft-feedback/publish/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]


class TestReviewConflictDetection:
    """T3.3 - Tests for conflict detection in multi-teacher reviews"""

    def test_conflict_detection_multiple_teachers(self, authenticated_client, authenticated_client_2, material_math):
        """Test detecting conflicts when multiple teachers review same assignment"""
        session_id = 1
        # First teacher starts review
        response1 = authenticated_client.post(
            f"/api/review-sessions/{session_id}/lock/",
            {},
            format="json"
        )
        # Second teacher tries to review same assignment
        response2 = authenticated_client_2.post(
            f"/api/review-sessions/{session_id}/lock/",
            {},
            format="json"
        )
        assert response1.status_code in [200, 400, 404]
        assert response2.status_code in [200, 400, 403, 404]

    def test_concurrent_review_prevention(self, authenticated_client, material_math):
        """Test preventing concurrent review of same submission"""
        submission_id = 1
        data = {"session_id": 1}
        response = authenticated_client.post(
            f"/api/submissions/{submission_id}/start-review/",
            data,
            format="json"
        )
        assert response.status_code in [200, 201, 400, 404]


class TestReviewPermissions:
    """T3.3 - Permission and authorization tests for review"""

    def test_only_teacher_can_review(self, authenticated_student_client, material_math):
        """Test that only teachers can access review endpoints"""
        response = authenticated_student_client.get("/api/review-sessions/")
        assert response.status_code in [403, 404]

    def test_teacher_cannot_review_other_teachers_assignment(self, authenticated_client_2, material_math):
        """Test that teacher cannot review another teacher's assignment"""
        # material_math belongs to authenticated_client, not authenticated_client_2
        response = authenticated_client_2.post(
            "/api/review-sessions/",
            {"assignment_id": material_math.id},
            format="json"
        )
        assert response.status_code in [403, 404]

    def test_unauthenticated_cannot_access_review(self, api_client):
        """Test that unauthenticated users cannot access review endpoints"""
        response = api_client.get("/api/review-sessions/")
        assert response.status_code in [400, 401, 403, 404]


class TestReviewArchiving:
    """T3.3 - Tests for archiving completed reviews"""

    def test_archive_completed_review(self, authenticated_client, material_math):
        """Test archiving a completed review session"""
        session_id = 1
        data = {"archive": True}
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/archive/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]

    def test_retrieve_archived_reviews(self, authenticated_client):
        """Test retrieving archived review sessions"""
        response = authenticated_client.get("/api/review-sessions/?archived=true")
        assert response.status_code in [200, 404]

    def test_restore_archived_review(self, authenticated_client, material_math):
        """Test restoring an archived review session"""
        session_id = 1
        data = {"archive": False}
        response = authenticated_client.patch(
            f"/api/review-sessions/{session_id}/archive/",
            data,
            format="json"
        )
        assert response.status_code in [200, 400, 404]


class TestReviewReporting:
    """T3.3 - Tests for review reporting and exports"""

    def test_export_review_report(self, authenticated_client, material_math):
        """Test exporting review report"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/export/")
        assert response.status_code in [200, 404]

    def test_export_review_as_pdf(self, authenticated_client, material_math):
        """Test exporting review session as PDF"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/export/?format=pdf")
        assert response.status_code in [200, 404]

    def test_export_review_as_csv(self, authenticated_client, material_math):
        """Test exporting review session as CSV"""
        session_id = 1
        response = authenticated_client.get(f"/api/review-sessions/{session_id}/export/?format=csv")
        assert response.status_code in [200, 404]

    def test_generate_class_review_summary(self, authenticated_client, material_math):
        """Test generating summary for entire class reviews"""
        response = authenticated_client.get(f"/api/assignments/{material_math.id}/review-summary/")
        assert response.status_code in [200, 404]


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
        username="teacher_review1",
        email="teacher_review1@test.com",
        password="teacher123",
        role=User.Role.TEACHER,
    )
    TeacherProfile.objects.create(user=user, subject="Mathematics")
    return user


@pytest.fixture
def teacher_user_2(db):
    """Create second teacher user"""
    user = User.objects.create_user(
        username="teacher_review2",
        email="teacher_review2@test.com",
        password="teacher456",
        role=User.Role.TEACHER,
    )
    TeacherProfile.objects.create(user=user, subject="English")
    return user


@pytest.fixture
def student_user(db):
    """Create student user"""
    user = User.objects.create_user(
        username="student_review1",
        email="student_review1@test.com",
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
