"""
Grade Distribution Analytics Tests (T_ASSIGN_007).

Comprehensive tests for:
- Statistics calculation (mean, median, mode, std dev, quartiles)
- Grade distribution buckets (A-F)
- Submission rate metrics
- Class average comparison
- Cache management and invalidation
- API endpoint permissions
- Edge cases (no submissions, all same grade)
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Assignment, AssignmentSubmission
from .services.analytics import GradeDistributionAnalytics

User = get_user_model()


class GradeDistributionAnalyticsTestCase(APITestCase):
    """Test suite for grade distribution analytics service and API endpoint."""

    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()

        # Create users using the project's user creation pattern
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.tutor = User.objects.create_user(
            username="tutor",
            email="tutor@test.com",
            password="TestPass123!",
            role="tutor"
        )

        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="TestPass123!",
            role="student"
        )

        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="TestPass123!",
            role="student"
        )

        self.student3 = User.objects.create_user(
            username="student3",
            email="student3@test.com",
            password="TestPass123!",
            role="student"
        )

        self.other_teacher = User.objects.create_user(
            username="other_teacher",
            email="other_teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Create assignment
        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title="Algebra Test",
            description="Test algebra skills",
            instructions="Complete all problems",
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )

        # Assign to students
        self.assignment.assigned_to.set([self.student1, self.student2, self.student3])

        # Create an assignment for another teacher
        self.other_assignment = Assignment.objects.create(
            title="Physics Test",
            description="Test physics skills",
            instructions="Complete all problems",
            author=self.other_teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )
        self.other_assignment.assigned_to.set([self.student1])

        self.client = APIClient()

    def tearDown(self):
        """Clean up after each test."""
        cache.clear()

    # ============ Statistics Tests ============

    def test_statistics_calculation_basic(self):
        """Test basic statistics calculation with valid data."""
        # Create submissions with scores: 95, 85, 75
        scores = [95, 85, 75]
        for i, score in enumerate(scores):
            submission = AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=self.student1 if i == 0 else (self.student2 if i == 1 else self.student3),
                content="Answer",
                status=AssignmentSubmission.Status.GRADED,
                score=score,
                max_score=100
            )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["sample_size"] == 3
        assert stats["mean"] == 85.0
        assert stats["median"] == 85.0
        assert stats["min"] == 75
        assert stats["max"] == 95
        assert stats["std_dev"] is not None

    def test_statistics_no_submissions(self):
        """Test statistics when no submissions exist."""
        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["sample_size"] == 0
        assert stats["mean"] is None
        assert stats["median"] is None
        assert stats["mode"] is None
        assert stats["std_dev"] is None
        assert stats["min"] is None
        assert stats["max"] is None

    def test_statistics_all_same_grade(self):
        """Test statistics when all submissions have same grade."""
        # All students score 80
        for student in [self.student1, self.student2, self.student3]:
            AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content="Answer",
                status=AssignmentSubmission.Status.GRADED,
                score=80,
                max_score=100
            )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["mean"] == 80.0
        assert stats["median"] == 80.0
        assert stats["mode"] == 80.0
        assert stats["min"] == 80
        assert stats["max"] == 80
        assert stats["std_dev"] == 0.0  # No variance

    def test_statistics_ungraded_submissions_ignored(self):
        """Test that ungraded submissions are not included in statistics."""
        # Create graded submission
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        # Create ungraded submission (should be ignored)
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Answer",
            status=AssignmentSubmission.Status.SUBMITTED,
            score=None,
            max_score=None
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["sample_size"] == 1
        assert stats["mean"] == 90.0

    def test_quartiles_calculation(self):
        """Test quartile calculation with sufficient data."""
        # Create 10 submissions with scores: 50, 60, 70, 80, 85, 90, 92, 94, 96, 100
        scores = [50, 60, 70, 80, 85, 90, 92, 94, 96, 100]
        users = [self.student1, self.student2, self.student3] + [
            User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="TestPass123!",
                role="student"
            ) for i in range(4, 10)
        ]

        for score, student in zip(scores, users):
            AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content="Answer",
                status=AssignmentSubmission.Status.GRADED,
                score=score,
                max_score=100
            )
            self.assignment.assigned_to.add(student)

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["q1"] is not None
        assert stats["q2"] is not None
        assert stats["q3"] is not None
        assert stats["q1"] < stats["q2"] < stats["q3"]

    # ============ Distribution Tests ============

    def test_grade_distribution_all_buckets(self):
        """Test grade distribution across all buckets."""
        # Create submissions covering all grade ranges
        test_cases = [
            (95, self.student1, "A"),  # 95% -> A (90-100)
            (85, self.student2, "B"),  # 85% -> B (80-89)
            (75, self.student3, "C"),  # 75% -> C (70-79)
        ]

        for score, student, expected_bucket in test_cases:
            AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content="Answer",
                status=AssignmentSubmission.Status.GRADED,
                score=score,
                max_score=100
            )

        analytics = GradeDistributionAnalytics(self.assignment)
        distribution = analytics._calculate_distribution()

        assert distribution["total"] == 3
        assert distribution["buckets"]["A"]["count"] == 1
        assert distribution["buckets"]["B"]["count"] == 1
        assert distribution["buckets"]["C"]["count"] == 1
        assert distribution["buckets"]["D"]["count"] == 0
        assert distribution["buckets"]["F"]["count"] == 0

    def test_grade_distribution_percentages(self):
        """Test that grade percentages are calculated correctly."""
        # Create 4 submissions: 2 A's, 1 B, 1 F
        users = [self.student1, self.student2, self.student3] + [
            User.objects.create_user(
                username="student4",
                email="student4@test.com",
                password="TestPass123!",
                role="student"
            )
        ]
        self.assignment.assigned_to.add(users[3])

        scores = [95, 92, 85, 40]  # 2 A's, 1 B, 1 F
        for score, student in zip(scores, users):
            AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=student,
                content="Answer",
                status=AssignmentSubmission.Status.GRADED,
                score=score,
                max_score=100
            )

        analytics = GradeDistributionAnalytics(self.assignment)
        distribution = analytics._calculate_distribution()

        assert distribution["buckets"]["A"]["percentage"] == 50.0
        assert distribution["buckets"]["B"]["percentage"] == 25.0
        assert distribution["buckets"]["F"]["percentage"] == 25.0

    def test_grade_distribution_pie_chart_data(self):
        """Test pie chart data excludes zero-count buckets."""
        # Create only A and B grades
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=95,
            max_score=100
        )

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        distribution = analytics._calculate_distribution()
        pie_data = distribution["pie_chart_data"]

        # Should only have A and B, not C, D, F
        assert len(pie_data) == 2
        labels = [item["label"] for item in pie_data]
        assert "A" in labels
        assert "B" in labels
        assert "C" not in labels

    def test_distribution_no_submissions(self):
        """Test distribution when no submissions exist."""
        analytics = GradeDistributionAnalytics(self.assignment)
        distribution = analytics._calculate_distribution()

        assert distribution["total"] == 0
        assert distribution["pie_chart_data"] == []
        for bucket in ["A", "B", "C", "D", "F"]:
            assert distribution["buckets"][bucket]["count"] == 0

    # ============ Submission Rate Tests ============

    def test_submission_rate_calculation(self):
        """Test submission rate metrics."""
        # 2 of 3 students submitted, 1 graded, 1 late
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100,
            is_late=False
        )

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Answer",
            status=AssignmentSubmission.Status.SUBMITTED,
            is_late=True
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        metrics = analytics._calculate_submission_rate()

        assert metrics["assigned_count"] == 3
        assert metrics["submitted_count"] == 2
        assert metrics["graded_count"] == 1
        assert metrics["late_count"] == 1
        assert metrics["submission_rate"] == pytest.approx(66.67, 0.01)
        assert metrics["grading_rate"] == 50.0
        assert metrics["late_rate"] == 50.0

    def test_submission_rate_no_assignments(self):
        """Test submission rate when assignment has no students assigned."""
        # Create empty assignment
        now = timezone.now()
        empty_assignment = Assignment.objects.create(
            title="Empty Assignment",
            description="No students assigned",
            instructions="Test instructions",
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )

        analytics = GradeDistributionAnalytics(empty_assignment)
        metrics = analytics._calculate_submission_rate()

        assert metrics["assigned_count"] == 0
        assert metrics["submitted_count"] == 0
        assert metrics["submission_rate"] == 0.0

    # ============ Class Average Tests ============

    def test_class_average_comparison(self):
        """Test class average calculation and comparison."""
        # Create submission for this assignment
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        # Create submission for other assignment by same teacher
        # Note: other_assignment is by other_teacher, so it won't be in class average
        now = timezone.now()
        same_teacher_assignment = Assignment.objects.create(
            title="Another Test",
            description="Test",
            instructions="Test instructions",
            author=self.teacher,  # Same author as self.assignment
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )

        AssignmentSubmission.objects.create(
            assignment=same_teacher_assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=80,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        comparison = analytics._calculate_class_average_comparison()

        assert comparison["assignment_average"] == 90.0
        assert comparison["class_average"] == 85.0  # (90 + 80) / 2 from same teacher
        assert comparison["difference"] == 5.0
        assert comparison["performance"] == "Above average"

    def test_class_average_below_average(self):
        """Test performance categorization when below average."""
        # Assignment average 70, class average 80 (from same teacher)
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=70,
            max_score=100
        )

        # Create another assignment by the same teacher with higher score
        now = timezone.now()
        same_teacher_assignment = Assignment.objects.create(
            title="Another Test",
            description="Test",
            instructions="Test instructions",
            author=self.teacher,  # Same author as self.assignment
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )

        AssignmentSubmission.objects.create(
            assignment=same_teacher_assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        comparison = analytics._calculate_class_average_comparison()

        assert comparison["difference"] == -20.0
        assert comparison["performance"] == "Below average"

    def test_class_average_no_submissions(self):
        """Test class average when no submissions exist."""
        analytics = GradeDistributionAnalytics(self.assignment)
        comparison = analytics._calculate_class_average_comparison()

        assert comparison["assignment_average"] is None
        assert comparison["assignment_count"] == 0
        assert comparison["performance"] == "No data"

    # ============ Cache Tests ============

    def test_caching_of_analytics(self):
        """Test that analytics are cached."""
        # Create submissions
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)

        # First call - should calculate
        result1 = analytics.get_analytics()

        # Second call - should use cache
        result2 = analytics.get_analytics()

        assert result1 == result2
        # Verify cache is set
        cache_key = f"assignment_analytics_{self.assignment.id}"
        assert cache.get(cache_key) is not None

    def test_cache_invalidation_on_grading(self):
        """Test that cache is invalidated when grading submission."""
        # Create submission
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.SUBMITTED
        )

        analytics = GradeDistributionAnalytics(self.assignment)

        # Get initial analytics (no grades)
        result1 = analytics.get_analytics()
        assert result1["statistics"]["sample_size"] == 0

        # Grade the submission
        submission.score = 90
        submission.max_score = 100
        submission.status = AssignmentSubmission.Status.GRADED
        submission.save()

        # Invalidate cache
        GradeDistributionAnalytics.invalidate_assignment_cache(self.assignment.id)

        # Get fresh analytics (should include new grade)
        analytics2 = GradeDistributionAnalytics(self.assignment)
        result2 = analytics2.get_analytics()
        assert result2["statistics"]["sample_size"] == 1

    def test_manual_cache_invalidation(self):
        """Test manual cache invalidation."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        analytics.get_analytics()

        # Verify cache exists
        cache_key = f"assignment_analytics_{self.assignment.id}"
        assert cache.get(cache_key) is not None

        # Invalidate
        analytics.invalidate_cache()

        # Verify cache is gone
        assert cache.get(cache_key) is None

    # ============ API Endpoint Tests ============

    def test_analytics_endpoint_success(self):
        """Test successful analytics endpoint call."""
        # Create submissions
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=95,
            max_score=100
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f"/api/assignments/assignments/{self.assignment.id}/analytics/")

        assert response.status_code == status.HTTP_200_OK
        assert "statistics" in response.data
        assert "distribution" in response.data
        assert "submission_rate" in response.data
        assert "comparison" in response.data
        assert response.data["statistics"]["sample_size"] == 1
        assert response.data["statistics"]["mean"] == 95.0

    def test_analytics_endpoint_forbidden_for_non_author(self):
        """Test that only assignment author can view analytics."""
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.get(f"/api/assignments/assignments/{self.assignment.id}/analytics/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "error" in response.data

    def test_analytics_endpoint_forbidden_for_student(self):
        """Test that students cannot view analytics."""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(f"/api/assignments/assignments/{self.assignment.id}/analytics/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_analytics_endpoint_requires_authentication(self):
        """Test that unauthenticated users cannot access analytics."""
        response = self.client.get(f"/api/assignments/assignments/{self.assignment.id}/analytics/")

        # Unauthenticated users get 403 (forbidden) because of permission check
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_analytics_endpoint_tutor_as_author(self):
        """Test that tutor author can view analytics."""
        # Create assignment with tutor as author
        now = timezone.now()
        tutor_assignment = Assignment.objects.create(
            title="Tutor Assignment",
            description="Assignment by tutor",
            instructions="Test instructions",
            author=self.tutor,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7)
        )
        tutor_assignment.assigned_to.set([self.student1])

        AssignmentSubmission.objects.create(
            assignment=tutor_assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100
        )

        self.client.force_authenticate(user=self.tutor)
        response = self.client.get(f"/api/assignments/assignments/{tutor_assignment.id}/analytics/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["statistics"]["mean"] == 85.0

    def test_analytics_endpoint_not_found(self):
        """Test analytics endpoint with non-existent assignment."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/assignments/assignments/9999/analytics/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============ Edge Cases ============

    def test_edge_case_single_submission(self):
        """Test analytics with single submission."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["sample_size"] == 1
        assert stats["mean"] == 85.0
        assert stats["median"] == 85.0
        assert stats["std_dev"] is None  # Cannot calculate with n=1

    def test_edge_case_two_submissions(self):
        """Test analytics with two submissions (minimum for std dev)."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=80,
            max_score=100
        )

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["std_dev"] is not None
        assert stats["std_dev"] == 7.07  # sqrt(50)

    def test_edge_case_extreme_scores(self):
        """Test analytics with extreme score values."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=0,
            max_score=100
        )

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=100,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        stats = analytics._calculate_statistics()

        assert stats["min"] == 0
        assert stats["max"] == 100
        assert stats["mean"] == 50.0
        assert stats["std_dev"] is not None

    def test_full_analytics_response_structure(self):
        """Test complete analytics response structure."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100
        )

        analytics = GradeDistributionAnalytics(self.assignment)
        result = analytics.get_analytics()

        # Verify all required fields
        assert "assignment_id" in result
        assert "assignment_title" in result
        assert "max_score" in result
        assert "statistics" in result
        assert "distribution" in result
        assert "submission_rate" in result
        assert "comparison" in result
        assert "generated_at" in result

        # Verify statistics structure
        stats = result["statistics"]
        assert "mean" in stats
        assert "median" in stats
        assert "mode" in stats
        assert "std_dev" in stats
        assert "min" in stats
        assert "max" in stats
        assert "q1" in stats
        assert "q2" in stats
        assert "q3" in stats
        assert "sample_size" in stats

        # Verify distribution structure
        dist = result["distribution"]
        assert "buckets" in dist
        assert "total" in dist
        assert "pie_chart_data" in dist

        # Verify submission rate structure
        sr = result["submission_rate"]
        assert "assigned_count" in sr
        assert "submitted_count" in sr
        assert "graded_count" in sr
        assert "late_count" in sr
        assert "submission_rate" in sr
        assert "grading_rate" in sr
        assert "late_rate" in sr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
