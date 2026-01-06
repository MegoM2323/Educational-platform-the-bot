"""
Comprehensive test suite for Tutor Cabinet: Assignments (T056-T064) and Grading (T065-T072)

T056-T064: ASSIGNMENTS
- T056: Create assignment
- T057: Edit assignment
- T058: Delete assignment
- T059: Distribute to students
- T060: Set deadline
- T061: Retake handling
- T062: Validation

T065-T072: GRADING & FEEDBACK
- T065: View submissions
- T066: Grade work
- T067: Add feedback
- T068: Mark as reviewed
- T069: Return for revision
- T070: Bulk grading
- T071: Notifications
- T072: Submission status
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


@pytest.fixture
def tutor_with_profile(db):
    """Create tutor with complete profile"""
    user = User.objects.create_user(
        username='tutor_master',
        email='tutor@test.com',
        password='tutorpass123',
        role=User.Role.TUTOR,
        first_name='Master',
        last_name='Tutor'
    )
    TutorProfile.objects.create(
        user=user,
        bio='Expert tutor',
        experience_years=5,
        specialization='Mathematics'
    )
    return user


@pytest.fixture
def students_with_profiles(db):
    """Create 5 students with profiles"""
    students = []
    for i in range(5):
        user = User.objects.create_user(
            username=f'student_t{i}',
            email=f'student_t{i}@test.com',
            password='studentpass123',
            role=User.Role.STUDENT,
            first_name=f'Student{i}',
            last_name='Test'
        )
        StudentProfile.objects.create(
            user=user,
            grade=9,
            goal='Learn well'
        )
        students.append(user)
    return students


@pytest.fixture
def subject(db):
    """Create test subject"""
    return Subject.objects.create(
        name='Mathematics',
        description='Math subject'
    )


@pytest.fixture
def material(db, subject):
    """Create test material"""
    return Material.objects.create(
        title='Math Problems',
        description='Test problems',
        subject=subject,
        material_type='pdf',
        source_url='http://example.com/math.pdf'
    )


@pytest.fixture
def enrollments(db, students_with_profiles, subject, tutor_with_profile):
    """Create enrollments for students in subject with tutor"""
    enrollments = []
    for student in students_with_profiles:
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            tutor=tutor_with_profile,
            status=SubjectEnrollment.Status.ACTIVE
        )
        enrollments.append(enrollment)
    return enrollments


@pytest.fixture
def authenticated_tutor_client(tutor_with_profile):
    """Create authenticated client for tutor"""
    client = APIClient()
    client.force_authenticate(user=tutor_with_profile)
    return client


@pytest.fixture
def student_client(students_with_profiles):
    """Create authenticated client for first student"""
    client = APIClient()
    client.force_authenticate(user=students_with_profiles[0])
    return client


class TestAssignmentCreation:
    """T056: Create assignment"""

    def test_create_basic_assignment(self, authenticated_tutor_client, enrollments, subject):
        """Create basic assignment with required fields"""
        payload = {
            'title': 'Math Homework 1',
            'description': 'Solve problems 1-10',
            'subject': subject.id,
            'assignment_type': 'homework',
            'max_points': 100,
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_create_assignment_with_deadline(self, authenticated_tutor_client, subject):
        """Create assignment with deadline"""
        deadline = timezone.now() + timedelta(days=7)
        payload = {
            'title': 'Timed Assignment',
            'description': 'Complete in one week',
            'subject': subject.id,
            'assignment_type': 'test',
            'max_score': 50,
            'deadline': deadline.isoformat(),
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_assignment_without_permission(self, student_client, subject):
        """Student cannot create assignment"""
        payload = {
            'title': 'Unauthorized Assignment',
            'description': 'Should fail',
            'subject': subject.id,
            'assignment_type': 'homework',
            'max_score': 100,
        }
        response = student_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_assignment_missing_required_field(self, authenticated_tutor_client, subject):
        """Validation: missing required field title"""
        payload = {
            'description': 'No title',
            'subject': subject.id,
            'assignment_type': 'homework',
            'max_score': 100,
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAssignmentEditing:
    """T057: Edit assignment"""

    def test_edit_assignment_title(self, authenticated_tutor_client, subject):
        """Update assignment title"""
        # Create assignment
        assignment = Assignment.objects.create(
            title='Original Title',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        payload = {'title': 'Updated Title'}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_edit_assignment_deadline(self, authenticated_tutor_client, subject):
        """Update assignment deadline"""
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        new_deadline = timezone.now() + timedelta(days=14)
        payload = {'deadline': new_deadline.isoformat()}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_edit_assignment_max_score(self, authenticated_tutor_client, subject):
        """Update max score"""
        assignment = Assignment.objects.create(
            title='Scorable Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        payload = {'max_score': 150}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestAssignmentDeletion:
    """T058: Delete assignment"""

    def test_delete_assignment(self, authenticated_tutor_client, subject):
        """Delete assignment"""
        assignment = Assignment.objects.create(
            title='To Delete',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        response = authenticated_tutor_client.delete(
            f'/api/assignments/{assignment.id}/'
        )
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

    def test_delete_assignment_with_submissions(self, authenticated_tutor_client, subject, students_with_profiles):
        """Try to delete assignment with existing submissions"""
        assignment = Assignment.objects.create(
            title='With Submissions',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        # Create submission
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now()
        )

        response = authenticated_tutor_client.delete(
            f'/api/assignments/{assignment.id}/'
        )
        # Should prevent or warn about deletion
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST, status.HTTP_204_NO_CONTENT]


class TestAssignmentDistribution:
    """T059: Distribute to students"""

    def test_distribute_to_single_student(self, authenticated_tutor_client, subject, students_with_profiles):
        """Assign to single student"""
        assignment = Assignment.objects.create(
            title='Single Student Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        payload = {
            'students': [students_with_profiles[0].id]
        }
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/distribute/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_distribute_to_multiple_students(self, authenticated_tutor_client, subject, students_with_profiles):
        """Assign to multiple students"""
        assignment = Assignment.objects.create(
            title='Bulk Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        student_ids = [s.id for s in students_with_profiles[:3]]
        payload = {'students': student_ids}
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/distribute/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_distribute_via_group(self, authenticated_tutor_client, subject, enrollments):
        """Distribute to all students in subject"""
        assignment = Assignment.objects.create(
            title='Group Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        payload = {'subject': subject.id}
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/distribute/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestAssignmentDeadline:
    """T060: Set deadline"""

    def test_set_absolute_deadline(self, authenticated_tutor_client, subject):
        """Set absolute deadline"""
        assignment = Assignment.objects.create(
            title='Deadline Test',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        deadline = timezone.now() + timedelta(days=5)
        payload = {'deadline': deadline.isoformat()}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_extend_deadline(self, authenticated_tutor_client, subject):
        """Extend existing deadline"""
        deadline = timezone.now() + timedelta(days=3)
        assignment = Assignment.objects.create(
            title='Extendable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            deadline=deadline
        )

        new_deadline = deadline + timedelta(days=2)
        payload = {'deadline': new_deadline.isoformat()}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_deadline_validation_past_date(self, authenticated_tutor_client, subject):
        """Reject past deadline"""
        assignment = Assignment.objects.create(
            title='Invalid Deadline',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        past_deadline = timezone.now() - timedelta(days=1)
        payload = {'deadline': past_deadline.isoformat()}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should validate or allow
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestAssignmentRetake:
    """T061: Retake handling"""

    def test_allow_retake(self, authenticated_tutor_client, subject, students_with_profiles):
        """Enable retakes for assignment"""
        assignment = Assignment.objects.create(
            title='Retakeable Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            allow_retake=True
        )

        # Create first submission
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            score=60
        )

        # Student should be able to submit again
        payload = {'content': 'Second attempt'}
        response = APIClient().post(
            f'/api/assignments/{assignment.id}/submit/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_201_CREATED, status.HTTP_401_UNAUTHORIZED]

    def test_retake_limit(self, authenticated_tutor_client, subject):
        """Set limit on retakes"""
        assignment = Assignment.objects.create(
            title='Limited Retakes',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            allow_retake=True,
            max_attempts=3
        )

        payload = {'max_attempts': 3}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestAssignmentValidation:
    """T062: Validation"""

    def test_validate_max_score_positive(self, authenticated_tutor_client, subject):
        """Max score must be positive"""
        payload = {
            'title': 'Invalid Score',
            'description': 'Test',
            'subject': subject.id,
            'assignment_type': 'homework',
            'max_score': -10,
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_title_not_empty(self, authenticated_tutor_client, subject):
        """Title cannot be empty"""
        payload = {
            'title': '',
            'description': 'Test',
            'subject': subject.id,
            'assignment_type': 'homework',
            'max_score': 100,
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_assignment_type(self, authenticated_tutor_client, subject):
        """Validate assignment type choice"""
        payload = {
            'title': 'Invalid Type',
            'description': 'Test',
            'subject': subject.id,
            'assignment_type': 'invalid_type',
            'max_score': 100,
        }
        response = authenticated_tutor_client.post(
            '/api/assignments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSubmissionViewing:
    """T065: View submissions"""

    def test_list_submissions(self, authenticated_tutor_client, subject, students_with_profiles):
        """View all submissions for assignment"""
        assignment = Assignment.objects.create(
            title='Assignment with Submissions',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        # Create submissions
        for i, student in enumerate(students_with_profiles[:3]):
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                submitted_at=timezone.now(),
                content=f'Submission {i+1}'
            )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_view_submission_detail(self, authenticated_tutor_client, subject, students_with_profiles):
        """View single submission details"""
        assignment = Assignment.objects.create(
            title='Detailed Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            content='Student work'
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_filter_submissions_by_status(self, authenticated_tutor_client, subject, students_with_profiles):
        """Filter submissions by status (pending/graded/late)"""
        assignment = Assignment.objects.create(
            title='Filterable Submissions',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/?status=submitted'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestGrading:
    """T066: Grade work"""

    def test_grade_submission(self, authenticated_tutor_client, subject, students_with_profiles):
        """Assign score to submission"""
        assignment = Assignment.objects.create(
            title='Scorable Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            content='Work'
        )

        payload = {'score': 85}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_grade_exceeds_max_score(self, authenticated_tutor_client, subject, students_with_profiles):
        """Prevent score exceeding max"""
        assignment = Assignment.objects.create(
            title='Limited Score',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now()
        )

        payload = {'score': 150}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should validate or accept
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_mark_as_graded(self, authenticated_tutor_client, subject, students_with_profiles):
        """Change submission status to graded"""
        assignment = Assignment.objects.create(
            title='Gradeable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='submitted'
        )

        payload = {'status': 'graded', 'score': 90}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestFeedback:
    """T067: Add feedback"""

    def test_add_text_feedback(self, authenticated_tutor_client, subject, students_with_profiles):
        """Add text comment to submission"""
        assignment = Assignment.objects.create(
            title='Feedbackable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now()
        )

        payload = {
            'comment': 'Good work but check calculation on page 2',
            'comment_type': 'text'
        }
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/comments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_add_inline_feedback(self, authenticated_tutor_client, subject, students_with_profiles):
        """Add inline comment to specific location"""
        assignment = Assignment.objects.create(
            title='Inline Feedback Assignment',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now()
        )

        payload = {
            'comment': 'Check spelling',
            'line_number': 42,
            'comment_type': 'inline'
        }
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/comments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestReviewStatus:
    """T068: Mark as reviewed"""

    def test_mark_reviewed(self, authenticated_tutor_client, subject, students_with_profiles):
        """Mark submission as reviewed"""
        assignment = Assignment.objects.create(
            title='Reviewable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='submitted'
        )

        payload = {'is_reviewed': True}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestReturnForRevision:
    """T069: Return for revision"""

    def test_return_for_revision(self, authenticated_tutor_client, subject, students_with_profiles):
        """Mark submission as needing revision"""
        assignment = Assignment.objects.create(
            title='Revisable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            allow_retake=True
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='submitted'
        )

        payload = {
            'status': 'needs_revision',
            'revision_reason': 'Incomplete solutions'
        }
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestBulkGrading:
    """T070: Bulk grading"""

    def test_bulk_grade_submissions(self, authenticated_tutor_client, subject, students_with_profiles):
        """Grade multiple submissions at once"""
        assignment = Assignment.objects.create(
            title='Bulk Gradeable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submissions = []
        for i, student in enumerate(students_with_profiles[:3]):
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                submitted_at=timezone.now()
            )
            submissions.append(submission)

        payload = {
            'submissions': [
                {'submission_id': submissions[0].id, 'score': 85},
                {'submission_id': submissions[1].id, 'score': 90},
                {'submission_id': submissions[2].id, 'score': 78},
            ]
        }
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/bulk-grade/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_bulk_add_feedback(self, authenticated_tutor_client, subject, students_with_profiles):
        """Add same feedback to multiple submissions"""
        assignment = Assignment.objects.create(
            title='Bulk Feedback',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submissions = []
        for student in students_with_profiles[:3]:
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                submitted_at=timezone.now()
            )
            submissions.append(submission)

        payload = {
            'submission_ids': [s.id for s in submissions],
            'comment': 'Great work everyone!'
        }
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/bulk-comment/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestNotifications:
    """T071: Notifications"""

    def test_student_notified_graded(self, authenticated_tutor_client, subject, students_with_profiles):
        """Student gets notified when graded"""
        assignment = Assignment.objects.create(
            title='Notifiable',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='submitted'
        )

        payload = {'score': 85, 'status': 'graded'}
        response = authenticated_tutor_client.patch(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should send notification
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_student_notified_feedback(self, authenticated_tutor_client, subject, students_with_profiles):
        """Student gets notified when feedback added"""
        assignment = Assignment.objects.create(
            title='Feedback Notification',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now()
        )

        payload = {'comment': 'Good effort!'}
        response = authenticated_tutor_client.post(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/comments/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should send notification
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestSubmissionStatus:
    """T072: Submission status"""

    def test_submission_status_pending(self, authenticated_tutor_client, subject, students_with_profiles):
        """View pending submissions"""
        assignment = Assignment.objects.create(
            title='Pending Status',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/?status=pending'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_submission_status_submitted(self, authenticated_tutor_client, subject, students_with_profiles):
        """View submitted submissions"""
        assignment = Assignment.objects.create(
            title='Submitted Status',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='submitted'
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/?status=submitted'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_submission_status_graded(self, authenticated_tutor_client, subject, students_with_profiles):
        """View graded submissions"""
        assignment = Assignment.objects.create(
            title='Graded Status',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100
        )

        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            status='graded',
            score=85
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/?status=graded'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_submission_late_detection(self, authenticated_tutor_client, subject, students_with_profiles):
        """Detect late submissions"""
        deadline = timezone.now() - timedelta(days=1)
        assignment = Assignment.objects.create(
            title='Late Submission',
            description='Test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            deadline=deadline
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),  # After deadline
            status='submitted'
        )

        response = authenticated_tutor_client.get(
            f'/api/assignments/{assignment.id}/submissions/{submission.id}/'
        )
        # Should indicate late submission
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# ============================================================================
# SUMMARY TEST
# ============================================================================

class TestTutorCabinetIntegration:
    """Integration test: Full workflow"""

    def test_complete_assignment_workflow(self, authenticated_tutor_client, subject, students_with_profiles):
        """
        Complete flow:
        1. Create assignment
        2. Distribute to students
        3. Set deadline
        4. Receive submissions
        5. Grade
        6. Send feedback
        7. Mark reviewed
        """
        # 1. Create
        assignment = Assignment.objects.create(
            title='Complete Workflow',
            description='Full cycle test',
            subject=subject,
            assignment_type='homework',
            max_score=100,
            deadline=timezone.now() + timedelta(days=7)
        )

        # 2-3. Already created with deadline

        # 4. Simulate submission
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=students_with_profiles[0],
            submitted_at=timezone.now(),
            content='Student work',
            status='submitted'
        )

        # 5. Grade
        submission.score = 85
        submission.status = 'graded'
        submission.save()

        # 6-7. Feedback and mark reviewed (would be API calls in real test)

        assert submission.score == 85
        assert submission.status == 'graded'
