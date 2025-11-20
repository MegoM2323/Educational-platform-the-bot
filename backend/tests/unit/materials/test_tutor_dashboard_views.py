"""
Комплексные unit-тесты для Tutor Dashboard Views

Покрывает:
- tutor_dashboard() - главный дашборд
- tutor_students() - список студентов
- tutor_student_subjects() - предметы студента
- tutor_student_progress() - прогресс студента
- tutor_assign_subject() - назначение предмета
- tutor_create_report() - создание отчета
- tutor_reports() - список отчетов
"""
import pytest
import json
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from materials.models import Subject, SubjectEnrollment, Material, MaterialProgress
from reports.models import Report, ReportRecipient

User = get_user_model()


@pytest.fixture
def api_client():
    """API клиент для тестов"""
    return APIClient()


# ===== Dashboard Main Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorDashboardView:
    """Тесты для главного дашборда тьютора"""

    def test_tutor_dashboard_success(self, api_client, tutor_user):
        """Успешное получение дашборда тьютором"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 200
        data = response.json()
        assert 'tutor_info' in data
        assert 'statistics' in data
        assert 'students' in data
        assert 'reports' in data

    def test_tutor_dashboard_non_tutor_forbidden(self, api_client, student_user):
        """Не-тьютор получает 403"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 403
        assert 'error' in response.json()

    def test_tutor_dashboard_unauthenticated(self, api_client):
        """Неаутентифицированный пользователь получает 401"""
        response = api_client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 401

    def test_tutor_dashboard_with_students(self, api_client, tutor_user, student_user):
        """Дашборд показывает студентов тьютора"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 200
        data = response.json()
        assert len(data['students']) == 1
        assert data['students'][0]['id'] == student_user.id


# ===== Students List Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorStudentsView:
    """Тесты для списка студентов"""

    def test_tutor_students_success(self, api_client, tutor_user, student_user):
        """Успешное получение списка студентов"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/students/')

        assert response.status_code == 200
        data = response.json()
        assert 'students' in data
        assert len(data['students']) == 1

    def test_tutor_students_non_tutor_forbidden(self, api_client, teacher_user):
        """Не-тьютор получает 403"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/materials/dashboard/tutor/students/')

        assert response.status_code == 403

    def test_tutor_students_empty_list(self, api_client, tutor_user):
        """Пустой список когда нет студентов"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/students/')

        assert response.status_code == 200
        data = response.json()
        assert data['students'] == []


