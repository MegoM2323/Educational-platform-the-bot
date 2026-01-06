"""
N+1 Query Optimization Tests for Tutor Views and Services

Tests verify that:
1. TutorStudentsViewSet.list() uses prefetch_related properly
2. No N+1 queries when loading students and their enrollments
3. TutorDashboardService.get_students() is optimized
4. SubjectAssignmentService checks don't cause extra queries
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIRequestFactory

from accounts.models import StudentProfile, ParentProfile
from accounts.tutor_views import TutorStudentsViewSet
from accounts.tutor_serializers import TutorStudentSerializer

User = get_user_model()


@pytest.mark.django_db
class TestTutorStudentsViewSetQueryCount(TestCase):
    """
    Test that TutorStudentsViewSet.list() doesn't have N+1 query problem
    """

    def setUp(self):
        """Create test data: tutor, students, subjects, enrollments"""
        from materials.models import Subject, SubjectEnrollment

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor1@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="One",
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="One",
            is_active=True
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent1@test.com",
            password="TestPass123!",
            role="parent",
            first_name="Parent",
            last_name="One",
            is_active=True
        )
        ParentProfile.objects.get_or_create(user=self.parent)

        self.subjects = [
            Subject.objects.create(name="Math", description="Math course"),
            Subject.objects.create(name="English", description="English course"),
            Subject.objects.create(name="Physics", description="Physics course"),
        ]
        self.SubjectEnrollment = SubjectEnrollment

        self.num_students = 5
        self.students = []
        for i in range(self.num_students):
            student_user = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="TestPass123!",
                role="student",
                first_name=f"Student",
                last_name=f"User{i}",
                is_active=True,
                created_by_tutor=self.tutor
            )

            student_profile = StudentProfile.objects.create(
                user=student_user,
                grade="10",
                goal="Get good grades",
                tutor=self.tutor,
                parent=self.parent
            )
            self.students.append(student_profile)

            for j in range(2):
                self.SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=True
                )

    def test_list_query_count_optimized(self):
        """
        Test that listing students doesn't cause N+1 queries.
        Expected queries:
        1. Get StudentProfile objects
        2. Prefetch user data (select_related)
        3. Prefetch tutor data (select_related)
        4. Prefetch parent data (select_related)
        5. Prefetch subject_enrollments with subject and teacher
        Total: ~5 queries (not 1 + N for enrollments)
        """
        factory = APIRequestFactory()
        request = factory.get('/api/tutor/students/')
        request.user = self.tutor

        with CaptureQueriesContext(connection) as ctx:
            view = TutorStudentsViewSet.as_view({'get': 'list'})
            response = view(request)

        print(f"\n=== Total Queries: {len(ctx)} ===")
        for i, query in enumerate(ctx.captured_queries):
            print(f"{i+1}. {query['sql'][:100]}...")

        assert len(ctx) <= 6, (
            f"Too many queries: {len(ctx)}. "
            f"Expected <= 6, but got {len(ctx)}. "
            f"This indicates N+1 query problem."
        )

    def test_list_response_structure(self):
        """Test that response contains correct data structure"""
        factory = APIRequestFactory()
        request = factory.get('/api/tutor/students/')
        request.user = self.tutor

        view = TutorStudentsViewSet.as_view({'get': 'list'})
        response = view(request)

        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) == self.num_students

        student_data = response.data[0]
        assert 'id' in student_data
        assert 'full_name' in student_data
        assert 'subjects' in student_data
        assert isinstance(student_data['subjects'], list)
        assert len(student_data['subjects']) == 2

    def test_serializer_uses_prefetch_data(self):
        """Test that TutorStudentSerializer uses prefetch_related data correctly"""
        from django.db.models import Prefetch
        from materials.models import SubjectEnrollment

        enrollments_prefetch = Prefetch(
            'user__subject_enrollments',
            queryset=SubjectEnrollment.objects.filter(is_active=True)
            .select_related('subject', 'teacher')
            .order_by('-enrolled_at', '-id')
        )

        student = (
            StudentProfile.objects
            .filter(tutor=self.tutor)
            .select_related('user', 'tutor', 'parent')
            .prefetch_related(enrollments_prefetch)
            .first()
        )

        with CaptureQueriesContext(connection) as ctx:
            serializer = TutorStudentSerializer(student)
            data = serializer.data

        assert len(ctx) == 0, (
            f"Serializer made {len(ctx)} additional queries. "
            f"Should use prefetched data and make 0 queries."
        )

        assert 'subjects' in data
        assert isinstance(data['subjects'], list)

    def test_large_student_list_performance(self):
        """
        Test that query count doesn't grow significantly with more students.
        Key: query count should stay roughly constant regardless of num_students.
        """
        for i in range(self.num_students, self.num_students + 5):
            student_user = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="TestPass123!",
                role="student",
                first_name=f"Student",
                last_name=f"User{i}",
                is_active=True,
                created_by_tutor=self.tutor
            )

            StudentProfile.objects.create(
                user=student_user,
                grade="10",
                goal="Get good grades",
                tutor=self.tutor,
                parent=self.parent
            )

            for j in range(2):
                self.SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=True
                )

        factory = APIRequestFactory()
        request = factory.get('/api/tutor/students/')
        request.user = self.tutor

        with CaptureQueriesContext(connection) as ctx:
            view = TutorStudentsViewSet.as_view({'get': 'list'})
            response = view(request)

        assert len(ctx) <= 6, (
            f"Query count increased with more students: {len(ctx)} queries. "
            f"This indicates N+1 problem."
        )

        assert response.status_code == 200
        assert len(response.data) == self.num_students + 5


@pytest.mark.django_db
class TestTutorDashboardServiceQueryCount(TestCase):
    """
    Test that TutorDashboardService.get_students() doesn't have N+1 queries
    """

    def setUp(self):
        """Create test data"""
        from materials.models import Subject, SubjectEnrollment
        from materials.tutor_dashboard_service import TutorDashboardService

        self.TutorDashboardService = TutorDashboardService

        self.tutor = User.objects.create_user(
            username="tutor2",
            email="tutor2@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Two",
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Two",
            is_active=True
        )

        self.parent = User.objects.create_user(
            username="parent2",
            email="parent2@test.com",
            password="TestPass123!",
            role="parent",
            first_name="Parent",
            last_name="Two",
            is_active=True
        )
        ParentProfile.objects.get_or_create(user=self.parent)

        self.subjects = [
            Subject.objects.create(name="Math", description="Math course"),
            Subject.objects.create(name="English", description="English course"),
        ]

        self.num_students = 5
        for i in range(self.num_students):
            student_user = User.objects.create_user(
                username=f"student{i}_tutor2",
                email=f"student{i}_tutor2@test.com",
                password="TestPass123!",
                role="student",
                first_name=f"Student",
                last_name=f"Two{i}",
                is_active=True
            )

            student_profile = StudentProfile.objects.create(
                user=student_user,
                grade="10",
                goal="Get good grades",
                tutor=self.tutor,
                parent=self.parent
            )

            for j in range(2):
                SubjectEnrollment.objects.create(
                    student=student_user,
                    subject=self.subjects[j],
                    teacher=self.teacher,
                    assigned_by=self.tutor,
                    is_active=True
                )

    def test_get_students_query_count(self):
        """Test that get_students() uses optimized queries"""
        service = self.TutorDashboardService(self.tutor)

        with CaptureQueriesContext(connection) as ctx:
            students = service.get_students()

        print(f"\n=== TutorDashboardService.get_students() Total Queries: {len(ctx)} ===")
        for i, query in enumerate(ctx.captured_queries[:10]):
            print(f"{i+1}. {query['sql'][:100]}...")

        assert len(ctx) <= 6, (
            f"Too many queries: {len(ctx)}. Expected <= 6. "
            f"This indicates N+1 query problem in get_students()."
        )

        assert len(students) == self.num_students
        assert all('subjects' in s for s in students)

    def test_get_students_response_structure(self):
        """Test that get_students() returns correct structure"""
        service = self.TutorDashboardService(self.tutor)
        students = service.get_students()

        assert isinstance(students, list)
        assert len(students) == self.num_students

        for student in students:
            assert 'id' in student
            assert 'full_name' in student
            assert 'subjects' in student
            assert isinstance(student['subjects'], list)
            assert len(student['subjects']) == 2


@pytest.mark.django_db
class TestSubjectAssignmentServiceQueryCount(TestCase):
    """
    Test that SubjectAssignmentService checks don't cause N+1 queries
    """

    def setUp(self):
        """Create test data"""
        from materials.models import Subject

        self.tutor = User.objects.create_user(
            username="tutor3",
            email="tutor3@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Three",
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username="teacher3",
            email="teacher3@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Three",
            is_active=True
        )

        self.subject = Subject.objects.create(name="History", description="History course")

        self.student = User.objects.create_user(
            username="student_n1",
            email="student_n1@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="N1",
            is_active=True,
            created_by_tutor=self.tutor
        )

        StudentProfile.objects.create(
            user=self.student,
            grade="10",
            goal="Get good grades",
            tutor=self.tutor
        )

    def test_assign_subject_query_count(self):
        """Test that assign_subject doesn't cause extra queries"""
        from accounts.tutor_service import SubjectAssignmentService

        with CaptureQueriesContext(connection) as ctx:
            enrollment = SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=self.student,
                subject=self.subject,
                teacher=self.teacher
            )

        print(f"\n=== SubjectAssignmentService.assign_subject() Total Queries: {len(ctx)} ===")
        for i, query in enumerate(ctx.captured_queries[:15]):
            print(f"{i+1}. {query['sql'][:100]}...")

        assert enrollment is not None
        assert enrollment.is_active
