"""
Unit tests для assign_students_to_teacher function

ЗАМЕТКА: Функция assign_students_to_teacher существует в staff_views.py но НЕ зарегистрирована в urls.py.
Тесты проверяют логику напрямую через вызов view function, а не через HTTP endpoint.

Проверяет:
1. Успешное назначение студентов учителю на предмет
2. Валидация входных данных (teacher, students, subject)
3. Permissions (IsStaffOrAdmin)
4. Error responses (400, 404)
5. Создание SubjectEnrollment
6. Идемпотентность (update_or_create)
"""
import pytest
import json
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status

from accounts.models import StudentProfile
from accounts.staff_views import assign_students_to_teacher
from materials.models import Subject, SubjectEnrollment
from accounts.factories import (
    StudentFactory,
    TeacherFactory,
    UserFactory,
)
from accounts.factories import StudentProfileFactory, TeacherProfileFactory
from materials.factories import SubjectFactory

User = get_user_model()

pytestmark = pytest.mark.unit


@pytest.fixture
def api_factory():
    """API request factory for direct view testing."""
    return APIRequestFactory()


@pytest.fixture
def admin_user():
    """Admin user for permission tests."""
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


@pytest.fixture
def staff_user():
    """Staff user for permission tests."""
    user = UserFactory(
        username="staff",
        email="staff@example.com",
        role="ADMIN",
        is_staff=True,
        is_superuser=False,
    )
    user.set_password("staff123")
    user.save()
    return user


@pytest.fixture
def regular_user():
    """Regular student user."""
    user = StudentFactory(username="student", email="student@example.com")
    user.set_password("student123")
    user.save()
    return user


@pytest.mark.django_db
class TestAssignStudentsToTeacherSuccess:
    """Тесты успешного назначения студентов учителю"""

    def test_assign_single_student_to_teacher(self, api_factory, admin_user):
        """Назначение одного студента учителю на предмет"""
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        data = {"student_ids": [student.id], "subject_id": subject.id}
        request = api_factory.post(
            f"/api/staff/teachers/{teacher.id}/assign-students/",
            data=json.dumps(data),
            content_type="application/json",
        )
        force_authenticate(request, user=admin_user)

        response = assign_students_to_teacher(request, teacher.id)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.data
        assert response_data["success"] is True
        assert response_data["assigned_students"] == [student.id]
        assert len(response_data["assigned_students"]) == 1
        assert "студентов успешно назначено учителю" in response_data["message"]

        # Проверка создания SubjectEnrollment
        enrollment = SubjectEnrollment.objects.filter(
            student=student, subject=subject, teacher=teacher
        ).first()
        assert enrollment is not None
        assert enrollment.is_active is True
        assert enrollment.assigned_by == admin_user

    def test_assign_multiple_students_to_teacher(self, api_factory, admin_user):
        """Назначение нескольких студентов учителю на предмет"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        students = []
        for i in range(3):
            student = StudentFactory(username=f"student{i}", email=f"student{i}@test.com")
            students.append(student)

        subject = SubjectFactory(name="Physics")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        student_ids = [s.id for s in students]
        data = {"student_ids": student_ids, "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["assigned_students"]) == 3
        assert set(response.data["assigned_students"]) == set(student_ids)

        # Проверка создания всех enrollments
        enrollments = SubjectEnrollment.objects.filter(
            teacher=teacher, subject=subject, is_active=True
        )
        assert enrollments.count() == 3

    def test_assign_students_idempotent(self, api_factory, admin_user):
        """Повторное назначение (update_or_create) не создает дубликатов"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Chemistry")

        # Создаем существующий enrollment
        existing_enrollment = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher, is_active=False
        )

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        # Проверка что enrollment обновился, а не создался новый
        enrollments = SubjectEnrollment.objects.filter(
            student=student, subject=subject, teacher=teacher
        )
        assert enrollments.count() == 1

        enrollment = enrollments.first()
        assert enrollment.id == existing_enrollment.id  # Тот же объект
        assert enrollment.is_active is True  # Обновился
        assert enrollment.assigned_by == admin_user


