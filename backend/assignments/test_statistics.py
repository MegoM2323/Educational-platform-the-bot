"""
T_ASN_005: Assignment Statistics Tests.

Comprehensive tests for assignment statistics endpoints:
- Overall statistics (T_ASN_005 main endpoint)
- Per-student breakdown
- Per-question difficulty analysis
- Time spent analysis

Features tested:
- Statistics calculation accuracy
- Caching (1-hour TTL)
- Cache invalidation on submission changes
- Permission enforcement (teachers/tutors only)
- Edge cases (no submissions, single submission)
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from assignments.models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer
from assignments.services.statistics import AssignmentStatisticsService

User = get_user_model()


class AssignmentStatisticsServiceTestCase(APITestCase):
    """Test suite for AssignmentStatisticsService."""

    def setUp(self):
        """Set up test data."""
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

        self.student3 = User.objects.create_user(
            username="student3",
            email="student3@test.com",
            password="TestPass123!",
            role="student"
        )

        # Create assignment
        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title="Statistics Test Assignment",
            description="Test statistics calculation",
            instructions="Complete the test",
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        self.assignment.assigned_to.set([self.student1, self.student2, self.student3])

        # Create questions
        self.question1 = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text="What is 2+2?",
            question_type=AssignmentQuestion.Type.SINGLE_CHOICE,
            points=25,
            order=1,
            options=["4", "5", "6"],
            correct_answer={"value": 0}
        )

        self.question2 = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text="What is 3+3?",
            question_type=AssignmentQuestion.Type.SINGLE_CHOICE,
            points=25,
            order=2,
            options=["6", "7", "8"],
            correct_answer={"value": 0}
        )

        # Create submissions with different scores
        self.submission1 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            content="My answers",
            status=AssignmentSubmission.Status.GRADED,
            score=90,
            max_score=100,
            submitted_at=now - timedelta(days=5),
            graded_at=now - timedelta(days=4),
        )

        self.submission2 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student2,
            content="My answers",
            status=AssignmentSubmission.Status.GRADED,
            score=75,
            max_score=100,
            submitted_at=now - timedelta(days=3),
            graded_at=now - timedelta(days=2),
        )

        self.submission3 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student3,
            content="My answers",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100,
            submitted_at=now + timedelta(days=10),  # Late submission
            graded_at=now + timedelta(days=11),
            is_late=True,
            days_late=3,
        )

        # Create answers for each submission
        # Student 1 answers (correct answers = score 90)
        AssignmentAnswer.objects.create(
            submission=self.submission1,
            question=self.question1,
            answer_choice=[0]
        )
        AssignmentAnswer.objects.create(
            submission=self.submission1,
            question=self.question2,
            answer_choice=[0]
        )

        # Student 2 answers (one wrong = score 75)
        AssignmentAnswer.objects.create(
            submission=self.submission2,
            question=self.question1,
            answer_choice=[0]
        )
        AssignmentAnswer.objects.create(
            submission=self.submission2,
            question=self.question2,
            answer_choice=[1]  # Wrong
        )

        # Student 3 answers (correct = score 85)
        AssignmentAnswer.objects.create(
            submission=self.submission3,
            question=self.question1,
            answer_choice=[0]
        )
        AssignmentAnswer.objects.create(
            submission=self.submission3,
            question=self.question2,
            answer_choice=[0]
        )

    def test_overall_statistics(self):
        """Test overall statistics calculation."""
        service = AssignmentStatisticsService(self.assignment)
        stats = service.get_overall_statistics()

        # Verify structure
        assert 'assignment_id' in stats
        assert 'statistics' in stats
        assert 'distribution' in stats
        assert 'submission_metrics' in stats
        assert 'performance_summary' in stats

        # Verify statistics values
        assert stats['statistics']['mean'] == 83.33
        assert stats['statistics']['median'] == 85
        assert stats['statistics']['min'] == 75
        assert stats['statistics']['max'] == 90
        assert stats['statistics']['sample_size'] == 3

        # Verify submission metrics
        assert stats['submission_metrics']['total_submissions'] == 3
        assert stats['submission_metrics']['graded_submissions'] == 3
        assert stats['submission_metrics']['late_submissions'] == 1
        assert stats['submission_metrics']['assigned_count'] == 3

    def test_student_breakdown(self):
        """Test per-student breakdown."""
        service = AssignmentStatisticsService(self.assignment)
        stats = service.get_student_breakdown()

        # Verify structure
        assert 'students' in stats
        assert 'class_metrics' in stats
        assert 'performance_tiers' in stats

        # Verify student list is sorted by score (descending)
        assert len(stats['students']) == 3
        assert stats['students'][0]['score'] == 90
        assert stats['students'][1]['score'] == 85
        assert stats['students'][2]['score'] == 75

        # Verify performance tiers
        assert stats['performance_tiers']['excellent']['count'] == 1
        assert stats['performance_tiers']['good']['count'] == 1  # 85% = good
        assert stats['performance_tiers']['satisfactory']['count'] == 1  # 75% = satisfactory

    def test_question_analysis(self):
        """Test per-question difficulty analysis."""
        service = AssignmentStatisticsService(self.assignment)
        stats = service.get_question_analysis()

        # Verify structure
        assert 'questions' in stats
        assert 'difficulty_ranking' in stats
        assert 'average_difficulty' in stats
        assert 'common_errors' in stats

        # Verify questions
        assert len(stats['questions']) == 2

        # Question 1: All correct (0% difficulty)
        q1 = next(q for q in stats['questions'] if q['question_id'] == self.question1.id)
        assert q1['correct_answers'] == 3
        assert q1['wrong_answers'] == 0
        assert q1['correct_rate'] == 100.0
        assert q1['difficulty_score'] == 0.0

        # Question 2: One wrong (33% difficulty)
        q2 = next(q for q in stats['questions'] if q['question_id'] == self.question2.id)
        assert q2['correct_answers'] == 2
        assert q2['wrong_answers'] == 1
        assert q2['correct_rate'] == 66.67
        assert q2['difficulty_score'] == 33.33

    def test_time_analysis(self):
        """Test time spent analysis."""
        service = AssignmentStatisticsService(self.assignment)
        stats = service.get_time_analysis()

        # Verify structure
        assert 'submission_timing' in stats
        assert 'grading_speed' in stats
        assert 'late_submissions' in stats
        assert 'response_times' in stats

        # Verify submission timing
        timing = stats['submission_timing']
        assert timing['on_time_submissions'] == 2
        assert timing['late_submissions'] == 1
        assert timing['total_submissions'] == 3

        # Verify grading speed
        grading = stats['grading_speed']
        assert grading['total_graded'] == 3
        assert grading['average_time_to_grade_hours'] is not None
        assert grading['average_time_to_grade_days'] is not None

        # Verify late submissions
        late = stats['late_submissions']
        assert late['late_submission_count'] == 1
        assert late['late_submission_rate'] == 33.33

    def test_caching(self):
        """Test that statistics are cached."""
        service = AssignmentStatisticsService(self.assignment)

        # First call - should calculate and cache
        cache.clear()
        stats1 = service.get_overall_statistics()

        # Second call - should be cached
        stats2 = service.get_overall_statistics()

        assert stats1 == stats2

        # Verify cache key exists
        cache_key = f"assignment_stats_{self.assignment.id}_overall"
        cached = cache.get(cache_key)
        assert cached is not None

    def test_cache_invalidation(self):
        """Test that cache is invalidated on submission changes."""
        service = AssignmentStatisticsService(self.assignment)
        cache.clear()

        # Get initial stats
        stats1 = service.get_overall_statistics()
        mean1 = stats1['statistics']['mean']

        # Add new submission
        new_student = User.objects.create_user(
            username="student4",
            email="student4@test.com",
            password="TestPass123!",
            role="student"
        )

        new_submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=new_student,
            content="New answer",
            status=AssignmentSubmission.Status.GRADED,
            score=100,
            max_score=100,
        )

        # Cache should be invalidated, new stats should reflect new submission
        stats2 = service.get_overall_statistics()
        mean2 = stats2['statistics']['mean']

        # Mean should increase with the new 100 score
        assert mean2 > mean1

    def test_edge_case_no_submissions(self):
        """Test statistics with no submissions."""
        # Create new assignment with no submissions
        new_assignment = Assignment.objects.create(
            title="Empty Assignment",
            description="No submissions",
            instructions="Test",
            author=self.teacher,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
        )

        service = AssignmentStatisticsService(new_assignment)
        stats = service.get_overall_statistics()

        # Verify null values for statistics
        assert stats['statistics']['mean'] is None
        assert stats['statistics']['median'] is None
        assert stats['statistics']['sample_size'] == 0


class AssignmentStatisticsAPITestCase(APITestCase):
    """Test suite for statistics API endpoints."""

    def setUp(self):
        """Set up test data."""
        cache.clear()
        self.client = APIClient()

        # Create users
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.other_teacher = User.objects.create_user(
            username="other_teacher",
            email="other_teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        # Create assignment
        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title="API Test Assignment",
            description="Test API endpoints",
            instructions="Complete the test",
            author=self.teacher,
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=7),
        )

        self.assignment.assigned_to.add(self.student)

        # Create submission
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content="My answer",
            status=AssignmentSubmission.Status.GRADED,
            score=85,
            max_score=100,
        )

    def test_statistics_endpoint_permission_denied_student(self):
        """Test that students cannot view statistics."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_statistics_endpoint_permission_denied_other_teacher(self):
        """Test that other teachers cannot view statistics."""
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_statistics_endpoint_success(self):
        """Test successful statistics endpoint call."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'assignment_id' in data
        assert 'statistics' in data
        assert data['assignment_id'] == self.assignment.id

    def test_statistics_by_student_endpoint(self):
        """Test per-student statistics endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics_by_student/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'students' in data
        assert 'performance_tiers' in data
        assert len(data['students']) >= 1

    def test_statistics_by_question_endpoint(self):
        """Test per-question statistics endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics_by_question/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'questions' in data
        assert 'difficulty_ranking' in data

    def test_statistics_time_analysis_endpoint(self):
        """Test time analysis endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics_time_analysis/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'submission_timing' in data
        assert 'grading_speed' in data
        assert 'late_submissions' in data

    def test_statistics_endpoint_not_authenticated(self):
        """Test that unauthenticated users cannot access statistics."""
        response = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_statistics_endpoint_not_found(self):
        """Test statistics endpoint with non-existent assignment."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/assignments/99999/statistics/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cache_hit_rate_caching(self):
        """Test that subsequent calls use cache."""
        self.client.force_authenticate(user=self.teacher)

        # First call
        response1 = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')
        assert response1.status_code == status.HTTP_200_OK

        # Second call should be from cache
        response2 = self.client.get(f'/api/assignments/{self.assignment.id}/statistics/')
        assert response2.status_code == status.HTTP_200_OK

        # Data should be identical (from cache)
        assert response1.json() == response2.json()
