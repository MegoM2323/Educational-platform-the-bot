"""
Unit тесты для views приложения accounts

Покрытие:
- login_view: успешный/неуспешный логин, email/username, Supabase fallback
- logout_view: успешный logout, без аутентификации
- refresh_token_view: обновление токена, неверный токен
- profile view: получение профиля по роли
- update_profile: обновление профиля
- change_password: смена пароля
- list_users: список пользователей с фильтрацией
- Profile views: StudentProfileView, TeacherProfileView, etc.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture для API клиента"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, db):
    """Fixture для аутентифицированного клиента"""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        role=User.Role.STUDENT
    )
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    api_client.user = user
    return api_client


@pytest.mark.unit
@pytest.mark.django_db
class TestLoginView:
    """Тесты для login_view"""

    def test_login_with_email_success(self, api_client):
        """Тест успешного входа через email"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'token' in response.data['data']
        assert response.data['data']['user']['email'] == 'test@example.com'
        assert response.data['data']['user']['role'] == User.Role.STUDENT

    def test_login_with_username_success(self, api_client):
        """Тест успешного входа через username"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'token' in response.data['data']
        assert response.data['data']['user']['role'] == User.Role.TEACHER

    def test_login_with_wrong_password(self, api_client):
        """Тест входа с неверным паролем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        with patch('accounts.views.SupabaseAuthService') as mock_supabase:
            # Мокируем Supabase чтобы он тоже вернул ошибку
            mock_instance = MagicMock()
            mock_instance.sign_in.return_value = {'success': False, 'error': 'Invalid credentials'}
            mock_supabase.return_value = mock_instance

            response = api_client.post('/api/auth/login/', data, format='json')

            # DRF может возвращать 403 вместо 401 в некоторых случаях
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
            assert response.data['success'] is False

    def test_login_with_nonexistent_user(self, api_client):
        """Тест входа с несуществующим пользователем"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }

        with patch('accounts.views.SupabaseAuthService') as mock_supabase:
            mock_instance = MagicMock()
            mock_instance.sign_in.return_value = {'success': False, 'error': 'User not found'}
            mock_supabase.return_value = mock_instance

            response = api_client.post('/api/auth/login/', data, format='json')

            # DRF может возвращать 403 вместо 401 в некоторых случаях
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
            assert response.data['success'] is False

    def test_login_with_inactive_user(self, api_client):
        """Тест входа с неактивным пользователем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_active=False
        )

        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        with patch('accounts.views.SupabaseAuthService') as mock_supabase:
            mock_instance = MagicMock()
            mock_instance.sign_in.return_value = {'success': False, 'error': 'User inactive'}
            mock_supabase.return_value = mock_instance

            response = api_client.post('/api/auth/login/', data, format='json')

            # Может быть 401 (неверные данные) или 403 (аккаунт деактивирован)
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
            assert response.data['success'] is False

    def test_login_without_email_or_username(self, api_client):
        """Тест входа без email или username"""
        data = {
            'password': 'testpass123'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_without_password(self, api_client):
        """Тест входа без пароля"""
        data = {
            'email': 'test@example.com'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_creates_new_token(self, api_client):
        """Тест что при входе создается новый токен"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Создаем старый токен
        old_token = Token.objects.create(user=user)
        old_token_key = old_token.key

        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        new_token_key = response.data['data']['token']

        # Новый токен должен отличаться от старого
        assert new_token_key != old_token_key

        # Старый токен должен быть удален
        assert not Token.objects.filter(key=old_token_key).exists()

    @pytest.mark.parametrize('role', [
        User.Role.STUDENT,
        User.Role.TEACHER,
        User.Role.TUTOR,
        User.Role.PARENT
    ])
    def test_login_returns_correct_role(self, api_client, role):
        """Тест что при входе возвращается правильная роль"""
        user = User.objects.create_user(
            username=f'user_{role}',
            email=f'{role}@example.com',
            password='testpass123',
            role=role
        )

        data = {
            'email': f'{role}@example.com',
            'password': 'testpass123'
        }

        response = api_client.post('/api/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == role

    def test_login_with_supabase_fallback(self, api_client):
        """Тест фоллбэка на Supabase при отсутствии локального пароля"""
        user = User.objects.create(
            username='testuser_supabase',
            email='testsupabase@example.com',
            password='',  # blank пароль для Supabase
            role=User.Role.STUDENT
        )

        data = {
            'email': 'testsupabase@example.com',
            'password': 'testpass123'
        }

        with patch('accounts.views.SupabaseAuthService') as mock_supabase:
            mock_instance = MagicMock()
            mock_instance.sign_in.return_value = {'success': True}
            mock_supabase.return_value = mock_instance

            response = api_client.post('/api/auth/login/', data, format='json')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True


@pytest.mark.unit
@pytest.mark.django_db
class TestLogoutView:
    """Тесты для logout_view"""

    def test_logout_success(self, authenticated_client):
        """Тест успешного выхода"""
        user = authenticated_client.user
        token_key = Token.objects.get(user=user).key

        response = authenticated_client.post('/api/auth/logout/')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

        # Токен должен быть удален
        assert not Token.objects.filter(key=token_key).exists()

    def test_logout_without_authentication(self, api_client):
        """Тест выхода без аутентификации"""
        response = api_client.post('/api/auth/logout/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_logout_with_invalid_token(self, api_client):
        """Тест выхода с невалидным токеном"""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid-token-123')

        response = api_client.post('/api/auth/logout/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
@pytest.mark.django_db
class TestRefreshTokenView:
    """Тесты для refresh_token_view"""

    def test_refresh_token_success(self, authenticated_client):
        """Тест успешного обновления токена"""
        user = authenticated_client.user
        old_token = Token.objects.get(user=user)
        old_token_key = old_token.key

        response = authenticated_client.post('/api/auth/refresh/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'token' in response.data['data']

        new_token_key = response.data['data']['token']

        # Новый токен должен отличаться от старого
        assert new_token_key != old_token_key

        # Старый токен должен быть удален
        assert not Token.objects.filter(key=old_token_key).exists()

        # Новый токен должен существовать
        assert Token.objects.filter(key=new_token_key, user=user).exists()

    def test_refresh_token_without_authentication(self, api_client):
        """Тест обновления токена без аутентификации"""
        response = api_client.post('/api/auth/refresh/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_refresh_token_with_invalid_token(self, api_client):
        """Тест обновления токена с невалидным токеном"""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid-token-123')

        response = api_client.post('/api/auth/refresh/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_refresh_token_returns_user_data(self, authenticated_client):
        """Тест что обновление токена возвращает данные пользователя"""
        response = authenticated_client.post('/api/auth/refresh/')

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data['data']
        assert response.data['data']['user']['id'] == authenticated_client.user.id


@pytest.mark.unit
@pytest.mark.django_db
class TestProfileView:
    """Тесты для profile view"""

    def test_get_profile_student(self, api_client):
        """Тест получения профиля студента"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            first_name='Ivan',
            last_name='Ivanov',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(
            user=user,
            grade='8',
            goal='Подготовка к ОГЭ'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['email'] == 'student@example.com'
        assert response.data['profile'] is not None
        assert response.data['profile']['grade'] == '8'
        assert response.data['profile']['goal'] == 'Подготовка к ОГЭ'

    def test_get_profile_teacher(self, api_client):
        """Тест получения профиля преподавателя"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            experience_years=5
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['subject'] == 'Математика'
        assert response.data['profile']['experience_years'] == 5

    def test_get_profile_tutor(self, api_client):
        """Тест получения профиля тьютора"""
        user = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )
        profile = TutorProfile.objects.create(
            user=user,
            specialization='ОГЭ',
            experience_years=3
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['specialization'] == 'ОГЭ'

    def test_get_profile_parent(self, api_client):
        """Тест получения профиля родителя"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        profile = ParentProfile.objects.create(user=user)

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile'] is not None

    def test_get_profile_without_profile_model(self, api_client):
        """Тест получения профиля пользователя без созданного профиля"""
        user = User.objects.create_user(
            username='user1',
            email='user@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile'] is None

    def test_get_profile_without_authentication(self, api_client):
        """Тест получения профиля без аутентификации"""
        response = api_client.get('/api/auth/profile/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
@pytest.mark.django_db
class TestUpdateProfileView:
    """Тесты для update_profile view"""

    def test_update_user_fields(self, authenticated_client):
        """Тест обновления полей пользователя"""
        user = authenticated_client.user

        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+79991234567'
        }

        response = authenticated_client.put('/api/auth/profile/update/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'
        assert user.phone == '+79991234567'

    def test_update_student_profile(self, api_client):
        """Тест обновления профиля студента"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(user=user, grade='8')

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        data = {
            'grade': '9',
            'goal': 'Подготовка к ОГЭ'
        }

        response = api_client.put('/api/auth/profile/update/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.grade == '9'
        assert profile.goal == 'Подготовка к ОГЭ'

    def test_update_profile_with_invalid_data(self, authenticated_client):
        """Тест обновления профиля с невалидными данными"""
        data = {
            'email': 'invalid-email'  # Невалидный email
        }

        response = authenticated_client.put('/api/auth/profile/update/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_profile_without_authentication(self, api_client):
        """Тест обновления профиля без аутентификации"""
        data = {'first_name': 'Test'}

        response = api_client.put('/api/auth/profile/update/', data, format='json')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
@pytest.mark.django_db
class TestChangePasswordView:
    """Тесты для change_password view"""

    def test_change_password_success(self, api_client):
        """Тест успешной смены пароля"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }

        response = api_client.post('/api/auth/change-password/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('newpass123') is True

    def test_change_password_wrong_old_password(self, api_client):
        """Тест смены пароля с неверным старым паролем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }

        response = api_client.post('/api/auth/change-password/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, api_client):
        """Тест смены пароля с несовпадающими новыми паролями"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'different123'
        }

        response = api_client.post('/api/auth/change-password/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
@pytest.mark.django_db
class TestListUsersView:
    """Тесты для list_users view"""

    def test_list_all_users(self, authenticated_client):
        """Тест получения списка всех пользователей"""
        # Создаем пользователей разных ролей
        User.objects.create_user(username='student1', email='s1@example.com', role=User.Role.STUDENT)
        User.objects.create_user(username='teacher1', email='t1@example.com', role=User.Role.TEACHER)
        User.objects.create_user(username='parent1', email='p1@example.com', role=User.Role.PARENT)

        response = authenticated_client.get('/api/auth/users/')

        assert response.status_code == status.HTTP_200_OK
        # +1 для authenticated_client.user
        assert len(response.data) >= 3

    def test_list_users_filter_by_role(self, authenticated_client):
        """Тест фильтрации пользователей по роли"""
        User.objects.create_user(username='student1', email='s1@example.com', role=User.Role.STUDENT)
        User.objects.create_user(username='student2', email='s2@example.com', role=User.Role.STUDENT)
        User.objects.create_user(username='teacher1', email='t1@example.com', role=User.Role.TEACHER)

        response = authenticated_client.get('/api/auth/users/?role=student')

        assert response.status_code == status.HTTP_200_OK
        # Должно быть минимум 2 студента (может быть больше если authenticated_client.user тоже студент)
        assert len(response.data) >= 2
        for user_data in response.data:
            assert user_data['role'] == User.Role.STUDENT

    def test_list_users_with_limit(self, authenticated_client):
        """Тест ограничения количества результатов"""
        for i in range(10):
            User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                role=User.Role.STUDENT
            )

        response = authenticated_client.get('/api/auth/users/?limit=5')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_list_users_without_authentication(self, api_client):
        """Тест получения списка без аутентификации"""
        response = api_client.get('/api/auth/users/')

        # DRF может возвращать 403 вместо 401 в некоторых случаях
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.parametrize('role', [
        User.Role.STUDENT,
        User.Role.TEACHER,
        User.Role.TUTOR,
        User.Role.PARENT
    ])
    def test_list_users_filter_each_role(self, authenticated_client, role):
        """Тест фильтрации по каждой роли"""
        User.objects.create_user(
            username=f'user_{role}',
            email=f'{role}@example.com',
            role=role
        )

        response = authenticated_client.get(f'/api/auth/users/?role={role}')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