@pytest.mark.django_db
class TestAssignStudentsToTeacherValidation:
    """Тесты валидации входных данных"""

    def test_missing_student_ids(self, api_factory, admin_user):
        """Ошибка если student_ids не передан"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "student_ids должен быть непустым списком" in response.data["detail"]

    def test_empty_student_ids(self, api_factory, admin_user):
        """Ошибка если student_ids пустой список"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "student_ids должен быть непустым списком" in response.data["detail"]

    def test_missing_subject_id(self, api_factory, admin_user):
        """Ошибка если subject_id не передан"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id]}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "subject_id обязателен" in response.data["detail"]

    def test_teacher_not_found(self, api_factory, admin_user):
        """Ошибка если учитель не найден"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = "/api/staff/teachers/99999/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Учитель не найден" in response.data["detail"]

    def test_subject_not_found(self, api_factory, admin_user):
        """Ошибка если предмет не найден"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": 99999}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Предмет не найден" in response.data["detail"]

    def test_students_not_found(self, api_factory, admin_user):
        """Ошибка если студенты не найдены"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [99999, 99998], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Студенты не найдены или неактивны" in response.data["detail"]

    def test_inactive_student_rejected(self, api_factory, admin_user):
        """Ошибка если студент неактивен"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory(is_active=False)
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Студенты не найдены или неактивны" in response.data["detail"]

    def test_partial_students_found(self, api_factory, admin_user):
        """Ошибка если часть студентов не найдена"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student1 = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student1.id, 99999], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Студенты не найдены или неактивны" in response.data["detail"]
        assert "99999" in response.data["detail"]


@pytest.mark.django_db
class TestAssignStudentsToTeacherPermissions:
    """Тесты прав доступа"""

    def test_admin_can_assign(self, api_factory, admin_user):
        """Admin может назначать студентов"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_staff_can_assign(self, api_factory, staff_user):
        """Staff может назначать студентов"""
        api_client = APIClient()
        api_client.force_authenticate(user=staff_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_regular_user_forbidden(self, api_factory, regular_user):
        """Regular user не может назначать студентов"""
        api_client = APIClient()
        api_client.force_authenticate(user=regular_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_forbidden(self):
        """Неавторизованный пользователь не может назначать студентов"""
        api_client = APIClient()
        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAssignStudentsToTeacherEdgeCases:
    """Тесты граничных случаев"""

    def test_assign_same_student_twice_same_request(self, api_factory, admin_user):
        """Дублирование ID студента в одном запросе"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id, student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Проверка что создался только один enrollment
        enrollments = SubjectEnrollment.objects.filter(
            student=student, subject=subject, teacher=teacher
        )
        assert enrollments.count() == 1

    def test_assign_student_to_inactive_teacher(self, api_factory, admin_user):
        """Ошибка при назначении студента неактивному учителю"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory(is_active=False)
        student = StudentFactory()
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Учитель не найден" in response.data["detail"]

    def test_assign_student_without_profile(self, api_factory, admin_user):
        """Успешное назначение студента без профиля (профиль не обязателен)"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        student = StudentFactory()
        # Не создаем StudentProfile
        subject = SubjectFactory(name="Math")

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        data = {"student_ids": [student.id], "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        # Должно работать, т.к. SubjectEnrollment не требует StudentProfile
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_assign_large_batch_students(self, api_factory, admin_user):
        """Назначение большого количества студентов"""
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        teacher = TeacherFactory()
        subject = SubjectFactory(name="Math")

        students = []
        for i in range(50):
            student = StudentFactory(username=f"student{i}", email=f"student{i}@test.com")
            students.append(student)

        url = f"/api/staff/teachers/{teacher.id}/assign-students/"
        student_ids = [s.id for s in students]
        data = {"student_ids": student_ids, "subject_id": subject.id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["assigned_students"]) == 50

        # Проверка что все enrollments созданы
        enrollments = SubjectEnrollment.objects.filter(teacher=teacher, subject=subject)
        assert enrollments.count() == 50
