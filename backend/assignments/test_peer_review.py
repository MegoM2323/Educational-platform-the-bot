"""
T_ASSIGN_005: Peer Review Functionality Tests

Comprehensive test suite for:
- Random peer assignment without self-review
- Manual peer assignment validation
- Anonymous review toggles
- Review deadline enforcement
- Permission checks
- Review aggregation and averaging
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase

from assignments.models import (
    Assignment, AssignmentSubmission,
    PeerReviewAssignment, PeerReview
)
from assignments.services.peer_assignment import PeerAssignmentService

User = get_user_model()


class PeerReviewModelTests(TestCase):
    """Tests for PeerReviewAssignment and PeerReview models"""

    def setUp(self):
        """Set up test data"""
        # Create users
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher',
            first_name='John',
            last_name='Doe'
        )

        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='test123',
                role='student',
                first_name=f'Student{i}',
                last_name='User'
            )
            for i in range(1, 6)
        ]

        # Create assignment
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            type=Assignment.Type.HOMEWORK,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
            attempts_limit=1
        )

        # Assign students
        self.assignment.assigned_to.set(self.students)

        # Create submissions
        self.submissions = []
        for student in self.students:
            submission = AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content='Test submission',
                status=AssignmentSubmission.Status.SUBMITTED
            )
            self.submissions.append(submission)

    def test_peer_review_assignment_creation(self):
        """Test creating a peer review assignment"""
        deadline = timezone.now() + timedelta(days=7)

        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        self.assertEqual(assignment.submission, self.submissions[0])
        self.assertEqual(assignment.reviewer, self.students[1])
        self.assertEqual(assignment.status, PeerReviewAssignment.Status.PENDING)
        self.assertFalse(assignment.is_anonymous)

    def test_peer_review_assignment_no_self_review_constraint(self):
        """Test unique constraint prevents self-review"""
        deadline = timezone.now() + timedelta(days=7)

        # This should work
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )
        self.assertIsNotNone(assignment)

        # Cannot create another assignment for same reviewer and submission
        with self.assertRaises(Exception):
            PeerReviewAssignment.objects.create(
                submission=self.submissions[0],
                reviewer=self.students[1],
                deadline=deadline
            )

    def test_peer_review_assignment_overdue_property(self):
        """Test is_overdue property"""
        # Create a past deadline assignment
        past_deadline = timezone.now() - timedelta(days=1)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=past_deadline,
            status=PeerReviewAssignment.Status.PENDING
        )

        self.assertTrue(assignment.is_overdue)

        # Create a future deadline assignment
        future_deadline = timezone.now() + timedelta(days=1)
        assignment2 = PeerReviewAssignment.objects.create(
            submission=self.submissions[1],
            reviewer=self.students[2],
            deadline=future_deadline,
            status=PeerReviewAssignment.Status.PENDING
        )

        self.assertFalse(assignment2.is_overdue)

    def test_peer_review_completion_not_overdue(self):
        """Test completed reviews are never overdue"""
        past_deadline = timezone.now() - timedelta(days=1)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=past_deadline,
            status=PeerReviewAssignment.Status.COMPLETED
        )

        self.assertFalse(assignment.is_overdue)

    def test_peer_review_creation(self):
        """Test creating a peer review"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        review = PeerReview.objects.create(
            peer_assignment=assignment,
            score=85,
            feedback_text='Good work but needs improvement',
            rubric_scores={'clarity': 8, 'completeness': 7, 'accuracy': 9}
        )

        self.assertEqual(review.score, 85)
        self.assertEqual(review.feedback_text, 'Good work but needs improvement')
        self.assertEqual(review.rubric_scores['clarity'], 8)

    def test_peer_review_rubric_average(self):
        """Test rubric_average property"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        review = PeerReview.objects.create(
            peer_assignment=assignment,
            score=85,
            feedback_text='Test feedback',
            rubric_scores={'clarity': 8, 'completeness': 7, 'accuracy': 9}
        )

        self.assertEqual(review.rubric_average, 8.0)

    def test_peer_review_no_rubric_average(self):
        """Test rubric_average returns None when no rubric"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        review = PeerReview.objects.create(
            peer_assignment=assignment,
            score=85,
            feedback_text='Test feedback'
        )

        self.assertIsNone(review.rubric_average)


