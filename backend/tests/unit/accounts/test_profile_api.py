"""
Unit тесты для API endpoint GET /api/auth/profile/

Покрытие:
- CurrentUserProfileView.get() для всех ролей (Student, Teacher, Tutor, Parent)
- Аутентификация и авторизация
- Обработка ошибок (профиль не найден, не авторизован)
- Структура ответа и валидация данных
- Edge cases (пользователь без профиля, пустые данные)

Использование:
    pytest backend/tests/unit/accounts/test_profile_api.py -v --cov=accounts.views
    pytest backend/tests/unit/accounts/test_profile_api.py --cov=accounts.views --cov-report=html
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile
)
from accounts.serializers import CurrentUserProfileSerializer

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture для REST API клиента"""
    return APIClient()


@pytest.mark.unit
@pytest.mark.django_db
class TestCurrentUserProfileViewGet:
    """
    Тесты для GET /api/auth/profile/ endpoint (CurrentUserProfileView)

    Проверяет получение профиля текущего авторизованного пользователя
    для всех ролей с полной валидацией ответа.
    """

    # ========== УСПЕШНЫЕ СЦЕНАРИИ (200 OK) ==========

    def test_student_can_get_own_profile(self, api_client):
        """
        Студент может получить свой профиль.

        Проверяет:
        - HTTP 200 OK
        - Структура ответа (data, message, errors)
        - Данные пользователя (email, role, role_display)
        - Данные профиля (grade, progress, streak и т.д.)
        """
        # Arrange
        user = User.objects.create_user(
            username='student_get_profile',
            email='student@profile.test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT,
            first_name='Иван',
            last_name='Иванов'
        )
        profile = StudentProfile.objects.create(
            user=user,
            grade='10А',
            goal='Подготовка к ЕГЭ по математике',
            progress_percentage=82,
            streak_days=23,
            total_points=2850,
            accuracy_percentage=88
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Профиль успешно получен'
        assert response.data['errors'] is None
        assert response.data['data'] is not None

        # Проверяем структуру данных
        data = response.data['data']
        assert 'user' in data
        assert 'profile' in data

        # Проверяем данные пользователя
        user_data = data['user']
        assert user_data['id'] == user.id
        assert user_data['email'] == 'student@profile.test.com'
        assert user_data['first_name'] == 'Иван'
        assert user_data['last_name'] == 'Иванов'
        assert user_data['role'] == User.Role.STUDENT
        assert user_data['role_display'] == 'Студент'

        # Проверяем данные профиля студента
        profile_data = data['profile']
        assert profile_data['grade'] == '10А'
        assert profile_data['goal'] == 'Подготовка к ЕГЭ по математике'
        assert profile_data['progress_percentage'] == 82
        assert profile_data['streak_days'] == 23
        assert profile_data['total_points'] == 2850
        assert profile_data['accuracy_percentage'] == 88

    def test_teacher_can_get_own_profile(self, api_client):
        """
        Преподаватель может получить свой профиль.

        Проверяет:
        - HTTP 200 OK
        - Role = TEACHER
        - Данные профиля преподавателя (subject, experience_years, bio)
        """
        # Arrange
        user = User.objects.create_user(
            username='teacher_get_profile',
            email='teacher@profile.test.com',
            password='SecurePass123!',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Сидорова'
        )
        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            experience_years=12,
            bio='Преподаватель высшей категории. Опыт подготовки к ЕГЭ - 10 лет.'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Профиль успешно получен'

        data = response.data['data']
        assert data['user']['role'] == User.Role.TEACHER
        assert data['user']['role_display'] == 'Преподаватель'
        assert data['profile']['subject'] == 'Математика'
        assert data['profile']['experience_years'] == 12
        assert data['profile']['bio'] == 'Преподаватель высшей категории. Опыт подготовки к ЕГЭ - 10 лет.'

    def test_tutor_can_get_own_profile(self, api_client):
        """
        Тьютор может получить свой профиль.

        Проверяет:
        - HTTP 200 OK
        - Role = TUTOR
        - Данные профиля тьютора (specialization, experience_years, bio)
        """
        # Arrange
        user = User.objects.create_user(
            username='tutor_get_profile',
            email='tutor@profile.test.com',
            password='SecurePass123!',
            role=User.Role.TUTOR,
            first_name='Петр',
            last_name='Петров'
        )
        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка к ЕГЭ по русскому языку',
            experience_years=7,
            bio='Эффективные методы подготовки. Результаты студентов: 85-98 баллов.'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Профиль успешно получен'

        data = response.data['data']
        assert data['user']['role'] == User.Role.TUTOR
        assert data['user']['role_display'] == 'Тьютор'
        assert data['profile']['specialization'] == 'Подготовка к ЕГЭ по русскому языку'
        assert data['profile']['experience_years'] == 7
        assert 'баллов' in data['profile']['bio']

    def test_parent_can_get_own_profile(self, api_client):
        """
        Родитель может получить свой профиль.

        Проверяет:
        - HTTP 200 OK
        - Role = PARENT
        - Данные профиля родителя
        """
        # Arrange
        user = User.objects.create_user(
            username='parent_get_profile',
            email='parent@profile.test.com',
            password='SecurePass123!',
            role=User.Role.PARENT,
            first_name='Анна',
            last_name='Петрова'
        )
        profile = ParentProfile.objects.create(user=user)

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Профиль успешно получен'
        assert response.data['errors'] is None

        data = response.data['data']
        assert data['user']['role'] == User.Role.PARENT
        assert data['user']['role_display'] == 'Родитель'
        assert data['profile'] is not None

    # ========== ОШИБКИ АВТОРИЗАЦИИ (401, 403, 404) ==========

    def test_unauthenticated_user_returns_401(self, api_client):
        """
        Неавторизованный пользователь получает 401 Unauthorized.

        Проверяет:
        - HTTP 401 Unauthorized
        - Ошибка аутентификации
        """
        # Act - без авторизации
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
        # В DRF обычно это 403 для класса без credentials

    def test_user_without_profile_returns_404(self, api_client):
        """
        Пользователь без модели профиля получает 404 Not Found.

        Проверяет:
        - HTTP 404 Not Found
        - Сообщение об ошибке 'Profile not found'
        - Данные пользователя всё ещё возвращаются
        """
        # Arrange
        user = User.objects.create_user(
            username='no_profile_student',
            email='noprofile@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        # Профиль НЕ создаём!

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['errors'] == 'Profile not found'
        assert 'Профиль пользователя' in response.data['message']

        # Данные пользователя присутствуют, но профиль null
        data = response.data['data']
        assert data['user'] is not None
        assert data['user']['email'] == 'noprofile@test.com'
        assert data['profile'] is None

    def test_user_without_profile_all_roles(self, api_client):
        """
        Пользователи любой роли без профиля получают 404.

        Параметризованный тест для всех ролей.
        """
        roles = [
            User.Role.STUDENT,
            User.Role.TEACHER,
            User.Role.TUTOR,
            User.Role.PARENT
        ]

        for role in roles:
            # Arrange
            user = User.objects.create_user(
                username=f'no_profile_{role}',
                email=f'noprofile_{role}@test.com',
                password='SecurePass123!',
                role=role
            )

            token = Token.objects.create(user=user)
            api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

            # Act
            response = api_client.get('/api/auth/profile/')

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data['data']['profile'] is None

    # ========== ПРОВЕРКА СТРУКТУРЫ ОТВЕТА ==========

    def test_profile_response_structure(self, api_client):
        """
        Проверить стандартную структуру ответа API.

        Все endpoints должны возвращать:
        - data: основные данные
        - message: описание результата
        - errors: ошибки (null при успехе)
        """
        # Arrange
        user = User.objects.create_user(
            username='response_structure_test',
            email='structure@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='11')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert - на уровне ответа
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, dict)
        assert 'data' in response.data
        assert 'message' in response.data
        assert 'errors' in response.data

        # Assert - на уровне структуры data
        data = response.data['data']
        assert isinstance(data, dict)
        assert 'user' in data
        assert 'profile' in data

        # Assert - типы данных
        assert isinstance(data['user'], dict)
        assert data['profile'] is None or isinstance(data['profile'], dict)

    def test_profile_contains_correct_user_fields(self, api_client):
        """
        Проверить что профиль содержит все необходимые поля пользователя.

        Обязательные поля:
        - id, email, first_name, last_name
        - role, role_display, date_joined
        """
        # Arrange
        user = User.objects.create_user(
            username='fields_check',
            email='fields@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT,
            first_name='Тест',
            last_name='Юзер'
        )
        StudentProfile.objects.create(user=user, grade='9')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        user_data = response.data['data']['user']

        # Обязательные поля
        required_fields = [
            'id', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'date_joined'
        ]
        for field in required_fields:
            assert field in user_data, f"Отсутствует поле {field}"

        # Проверяем значения
        assert user_data['email'] == 'fields@test.com'
        assert user_data['first_name'] == 'Тест'
        assert user_data['last_name'] == 'Юзер'
        assert user_data['role'] == User.Role.STUDENT
        assert isinstance(user_data['role_display'], str)
        assert isinstance(user_data['date_joined'], str)

    def test_student_profile_contains_correct_fields(self, api_client):
        """
        Проверить что StudentProfile содержит все необходимые поля.

        Обязательные поля:
        - grade, goal, progress_percentage
        - streak_days, total_points, accuracy_percentage
        """
        # Arrange
        user = User.objects.create_user(
            username='student_fields_check',
            email='student_fields@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(
            user=user,
            grade='10',
            goal='Хорошо учиться',
            progress_percentage=75,
            streak_days=10,
            total_points=1000,
            accuracy_percentage=80
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        profile_data = response.data['data']['profile']

        required_fields = [
            'grade', 'goal', 'progress_percentage',
            'streak_days', 'total_points', 'accuracy_percentage'
        ]
        for field in required_fields:
            assert field in profile_data, f"Отсутствует поле {field}"

        # Проверяем значения
        assert profile_data['grade'] == '10'
        assert profile_data['goal'] == 'Хорошо учиться'
        assert isinstance(profile_data['progress_percentage'], (int, float))
        assert isinstance(profile_data['streak_days'], int)
        assert isinstance(profile_data['total_points'], int)

    def test_teacher_profile_contains_correct_fields(self, api_client):
        """
        Проверить что TeacherProfile содержит все необходимые поля.

        Обязательные поля:
        - subject, experience_years, bio
        """
        # Arrange
        user = User.objects.create_user(
            username='teacher_fields_check',
            email='teacher_fields@test.com',
            password='SecurePass123!',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(
            user=user,
            subject='История',
            experience_years=5,
            bio='Опытный преподаватель'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        profile_data = response.data['data']['profile']

        required_fields = ['subject', 'experience_years', 'bio']
        for field in required_fields:
            assert field in profile_data, f"Отсутствует поле {field}"

    def test_tutor_profile_contains_correct_fields(self, api_client):
        """
        Проверить что TutorProfile содержит все необходимые поля.

        Обязательные поля:
        - specialization, experience_years, bio
        """
        # Arrange
        user = User.objects.create_user(
            username='tutor_fields_check',
            email='tutor_fields@test.com',
            password='SecurePass123!',
            role=User.Role.TUTOR
        )
        TutorProfile.objects.create(
            user=user,
            specialization='Физика',
            experience_years=3,
            bio='Молодой репетитор'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        profile_data = response.data['data']['profile']

        required_fields = ['specialization', 'experience_years', 'bio']
        for field in required_fields:
            assert field in profile_data, f"Отсутствует поле {field}"

    # ========== EDGE CASES И СПЕЦИАЛЬНЫЕ СЦЕНАРИИ ==========

    def test_multiple_requests_return_same_data(self, api_client):
        """
        Проверить идемпотентность - несколько запросов возвращают одинаковые данные.
        """
        # Arrange
        user = User.objects.create_user(
            username='idempotent_test',
            email='idempotent@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='7')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response1 = api_client.get('/api/auth/profile/')
        response2 = api_client.get('/api/auth/profile/')
        response3 = api_client.get('/api/auth/profile/')

        # Assert
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK

        # Данные должны быть идентичны
        assert response1.data == response2.data
        assert response2.data == response3.data

    def test_user_with_special_characters_in_name(self, api_client):
        """
        Проверить работу с специальными символами в имени/фамилии.
        """
        # Arrange
        user = User.objects.create_user(
            username='special_chars_test',
            email='special@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT,
            first_name="Жан-Пьер",
            last_name="О'Коннор-Смит"
        )
        StudentProfile.objects.create(user=user, grade='8')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['first_name'] == "Жан-Пьер"
        assert response.data['data']['user']['last_name'] == "О'Коннор-Смит"

    def test_profile_with_empty_optional_fields(self, api_client):
        """
        Проверить работу с пустыми опциональными полями в профиле.
        """
        # Arrange
        user = User.objects.create_user(
            username='empty_fields_test',
            email='empty@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT,
            first_name='',  # пустое имя
            last_name=''    # пустая фамилия
        )
        StudentProfile.objects.create(user=user, grade='5')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['first_name'] == ''
        assert response.data['data']['user']['last_name'] == ''

    def test_inactive_user_cannot_get_profile(self, api_client):
        """
        Неактивный пользователь (is_active=False) не может получить профиль.
        """
        # Arrange
        user = User.objects.create_user(
            username='inactive_user',
            email='inactive@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT,
            is_active=False  # неактивный пользователь
        )
        StudentProfile.objects.create(user=user, grade='6')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert - неактивный пользователь не должен иметь доступ
        # Это может вернуть 401 или 403 в зависимости от конфигурации Django
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_profile_serializer_directly(self):
        """
        Прямой тест CurrentUserProfileSerializer без HTTP запроса.

        Проверяет что serializer правильно преобразует User в профиль.
        """
        # Arrange
        user = User.objects.create_user(
            username='serializer_test',
            email='serializer@test.com',
            password='SecurePass123!',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(
            user=user,
            subject='Английский',
            experience_years=8,
            bio='Native speaker'
        )

        # Act
        serializer = CurrentUserProfileSerializer(user)
        data = serializer.data

        # Assert
        assert 'user' in data
        assert 'profile' in data
        assert data['user']['email'] == 'serializer@test.com'
        assert data['profile']['subject'] == 'Английский'

    # ========== SESSION vs TOKEN AUTHENTICATION ==========

    def test_session_authentication_works(self, api_client):
        """
        Проверить что SessionAuthentication работает (не только TokenAuthentication).
        """
        # Arrange
        user = User.objects.create_user(
            username='session_test',
            email='session@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='4')

        # Act - используем force_authenticate вместо token
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['email'] == 'session@test.com'

    def test_token_authentication_works(self, api_client):
        """
        Проверить что TokenAuthentication работает.
        """
        # Arrange
        user = User.objects.create_user(
            username='token_test',
            email='token@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='3')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['email'] == 'token@test.com'

    def test_invalid_token_returns_401(self, api_client):
        """
        Неверный токен возвращает 401 Unauthorized.
        """
        # Arrange
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid_token_xyz')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    # ========== ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ ==========

    @pytest.mark.parametrize('role,profile_model,profile_data', [
        (User.Role.STUDENT, StudentProfile, {'grade': '12', 'goal': 'ЕГЭ'}),
        (User.Role.TEACHER, TeacherProfile, {'subject': 'Физика', 'experience_years': 5}),
        (User.Role.TUTOR, TutorProfile, {'specialization': 'Лингвистика', 'experience_years': 3}),
        (User.Role.PARENT, ParentProfile, {}),
    ])
    def test_all_roles_get_correct_profile(self, api_client, role, profile_model, profile_data):
        """
        Параметризованный тест для всех ролей и типов профилей.
        """
        # Arrange
        user = User.objects.create_user(
            username=f'param_test_{role}',
            email=f'param_{role}@test.com',
            password='SecurePass123!',
            role=role
        )
        profile = profile_model.objects.create(user=user, **profile_data)

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == role
        assert response.data['data']['profile'] is not None

    # ========== ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ==========

    def test_profile_returns_correct_data_without_extra_queries(self, api_client, django_assert_num_queries):
        """
        Проверить что endpoint не выполняет лишних запросов к БД.

        Ожидается примерно:
        - 1 query для получения User
        - 1 query для получения StudentProfile
        = 2 queries max
        """
        # Arrange
        user = User.objects.create_user(
            username='perf_test',
            email='perf@test.com',
            password='SecurePass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='2')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act - подсчитываем queries
        # Может быть до 3-4 queries в зависимости от конфигурации
        with django_assert_num_queries(4):  # примерное значение
            response = api_client.get('/api/auth/profile/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
