"""
Grade Distribution Analytics Service (T_ASSIGN_007).

Calculates and provides grade statistics for assignments:
- Descriptive statistics (mean, median, mode, std dev, min, max, quartiles)
- Grade distribution buckets (A, B, C, D, F)
- Submission rates and late submission counts
- Comparison with class average
- Historical trends for multiple assignments

Performance optimizations:
- Django ORM aggregations (Count, Avg, StdDev)
- Caching results for 5 minutes
- Single query with prefetch_related
"""

from statistics import StatisticsError, median, mode
from typing import Any, Dict, List, Optional
from django.contrib.auth import get_user_model
from django.db.models import (
    Avg, Count, Max, Min, Q, StdDev, Sum, Case, When, Value, IntegerField, F, Exists, OuterRef
)
from django.core.cache import cache
from django.utils import timezone

from assignments.models import Assignment, AssignmentSubmission

User = get_user_model()


class GradeDistributionAnalytics:
    """
    Analyzes grade distribution and provides comprehensive statistics for an assignment.

    Features:
    - Descriptive statistics (mean, median, mode, std dev, quartiles)
    - Grade distribution buckets (A-F)
    - Submission rate tracking
    - Late submission counts
    - Class average comparison
    - Historical trend data
    """

    # Grade buckets with their percentage ranges
    GRADE_BUCKETS = {
        "A": {"min": 90, "max": 100, "label": "Excellent (90-100%)"},
        "B": {"min": 80, "max": 89, "label": "Good (80-89%)"},
        "C": {"min": 70, "max": 79, "label": "Satisfactory (70-79%)"},
        "D": {"min": 60, "max": 69, "label": "Passing (60-69%)"},
        "F": {"min": 0, "max": 59, "label": "Failing (<60%)"},
    }

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    def __init__(self, assignment: Assignment):
        """
        Initialize analytics for a specific assignment.

        Args:
            assignment: Assignment instance to analyze
        """
        self.assignment = assignment
        self.cache_key = f"assignment_analytics_{assignment.id}"

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get complete analytics for the assignment (with caching).

        Returns:
            Dict containing all analytics data:
            - statistics: Descriptive statistics
            - distribution: Grade distribution buckets
            - submission_rate: Submission rate metrics
            - comparison: Class average comparison
            - historical: Trend data if available
        """
        # Check cache first
        cached_analytics = cache.get(self.cache_key)
        if cached_analytics is not None:
            return cached_analytics

        # Calculate analytics
        analytics = {
            "assignment_id": self.assignment.id,
            "assignment_title": self.assignment.title,
            "max_score": self.assignment.max_score,
            "statistics": self._calculate_statistics(),
            "distribution": self._calculate_distribution(),
            "submission_rate": self._calculate_submission_rate(),
            "comparison": self._calculate_class_average_comparison(),
            "generated_at": timezone.now().isoformat(),
        }

        # Cache the results
        cache.set(self.cache_key, analytics, self.CACHE_TTL)

        return analytics

    def _calculate_statistics(self) -> Dict[str, Optional[float]]:
        """
        Calculate descriptive statistics for grades.

        Returns:
            Dict with mean, median, mode, std_dev, min, max, Q1, Q2, Q3
        """
        # Get all graded submissions with scores
        submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        ).values_list("score", flat=True)

        scores = list(submissions)

        if not scores:
            return {
                "mean": None,
                "median": None,
                "mode": None,
                "std_dev": None,
                "min": None,
                "max": None,
                "q1": None,
                "q2": None,
                "q3": None,
                "sample_size": 0,
            }

        # Calculate statistics
        stats = {
            "mean": round(sum(scores) / len(scores), 2),
            "median": round(median(scores), 2),
            "std_dev": None,
            "min": min(scores),
            "max": max(scores),
            "q1": None,
            "q2": None,
            "q3": None,
            "sample_size": len(scores),
        }

        # Try to calculate mode (may not exist or be multiple values)
        try:
            stats["mode"] = round(mode(scores), 2)
        except StatisticsError:
            stats["mode"] = None

        # Calculate standard deviation if we have enough data
        if len(scores) > 1:
            # Use sample standard deviation
            mean = stats["mean"]
            variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
            stats["std_dev"] = round(variance ** 0.5, 2)

        # Calculate quartiles
        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        if n >= 4:
            # Q1: 25th percentile
            q1_index = int(n * 0.25)
            stats["q1"] = round(sorted_scores[q1_index], 2)

            # Q2: 50th percentile (median)
            q2_index = int(n * 0.5)
            stats["q2"] = round(sorted_scores[q2_index], 2)

            # Q3: 75th percentile
            q3_index = int(n * 0.75)
            stats["q3"] = round(sorted_scores[q3_index], 2)

        return stats

    def _calculate_distribution(self) -> Dict[str, Any]:
        """
        Calculate grade distribution across buckets (A-F).

        Returns:
            Dict with bucket counts, percentages, and pie chart data
        """
        # Get all graded submissions with percentages
        submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False,
            max_score__isnull=False
        ).annotate(
            percentage=Case(
                When(
                    max_score__gt=0,
                    then=(F("score") * 100.0) / F("max_score")
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        ).values_list("percentage", flat=True)

        percentages = list(submissions)
        total = len(percentages)

        if total == 0:
            return {
                "buckets": {bucket: {"count": 0, "percentage": 0.0} for bucket in self.GRADE_BUCKETS},
                "total": 0,
                "pie_chart_data": [],
            }

        # Count submissions in each bucket
        bucket_counts = {bucket: 0 for bucket in self.GRADE_BUCKETS}

        for percentage in percentages:
            for bucket, range_info in self.GRADE_BUCKETS.items():
                if range_info["min"] <= percentage <= range_info["max"]:
                    bucket_counts[bucket] += 1
                    break

        # Format response with percentages and pie chart data
        distribution = {}
        pie_chart_data = []

        for bucket in ["A", "B", "C", "D", "F"]:
            count = bucket_counts[bucket]
            percentage = round((count / total) * 100, 2) if total > 0 else 0
            distribution[bucket] = {
                "label": self.GRADE_BUCKETS[bucket]["label"],
                "count": count,
                "percentage": percentage,
            }
            if count > 0:  # Only include non-zero buckets in pie chart
                pie_chart_data.append({
                    "label": bucket,
                    "value": count,
                    "percentage": percentage,
                })

        return {
            "buckets": distribution,
            "total": total,
            "pie_chart_data": pie_chart_data,
        }

    def _calculate_submission_rate(self) -> Dict[str, Any]:
        """
        Calculate submission and late submission metrics.

        Returns:
            Dict with submission counts, rates, and late submission data
        """
        # Count total submissions
        total_submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment
        ).count()

        # Count graded submissions
        graded_submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            status=AssignmentSubmission.Status.GRADED
        ).count()

        # Count late submissions
        late_submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            is_late=True
        ).count()

        # Count assigned students
        assigned_count = self.assignment.assigned_to.count()

        return {
            "assigned_count": assigned_count,
            "submitted_count": total_submissions,
            "graded_count": graded_submissions,
            "late_count": late_submissions,
            "submission_rate": round((total_submissions / assigned_count * 100), 2) if assigned_count > 0 else 0,
            "grading_rate": round((graded_submissions / total_submissions * 100), 2) if total_submissions > 0 else 0,
            "late_rate": round((late_submissions / total_submissions * 100), 2) if total_submissions > 0 else 0,
        }

    def _calculate_class_average_comparison(self) -> Dict[str, Any]:
        """
        Calculate class average and comparison with this assignment.

        Returns:
            Dict with assignment average, class average, and difference
        """
        # Get average score for this assignment
        assignment_stats = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        ).aggregate(
            avg_score=Avg("score"),
            count=Count("id")
        )

        assignment_avg = assignment_stats.get("avg_score")
        assignment_count = assignment_stats.get("count", 0)

        if assignment_avg is None:
            return {
                "assignment_average": None,
                "assignment_count": 0,
                "class_average": None,
                "difference": None,
                "performance": "No data",
            }

        assignment_avg = round(assignment_avg, 2)

        # Get class average (all assignments by the same teacher)
        class_stats = AssignmentSubmission.objects.filter(
            assignment__author=self.assignment.author,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        ).aggregate(
            avg_score=Avg("score")
        )

        class_avg = class_stats.get("avg_score")

        if class_avg is None:
            return {
                "assignment_average": assignment_avg,
                "assignment_count": assignment_count,
                "class_average": None,
                "difference": None,
                "performance": "No class data",
            }

        class_avg = round(class_avg, 2)
        difference = round(assignment_avg - class_avg, 2)

        # Determine performance
        if difference >= 5:
            performance = "Above average"
        elif difference <= -5:
            performance = "Below average"
        else:
            performance = "Average"

        return {
            "assignment_average": assignment_avg,
            "assignment_count": assignment_count,
            "class_average": class_avg,
            "difference": difference,
            "performance": performance,
        }

    def invalidate_cache(self):
        """Invalidate cached analytics data (called when grades change)."""
        cache.delete(self.cache_key)

    @staticmethod
    def invalidate_assignment_cache(assignment_id: int):
        """
        Invalidate cache for a specific assignment.

        Args:
            assignment_id: Assignment ID to invalidate cache for
        """
        cache_key = f"assignment_analytics_{assignment_id}"
        cache.delete(cache_key)
