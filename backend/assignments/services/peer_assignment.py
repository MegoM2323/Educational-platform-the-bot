"""
T_ASSIGN_005: Peer review assignment and management service.

Handles:
- Random peer assignment (ensure no self-review)
- Manual peer assignment (teacher specifies)
- Constraint validation (submitted students only, no self-review)
- Multi-reviewer support (each submission reviewed by N students)
- Review aggregation (average score from peers)
"""

import random
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from assignments.models import (
    Assignment, AssignmentSubmission,
    PeerReviewAssignment, PeerReview
)

User = get_user_model()


class PeerAssignmentService:
    """Service for managing peer review assignments"""

    @staticmethod
    def can_review_submission(reviewer, submission):
        """
        Check if a reviewer can review a submission.

        Constraints:
        - Reviewer must be a student
        - Reviewer cannot review their own submission
        - Reviewer must have submitted the assignment
        - Reviewer must not already have a review assignment for this submission

        Args:
            reviewer: User object (potential reviewer)
            submission: AssignmentSubmission object to review

        Returns:
            tuple: (is_valid, reason) where reason is None if valid
        """
        # Check if reviewer is a student
        if reviewer.role != 'student':
            return False, "Only students can be peer reviewers"

        # Check for self-review
        if reviewer == submission.student:
            return False, "Student cannot review their own submission"

        # Check if reviewer has submitted the assignment
        if not AssignmentSubmission.objects.filter(
            assignment=submission.assignment,
            student=reviewer
        ).exists():
            return False, "Reviewer must have submitted the assignment"

        # Check for existing assignment
        if PeerReviewAssignment.objects.filter(
            submission=submission,
            reviewer=reviewer
        ).exists():
            return False, "Reviewer already assigned to this submission"

        return True, None

    @classmethod
    def assign_random_peers(cls, assignment_id, num_reviewers=3, deadline_offset_days=7):
        """
        Randomly assign peer reviewers to all submissions.

        For each submission, randomly select N students (excluding the submitter)
        to review it. Ensures no student reviews their own work.

        Args:
            assignment_id: Assignment ID
            num_reviewers: Number of peer reviewers per submission
            deadline_offset_days: Days from now for review deadline

        Returns:
            dict: {
                'assigned': int - number of successful assignments,
                'skipped': int - number of skipped (couldn't find valid reviewers),
                'errors': list - error messages
            }

        Raises:
            Assignment.DoesNotExist: If assignment not found
        """
        assignment = Assignment.objects.get(id=assignment_id)
        submissions = AssignmentSubmission.objects.filter(assignment=assignment)

        if not submissions.exists():
            return {'assigned': 0, 'skipped': 0, 'errors': ['No submissions found']}

        deadline = timezone.now() + timedelta(days=deadline_offset_days)
        assigned = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for submission in submissions:
                # Get all students who could potentially review (submitted the assignment)
                potential_reviewers = AssignmentSubmission.objects.filter(
                    assignment=assignment
                ).values_list('student', flat=True).distinct()

                potential_reviewers = User.objects.filter(
                    id__in=potential_reviewers
                ).exclude(id=submission.student)

                # Get already assigned reviewers for this submission
                assigned_reviewers = PeerReviewAssignment.objects.filter(
                    submission=submission
                ).values_list('reviewer', flat=True)

                available_reviewers = potential_reviewers.exclude(id__in=assigned_reviewers)

                # Check if we have enough reviewers
                available_count = available_reviewers.count()
                if available_count < num_reviewers:
                    skipped += 1
                    errors.append(
                        f"Submission {submission.id}: Only {available_count} "
                        f"available reviewers (need {num_reviewers})"
                    )
                    continue

                # Randomly select N reviewers
                selected_reviewers = random.sample(
                    list(available_reviewers),
                    num_reviewers
                )

                # Create assignments
                for reviewer in selected_reviewers:
                    is_valid, reason = cls.can_review_submission(reviewer, submission)
                    if not is_valid:
                        continue

                    PeerReviewAssignment.objects.create(
                        submission=submission,
                        reviewer=reviewer,
                        assignment_type=PeerReviewAssignment.AssignmentType.RANDOM,
                        deadline=deadline
                    )
                    assigned += 1

        return {
            'assigned': assigned,
            'skipped': skipped,
            'errors': errors
        }

    @classmethod
    def assign_manual_peer(cls, submission_id, reviewer_id, deadline_offset_days=7):
        """
        Manually assign a specific reviewer to a submission.

        Args:
            submission_id: AssignmentSubmission ID
            reviewer_id: User ID of the reviewer
            deadline_offset_days: Days from now for review deadline

        Returns:
            PeerReviewAssignment: Created assignment object

        Raises:
            AssignmentSubmission.DoesNotExist
            User.DoesNotExist
            ValueError: If constraints are violated
        """
        submission = AssignmentSubmission.objects.get(id=submission_id)
        reviewer = User.objects.get(id=reviewer_id)

        is_valid, reason = cls.can_review_submission(reviewer, submission)
        if not is_valid:
            raise ValueError(reason)

        deadline = timezone.now() + timedelta(days=deadline_offset_days)

        with transaction.atomic():
            assignment, created = PeerReviewAssignment.objects.get_or_create(
                submission=submission,
                reviewer=reviewer,
                defaults={
                    'assignment_type': PeerReviewAssignment.AssignmentType.MANUAL,
                    'deadline': deadline
                }
            )

        return assignment

    @classmethod
    def submit_review(cls, peer_assignment_id, score, feedback_text, rubric_scores=None):
        """
        Submit a peer review.

        Args:
            peer_assignment_id: PeerReviewAssignment ID
            score: Numeric score (0-100)
            feedback_text: Detailed feedback
            rubric_scores: Optional dict of rubric criterion scores

        Returns:
            PeerReview: Created review object

        Raises:
            PeerReviewAssignment.DoesNotExist
            ValueError: If deadline has passed or already reviewed
        """
        assignment = PeerReviewAssignment.objects.get(id=peer_assignment_id)

        # Check if deadline has passed
        if timezone.now() > assignment.deadline:
            raise ValueError("Review deadline has passed")

        # Check if already reviewed
        if hasattr(assignment, 'review'):
            raise ValueError("Review already submitted for this assignment")

        # Validate score
        if not (0 <= score <= 100):
            raise ValueError("Score must be between 0 and 100")

        with transaction.atomic():
            review = PeerReview.objects.create(
                peer_assignment=assignment,
                score=score,
                feedback_text=feedback_text,
                rubric_scores=rubric_scores or {}
            )
            assignment.status = PeerReviewAssignment.Status.COMPLETED
            assignment.save()

        return review

    @classmethod
    def get_submission_reviews(cls, submission_id, anonymous=False):
        """
        Get all reviews for a submission.

        Args:
            submission_id: AssignmentSubmission ID
            anonymous: If True, hide reviewer information

        Returns:
            list: List of review data dicts
        """
        submission = AssignmentSubmission.objects.get(id=submission_id)

        reviews = PeerReview.objects.filter(
            peer_assignment__submission=submission
        ).select_related(
            'peer_assignment__reviewer'
        )

        result = []
        for review in reviews:
            data = {
                'id': review.id,
                'score': review.score,
                'feedback': review.feedback_text,
                'rubric_scores': review.rubric_scores,
                'created_at': review.created_at,
            }

            if not (anonymous or review.peer_assignment.is_anonymous):
                data['reviewer'] = {
                    'id': review.peer_assignment.reviewer.id,
                    'name': review.peer_assignment.reviewer.get_full_name(),
                }

            result.append(data)

        return result

    @classmethod
    def get_peer_score_average(cls, submission_id):
        """
        Calculate average peer review score for a submission.

        Args:
            submission_id: AssignmentSubmission ID

        Returns:
            float: Average score or None if no reviews
        """
        reviews = PeerReview.objects.filter(
            peer_assignment__submission_id=submission_id
        )

        if not reviews.exists():
            return None

        scores = list(reviews.values_list('score', flat=True))
        return round(sum(scores) / len(scores), 2)

    @classmethod
    def mark_as_skipped(cls, peer_assignment_id, reason=""):
        """
        Mark a peer review assignment as skipped.

        Args:
            peer_assignment_id: PeerReviewAssignment ID
            reason: Optional reason for skipping

        Returns:
            PeerReviewAssignment: Updated assignment
        """
        assignment = PeerReviewAssignment.objects.get(id=peer_assignment_id)
        assignment.status = PeerReviewAssignment.Status.SKIPPED
        assignment.save()
        return assignment

    @classmethod
    def start_review(cls, peer_assignment_id):
        """
        Mark a peer review as in progress.

        Args:
            peer_assignment_id: PeerReviewAssignment ID

        Returns:
            PeerReviewAssignment: Updated assignment
        """
        assignment = PeerReviewAssignment.objects.get(id=peer_assignment_id)
        if assignment.status == PeerReviewAssignment.Status.PENDING:
            assignment.status = PeerReviewAssignment.Status.IN_PROGRESS
            assignment.save()
        return assignment
