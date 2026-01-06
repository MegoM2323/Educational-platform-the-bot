"""
Tests for Prefetch optimization with filters (task_9_prefetch_with_filters)

Verifies that:
1. Prefetch with filters doesn't cause N+1 queries
2. Prefetch is applied AFTER filters
3. to_attr is used correctly to avoid conflicts
4. Serializers don't cause additional queries
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.db.models import Prefetch

from accounts.models import StudentProfile, ParentProfile

try:
    from accounts.tutor_views import TutorStudentsViewSet
    from accounts.tutor_serializers import TutorStudentSerializer
    from materials.models import Subject, SubjectEnrollment
except ImportError:
    TutorStudentsViewSet = None
    TutorStudentSerializer = None
    Subject = None
    SubjectEnrollment = None

User = get_user_model()


@pytest.mark.skipif(Subject is None, reason="materials.models not available")
@pytest.mark.django_db
class TestPrefetchWithFilters(TestCase):
    """Test that Prefetch with filters works correctly and doesn't cause N+1 queries"""

    def setUp(self):
        """Create test data with multiple students and enrollments"""
        if Subject is None or SubjectEnrollment is None:
            self.skipTest("materials.models not available")

        self.tutor = User.objects.create_user(
            username="tutor_prefetch",
            email="tutor@test.com",
            password="TestPass123!",
            role="tutor",
            is_active=True,
        )

        self.teacher = User.objects.create_user(
            username="teacher_prefetch",
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher",
            is_active=True,
        )

        self.parent = User.objects.create_user(
            username="parent_prefetch",
            email="parent@test.com",
            password="TestPass123!",
            role="parent",
            is_active=True,
        )
        ParentProfile.objects.get_or_create(user=self.parent)

        self.subjects = [
            Subject.objects.create(name="Math", description="Math course"),
            Subject.objects.create(name="English", description="English course"),
            Subject.objects.create(name="Physics", description="Physics course"),
        ]

        self.students = []
        for i in range(5):
            student_user = User.objects.create_user(
                username=f"student_prefetch_{i}",
                email=f"student_prefetch_{i}@test.com",
                password="TestPass123!",
                role="student",
                is_active=True,
                created_by_tutor=self.tutor,
            )

            student_profile = StudentProfile.objects.create(
                user=student_user,
                grade="10",
                goal="Get good grades",
                tutor=self.tutor,
                parent=self.parent,
            )
            self.students.append(student_profile)

            for j in range(2):
                SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=True,
                )

            for j in range(2, 3):
                SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=False,
                )

    def test_prefetch_after_filters_uses_to_attr(self):
        """
        Test that Prefetch with to_attr correctly stores filtered enrollments
        in a separate attribute without affecting the original queryset.
        """
        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True).select_related(
                "subject", "teacher"
            ),
            to_attr="active_enrollments",
        )

        students = (
            StudentProfile.objects.filter(tutor=self.tutor)
            .select_related("user", "tutor", "parent")
            .prefetch_related(enrollments_prefetch)
        )

        for student in students:
            assert hasattr(
                student.user, "active_enrollments"
            ), "User should have active_enrollments attribute"
            assert isinstance(
                student.user.active_enrollments, list
            ), "active_enrollments should be a list"
            assert all(
                e.is_active for e in student.user.active_enrollments
            ), "All enrollments in active_enrollments should be active"
            assert len(student.user.active_enrollments) == 2

    def test_tutor_viewset_list_query_count(self):
        """
        Test that TutorStudentsViewSet.list() doesn't have N+1 query problem
        when using Prefetch with filters.
        Expected: ~5-6 queries max (1 main + select_related joins + 1 prefetch)
        """
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/api/tutor/students/")
        request.user = self.tutor

        with CaptureQueriesContext(connection) as ctx:
            view = TutorStudentsViewSet.as_view({"get": "list"})
            response = view(request)

        assert response.status_code == 200
        assert len(ctx) <= 8, (
            f"Too many queries: {len(ctx)}. "
            f"Expected <= 8 (main query + joins + prefetch). "
            f"This indicates N+1 query problem or missing optimization."
        )

        assert (
            len(response.data) == 5
        ), f"Should return 5 students, got {len(response.data)}"

        for student_data in response.data:
            assert "subjects" in student_data
            assert len(student_data["subjects"]) == 2

    def test_serializer_uses_prefetched_data_no_extra_queries(self):
        """
        Test that TutorStudentSerializer uses prefetched data
        and doesn't make additional queries for enrollments.
        """
        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True).select_related(
                "subject", "teacher"
            ),
            to_attr="active_enrollments",
        )

        student = (
            StudentProfile.objects.filter(tutor=self.tutor)
            .select_related("user", "tutor", "parent")
            .prefetch_related(enrollments_prefetch)
            .first()
        )

        with CaptureQueriesContext(connection) as ctx:
            serializer = TutorStudentSerializer(student)
            data = serializer.data

        assert len(ctx) == 0, (
            f"Serializer made {len(ctx)} additional queries. "
            f"Should use prefetched data from active_enrollments attribute."
        )

        assert "subjects" in data
        assert isinstance(data["subjects"], list)
        assert len(data["subjects"]) == 2

    def test_prefetch_with_filter_and_order_by(self):
        """
        Test that Prefetch with both filter and order_by works correctly
        and doesn't interfere with subsequent filters.
        """
        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True)
            .select_related("subject", "teacher")
            .order_by("-enrolled_at", "-id"),
            to_attr="active_enrollments",
        )

        students = (
            StudentProfile.objects.filter(tutor=self.tutor)
            .select_related("user", "tutor", "parent")
            .prefetch_related(enrollments_prefetch)
            .order_by("-user__date_joined")
        )

        with CaptureQueriesContext(connection) as ctx:
            students_list = list(students)

        assert len(students_list) == 5
        for student in students_list:
            assert hasattr(student.user, "active_enrollments")
            if student.user.active_enrollments:
                assert student.user.active_enrollments[
                    0
                ].is_active, "Filtered enrollments should all be active"

    def test_prefetch_with_multiple_filters_on_main_queryset(self):
        """
        Test that Prefetch works correctly when applied AFTER multiple filters
        on the main queryset (tutor + is_active, etc).
        """
        from django.db.models import Q

        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True).select_related(
                "subject", "teacher"
            ),
            to_attr="active_enrollments",
        )

        students = (
            StudentProfile.objects.filter(
                Q(tutor=self.tutor) | Q(user__created_by_tutor=self.tutor),
                user__is_active=True,
            )
            .select_related("user", "tutor", "parent")
            .prefetch_related(enrollments_prefetch)
            .distinct()
        )

        with CaptureQueriesContext(connection) as ctx:
            students_list = list(students)

        assert len(students_list) == 5

        for student in students_list:
            assert hasattr(student.user, "active_enrollments")
            assert all(
                e.is_active for e in student.user.active_enrollments
            ), "Only active enrollments should be prefetched"

    def test_large_dataset_query_count_constant(self):
        """
        Test that query count stays constant regardless of dataset size.
        This is the key indicator that N+1 problem is solved.
        """
        for i in range(5, 15):
            student_user = User.objects.create_user(
                username=f"student_prefetch_{i}",
                email=f"student_prefetch_{i}@test.com",
                password="TestPass123!",
                role="student",
                is_active=True,
                created_by_tutor=self.tutor,
            )

            student_profile = StudentProfile.objects.create(
                user=student_user,
                grade="10",
                goal="Get good grades",
                tutor=self.tutor,
                parent=self.parent,
            )

            for j in range(2):
                SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=True,
                )

        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True).select_related(
                "subject", "teacher"
            ),
            to_attr="active_enrollments",
        )

        with CaptureQueriesContext(connection) as ctx:
            students = (
                StudentProfile.objects.filter(tutor=self.tutor)
                .select_related("user", "tutor", "parent")
                .prefetch_related(enrollments_prefetch)
            )
            students_list = list(students)

        assert len(ctx) <= 8, (
            f"Query count should stay constant. "
            f"Got {len(ctx)} queries for {len(students_list)} students. "
            f"Expected <= 8 regardless of student count."
        )

    def test_prefetch_caching_with_inactive_enrollments(self):
        """
        Test that Prefetch correctly filters out inactive enrollments
        even though they exist in the database.
        """
        student = StudentProfile.objects.filter(tutor=self.tutor).first()
        student_user = student.user

        assert (
            SubjectEnrollment.objects.filter(student=student_user).count() == 3
        ), "Should have 3 enrollments (2 active + 1 inactive)"

        enrollments_prefetch = Prefetch(
            "user__subject_enrollments",
            queryset=SubjectEnrollment.objects.filter(is_active=True).select_related(
                "subject", "teacher"
            ),
            to_attr="active_enrollments",
        )

        student = (
            StudentProfile.objects.filter(id=student.id)
            .select_related("user")
            .prefetch_related(enrollments_prefetch)
            .first()
        )

        assert len(student.user.active_enrollments) == 2
        assert all(
            e.is_active for e in student.user.active_enrollments
        ), "All prefetched enrollments should be active"
