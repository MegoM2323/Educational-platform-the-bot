"""
Тесты для проверки фильтрации админов из списка студентов преподавателя
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

User = get_user_model()


@pytest.mark.django_db
class TestTeacherStudentsFilter:
    """Тесты фильтрации студентов для преподавателя"""

    @pytest.fixture
    def setup_users(self):
        """Создаем пользователей для тестирования"""
        # Создаем преподавателя
        teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher',
            last_name='One'
        )
        teacher_token = Token.objects.create(user=teacher)

        # Создаем обычного студента
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='One'
        )

        # Создаем студента с правами админа (is_staff=True)
        admin_student = User.objects.create_user(
            username='admin_student',
            email='admin_student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Admin',
            last_name='Student',
            is_staff=True
        )

        # Создаем суперпользователя со ролью студента
        superuser_student = User.objects.create_user(
            username='superuser_student',
            email='superuser_student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Superuser',
            last_name='Student',
            is_superuser=True
        )

        # Создаем обычного админа (суперпользователь)
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=User.Role.TEACHER,  # У админа может быть любая роль
            first_name='Admin',
            last_name='User'
        )

        return {
            'teacher': teacher,
            'teacher_token': teacher_token,
            'student': student,
            'admin_student': admin_student,
            'superuser_student': superuser_student,
            'admin': admin
        }

    def test_get_all_students_excludes_admins(self, setup_users):
        """Тест: GET /materials/teacher/all-students/ исключает админов"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {setup_users["teacher_token"].key}')

        response = client.get('/materials/teacher/all-students/')

        assert response.status_code == 200
        assert 'students' in response.data

        students = response.data['students']
        student_ids = [s['id'] for s in students]

        # Проверяем, что обычный студент есть в списке
        assert setup_users['student'].id in student_ids

        # Проверяем, что студент с is_staff НЕТ в списке
        assert setup_users['admin_student'].id not in student_ids

        # Проверяем, что студент с is_superuser НЕТ в списке
        assert setup_users['superuser_student'].id not in student_ids

        # Проверяем, что обычный админ НЕТ в списке
        assert setup_users['admin'].id not in student_ids

    def test_teacher_dashboard_service_get_all_students(self, setup_users):
        """Тест: TeacherDashboardService.get_all_students() исключает админов"""
        from backend.materials.teacher_dashboard_service import TeacherDashboardService

        service = TeacherDashboardService(setup_users['teacher'])
        students = service.get_all_students()

        student_ids = [s['id'] for s in students]

        # Проверяем, что обычный студент есть в списке
        assert setup_users['student'].id in student_ids

        # Проверяем, что студент с is_staff НЕТ в списке
        assert setup_users['admin_student'].id not in student_ids

        # Проверяем, что студент с is_superuser НЕТ в списке
        assert setup_users['superuser_student'].id not in student_ids

        # Проверяем, что обычный админ НЕТ в списке
        assert setup_users['admin'].id not in student_ids

    def test_teacher_dashboard_service_get_teacher_students(self, setup_users):
        """Тест: TeacherDashboardService.get_teacher_students() исключает админов"""
        from backend.materials.teacher_dashboard_service import TeacherDashboardService
        from backend.materials.models import Subject, SubjectEnrollment

        # Создаем предмет
        subject = Subject.objects.create(
            name='Mathematics',
            description='Math subject',
            color='#FF0000'
        )

        # Зачисляем обычного студента
        SubjectEnrollment.objects.create(
            student=setup_users['student'],
            subject=subject,
            teacher=setup_users['teacher'],
            assigned_by=setup_users['teacher'],
            is_active=True
        )

        # Зачисляем студента с is_staff
        SubjectEnrollment.objects.create(
            student=setup_users['admin_student'],
            subject=subject,
            teacher=setup_users['teacher'],
            assigned_by=setup_users['teacher'],
            is_active=True
        )

        service = TeacherDashboardService(setup_users['teacher'])
        students = service.get_teacher_students()

        student_ids = [s['id'] for s in students]

        # Проверяем, что обычный студент есть в списке
        assert setup_users['student'].id in student_ids

        # Проверяем, что студент с is_staff НЕТ в списке
        assert setup_users['admin_student'].id not in student_ids

    def test_assign_subject_to_students_excludes_admins(self, setup_users):
        """Тест: назначение предмета исключает админов"""
        from backend.materials.teacher_dashboard_service import TeacherDashboardService
        from backend.materials.models import Subject

        # Создаем предмет
        subject = Subject.objects.create(
            name='Physics',
            description='Physics subject',
            color='#00FF00'
        )

        service = TeacherDashboardService(setup_users['teacher'])

        # Пытаемся назначить предмет обычному студенту и студенту-админу
        result = service.assign_subject_to_students(
            subject.id,
            [setup_users['student'].id, setup_users['admin_student'].id]
        )

        # Результат должен быть неуспешным, так как admin_student будет отфильтрован
        assert result['success'] is False
        assert 'администраторами' in result['message']

    def test_distribute_material_excludes_admins(self, setup_users):
        """Тест: распределение материала исключает админов"""
        from backend.materials.teacher_dashboard_service import TeacherDashboardService
        from backend.materials.models import Subject, Material

        # Создаем предмет
        subject = Subject.objects.create(
            name='Chemistry',
            description='Chemistry subject',
            color='#0000FF'
        )

        # Создаем материал
        material = Material.objects.create(
            title='Test Material',
            description='Test description',
            author=setup_users['teacher'],
            subject=subject,
            type='lesson',
            status='active'
        )

        service = TeacherDashboardService(setup_users['teacher'])

        # Пытаемся распределить материал обычному студенту и студенту-админу
        result = service.distribute_material(
            material.id,
            [setup_users['student'].id, setup_users['admin_student'].id]
        )

        # Материал должен быть назначен только обычному студенту
        assert result['success'] is True
        assert result['assigned_count'] == 1

        # Проверяем, что материал назначен только обычному студенту
        assigned_students = material.assigned_to.all()
        assert setup_users['student'] in assigned_students
        assert setup_users['admin_student'] not in assigned_students

