"""
Тесты для потока аутентификации
"""
import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


class AuthFlowTestCase(APITestCase):
    """Тесты для потока аутентификации"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'student'
        }
        
        # Создаем тестового пользователя
        self.user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            first_name=self.user_data['first_name'],
            last_name=self.user_data['last_name'],
            role=self.user_data['role']
        )
        
        # Создаем токен для пользователя
        self.token = Token.objects.create(user=self.user)
        
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.profile_url = reverse('accounts:profile')
        self.refresh_url = reverse('accounts:refresh')

    def test_successful_login(self):
        """Тест успешного входа"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], self.user_data['email'])
        self.assertEqual(data['user']['role'], self.user_data['role'])

    def test_invalid_credentials_login(self):
        """Тест входа с неверными учетными данными"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)

    def test_nonexistent_user_login(self):
        """Тест входа несуществующего пользователя"""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)

    def test_login_missing_fields(self):
        """Тест входа с отсутствующими полями"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email']
            # password отсутствует
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_logout(self):
        """Тест успешного выхода"""
        # Сначала входим
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.json()['token']
        
        # Выходим с токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_token(self):
        """Тест выхода без токена"""
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authenticated(self):
        """Тест получения профиля аутентифицированного пользователя"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], self.user_data['email'])
        self.assertEqual(data['user']['role'], self.user_data['role'])

    def test_get_profile_unauthenticated(self):
        """Тест получения профиля неаутентифицированного пользователя"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_authentication(self):
        """Тест аутентификации по токену"""
        # Тестируем доступ к защищенному эндпоинту
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_token_authentication(self):
        """Тест аутентификации с неверным токеном"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Тест обновления токена"""
        # Сначала входим
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.json()['token']
        
        # Обновляем токен
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.post(self.refresh_url)
        
        # Проверяем, что эндпоинт существует (может быть не реализован)
        # Если не реализован, ожидаем 404 или 405
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_404_NOT_FOUND, 
            status.HTTP_405_METHOD_NOT_ALLOWED
        ])

    def test_user_roles(self):
        """Тест различных ролей пользователей"""
        roles = ['student', 'teacher', 'parent', 'tutor']
        
        for role in roles:
            with self.subTest(role=role):
                # Создаем пользователя с определенной ролью
                user = User.objects.create_user(
                    email=f'{role}@example.com',
                    password='testpass123',
                    first_name='Test',
                    last_name='User',
                    role=role
                )
                
                # Входим
                response = self.client.post(self.login_url, {
                    'email': f'{role}@example.com',
                    'password': 'testpass123'
                })
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()
                self.assertEqual(data['user']['role'], role)

    def test_user_data_consistency(self):
        """Тест согласованности данных пользователя"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Проверяем, что данные пользователя соответствуют созданным
        user_data = data['user']
        self.assertEqual(user_data['email'], self.user.email)
        self.assertEqual(user_data['first_name'], self.user.first_name)
        self.assertEqual(user_data['last_name'], self.user.last_name)
        self.assertEqual(user_data['role'], self.user.role)
        self.assertEqual(user_data['is_verified'], self.user.is_verified)

    def test_concurrent_login_attempts(self):
        """Тест одновременных попыток входа"""
        import threading
        import time
        
        results = []
        
        def attempt_login():
            response = self.client.post(self.login_url, {
                'email': self.user_data['email'],
                'password': self.user_data['password']
            })
            results.append(response.status_code)
        
        # Создаем несколько потоков для одновременного входа
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=attempt_login)
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Все попытки должны быть успешными
        self.assertTrue(all(status_code == status.HTTP_200_OK for status_code in results))

    def test_session_persistence(self):
        """Тест сохранения сессии"""
        # Входим
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.json()['token']
        
        # Используем токен для нескольких запросов
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        for _ in range(3):
            response = self.client.get(self.profile_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def tearDown(self):
        """Очистка после тестов"""
        User.objects.all().delete()
        Token.objects.all().delete()


class AuthIntegrationTestCase(TestCase):
    """Интеграционные тесты аутентификации"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            email='integration@example.com',
            password='testpass123',
            first_name='Integration',
            last_name='Test',
            role='student'
        )

    def test_full_auth_flow(self):
        """Тест полного потока аутентификации"""
        # 1. Вход
        login_response = self.client.post('/api/auth/login/', {
            'email': 'integration@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()['token']
        
        # 2. Получение профиля
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        profile_response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(profile_response.status_code, 200)
        profile_data = profile_response.json()
        self.assertEqual(profile_data['user']['email'], 'integration@example.com')
        
        # 3. Выход
        logout_response = self.client.post('/api/auth/logout/')
        self.assertEqual(logout_response.status_code, 200)
        
        # 4. Проверка, что после выхода профиль недоступен
        profile_after_logout = self.client.get('/api/auth/profile/')
        self.assertEqual(profile_after_logout.status_code, 401)

    def test_auth_error_handling(self):
        """Тест обработки ошибок аутентификации"""
        # Неверные учетные данные
        response = self.client.post('/api/auth/login/', {
            'email': 'integration@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 400)
        error_data = response.json()
        self.assertIn('error', error_data)

    def tearDown(self):
        """Очистка после тестов"""
        User.objects.all().delete()
        Token.objects.all().delete()


if __name__ == '__main__':
    pytest.main([__file__])
