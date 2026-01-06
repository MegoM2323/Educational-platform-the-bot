"""
Unit tests для assign_students_to_teacher logic

Тестирует бизнес-логику назначения студентов учителю через прямой вызов функции.
URL для этой функции не зарегистрирован, поэтому тестируем напрямую.
"""
import pytest
import json
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from accounts.staff_views import assign_students_to_teacher
from materials.models import SubjectEnrollment
from tests.factories import (
    StudentFactory,
    TeacherFactory,
    SubjectFactory,
    UserFactory,
)

User = get_user_model()

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def admin_user():
    user = UserFactory(
        username="admin",
        email="admin@example.com",
        role="ADMIN",
        is_staff=True,
        is_superuser=True,
    )
    user.set_password("admin123")
    user.save()
    return user


class TestAssignStudentsToTeacherSuccess:
    """Тесты успешного назначения"""

    def test_assign_single_student(self, api_factory, admin_user):
        """Назначение одного студента"""
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            f"/fake/url/",
            data=json.dumps(data),
            content_type="application/json",
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["assigned_students"] == [student.id]

        # Проверка создания SubjectEnrollment
        enrollment = SubjectEnrollment.objects.get(
            student=student, subject=subject, teacher=teacher
        )
        assert enrollment.is_active is True
        assert enrollment.assigned_by == admin_user

    def test_assign_multiple_students(self, api_factory, admin_user):
        """Назначение нескольких студентов"""
        teacher = TeacherFactory()
        students = [
            StudentFactory(username=f"s{i}", email=f"s{i}@test.com") for i in range(3)
        ]
        subject = SubjectFactory(name="Physics")

        student_ids = [s.id for s in students]
        data = {"student_ids": student_ids, "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["assigned_students"]) == set(student_ids)

        # Все enrollments созданы
        assert SubjectEnrollment.objects.filter(teacher=teacher, subject=subject).count() == 3

    def test_idempotent_update_existing_enrollment(self, api_factory, admin_user):
        """Повторное назначение обновляет enrollment"""
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Chemistry")

        # Создаем неактивный enrollment
        existing = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher, is_active=False
        )

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_200_OK

        # Только один enrollment
        assert SubjectEnrollment.objects.filter(
            student=student, subject=subject, teacher=teacher
        ).count() == 1

        # Обновился на активный
        existing.refresh_from_db()
        assert existing.is_active is True


class TestAssignStudentsValidation:
    """Тесты валидации"""

    def test_missing_student_ids(self, api_factory, admin_user):
        """Ошибка если student_ids не передан"""
        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        data = {"subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "student_ids должен быть непустым списком" in response.data["detail"]

    def test_missing_subject_id(self, api_factory, admin_user):
        """Ошибка если subject_id не передан"""
        teacher = TeacherFactory()
        student = StudentFactory()

        data = {"student_ids": [student.id]}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "subject_id обязателен" in response.data["detail"]

    def test_teacher_not_found(self, api_factory, admin_user):
        """Ошибка если учитель не найден"""
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, 99999)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Учитель не найден" in response.data["detail"]

    def test_subject_not_found(self, api_factory, admin_user):
        """Ошибка если предмет не найден"""
        teacher = TeacherFactory()
        student = StudentFactory()

        data = {"student_ids": [student.id], "subject_id": 99999}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Предмет не найден" in response.data["detail"]

    def test_students_not_found(self, api_factory, admin_user):
        """Ошибка если студенты не найдены"""
        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [99999, 99998], "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Студенты не найдены или неактивны" in response.data["detail"]


class TestAssignStudentsPermissions:
    """Тесты прав доступа"""

    def test_staff_can_assign(self, api_factory):
        """Staff может назначать"""
        staff_user = UserFactory(
            username="staff", email="staff@example.com", role="ADMIN", is_staff=True
        )
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=staff_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_forbidden(self, api_factory):
        """Regular user не может назначать"""
        regular_user = StudentFactory(username="student", email="student@example.com")
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            "/fake/", data=json.dumps(data), content_type="application/json"
        )
        force_authenticate(request, user=regular_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_403_FORBIDDEN
