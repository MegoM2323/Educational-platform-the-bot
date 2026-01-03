"""
Auth-related pytest fixtures for testing
"""
import pytest
from tests.factories import (
    StudentFactory, TeacherFactory, TutorFactory, ParentFactory,
    StudentProfileFactory, TeacherProfileFactory,
    TutorProfileFactory, ParentProfileFactory
)


# ========== USER FIXTURES ==========

@pytest.fixture
def student_user(db):
    """Create and return a student user"""
    return StudentFactory()


@pytest.fixture
def teacher_user(db):
    """Create and return a teacher user"""
    return TeacherFactory()


@pytest.fixture
def tutor_user(db):
    """Create and return a tutor user"""
    return TutorFactory()


@pytest.fixture
def parent_user(db):
    """Create and return a parent user"""
    return ParentFactory()


@pytest.fixture
def another_student_user(db):
    """Create and return another student user (for testing relationships)"""
    return StudentFactory()


@pytest.fixture
def another_teacher_user(db):
    """Create and return another teacher user"""
    return TeacherFactory()


# ========== PROFILE FIXTURES ==========

@pytest.fixture
def student_with_profile(db, student_user):
    """Create student with profile"""
    profile = StudentProfileFactory(user=student_user)
    return student_user, profile


@pytest.fixture
def teacher_with_profile(db, teacher_user):
    """Create teacher with profile"""
    profile = TeacherProfileFactory(user=teacher_user)
    return teacher_user, profile


@pytest.fixture
def tutor_with_profile(db, tutor_user):
    """Create tutor with profile"""
    profile = TutorProfileFactory(user=tutor_user)
    return tutor_user, profile


@pytest.fixture
def parent_with_profile(db, parent_user):
    """Create parent with profile"""
    profile = ParentProfileFactory(user=parent_user)
    return parent_user, profile


@pytest.fixture
def tutor_with_students(db, tutor_user):
    """Create tutor with assigned students"""
    tutor_profile = TutorProfileFactory(user=tutor_user)

    student1 = StudentFactory()
    student1_profile = StudentProfileFactory(user=student1, tutor=tutor_user)

    student2 = StudentFactory()
    student2_profile = StudentProfileFactory(user=student2, tutor=tutor_user)

    return tutor_user, [student1, student2]


@pytest.fixture
def parent_with_children(db, parent_user):
    """Create parent with children students"""
    parent_profile = ParentProfileFactory(user=parent_user)

    child1 = StudentFactory()
    child1_profile = StudentProfileFactory(user=child1, parent=parent_user)

    child2 = StudentFactory()
    child2_profile = StudentProfileFactory(user=child2, parent=parent_user)

    return parent_user, [child1, child2]


# ========== AUTHENTICATED CLIENT FIXTURES ==========

@pytest.fixture
def student_client(db, student_user):
    """Authenticated client for student"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=student_user)
    return client, student_user


@pytest.fixture
def teacher_client(db, teacher_user):
    """Authenticated client for teacher"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client, teacher_user


@pytest.fixture
def tutor_client(db, tutor_user):
    """Authenticated client for tutor"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=tutor_user)
    return client, tutor_user


@pytest.fixture
def parent_client(db, parent_user):
    """Authenticated client for parent"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=parent_user)
    return client, parent_user


@pytest.fixture
def anonymous_client():
    """Anonymous API client"""
    from rest_framework.test import APIClient
    return APIClient()
