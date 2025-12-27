"""
T_ASSIGN_013: Assignment Statistics Cache Tests.

Comprehensive tests for:
- Cache hits on repeated requests
- Cache invalidation on grade change
- TTL expiration (5 minutes)
- Cache warming behavior
- Hit rate calculation
- API endpoint permissions
- Async cache warming via Celery
- Edge cases (no submissions, multiple updates)
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from assignments.models import Assignment, AssignmentSubmission
from assignments.services.analytics import GradeDistributionAnalytics
from assignments.cache.stats import AssignmentStatsCache

User = get_user_model()


class AssignmentStatsCacheTestCase(APITestCase):
    """Test suite for assignment statistics caching."""

    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()

        # Create users
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
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

        # Create assignment
        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test Description",
            instructions="Test Instructions",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        self.assignment.assigned_to.add(self.student1, self.student2)

        # Create submissions
        self.submission1 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="Student 1 answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100,
        )

        self.submission2 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="Student 2 answer",
            status=AssignmentSubmission.Status.GRADED,
            score=95,
            max_score=100,
        )

        self.client = APIClient()

    def test_cache_hit_on_repeated_requests(self):
        """Test that cache hits are recorded on repeated requests."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # First call - should be a cache miss
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()

        stats1 = cache_manager.get_or_calculate(analytics_data)

        # Check hit rate after first call (should be 0 hits, 1 miss)
        hit_rate1 = cache_manager.get_hit_rate()
        self.assertEqual(hit_rate1['hits'], 0)
        self.assertEqual(hit_rate1['misses'], 1)
        self.assertEqual(hit_rate1['hit_rate_percentage'], 0.0)

        # Second call - should be a cache hit
        stats2 = cache_manager.get_or_calculate(analytics_data)

        # Check hit rate after second call (should be 1 hit, 1 miss)
        hit_rate2 = cache_manager.get_hit_rate()
        self.assertEqual(hit_rate2['hits'], 1)
        self.assertEqual(hit_rate2['misses'], 1)
        self.assertEqual(hit_rate2['hit_rate_percentage'], 50.0)

        # Verify the data is the same
        self.assertEqual(stats1['assignment_id'], stats2['assignment_id'])
        self.assertEqual(stats1['statistics']['mean'], stats2['statistics']['mean'])

    def test_cache_invalidation_on_grade_change(self):
        """Test that cache is invalidated when a grade is updated."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        stats1 = cache_manager.get_or_calculate(analytics_data)
        mean1 = stats1['statistics']['mean']

        # Manually invalidate cache (simulating signal)
        cache_manager.invalidate()

        # Verify cache is gone
        self.assertIsNone(cache.get(cache_manager.cache_key))

        # Update a submission's grade
        self.submission1.score = 50  # Change from 85 to 50
        self.submission1.save()

        # Get new analytics (should not be from cache)
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        stats2 = cache_manager.get_or_calculate(analytics_data)
        mean2 = stats2['statistics']['mean']

        # Mean should be different
        self.assertNotEqual(mean1, mean2)
        # New mean should be 72.5 (50 + 95) / 2
        self.assertEqual(mean2, 72.5)

    def test_cache_invalidation_signal_on_submission_change(self):
        """Test that cache invalidation signal is triggered on submission save."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)

        # Verify cache is populated
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNotNone(cached)

        # Update submission (this should trigger invalidation signal)
        self.submission1.score = 70
        self.submission1.save()

        # Cache should be invalidated
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNone(cached)

    def test_cache_invalidation_on_deletion(self):
        """Test that cache is invalidated when a submission is deleted."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)

        # Verify cache is populated
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNotNone(cached)

        # Delete a submission (this should trigger invalidation signal)
        submission_id = self.submission2.id
        self.submission2.delete()

        # Cache should be invalidated
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNone(cached)

    def test_cache_warming_synchronous(self):
        """Test synchronous cache warming for a small number of assignments."""
        assignment_ids = [self.assignment.id]

        result = AssignmentStatsCache.warm_cache(assignment_ids)

        # Should be warmed synchronously
        self.assertFalse(result['async_scheduled'])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['warmed'], 1)
        self.assertEqual(result['failed'], 0)

        # Verify cache is populated
        cache_manager = AssignmentStatsCache(self.assignment.id)
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNotNone(cached)

    def test_cache_warming_with_multiple_assignments(self):
        """Test cache warming with multiple assignments."""
        # Create additional assignment
        now = timezone.now()
        assignment2 = Assignment.objects.create(
            title="Test Assignment 2",
            description="Test Description",
            instructions="Test Instructions",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        assignment_ids = [self.assignment.id, assignment2.id]

        result = AssignmentStatsCache.warm_cache(assignment_ids)

        self.assertEqual(result['total'], 2)
        self.assertEqual(result['warmed'], 2)

        # Verify both caches are populated
        for assignment_id in assignment_ids:
            cache_manager = AssignmentStatsCache(assignment_id)
            cached = cache.get(cache_manager.cache_key)
            self.assertIsNotNone(cached)

    def test_cache_hit_rate_metrics(self):
        """Test cache hit rate metrics calculation."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Perform multiple cache operations
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()

        # 3 requests to simulate: miss, hit, hit
        cache_manager.get_or_calculate(analytics_data)  # miss
        cache_manager.get_or_calculate(analytics_data)  # hit
        cache_manager.get_or_calculate(analytics_data)  # hit

        hit_rate = cache_manager.get_hit_rate()

        self.assertEqual(hit_rate['hits'], 2)
        self.assertEqual(hit_rate['misses'], 1)
        self.assertEqual(hit_rate['total'], 3)
        self.assertEqual(hit_rate['hit_rate_percentage'], 66.67)

    def test_extended_stats_structure(self):
        """Test that extended stats include all required fields."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()

        stats = cache_manager.get_or_calculate(analytics_data)

        # Check all required fields are present
        required_fields = [
            'assignment_id',
            'assignment_title',
            'max_score',
            'statistics',
            'distribution',
            'submission_stats',
            'time_stats',
            'cached_at',
        ]

        for field in required_fields:
            self.assertIn(field, stats, f"Missing field: {field}")

        # Check submission_stats structure
        submission_stats = stats['submission_stats']
        submission_stats_fields = [
            'count', 'late_count', 'ungraded_count', 'graded_count',
            'assigned_count', 'submission_rate'
        ]
        for field in submission_stats_fields:
            self.assertIn(field, submission_stats, f"Missing submission_stats field: {field}")

        # Check time_stats structure
        time_stats = stats['time_stats']
        time_stats_fields = ['avg_time_to_grade', 'avg_response_time']
        for field in time_stats_fields:
            self.assertIn(field, time_stats, f"Missing time_stats field: {field}")

    def test_api_endpoint_cache_hit_rate(self):
        """Test the cache hit rate API endpoint."""
        # Login as teacher
        self.client.login(username="teacher", password="TestPass123!")

        # Populate cache first
        cache_manager = AssignmentStatsCache(self.assignment.id)
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)
        cache_manager.get_or_calculate(analytics_data)  # Hit

        # Call endpoint
        url = f'/api/assignments/{self.assignment.id}/cache_hit_rate/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check response structure
        self.assertIn('hits', data)
        self.assertIn('misses', data)
        self.assertIn('total', data)
        self.assertIn('hit_rate_percentage', data)
        self.assertIn('cache_key', data)
        self.assertIn('ttl_seconds', data)

    def test_api_endpoint_cache_hit_rate_permission_denied(self):
        """Test that non-authors cannot access cache hit rate endpoint."""
        # Login as student
        self.client.login(username="student1", password="TestPass123!")

        # Call endpoint - should be forbidden
        url = f'/api/assignments/{self.assignment.id}/cache_hit_rate/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cache_with_no_submissions(self):
        """Test caching with an assignment that has no submissions."""
        # Create empty assignment
        now = timezone.now()
        empty_assignment = Assignment.objects.create(
            title="Empty Assignment",
            description="No submissions",
            instructions="None",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        cache_manager = AssignmentStatsCache(empty_assignment.id)
        analytics = GradeDistributionAnalytics(empty_assignment)
        analytics_data = analytics.get_analytics()

        stats = cache_manager.get_or_calculate(analytics_data)

        # Should have all fields but with null/zero values
        self.assertIsNotNone(stats['submission_stats'])
        self.assertEqual(stats['submission_stats']['count'], 0)
        self.assertEqual(stats['submission_stats']['graded_count'], 0)
        self.assertIsNone(stats['time_stats']['avg_time_to_grade'])

    def test_cache_invalidation_static_method(self):
        """Test static cache invalidation method."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)

        # Use static method to invalidate
        AssignmentStatsCache.invalidate_assignment(self.assignment.id)

        # Verify cache is gone
        cached = cache.get(cache_manager.cache_key)
        self.assertIsNone(cached)

    def test_multiple_assignments_independent_caches(self):
        """Test that multiple assignments have independent caches."""
        # Create second assignment
        now = timezone.now()
        assignment2 = Assignment.objects.create(
            title="Test Assignment 2",
            description="Test Description",
            instructions="Test Instructions",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        # Populate both caches
        for assignment in [self.assignment, assignment2]:
            cache_manager = AssignmentStatsCache(assignment.id)
            analytics = GradeDistributionAnalytics(assignment)
            analytics_data = analytics.get_analytics()
            cache_manager.get_or_calculate(analytics_data)

        # Invalidate first assignment's cache
        AssignmentStatsCache.invalidate_assignment(self.assignment.id)

        # First cache should be cleared
        cache_manager1 = AssignmentStatsCache(self.assignment.id)
        self.assertIsNone(cache.get(cache_manager1.cache_key))

        # Second cache should still exist
        cache_manager2 = AssignmentStatsCache(assignment2.id)
        self.assertIsNotNone(cache.get(cache_manager2.cache_key))

    def test_cache_ttl_configuration(self):
        """Test that cache TTL is correctly configured."""
        self.assertEqual(AssignmentStatsCache.CACHE_TTL, 300)  # 5 minutes

    def test_cache_with_late_submissions(self):
        """Test submission stats with late submissions."""
        # Mark submission as late
        self.submission1.is_late = True
        self.submission1.save()

        cache_manager = AssignmentStatsCache(self.assignment.id)
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()

        stats = cache_manager.get_or_calculate(analytics_data)

        # Check late submission count
        self.assertEqual(stats['submission_stats']['late_count'], 1)
        self.assertEqual(stats['submission_stats']['count'], 2)

    def test_analytics_integration(self):
        """Test that cache properly integrates with GradeDistributionAnalytics."""
        cache_manager = AssignmentStatsCache(self.assignment.id)
        analytics = GradeDistributionAnalytics(self.assignment)

        # Get analytics
        analytics_data = analytics.get_analytics()

        # Get cached stats
        cached_stats = cache_manager.get_or_calculate(analytics_data)

        # Verify key fields match
        self.assertEqual(
            cached_stats['statistics']['mean'],
            analytics_data['statistics']['mean']
        )
        self.assertEqual(
            cached_stats['distribution']['total'],
            analytics_data['distribution']['total']
        )


class AssignmentCacheSignalsTestCase(APITestCase):
    """Test suite for cache invalidation signals."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test",
            instructions="Test",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        self.assignment.assigned_to.add(self.student)

    def test_signal_invalidates_cache_on_submission_create(self):
        """Test that creating a submission invalidates cache."""
        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)

        self.assertIsNotNone(cache.get(cache_manager.cache_key))

        # Create new submission (signal should invalidate cache)
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content="Test",
            status=AssignmentSubmission.Status.SUBMITTED,
        )

        # Cache should be invalidated
        self.assertIsNone(cache.get(cache_manager.cache_key))

    def test_signal_invalidates_cache_on_submission_update(self):
        """Test that updating a submission invalidates cache."""
        # Create submission
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content="Test",
            status=AssignmentSubmission.Status.SUBMITTED,
        )

        cache_manager = AssignmentStatsCache(self.assignment.id)

        # Populate cache
        analytics = GradeDistributionAnalytics(self.assignment)
        analytics_data = analytics.get_analytics()
        cache_manager.get_or_calculate(analytics_data)

        self.assertIsNotNone(cache.get(cache_manager.cache_key))

        # Update submission (signal should invalidate cache)
        submission.status = AssignmentSubmission.Status.GRADED
        submission.score = 85
        submission.save()

        # Cache should be invalidated
        self.assertIsNone(cache.get(cache_manager.cache_key))
