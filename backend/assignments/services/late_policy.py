"""
T_ASSIGN_012: Late Submission Policy Service

Handles late submission detection, penalty calculation, and exemption management.

Features:
- Detects late submissions based on assignment deadline
- Calculates penalties based on configurable policies
- Handles exemptions for special cases
- Supports percentage and fixed-point penalties
- Tracks days/hours late and penalty amounts
"""

from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.utils import timezone
from assignments.models import Assignment, AssignmentSubmission, SubmissionExemption


class LatePolicyService:
    """
    Service for managing late submission policies and penalties.

    Usage:
        submission = AssignmentSubmission.objects.get(id=1)
        service = LatePolicyService(submission)

        # Check if late
        is_late = service.is_late()

        # Calculate days late
        days_late = service.calculate_days_late()

        # Calculate penalty
        penalty = service.calculate_penalty(original_score=85)

        # Apply penalty
        service.apply_penalty(original_score=85)

        # Check exemption
        is_exempt = service.is_exempt()
    """

    def __init__(self, submission: AssignmentSubmission):
        """
        Initialize service with submission.

        Args:
            submission: AssignmentSubmission instance
        """
        self.submission = submission
        self.assignment = submission.assignment

    def is_late(self) -> bool:
        """
        Check if submission is late.

        Returns True if submitted after assignment due_date.

        Returns:
            bool: True if submission is late, False otherwise
        """
        return self.submission.submitted_at > self.assignment.due_date

    def can_accept_late_submission(self) -> Tuple[bool, Optional[str]]:
        """
        Check if late submission is acceptable.

        Checks:
        1. allow_late_submission flag on assignment
        2. late_submission_deadline (if set)

        Returns:
            Tuple of (can_accept, reason_if_not)
            - (True, None) if can accept
            - (False, error_message) if cannot accept
        """
        if not self.is_late():
            return True, None

        # Check if late submissions are allowed
        if not self.assignment.allow_late_submission:
            return False, "Late submissions are not allowed for this assignment"

        # Check late submission deadline (if set)
        if self.assignment.late_submission_deadline:
            if self.submission.submitted_at > self.assignment.late_submission_deadline:
                return (
                    False,
                    f"Late submission deadline was {self.assignment.late_submission_deadline}"
                )

        return True, None

    def calculate_days_late(self) -> Decimal:
        """
        Calculate time late based on penalty frequency.

        If penalty_frequency='per_day', returns days late (decimal).
        If penalty_frequency='per_hour', returns hours late (decimal).

        Returns:
            Decimal: Time late in units specified by penalty_frequency
        """
        if not self.is_late():
            return Decimal("0")

        time_delta = self.submission.submitted_at - self.assignment.due_date

        if self.assignment.penalty_frequency == "per_day":
            # Convert to days
            days = Decimal(str(time_delta.total_seconds() / (24 * 3600)))
            # Round up to next day if any fraction of day
            if days > 0 and days % 1 != 0:
                days = int(days) + 1
            return days
        elif self.assignment.penalty_frequency == "per_hour":
            # Convert to hours
            hours = Decimal(str(time_delta.total_seconds() / 3600))
            # Round up to next hour if any fraction of hour
            if hours > 0 and hours % 1 != 0:
                hours = int(hours) + 1
            return hours

        return Decimal("0")

    def calculate_penalty(self, original_score: int) -> Decimal:
        """
        Calculate penalty for late submission.

        Formula:
        1. If exempt: return 0
        2. If percentage type: penalty = original_score * (penalty_value * days_late / 100)
        3. If fixed_points type: penalty = penalty_value * days_late
        4. Cap at max_penalty

        Args:
            original_score: Score before penalty (out of max_score)

        Returns:
            Decimal: Penalty amount (points to deduct from score)
        """
        if not self.is_late():
            return Decimal("0")

        # Check if exempt
        if self.is_exempt():
            exemption = self.submission.exemption
            if exemption.exemption_type == "full":
                return Decimal("0")
            elif exemption.exemption_type == "custom_rate":
                if exemption.custom_penalty_rate is None:
                    return Decimal("0")
                penalty_value = exemption.custom_penalty_rate
            else:
                return Decimal("0")
        else:
            penalty_value = Decimal(str(self.assignment.late_penalty_value))

        # No penalty if penalty_value is 0
        if penalty_value == 0:
            return Decimal("0")

        days_late = self.calculate_days_late()

        # Calculate penalty based on type
        if self.assignment.late_penalty_type == "percentage":
            # Percentage: (score * penalty_rate * days_late) / 100
            penalty = (
                Decimal(str(original_score))
                * penalty_value
                * days_late
                / Decimal("100")
            )
        elif self.assignment.late_penalty_type == "fixed_points":
            # Fixed points: penalty_value * days_late
            penalty = penalty_value * days_late
        else:
            penalty = Decimal("0")

        # Cap penalty at max_penalty % of original score
        max_penalty_amount = (
            Decimal(str(original_score))
            * Decimal(str(self.assignment.max_penalty))
            / Decimal("100")
        )
        penalty = min(penalty, max_penalty_amount)

        return penalty

    def apply_penalty(self, original_score: int) -> Dict:
        """
        Apply late submission penalty to submission.

        Updates:
        - days_late: calculated days/hours late
        - penalty_applied: penalty amount
        - is_late: marked as late submission

        Args:
            original_score: Score before penalty

        Returns:
            Dict with 'penalty' and 'final_score' keys
        """
        penalty = self.calculate_penalty(original_score)

        # Update submission fields
        self.submission.days_late = self.calculate_days_late()
        self.submission.penalty_applied = penalty
        self.submission.is_late = True
        self.submission.save(update_fields=["days_late", "penalty_applied", "is_late"])

        final_score = int(Decimal(str(original_score)) - penalty)

        return {
            "penalty": float(penalty),
            "final_score": max(0, final_score),  # Score can't go below 0
            "days_late": float(self.submission.days_late),
        }

    def is_exempt(self) -> bool:
        """
        Check if submission has exemption from penalties.

        Returns:
            bool: True if submission has an exemption
        """
        return hasattr(self.submission, "exemption") and self.submission.exemption is not None

    def create_exemption(
        self,
        exemption_type: str,
        reason: str,
        created_by,
        custom_penalty_rate: Optional[Decimal] = None
    ) -> SubmissionExemption:
        """
        Create exemption for this submission.

        Args:
            exemption_type: 'full' or 'custom_rate'
            reason: Reason for exemption
            created_by: User creating exemption
            custom_penalty_rate: Custom rate if exemption_type='custom_rate'

        Returns:
            SubmissionExemption instance

        Raises:
            ValueError: If exemption_type is invalid
        """
        if exemption_type not in ["full", "custom_rate"]:
            raise ValueError(f"Invalid exemption_type: {exemption_type}")

        exemption = SubmissionExemption.objects.create(
            submission=self.submission,
            exemption_type=exemption_type,
            reason=reason,
            exemption_created_by=created_by,
            custom_penalty_rate=custom_penalty_rate,
        )

        return exemption

    def remove_exemption(self) -> bool:
        """
        Remove exemption from this submission.

        Returns:
            bool: True if exemption was removed, False if none existed
        """
        if self.is_exempt():
            self.submission.exemption.delete()
            return True
        return False

    def get_summary(self) -> Dict:
        """
        Get complete late submission summary.

        Returns:
            Dict with all relevant late submission info:
            - is_late: Whether submission is late
            - days_late: How many days/hours late
            - is_exempt: Whether exempt from penalty
            - penalty_applied: Penalty amount (if graded)
            - exemption_reason: Reason if exempt
        """
        result = {
            "is_late": self.is_late(),
            "days_late": float(self.calculate_days_late()) if self.is_late() else 0,
            "is_exempt": self.is_exempt(),
            "penalty_applied": float(self.submission.penalty_applied) if self.submission.penalty_applied else None,
            "exemption_reason": None,
        }

        if self.is_exempt():
            result["exemption_reason"] = self.submission.exemption.reason
            result["exemption_type"] = self.submission.exemption.exemption_type

        return result

    @staticmethod
    def check_late_deadline(assignment: Assignment, submission_time) -> Tuple[bool, Optional[str]]:
        """
        Static method to check if submission time violates late deadline.

        Useful for validation before submission is created.

        Args:
            assignment: Assignment instance
            submission_time: Submitted datetime

        Returns:
            Tuple of (is_valid, error_message)
        """
        if submission_time <= assignment.due_date:
            return True, None

        if not assignment.allow_late_submission:
            return False, "Late submissions are not allowed"

        if assignment.late_submission_deadline:
            if submission_time > assignment.late_submission_deadline:
                return (
                    False,
                    f"Late submission deadline has passed ({assignment.late_submission_deadline})"
                )

        return True, None
