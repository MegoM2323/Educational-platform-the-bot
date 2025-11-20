"""
Тесты для проверки создания ученика тьютором и правильной привязки
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from backend.accounts.models import StudentProfile, ParentProfile
from backend.accounts.tutor_service import StudentCreationService

User = get_user_model()


@pytest.mark.django_db
class TestTutorStudentCreation:
    """Тесты создания ученика тьютором"""

    @pytest.fixture
    def setup_tutor(self):
        """Создаем тьютора для тестирования"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@test.com',
            password='testpass123',
            role=User.Role.TUTOR,
            first_name='Tutor',
            last_name='One'
        )
        token = Token.objects.create(user=tutor)
        return {'tutor': tutor, 'token': token}

    @pytest.fixture
    def setup_admin_tutor(self):
        """Создаем администратора с правами тьютора"""
        admin = User.objects.create_user(
            username='admin_tutor',
            email='admin_tutor@test.com',
            password='testpass123',
            role=User.Role.TEACHER,  # Роль не TUTOR, но есть права админа
            first_name='Admin',
            last_name='Tutor',
            is_staff=True,
            is_superuser=True
        )
        token = Token.objects.create(user=admin)
        return {'admin_tutor': admin, 'token': token}

    def test_tutor_creates_student_profile_has_tutor(self, setup_tutor):
        """Тест: при создании ученика тьютором, в профиле устанавливается tutor"""
        tutor = setup_tutor['tutor']

        # Создаем ученика через сервис
        student, parent, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
            tutor=tutor,
            student_first_name='Test',
            student_last_name='Student',
            grade='5',
            goal='Изучить математику',
            parent_first_name='Test',
            parent_last_name='Parent',
            parent_email='parent@test.com',
            parent_phone='+79991234567'
        )

        # Проверяем, что профиль создан
        assert hasattr(student, 'student_profile')
        profile = student.student_profile

        # Проверяем, что tutor установлен в профиле
        assert profile.tutor == tutor
        assert profile.tutor_id == tutor.id

        # Проверяем, что created_by_tutor установлен в User
        assert student.created_by_tutor == tutor
        assert student.created_by_tutor_id == tutor.id

        # Проверяем, что родитель установлен
        assert profile.parent == parent
        assert profile.parent_id == parent.id

        print(f"✅ Ученик {student.username} успешно привязан к тьютору {tutor.username}")

    def test_admin_creates_student_profile_has_tutor(self, setup_admin_tutor):
        """Тест: при создании ученика администратором, в профиле устанавливается tutor"""
        admin = setup_admin_tutor['admin_tutor']

        # Создаем ученика через сервис
        student, parent, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
            tutor=admin,  # Передаем админа как тьютора
            student_first_name='Test',
            student_last_name='Student2',
            grade='6',
            goal='Изучить физику',
            parent_first_name='Test',
            parent_last_name='Parent2',
            parent_email='parent2@test.com',
            parent_phone='+79991234568'
        )

        # Проверяем, что профиль создан
        assert hasattr(student, 'student_profile')
        profile = student.student_profile

        # Проверяем, что tutor установлен в профиле (даже если создатель - админ)
        assert profile.tutor == admin
        assert profile.tutor_id == admin.id

        # Проверяем, что created_by_tutor установлен в User
        assert student.created_by_tutor == admin
        assert student.created_by_tutor_id == admin.id

        print(f"✅ Ученик {student.username} успешно привязан к администратору {admin.username}")

    def test_tutor_can_see_created_students(self, setup_tutor):
        """Тест: тьютор видит созданных им учеников в API"""
        tutor = setup_tutor['tutor']
        token = setup_tutor['token']

        # Создаем ученика
        student, parent, _, _ = StudentCreationService.create_student_with_parent(
            tutor=tutor,
            student_first_name='Test',
            student_last_name='Student3',
            grade='7',
            goal='Изучить химию',
            parent_first_name='Test',
            parent_last_name='Parent3',
            parent_email='parent3@test.com'
        )

        # Проверяем через API
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/accounts/students/')

        assert response.status_code == 200
        assert 'data' in response.data

        students = response.data['data']
        assert len(students) > 0

        # Проверяем, что созданный ученик есть в списке
        student_ids = [s['id'] for s in students]
        assert student.student_profile.id in student_ids

        print(f"✅ Тьютор {tutor.username} видит {len(students)} учеников")

    def test_admin_can_see_created_students(self, setup_admin_tutor):
        """Тест: администратор видит созданных им учеников в API"""
        admin = setup_admin_tutor['admin_tutor']
        token = setup_admin_tutor['token']

        # Создаем ученика
        student, parent, _, _ = StudentCreationService.create_student_with_parent(
            tutor=admin,
            student_first_name='Test',
            student_last_name='Student4',
            grade='8',
            goal='Изучить биологию',
            parent_first_name='Test',
            parent_last_name='Parent4',
            parent_email='parent4@test.com'
        )

        # Проверяем через API
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/accounts/students/')

        assert response.status_code == 200
        assert 'data' in response.data

        students = response.data['data']
        assert len(students) > 0

        # Проверяем, что созданный ученик есть в списке
        student_ids = [s['id'] for s in students]
        assert student.student_profile.id in student_ids

        print(f"✅ Администратор {admin.username} видит {len(students)} учеников")

    def test_parent_children_relationship(self, setup_tutor):
        """Тест: родитель может видеть своих детей"""
        tutor = setup_tutor['tutor']

        # Создаем ученика
        student, parent, _, _ = StudentCreationService.create_student_with_parent(
            tutor=tutor,
            student_first_name='Test',
            student_last_name='Student5',
            grade='9',
            goal='Изучить историю',
            parent_first_name='Test',
            parent_last_name='Parent5',
            parent_email='parent5@test.com'
        )

        # Проверяем связь родитель-ребенок
        parent_profile = parent.parent_profile
        children = list(parent_profile.children)

        assert len(children) > 0
        assert student in children

        print(f"✅ Родитель {parent.username} видит {len(children)} детей")

    def test_tutor_can_retrieve_specific_student(self, setup_tutor):
        """Тест: тьютор может получить конкретного ученика через API"""
        tutor = setup_tutor['tutor']
        token = setup_tutor['token']

        # Создаем ученика
        student, parent, _, _ = StudentCreationService.create_student_with_parent(
            tutor=tutor,
            student_first_name='Test',
            student_last_name='Student6',
            grade='10',
            goal='Изучить географию',
            parent_first_name='Test',
            parent_last_name='Parent6',
            parent_email='parent6@test.com'
        )

        # Проверяем через API retrieve
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get(f'/accounts/students/{student.student_profile.id}/')

        assert response.status_code == 200
        assert response.data['id'] == student.student_profile.id
        assert response.data['user']['username'] == student.username

        print(f"✅ Тьютор {tutor.username} может получить ученика {student.username}")