class PeerAssignmentServiceTests(TestCase):
    """Tests for PeerAssignmentService"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher',
            first_name='John',
            last_name='Doe'
        )

        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='test123',
                role='student',
                first_name=f'Student{i}',
                last_name='User'
            )
            for i in range(1, 6)
        ]

        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            type=Assignment.Type.HOMEWORK,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
            attempts_limit=1
        )

        self.assignment.assigned_to.set(self.students)

        self.submissions = []
        for student in self.students:
            submission = AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content='Test submission',
                status=AssignmentSubmission.Status.SUBMITTED
            )
            self.submissions.append(submission)

    def test_can_review_submission_valid(self):
        """Test can_review_submission with valid reviewer"""
        is_valid, reason = PeerAssignmentService.can_review_submission(
            self.students[1], self.submissions[0]
        )

        self.assertTrue(is_valid)
        self.assertIsNone(reason)

    def test_can_review_submission_self_review(self):
        """Test can_review_submission prevents self-review"""
        is_valid, reason = PeerAssignmentService.can_review_submission(
            self.students[0], self.submissions[0]
        )

        self.assertFalse(is_valid)
        self.assertIn('cannot review their own submission', reason)

    def test_can_review_submission_not_submitted(self):
        """Test can_review_submission requires reviewer to have submitted"""
        # Create a student who hasn't submitted
        non_submitter = User.objects.create_user(
            email='nostudent@test.com',
            password='test123',
            role='student'
        )

        is_valid, reason = PeerAssignmentService.can_review_submission(
            non_submitter, self.submissions[0]
        )

        self.assertFalse(is_valid)
        self.assertIn('must have submitted', reason)

    def test_can_review_submission_non_student(self):
        """Test can_review_submission rejects non-student reviewers"""
        is_valid, reason = PeerAssignmentService.can_review_submission(
            self.teacher, self.submissions[0]
        )

        self.assertFalse(is_valid)
        self.assertIn('Only students', reason)

    def test_can_review_submission_already_assigned(self):
        """Test can_review_submission rejects if already assigned"""
        deadline = timezone.now() + timedelta(days=7)
        PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        is_valid, reason = PeerAssignmentService.can_review_submission(
            self.students[1], self.submissions[0]
        )

        self.assertFalse(is_valid)
        self.assertIn('already assigned', reason)

    def test_assign_random_peers_success(self):
        """Test random peer assignment with sufficient reviewers"""
        result = PeerAssignmentService.assign_random_peers(
            self.assignment.id,
            num_reviewers=2,
            deadline_offset_days=7
        )

        self.assertEqual(result['assigned'], 10)  # 5 submissions * 2 reviewers
        self.assertEqual(result['skipped'], 0)

        # Check assignments were created
        assignments = PeerReviewAssignment.objects.filter(
            submission__assignment=self.assignment
        )
        self.assertEqual(assignments.count(), 10)

    def test_assign_random_peers_no_self_review(self):
        """Test random peer assignment prevents self-review"""
        result = PeerAssignmentService.assign_random_peers(
            self.assignment.id,
            num_reviewers=3,
            deadline_offset_days=7
        )

        # Check no student reviews their own submission
        assignments = PeerReviewAssignment.objects.filter(
            submission__assignment=self.assignment
        )

        for assignment in assignments:
            self.assertNotEqual(
                assignment.reviewer,
                assignment.submission.student,
                "Student should not review their own submission"
            )

    def test_assign_random_peers_insufficient_reviewers(self):
        """Test random peer assignment with insufficient reviewers"""
        result = PeerAssignmentService.assign_random_peers(
            self.assignment.id,
            num_reviewers=10,  # More than available
            deadline_offset_days=7
        )

        self.assertEqual(result['assigned'], 0)
        self.assertEqual(result['skipped'], 5)
        self.assertTrue(len(result['errors']) > 0)

    def test_assign_manual_peer_success(self):
        """Test manual peer assignment"""
        assignment = PeerAssignmentService.assign_manual_peer(
            self.submissions[0].id,
            self.students[1].id,
            deadline_offset_days=7
        )

        self.assertEqual(assignment.submission, self.submissions[0])
        self.assertEqual(assignment.reviewer, self.students[1])
        self.assertEqual(
            assignment.assignment_type,
            PeerReviewAssignment.AssignmentType.MANUAL
        )

    def test_assign_manual_peer_self_review_error(self):
        """Test manual peer assignment rejects self-review"""
        with self.assertRaises(ValueError):
            PeerAssignmentService.assign_manual_peer(
                self.submissions[0].id,
                self.students[0].id,  # Same student
                deadline_offset_days=7
            )

    def test_assign_manual_peer_not_submitted_error(self):
        """Test manual peer assignment requires submitted reviewer"""
        non_submitter = User.objects.create_user(
            email='nostudent@test.com',
            password='test123',
            role='student'
        )

        with self.assertRaises(ValueError):
            PeerAssignmentService.assign_manual_peer(
                self.submissions[0].id,
                non_submitter.id,
                deadline_offset_days=7
            )

    def test_submit_review_success(self):
        """Test submitting a peer review"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        review = PeerAssignmentService.submit_review(
            assignment.id,
            score=85,
            feedback_text='Good work',
            rubric_scores={'clarity': 8, 'completeness': 7}
        )

        self.assertEqual(review.score, 85)
        self.assertEqual(review.feedback_text, 'Good work')
        self.assertEqual(
            assignment.status,
            PeerReviewAssignment.Status.COMPLETED
        )

    def test_submit_review_deadline_passed(self):
        """Test submitting a review after deadline"""
        past_deadline = timezone.now() - timedelta(days=1)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=past_deadline,
            status=PeerReviewAssignment.Status.PENDING
        )

        with self.assertRaises(ValueError):
            PeerAssignmentService.submit_review(
                assignment.id,
                score=85,
                feedback_text='Good work'
            )

    def test_submit_review_already_reviewed(self):
        """Test submitting a review when already reviewed"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        # Submit first review
        PeerAssignmentService.submit_review(
            assignment.id,
            score=85,
            feedback_text='Good work'
        )

        # Try to submit again
        with self.assertRaises(ValueError):
            PeerAssignmentService.submit_review(
                assignment.id,
                score=90,
                feedback_text='Better work'
            )

    def test_submit_review_invalid_score(self):
        """Test submitting a review with invalid score"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline
        )

        with self.assertRaises(ValueError):
            PeerAssignmentService.submit_review(
                assignment.id,
                score=150,  # Invalid score
                feedback_text='Good work'
            )

    def test_get_submission_reviews(self):
        """Test retrieving all reviews for a submission"""
        deadline = timezone.now() + timedelta(days=7)

        # Create multiple reviews
        for i, reviewer in enumerate(self.students[1:3]):
            assignment = PeerReviewAssignment.objects.create(
                submission=self.submissions[0],
                reviewer=reviewer,
                deadline=deadline
            )
            PeerAssignmentService.submit_review(
                assignment.id,
                score=80 + i * 5,
                feedback_text=f'Feedback {i}'
            )

        reviews = PeerAssignmentService.get_submission_reviews(
            self.submissions[0].id
        )

        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]['score'], 80)
        self.assertEqual(reviews[1]['score'], 85)

    def test_get_submission_reviews_anonymous(self):
        """Test anonymous reviews hide reviewer information"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline,
            is_anonymous=True
        )

        PeerAssignmentService.submit_review(
            assignment.id,
            score=85,
            feedback_text='Feedback'
        )

        reviews = PeerAssignmentService.get_submission_reviews(
            self.submissions[0].id,
            anonymous=True
        )

        self.assertEqual(len(reviews), 1)
        self.assertNotIn('reviewer', reviews[0])

    def test_get_peer_score_average(self):
        """Test calculating average peer score"""
        deadline = timezone.now() + timedelta(days=7)

        # Create reviews with different scores
        scores = [80, 85, 90]
        for i, (reviewer, score) in enumerate(zip(self.students[1:4], scores)):
            assignment = PeerReviewAssignment.objects.create(
                submission=self.submissions[0],
                reviewer=reviewer,
                deadline=deadline
            )
            PeerAssignmentService.submit_review(
                assignment.id,
                score=score,
                feedback_text=f'Feedback {i}'
            )

        average = PeerAssignmentService.get_peer_score_average(
            self.submissions[0].id
        )

        self.assertEqual(average, 85.0)

    def test_get_peer_score_average_no_reviews(self):
        """Test average score returns None when no reviews"""
        average = PeerAssignmentService.get_peer_score_average(
            self.submissions[0].id
        )

        self.assertIsNone(average)

    def test_mark_as_skipped(self):
        """Test marking review as skipped"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline,
            status=PeerReviewAssignment.Status.PENDING
        )

        updated = PeerAssignmentService.mark_as_skipped(assignment.id)

        self.assertEqual(
            updated.status,
            PeerReviewAssignment.Status.SKIPPED
        )

    def test_start_review(self):
        """Test marking review as in progress"""
        deadline = timezone.now() + timedelta(days=7)
        assignment = PeerReviewAssignment.objects.create(
            submission=self.submissions[0],
            reviewer=self.students[1],
            deadline=deadline,
            status=PeerReviewAssignment.Status.PENDING
        )

        updated = PeerAssignmentService.start_review(assignment.id)

        self.assertEqual(
            updated.status,
            PeerReviewAssignment.Status.IN_PROGRESS
        )


# API endpoint tests would go here (using Django test client or pytest-django)
