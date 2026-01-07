"""
Tests for AvailableContactsView

This test suite verifies:
1. Teacher can get list of contacts even if student has no StudentProfile
2. Student can get list of contacts
3. Tutor can get list of contacts
4. Parent can get list of contacts
5. API returns proper response format with success flag
6. HTTP 500 errors are gracefully handled when StudentProfile is missing
"""

import pytest
import json
from uuid import uuid4
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from materials.models import Subject, SubjectEnrollment
from chat.models import ChatRoom, ChatParticipant
from accounts.models import StudentProfile, ParentProfile, TeacherProfile

User = get_user_model()


def get_contacts_from_response(data):
    """Helper to extract contacts list from API response (handles both 'results' and 'data' keys)"""
    if 'results' in data:
        return data['results']
    elif 'data' in data:
        return data['data']
    return None


def get_user_id_from_contact(contact):
    """Helper to extract user ID from contact (handles both nested and flat structures)"""
    if 'user' in contact:
        return contact['user']['id']
    elif 'user_id' in contact:
        return contact['user_id']
    elif 'id' in contact:
        return contact['id']
    return None


def get_user_role_from_contact(contact):
    """Helper to extract user role from contact"""
    if 'user' in contact:
        return contact['user'].get('role')
    return contact.get('role')


@pytest.mark.django_db(transaction=True)
class TestAvailableContactsViewWithMissingProfile:
    """Test teacher can get contacts even if student has no StudentProfile"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}"
        )

    @pytest.fixture
    def student_without_profile(self):
        """Student WITHOUT StudentProfile - edge case"""
        student = User.objects.create_user(
            username=f"student_no_profile_{uuid4().hex[:8]}",
            email=f"student_no_profile_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="student"
        )
        # Explicitly NOT creating StudentProfile
        return student

    @pytest.fixture
    def teacher(self):
        """Teacher user"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="teacher"
        )
        TeacherProfile.objects.create(user=teacher)
        return teacher

    def test_teacher_get_contacts_without_500_error(self, client, teacher, student_without_profile, subject):
        """Teacher should get HTTP 200 even if student has no StudentProfile"""
        # Create enrollment for student without profile
        SubjectEnrollment.objects.create(
            student=student_without_profile,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        # Login as teacher
        token, _ = Token.objects.get_or_create(user=teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # GET available contacts
        response = client.get('/api/chat/available-contacts/')

        # Should return 200 OK, not 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.content}"

        data = response.json()
        assert 'success' in data, "Response missing 'success' field"
        assert data['success'] is True, "Response 'success' should be True"
        contacts = get_contacts_from_response(data)
        assert contacts is not None, "Response missing contacts"
        assert isinstance(contacts, list), "Response contacts should be a list"

    def test_teacher_contacts_list_includes_student_without_profile(self, client, teacher, student_without_profile, subject):
        """Teacher's contact list should include student even without StudentProfile"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_without_profile,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        token, _ = Token.objects.get_or_create(user=teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        # Contact list should contain student
        contacts = get_contacts_from_response(data)
        student_ids = [get_user_id_from_contact(c) for c in contacts]
        assert student_without_profile.id in student_ids, "Student should be in teacher's contacts"

    def test_teacher_contacts_include_tutors_even_without_student_profile(self, client, teacher, student_without_profile, subject):
        """Teacher should see tutors of students even if StudentProfile is missing"""
        tutor = User.objects.create_user(
            username=f"tutor_{uuid4().hex[:8]}",
            email=f"tutor_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="tutor"
        )

        # Set created_by_tutor (fallback when StudentProfile is missing)
        student_without_profile.created_by_tutor = tutor
        student_without_profile.save()

        SubjectEnrollment.objects.create(
            student=student_without_profile,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        token, _ = Token.objects.get_or_create(user=teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        # Should include tutor as contact
        contacts = get_contacts_from_response(data)
        tutor_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'tutor']
        assert tutor.id in tutor_ids, "Tutor should be in teacher's contacts"


@pytest.mark.django_db(transaction=True)
class TestAvailableContactsStudentView:
    """Test student can get list of contacts"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}"
        )

    @pytest.fixture
    def student(self):
        """Student with profile"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="student"
        )
        StudentProfile.objects.create(user=student)
        return student

    @pytest.fixture
    def teacher(self):
        """Teacher user"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="teacher"
        )
        TeacherProfile.objects.create(user=teacher)
        return teacher

    @pytest.fixture
    def tutor(self):
        """Tutor assigned to student"""
        tutor = User.objects.create_user(
            username=f"tutor_{uuid4().hex[:8]}",
            email=f"tutor_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="tutor"
        )
        return tutor

    def test_student_get_contacts_returns_200(self, client, student):
        """Student should get HTTP 200 when fetching contacts"""
        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        assert response.status_code == 200

    def test_student_contacts_response_format(self, client, student):
        """Student contacts response should have correct format"""
        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        assert 'success' in data
        assert data['success'] is True
        contacts = get_contacts_from_response(data)
        assert contacts is not None
        assert isinstance(contacts, list)

    def test_student_contacts_include_enrolled_teachers(self, client, student, teacher, subject):
        """Student contacts should include enrolled teachers"""
        SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        teacher_ids = [get_user_id_from_contact(c) for c in contacts]
        assert teacher.id in teacher_ids, "Enrolled teacher should be in student's contacts"

    def test_student_contacts_include_assigned_tutor(self, client, student, tutor):
        """Student contacts should include assigned tutor"""
        # Assign tutor to student
        student_profile = student.student_profile
        student_profile.tutor = tutor
        student_profile.save()

        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        tutor_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'tutor']
        assert tutor.id in tutor_ids, "Assigned tutor should be in student's contacts"

    def test_student_contacts_exclude_non_enrolled_teachers(self, client, student):
        """Student should not see teachers they're not enrolled with"""
        # Create teacher but don't enroll student
        teacher = User.objects.create_user(
            username=f"unrelated_teacher_{uuid4().hex[:8]}",
            email=f"unrelated_teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="teacher"
        )

        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        teacher_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'teacher']
        assert teacher.id not in teacher_ids, "Non-enrolled teacher should not be in contacts"