# ===== Student Subjects Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorStudentSubjectsView:
    """Тесты для получения предметов студента"""

    def test_student_subjects_success(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Успешное получение предметов студента"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/subjects/')

        assert response.status_code == 200
        data = response.json()
        assert 'subjects' in data
        assert len(data['subjects']) == 1

    def test_student_subjects_not_own_student(self, api_client, tutor_user, student_user):
        """Ошибка при запросе предметов не своего студента"""
        # Студент не привязан к тьютору
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/subjects/')

        assert response.status_code == 403

    def test_student_subjects_non_tutor_forbidden(self, api_client, parent_user, student_user):
        """Не-тьютор получает 403"""
        api_client.force_authenticate(user=parent_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/subjects/')

        assert response.status_code == 403


# ===== Student Progress Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorStudentProgressView:
    """Тесты для получения прогресса студента"""

    def test_student_progress_success(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Успешное получение прогресса студента"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/progress/')

        assert response.status_code == 200
        data = response.json()
        assert 'total_materials' in data
        assert 'completed_materials' in data
        assert 'subject_progress' in data

    def test_student_progress_with_materials(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Прогресс студента с материалами"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материал и прогресс
        material = Material.objects.create(
            title='Test Material',
            subject=subject,
            author=teacher_user
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=75,
            is_completed=False
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/progress/')

        assert response.status_code == 200
        data = response.json()
        assert data['total_materials'] == 1
        assert data['completed_materials'] == 0

    def test_student_progress_not_own_student(self, api_client, tutor_user, student_user):
        """Ошибка при запросе прогресса не своего студента"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/progress/')

        assert response.status_code == 403

    def test_student_progress_non_tutor_forbidden(self, api_client, student_user):
        """Не-тьютор получает 403"""
        other_student = User.objects.create_user(
            username='other_student',
            email='other@test.com',
            role=User.Role.STUDENT
        )
        from accounts.models import StudentProfile
        StudentProfile.objects.create(user=other_student)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{other_student.id}/progress/')

        assert response.status_code == 403


# ===== Assign Subject Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorAssignSubjectView:
    """Тесты для назначения предмета студенту"""

    def test_assign_subject_success(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Успешное назначение предмета"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        data = {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'teacher_id': teacher_user.id
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/students/assign-subject/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 201
        result = response.json()
        assert result['success'] is True
        assert 'enrollment_id' in result

    def test_assign_subject_with_custom_name(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Назначение предмета с кастомным названием"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        data = {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'teacher_id': teacher_user.id,
            'custom_subject_name': 'Математика (углубленная)'
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/students/assign-subject/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 201
        result = response.json()
        assert result['success'] is True

        # Проверяем кастомное название
        enrollment = SubjectEnrollment.objects.get(id=result['enrollment_id'])
        assert enrollment.custom_subject_name == 'Математика (углубленная)'

    def test_assign_subject_missing_fields(self, api_client, tutor_user):
        """Ошибка при отсутствии обязательных полей"""
        data = {
            'student_id': 1
            # subject_id и teacher_id отсутствуют
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/students/assign-subject/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 400
        assert 'error' in response.json()

    def test_assign_subject_non_tutor_forbidden(self, api_client, teacher_user):
        """Не-тьютор не может назначать предметы"""
        data = {
            'student_id': 1,
            'subject_id': 1,
            'teacher_id': 1
        }

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/students/assign-subject/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 403

    def test_assign_subject_already_assigned(self, api_client, tutor_user, student_user, subject, teacher_user):
        """Ошибка при попытке назначить уже назначенный предмет"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем существующий enrollment
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        data = {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'teacher_id': teacher_user.id
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/students/assign-subject/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 400
        result = response.json()
        assert result['success'] is False


# ===== Create Report Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorCreateReportView:
    """Тесты для создания отчетов"""

    def test_create_report_success(self, api_client, tutor_user, student_user, parent_user):
        """Успешное создание отчета"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        data = {
            'student_id': student_user.id,
            'parent_id': parent_user.id,
            'title': 'Недельный отчет',
            'content': 'Студент показал хороший прогресс',
            'period_start': '2024-01-01',
            'period_end': '2024-01-07'
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/reports/create/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 201
        result = response.json()
        assert result['success'] is True
        assert 'report_id' in result

        # Проверяем создание отчета
        report = Report.objects.get(id=result['report_id'])
        assert report.author == tutor_user
        assert report.title == 'Недельный отчет'

    def test_create_report_missing_fields(self, api_client, tutor_user):
        """Ошибка при отсутствии обязательных полей"""
        data = {
            'student_id': 1
            # parent_id отсутствует
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/reports/create/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 400
        assert 'error' in response.json()

    def test_create_report_non_tutor_forbidden(self, api_client, teacher_user):
        """Не-тьютор не может создавать отчеты"""
        data = {
            'student_id': 1,
            'parent_id': 1,
            'title': 'Test Report'
        }

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/reports/create/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 403

    def test_create_report_wrong_parent(self, api_client, tutor_user, student_user, parent_user):
        """Ошибка при несовпадении родителя и студента"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()
        # Не привязываем родителя

        data = {
            'student_id': student_user.id,
            'parent_id': parent_user.id,
            'title': 'Test Report'
        }

        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/dashboard/tutor/reports/create/',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 400
        result = response.json()
        assert result['success'] is False


# ===== Reports List Endpoint Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorReportsView:
    """Тесты для получения списка отчетов"""

    def test_tutor_reports_success(self, api_client, tutor_user, parent_user):
        """Успешное получение списка отчетов"""
        report = Report.objects.create(
            title='Test Report',
            author=tutor_user,
            type=Report.Type.CUSTOM,
            status=Report.Status.DRAFT
        )
        ReportRecipient.objects.create(
            report=report,
            recipient=parent_user
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/reports/')

        assert response.status_code == 200
        data = response.json()
        assert 'reports' in data
        assert len(data['reports']) == 1

    def test_tutor_reports_empty_list(self, api_client, tutor_user):
        """Пустой список отчетов"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/reports/')

        assert response.status_code == 200
        data = response.json()
        assert data['reports'] == []

    def test_tutor_reports_non_tutor_forbidden(self, api_client, student_user):
        """Не-тьютор получает 403"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/dashboard/tutor/reports/')

        assert response.status_code == 403

    def test_tutor_reports_only_own_reports(self, api_client, tutor_user):
        """Тьютор видит только свои отчеты"""
        # Создаем другого тьютора
        other_tutor = User.objects.create_user(
            username='other_tutor',
            email='other@test.com',
            role=User.Role.TUTOR
        )

        # Отчет другого тьютора
        Report.objects.create(
            title='Other Report',
            author=other_tutor,
            type=Report.Type.CUSTOM,
            status=Report.Status.DRAFT
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/reports/')

        assert response.status_code == 200
        data = response.json()
        assert len(data['reports']) == 0
