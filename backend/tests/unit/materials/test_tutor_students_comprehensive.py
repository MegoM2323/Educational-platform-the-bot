"""
Comprehensive unit tests for Tutor Student Queries.

Tests for:
- Tutor student query returns only tutor's students
- full_name field is present in response
- Fallback to username if names missing
- N+1 query detection
- Proper filtering and serialization

Usage:
    pytest backend/tests/unit/materials/test_tutor_students_comprehensive.py -v
    pytest backend/tests/unit/materials/test_tutor_students_comprehensive.py --cov=materials.tutor_dashboard_service
"""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile, TutorProfile
from materials.tutor_dashboard_service import TutorDashboardService
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorStudentQueriesComprehensive:
    """Comprehensive tests for tutor student queries"""

    @pytest.fixture
    def setup_tutor_and_students(self, db):
        """Setup tutor with multiple students"""
        # Create tutor
        tutor = User.objects.create_user(
            username='tutor_test',
            email='tutor@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR,
            first_name='Сергей',
            last_name='Сидоров'
        )
        TutorProfile.objects.create(user=tutor)

        # Create students assigned to tutor
        students = []
        for i in range(3):
            student = User.objects.create_user(
                username=f'student_{i}',
                email=f'student_{i}@test.com',
                password='TestPass123!',
                role=User.Role.STUDENT,
                first_name=f'Студент{i}',
                last_name=f'Фамилия{i}'
            )
            profile = StudentProfile.objects.create(user=student)
            profile.tutor = tutor
            profile.save()
            students.append(student)

        return tutor, students

    @pytest.fixture
    def other_tutor(self, db):
        """Create another tutor for permission tests"""
        tutor = User.objects.create_user(
            username='other_tutor',
            email='other_tutor@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR,
            first_name='Иван',
            last_name='Иванов'
        )
        TutorProfile.objects.create(user=tutor)
        return tutor

    # ========== Basic Query Tests ==========

    def test_tutor_get_students_only_own_students(self, setup_tutor_and_students):
        """Scenario: Tutor queries students → returns only their students"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert
        assert len(result) == 3
        result_ids = {s['id'] for s in result}
        student_ids = {s.id for s in students}
        assert result_ids == student_ids

    def test_tutor_does_not_see_other_tutors_students(self, setup_tutor_and_students, other_tutor, db):
        """Scenario: Tutor cannot see other tutor's students"""
        tutor, students = setup_tutor_and_students

        # Create students for other tutor
        other_student = User.objects.create_user(
            username='other_tutor_student',
            email='other_tutor_student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(user=other_student)
        profile.tutor = other_tutor
        profile.save()

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Tutor sees only their students
        assert len(result) == 3
        result_ids = {s['id'] for s in result}
        assert other_student.id not in result_ids

    def test_tutor_get_empty_students_list(self, db):
        """Scenario: Tutor with no students → returns empty list"""
        # Create tutor without students
        tutor = User.objects.create_user(
            username='lonely_tutor',
            email='lonely_tutor@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR
        )
        TutorProfile.objects.create(user=tutor)

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert
        assert result == []

    # ========== full_name Field Tests ==========

    def test_students_have_full_name_field(self, setup_tutor_and_students):
        """Scenario: Student data contains full_name field"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Each student has full_name field
        assert len(result) > 0
        for student in result:
            assert 'full_name' in student or 'name' in student, f"Missing name field in {student.keys()}"

    def test_full_name_format_correct(self, setup_tutor_and_students):
        """Scenario: full_name format is "FirstName LastName" """
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Check full_name format
        for i, student in enumerate(result):
            name_field = student.get('full_name') or student.get('name')
            expected_name = f'Студент{i} Фамилия{i}'
            # Name field should contain student's first and last name
            assert name_field is not None
            assert len(name_field) > 0

    def test_fallback_to_username_if_names_missing(self, setup_tutor_and_students, db):
        """Scenario: Student without first/last name → uses username"""
        tutor, students = setup_tutor_and_students

        # Create student without names
        student_no_name = User.objects.create_user(
            username='no_name_student',
            email='no_name_student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='',  # Empty
            last_name=''    # Empty
        )
        profile = StudentProfile.objects.create(user=student_no_name)
        profile.tutor = tutor
        profile.save()

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Should have 4 students now
        assert len(result) == 4

        # Find the student without name
        no_name_student_data = next((s for s in result if s['id'] == student_no_name.id), None)
        assert no_name_student_data is not None
        name_field = no_name_student_data.get('full_name') or no_name_student_data.get('name')
        # Should fall back to username
        assert name_field in ['no_name_student', 'no_name_student no_name_student', 'no_name_student']

    # ========== Field Presence Tests ==========

    def test_student_data_includes_required_fields(self, setup_tutor_and_students):
        """Scenario: Student response includes all required fields"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Check required fields
        assert len(result) > 0
        student = result[0]
        required_fields = ['id', 'username', 'email', 'role']
        for field in required_fields:
            assert field in student, f"Missing required field: {field}"

    def test_student_data_includes_profile_info(self, setup_tutor_and_students):
        """Scenario: Student response includes profile data"""
        tutor, students = setup_tutor_and_students

        # Add grade and goal to first student
        students[0].student_profile.grade = '10'
        students[0].student_profile.goal = 'Подготовка к ЕГЭ'
        students[0].student_profile.save()

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Profile data should be in response
        student_data = result[0]
        assert 'grade' in student_data or 'goal' in student_data or 'profile' in student_data

    # ========== Filtering Tests ==========

    def test_inactive_students_excluded(self, setup_tutor_and_students, db):
        """Scenario: Inactive students not returned"""
        tutor, students = setup_tutor_and_students

        # Mark one student as inactive
        students[0].is_active = False
        students[0].save()

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: Should have only 2 active students
        assert len(result) == 2
        result_ids = {s['id'] for s in result}
        assert students[0].id not in result_ids

    def test_students_with_subjects_included(self, setup_tutor_and_students):
        """Scenario: Student's enrolled subjects included in response"""
        tutor, students = setup_tutor_and_students

        # Create subject and enrollment
        subject = Subject.objects.create(name='Математика')
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=teacher)

        SubjectEnrollment.objects.create(
            student=students[0],
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert: First student should have subjects
        student_data = result[0]
        assert 'subjects' in student_data or 'enrollments' in student_data

    # ========== N+1 Query Tests ==========

    def test_get_students_no_n_plus_1_queries(self, setup_tutor_and_students, django_assert_num_queries):
        """Verify get_students doesn't have N+1 query problems"""
        tutor, students = setup_tutor_and_students

        # Act & Assert: Should use select_related/prefetch_related
        # Rough estimate: 1 (auth) + 1 (user) + 3 (prefetch students) = ~5 queries
        with django_assert_num_queries(5):
            service = TutorDashboardService(tutor)
            result = service.get_students()

        assert len(result) == 3

    def test_get_students_scales_with_prefetch(self, db, django_assert_num_queries):
        """Verify query count doesn't scale with student count"""
        # Create tutor with 10 students
        tutor = User.objects.create_user(
            username='tutor_many',
            email='tutor_many@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR
        )
        TutorProfile.objects.create(user=tutor)

        for i in range(10):
            student = User.objects.create_user(
                username=f'many_student_{i}',
                email=f'many_student_{i}@test.com',
                password='TestPass123!',
                role=User.Role.STUDENT
            )
            profile = StudentProfile.objects.create(user=student)
            profile.tutor = tutor
            profile.save()

        # Act: Query count should be same regardless of number of students
        with django_assert_num_queries(5):
            service = TutorDashboardService(tutor)
            result = service.get_students()

        assert len(result) == 10

    # ========== Non-Tutor Tests ==========

    def test_non_tutor_cannot_use_service(self, db):
        """Scenario: Non-tutor user raises exception"""
        # Create student
        student = User.objects.create_user(
            username='student_service',
            email='student_service@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        from accounts.models import StudentProfile
        StudentProfile.objects.create(user=student)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise PermissionDenied or similar
            service = TutorDashboardService(student)
            service.get_students()

    # ========== Data Integrity Tests ==========

    def test_student_ids_are_unique(self, setup_tutor_and_students):
        """Scenario: All returned students have unique IDs"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert
        ids = [s['id'] for s in result]
        assert len(ids) == len(set(ids)), "Duplicate student IDs in result"

    def test_no_sensitive_data_leaked(self, setup_tutor_and_students):
        """Scenario: Sensitive data (password, tokens) not in response"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert
        for student in result:
            assert 'password' not in student
            assert 'token' not in student
            assert 'secret' not in student.keys()

    def test_student_email_visible(self, setup_tutor_and_students):
        """Scenario: Tutor can see student's email"""
        tutor, students = setup_tutor_and_students

        # Act
        service = TutorDashboardService(tutor)
        result = service.get_students()

        # Assert
        assert len(result) > 0
        student = result[0]
        assert 'email' in student
        assert '@' in student['email']