@pytest.mark.django_db(transaction=True)
class TestAvailableContactsTutorView:
    """Test tutor can get list of contacts"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}"
        )

    @pytest.fixture
    def tutor(self):
        """Tutor user"""
        tutor = User.objects.create_user(
            username=f"tutor_{uuid4().hex[:8]}",
            email=f"tutor_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="tutor"
        )
        return tutor

    @pytest.fixture
    def student(self, tutor):
        """Student assigned to tutor"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="student"
        )
        StudentProfile.objects.create(user=student, tutor=tutor)
        return student

    @pytest.fixture
    def teacher(self):
        """Teacher user"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="teacher"
        )
        TeacherProfile.objects.create(user=teacher)
        return teacher

    def test_tutor_get_contacts_returns_200(self, client, tutor):
        """Tutor should get HTTP 200 when fetching contacts"""
        token, _ = Token.objects.get_or_create(user=tutor)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        assert response.status_code == 200

    def test_tutor_contacts_include_assigned_students(self, client, tutor, student):
        """Tutor contacts should include their assigned students"""
        token, _ = Token.objects.get_or_create(user=tutor)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        student_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'student']
        assert student.id in student_ids, "Assigned student should be in tutor's contacts"

    def test_tutor_contacts_include_teachers_of_students(self, client, tutor, student, teacher, subject):
        """Tutor contacts should include teachers of their students"""
        SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        token, _ = Token.objects.get_or_create(user=tutor)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        teacher_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'teacher']
        assert teacher.id in teacher_ids, "Teacher of tutor's student should be in contacts"


@pytest.mark.django_db(transaction=True)
class TestAvailableContactsParentView:
    """Test parent can get list of contacts"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def subject(self):
        return Subject.objects.create(
            name=f"Test Subject {uuid4().hex[:8]}"
        )

    @pytest.fixture
    def parent(self):
        """Parent user"""
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="parent"
        )
        ParentProfile.objects.create(user=parent)
        return parent

    @pytest.fixture
    def child(self, parent):
        """Child student of parent"""
        student = User.objects.create_user(
            username=f"child_{uuid4().hex[:8]}",
            email=f"child_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="student"
        )
        StudentProfile.objects.create(user=student, parent=parent)
        return student

    @pytest.fixture
    def teacher(self):
        """Teacher of child"""
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="teacher"
        )
        TeacherProfile.objects.create(user=teacher)
        return teacher

    def test_parent_get_contacts_returns_200(self, client, parent):
        """Parent should get HTTP 200 when fetching contacts"""
        token, _ = Token.objects.get_or_create(user=parent)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        assert response.status_code == 200

    def test_parent_contacts_include_child_teachers(self, client, parent, child, teacher, subject):
        """Parent contacts should include teachers of their children"""
        SubjectEnrollment.objects.create(
            student=child,
            teacher=teacher,
            subject=subject,
            is_active=True
        )

        token, _ = Token.objects.get_or_create(user=parent)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        data = response.json()

        contacts = get_contacts_from_response(data)
        teacher_ids = [get_user_id_from_contact(c) for c in contacts if get_user_role_from_contact(c) == 'teacher']
        assert teacher.id in teacher_ids, "Teacher of parent's child should be in contacts"


@pytest.mark.django_db(transaction=True)
class TestAvailableContactsErrorHandling:
    """Test error handling in available contacts view"""

    @pytest.fixture
    def client(self):
        return APIClient()

    def test_unauthenticated_request_returns_401(self, client):
        """Unauthenticated request should return 401 Unauthorized"""
        response = client.get('/api/chat/available-contacts/')
        assert response.status_code == 401

    @pytest.fixture
    def student(self):
        """Student user"""
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role="student"
        )
        StudentProfile.objects.create(user=student)
        return student

    def test_authenticated_user_with_empty_contacts(self, client, student):
        """User with no enrollments should return empty contacts list"""
        token, _ = Token.objects.get_or_create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/chat/available-contacts/')
        assert response.status_code == 200

        data = response.json()
        contacts = get_contacts_from_response(data)
        assert contacts is not None, f"Response missing contacts: {data}"
        assert isinstance(contacts, list)
        # Should be empty list
        assert len(contacts) == 0
