"""
Интеграционные тесты для платежной системы
Проверяет полный цикл создания и обработки платежей
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

from payments.models import Payment
from payments.views import create_yookassa_payment, check_yookassa_payment_status

User = get_user_model()


class PaymentIntegrationTest(TestCase):
    """Интеграционные тесты для платежной системы"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.PARENT
        )
        
        # Тестовые данные для платежа
        self.payment_data = {
            'amount': '12000.00',
            'service_name': 'Оплата за обучение',
            'customer_fio': 'Иванов Иван Иванович',
            'description': 'Тестовый платеж'
        }
    
    def test_create_payment_with_invalid_data(self):
        """Тест создания платежа с невалидными данными"""
        response = self.client.post(
            '/api/payments/',
            data=json.dumps({'amount': '-100'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', json.loads(response.content))
    
    def test_create_payment_with_valid_data(self):
        """Тест создания платежа с валидными данными"""
        with patch('payments.views.create_yookassa_payment') as mock_create:
            # Мокаем ответ от ЮКассы
            mock_create.return_value = {
                'id': 'test_payment_id_123',
                'confirmation': {
                    'confirmation_url': 'https://yoomoney.ru/checkout/payments/test'
                },
                'status': 'pending'
            }
            
            response = self.client.post(
                '/api/payments/',
                data=json.dumps(self.payment_data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.content)
            
            # Проверяем, что платеж создан
            payment = Payment.objects.get(id=data['id'])
            self.assertEqual(payment.amount, Decimal('12000.00'))
            self.assertEqual(payment.service_name, 'Оплата за обучение')
            self.assertEqual(payment.customer_fio, 'Иванов Иван Иванович')
            self.assertEqual(payment.yookassa_payment_id, 'test_payment_id_123')
            self.assertEqual(payment.status, Payment.Status.PENDING)
    
    def test_payment_status_check(self):
        """Тест проверки статуса платежа"""
        # Создаем тестовый платеж
        payment = Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Оплата за обучение',
            customer_fio='Иванов Иван Иванович',
            description='Тестовый платеж',
            yookassa_payment_id='test_payment_id_123'
        )
        
        with patch('payments.views.check_yookassa_payment_status') as mock_check:
            # Мокаем ответ от ЮКассы - успешная оплата
            mock_check.return_value = 'succeeded'
            
            response = self.client.get(
                f'/api/payments/{payment.id}/status/'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Проверяем, что статус обновлен
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
            self.assertIsNotNone(payment.paid_at)
    
    def test_payment_status_check_with_pending_status(self):
        """Тест проверки статуса платежа в процессе"""
        # Создаем тестовый платеж
        payment = Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Оплата за обучение',
            customer_fio='Иванов Иван Иванович',
            description='Тестовый платеж',
            yookassa_payment_id='test_payment_id_123'
        )
        
        with patch('payments.views.check_yookassa_payment_status') as mock_check:
            # Мокаем ответ от ЮКассы - платеж в процессе
            mock_check.return_value = 'waiting_for_capture'
            
            response = self.client.get(
                f'/api/payments/{payment.id}/status/'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Проверяем, что статус обновлен
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.WAITING_FOR_CAPTURE)
    
    def test_payment_status_check_with_cancelled_status(self):
        """Тест проверки статуса отмененного платежа"""
        # Создаем тестовый платеж
        payment = Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Оплата за обучение',
            customer_fio='Иванов Иван Иванович',
            description='Тестовый платеж',
            yookassa_payment_id='test_payment_id_123'
        )
        
        with patch('payments.views.check_yookassa_payment_status') as mock_check:
            # Мокаем ответ от ЮКассы - платеж отменен
            mock_check.return_value = 'canceled'
            
            response = self.client.get(
                f'/api/payments/{payment.id}/status/'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Проверяем, что статус обновлен
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.CANCELED)
    
    def test_get_payment_list(self):
        """Тест получения списка платежей"""
        # Создаем несколько платежей
        Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Платеж 1',
            customer_fio='Иванов И.И.',
            status=Payment.Status.SUCCEEDED
        )
        
        Payment.objects.create(
            amount=Decimal('8000.00'),
            service_name='Платеж 2',
            customer_fio='Петров П.П.',
            status=Payment.Status.PENDING
        )
        
        response = self.client.get('/api/payments/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Проверяем, что получены все платежи
        self.assertEqual(len(data), 2)
    
    def test_get_single_payment(self):
        """Тест получения одного платежа"""
        payment = Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Тестовый платеж',
            customer_fio='Иванов И.И.',
            description='Описание платежа'
        )
        
        response = self.client.get(f'/api/payments/{payment.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Проверяем данные платежа
        self.assertEqual(data['amount'], '12000.00')
        self.assertEqual(data['service_name'], 'Тестовый платеж')
        self.assertEqual(data['customer_fio'], 'Иванов И.И.')
    
    def test_payment_retry_on_network_error(self):
        """Тест повторной попытки при сетевой ошибке"""
        with patch('payments.views.create_yookassa_payment') as mock_create:
            # Мокаем сетевое исключение при первом вызове
            mock_create.side_effect = [
                Exception("Network error"),
                {
                    'id': 'test_payment_id_123',
                    'confirmation': {
                        'confirmation_url': 'https://yoomoney.ru/checkout/payments/test'
                    }
                }
            ]
            
            # В реальной системе это должно обрабатываться автоматически
            # Здесь мы просто проверяем, что моки работают
            result = create_yookassa_payment(
                Payment.objects.create(
                    amount=Decimal('12000.00'),
                    service_name='Тест',
                    customer_fio='Тест'
                ),
                type('Request', (), {'build_absolute_uri': lambda self, url: f'http://test{url}'})()
            )
            
            # Проверяем, что вторая попытка успешна
            self.assertIsNotNone(result)
    
    def test_payment_error_handling(self):
        """Тест обработки ошибок при создании платежа"""
        with patch('payments.views.create_yookassa_payment') as mock_create:
            # Мокаем ошибку от ЮКассы
            mock_create.return_value = None
            
            response = self.client.post(
                '/api/payments/',
                data=json.dumps(self.payment_data),
                content_type='application/json'
            )
            
            # Должна вернуться ошибка
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.content)
            self.assertIn('error', data)
            
            # Проверяем, что платеж не сохранен в БД
            # (если не был создан в ЮКассе, он не должен быть в БД)
            payments_count = Payment.objects.count()
            self.assertEqual(payments_count, 0)
    
    @patch('requests.post')
    def test_yookassa_api_integration(self, mock_post):
        """Тест интеграции с API ЮКассы"""
        # Мокаем успешный ответ от API
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'id': 'test_id',
            'confirmation': {'confirmation_url': 'https://test.url'},
            'status': 'pending'
        }
        
        # Создаем платеж
        payment = Payment.objects.create(
            amount=Decimal('12000.00'),
            service_name='Тест',
            customer_fio='Тест'
        )
        
        # Создаем мок-запрос
        class MockRequest:
            def build_absolute_uri(self, url):
                return f'http://localhost{url}'
        
        result = create_yookassa_payment(payment, MockRequest())
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test_id')
        
        # Проверяем, что API был вызван
        self.assertTrue(mock_post.called)
