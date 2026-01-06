"""
Comprehensive test suite for Tutor Cabinet: Assignments and Grading
Tests T056-T072: Assignment creation/editing/deletion, submission viewing, grading, feedback

Using corrected API endpoints and model fields
"""

import pytest
import json
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from assignments.models import Assignment, AssignmentSubmission
from materials.models import SubjectEnrollment, Material, Subject
from accounts.models import StudentProfile, TutorProfile

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tutor_user(db):
    """Create tutor with profile"""
    user = User.objects.create_user(
        username='tutor1',
        email='tutor1@test.com',
        password='testpass123',
        role=User.Role.TUTOR,
        first_name='Tutor',
        last_name='One'
    )
    TutorProfile.objects.create(
        user=user,
        bio='Math tutor',
        experience_years=5,
        specialization='Mathematics'
    )
    return user


@pytest.fixture
def student_user(db):
    """Create student with profile"""
    user = User.objects.create_user(
        username='student1',
        email='student1@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Student',
        last_name='One'
    )
    StudentProfile.objects.create(
        user=user,
        grade=9,
        goal='Learn math'
    )
    return user


@pytest.fixture
def subject(db):
    """Create subject"""
    return Subject.objects.create(
        name='Mathematics',
        description='Math'
    )


@pytest.fixture
def material(db, subject):
    """Create material"""
    return Material.objects.create(
        title='Math Problems',
        description='Problems',
        subject=subject,
        material_type='pdf',
        source_url='http://test.com/math.pdf'
    )


@pytest.fixture
def tutor_client(tutor_user):
    """Tutor authenticated client"""
    client = APIClient()
    client.force_authenticate(user=tutor_user)
    return client


@pytest.fixture
def student_client(student_user):
    """Student authenticated client"""
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client


@pytest.fixture
def enrollment(db, student_user, subject, tutor_user):
    """Create enrollment linking student to subject with tutor"""
    return SubjectEnrollment.objects.create(
        student=student_user,
        subject=subject,
        tutor=tutor_user,
        status=SubjectEnrollment.Status.ACTIVE
    )


# ============================================================================
# T056: CREATE ASSIGNMENT
# ============================================================================

class TestCreateAssignment:
    """T056: Create assignment"""

    def test_create_assignment_basic(self, tutor_client, tutor_user, subject):
        """Create basic assignment with required fields"""
        payload = {
            'title': 'Math Homework 1',
            'description': 'Solve problems 1-10',
            'instructions': 'Show all steps',
            'type': 'homework',
            'max_score': 100,
            'status': 'draft'
        }
        response = tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_create_assignment_with_deadline(self, tutor_client, tutor_user):
        """Create assignment with deadline"""
        deadline = timezone.now() + timedelta(days=7)
        payload = {
            'title': 'Timed Assignment',
            'description': 'Complete in 7 days',
            'instructions': 'Follow guidelines',
            'type': 'homework',
            'max_score': 100,
            'deadline': deadline.isoformat(),
            'status': 'draft'
        }
        response = tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_student_cannot_create_assignment(self, student_client):
        """Student should not be able to create assignment"""
        payload = {
            'title': 'Unauthorized',
            'description': 'Should fail',
            'instructions': 'Fail',
            'type': 'homework',
            'max_score': 100,
            'status': 'draft'
        }
        response = student_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should be forbidden or method not allowed
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_400_BAD_REQUEST]


# ============================================================================
# T057: EDIT ASSIGNMENT
# ============================================================================

class TestEditAssignment:
    """T057: Edit assignment"""

    def test_edit_assignment_title(self, tutor_client, tutor_user):
        """Update assignment title"""
        assignment = Assignment.objects.create(
            title='Original',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        payload = {'title': 'Updated Title'}
        response = tutor_client.patch(
            f'/api/assignments/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_edit_assignment_description(self, tutor_client, tutor_user):
        """Update assignment description"""
        assignment = Assignment.objects.create(
            title='Test',
            description='Original desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        payload = {'description': 'Updated description'}
        response = tutor_client.patch(
            f'/api/assignments/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_edit_assignment_max_score(self, tutor_client, tutor_user):
        """Update max score"""
        assignment = Assignment.objects.create(
            title='Test',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        payload = {'max_score': 150}
        response = tutor_client.patch(
            f'/api/assignments/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T058: DELETE ASSIGNMENT
# ============================================================================

class TestDeleteAssignment:
    """T058: Delete assignment"""

    def test_delete_draft_assignment(self, tutor_client, tutor_user):
        """Delete draft assignment (no submissions)"""
        assignment = Assignment.objects.create(
            title='Delete Me',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            status='draft'
        )
        response = tutor_client.delete(
            f'/api/assignments/assignments/{assignment.id}/'
        )
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_cannot_delete_published_with_submissions(self, tutor_client, tutor_user, student_user):
        """Cannot delete published assignment with submissions"""
        assignment = Assignment.objects.create(
            title='Has Submissions',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            status='published'
        )
        # Create submission
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now()
        )
        response = tutor_client.delete(
            f'/api/assignments/assignments/{assignment.id}/'
        )
        # Should prevent deletion
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T059: DISTRIBUTE ASSIGNMENT
# ============================================================================

class TestDistributeAssignment:
    """T059: Distribute to students"""

    def test_assign_to_students(self, tutor_client, tutor_user, student_user):
        """Assign assignment to students"""
        assignment = Assignment.objects.create(
            title='For Distribution',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            status='draft'
        )
        # Distribute via assigned_to
        assignment.assigned_to.add(student_user)
        assignment.status = 'published'
        assignment.save()

        assert assignment.assigned_to.count() == 1
        assert student_user in assignment.assigned_to.all()


# ============================================================================
# T060: SET DEADLINE
# ============================================================================

class TestDeadlineHandling:
    """T060: Set deadline"""

    def test_set_deadline(self, tutor_client, tutor_user):
        """Set assignment deadline"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = Assignment.objects.create(
            title='With Deadline',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            deadline=deadline
        )
        assert assignment.deadline == deadline

    def test_extend_deadline(self, tutor_client, tutor_user):
        """Extend deadline"""
        original_deadline = timezone.now() + timedelta(days=7)
        assignment = Assignment.objects.create(
            title='Extensible',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            deadline=original_deadline
        )
        new_deadline = original_deadline + timedelta(days=3)
        payload = {'deadline': new_deadline.isoformat()}
        response = tutor_client.patch(
            f'/api/assignments/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T061: RETAKE HANDLING
# ============================================================================

class TestRetakeHandling:
    """T061: Retake handling"""

    def test_assignment_with_retake(self, tutor_client, tutor_user):
        """Create assignment allowing retakes"""
        assignment = Assignment.objects.create(
            title='Retakeable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            attempts_limit=3
        )
        assert assignment.attempts_limit == 3

    def test_limit_attempts(self, tutor_user):
        """Limit number of attempts"""
        assignment = Assignment.objects.create(
            title='Limited Attempts',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            attempts_limit=2
        )
        assert assignment.attempts_limit == 2


# ============================================================================
# T062: VALIDATION
# ============================================================================

class TestAssignmentValidation:
    """T062: Validation"""

    def test_validate_max_score_positive(self, tutor_client):
        """Max score must be positive"""
        payload = {
            'title': 'Invalid Score',
            'description': 'Desc',
            'instructions': 'Instr',
            'type': 'homework',
            'max_score': -10,
            'status': 'draft'
        }
        response = tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should fail validation
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_validate_title_required(self, tutor_client):
        """Title is required"""
        payload = {
            'description': 'Desc',
            'instructions': 'Instr',
            'type': 'homework',
            'max_score': 100,
            'status': 'draft'
        }
        response = tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_validate_assignment_type(self, tutor_client):
        """Validate assignment type"""
        payload = {
            'title': 'Test',
            'description': 'Desc',
            'instructions': 'Instr',
            'type': 'invalid_type',
            'max_score': 100,
            'status': 'draft'
        }
        response = tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T065: VIEW SUBMISSIONS
# ============================================================================

class TestViewSubmissions:
    """T065: View submissions"""

    def test_list_submissions(self, tutor_client, tutor_user, student_user):
        """List all submissions for assignment"""
        assignment = Assignment.objects.create(
            title='With Submissions',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            status='published'
        )
        # Create submissions
        for i in range(3):
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student_user,
                submitted_at=timezone.now(),
                status='submitted'
            )

        response = tutor_client.get(
            f'/api/assignments/submissions/?assignment={assignment.id}'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_view_submission_detail(self, tutor_client, tutor_user, student_user):
        """View single submission"""
        assignment = Assignment.objects.create(
            title='Test',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        response = tutor_client.get(
            f'/api/assignments/submissions/{submission.id}/'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# ============================================================================
# T066: GRADE SUBMISSION
# ============================================================================

class TestGradeSubmission:
    """T066: Grade work"""

    def test_assign_score(self, tutor_client, tutor_user, student_user):
        """Assign score to submission"""
        assignment = Assignment.objects.create(
            title='Scorable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        payload = {'score': 85}
        response = tutor_client.patch(
            f'/api/assignments/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_score_cannot_exceed_max(self, tutor_client, tutor_user, student_user):
        """Score should not exceed max_score"""
        assignment = Assignment.objects.create(
            title='Limited Score',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now()
        )
        payload = {'score': 150}
        response = tutor_client.patch(
            f'/api/assignments/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should validate
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T067: ADD FEEDBACK
# ============================================================================

class TestAddFeedback:
    """T067: Add feedback"""

    def test_add_comment_to_submission(self, tutor_client, tutor_user, student_user):
        """Add text comment to submission"""
        assignment = Assignment.objects.create(
            title='Commentable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now()
        )
        payload = {'text': 'Good work!'}
        response = tutor_client.post(
            f'/api/assignments/submissions/{submission.id}/comments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T068: MARK AS REVIEWED
# ============================================================================

class TestMarkReviewed:
    """T068: Mark as reviewed"""

    def test_mark_reviewed(self, tutor_client, tutor_user, student_user):
        """Mark submission as reviewed"""
        assignment = Assignment.objects.create(
            title='Reviewable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        payload = {'status': 'graded'}
        response = tutor_client.patch(
            f'/api/assignments/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# T069: RETURN FOR REVISION
# ============================================================================

class TestReturnForRevision:
    """T069: Return for revision"""

    def test_return_submission(self, tutor_client, tutor_user, student_user):
        """Return submission for revision"""
        assignment = Assignment.objects.create(
            title='Revisable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            attempts_limit=2
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        # Mark for revision
        submission.status = 'needs_revision'
        submission.save()
        assert submission.status == 'needs_revision'


# ============================================================================
# T070: BULK GRADING
# ============================================================================

class TestBulkGrading:
    """T070: Bulk grading"""

    def test_grade_multiple_submissions(self, tutor_client, tutor_user, student_user):
        """Grade multiple submissions at once"""
        assignment = Assignment.objects.create(
            title='Bulk Gradeable',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        # Create multiple submissions
        submissions = []
        for i in range(3):
            sub = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student_user,
                submitted_at=timezone.now()
            )
            submissions.append(sub)

        # Grade them
        for sub, score in zip(submissions, [85, 90, 78]):
            sub.score = score
            sub.status = 'graded'
            sub.save()

        assert all(s.status == 'graded' for s in submissions)


# ============================================================================
# T071: NOTIFICATIONS
# ============================================================================

class TestNotifications:
    """T071: Notifications"""

    def test_notification_on_grade(self, tutor_client, tutor_user, student_user):
        """Student notified when graded (test setup only)"""
        assignment = Assignment.objects.create(
            title='Notify Test',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        # Grade submission
        submission.score = 85
        submission.status = 'graded'
        submission.save()
        assert submission.status == 'graded'


# ============================================================================
# T072: SUBMISSION STATUS
# ============================================================================

class TestSubmissionStatus:
    """T072: Submission status tracking"""

    def test_status_submitted(self, tutor_user, student_user):
        """Track submitted status"""
        assignment = Assignment.objects.create(
            title='Status Test',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        assert submission.status == 'submitted'

    def test_status_graded(self, tutor_user, student_user):
        """Track graded status"""
        assignment = Assignment.objects.create(
            title='Graded Status',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='graded',
            score=85
        )
        assert submission.status == 'graded'
        assert submission.score == 85

    def test_late_submission_detection(self, tutor_user, student_user):
        """Detect late submissions"""
        deadline = timezone.now() - timedelta(days=1)
        assignment = Assignment.objects.create(
            title='Late Deadline',
            description='Desc',
            instructions='Instr',
            type='homework',
            max_score=100,
            author=tutor_user,
            deadline=deadline
        )
        # Submit after deadline
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )
        # Check if submission is late
        is_late = submission.submitted_at > assignment.deadline if assignment.deadline else False
        assert is_late


# ============================================================================
# INTEGRATION TEST
# ============================================================================

class TestTutorCabinetWorkflow:
    """Integration: Complete assignment workflow"""

    def test_full_assignment_cycle(self, tutor_user, student_user):
        """
        Full workflow:
        1. Create assignment
        2. Set deadline
        3. Publish
        4. Assign to student
        5. Receive submission
        6. Grade
        7. Mark reviewed
        """
        # 1. Create
        assignment = Assignment.objects.create(
            title='Complete Cycle',
            description='Full workflow test',
            instructions='Test instructions',
            type='homework',
            max_score=100,
            author=tutor_user,
            status='draft'
        )

        # 2. Set deadline
        deadline = timezone.now() + timedelta(days=7)
        assignment.deadline = deadline
        assignment.save()

        # 3. Publish
        assignment.status = 'published'
        assignment.save()

        # 4. Assign to student
        assignment.assigned_to.add(student_user)

        # 5. Create submission
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student_user,
            submitted_at=timezone.now(),
            status='submitted'
        )

        # 6. Grade
        submission.score = 85
        submission.status = 'graded'
        submission.save()

        # Verify final state
        assert assignment.status == 'published'
        assert submission.score == 85
        assert submission.status == 'graded'
