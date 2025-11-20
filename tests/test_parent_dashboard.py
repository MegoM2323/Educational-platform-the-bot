import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from materials.models import Subject, SubjectEnrollment, SubjectPayment, Material, MaterialProgress
from materials.parent_dashboard_service import ParentDashboardService
from payments.models import Payment

User = get_user_model()


class ParentDashboardServiceTest(TestCase):
    """
    Тесты для ParentDashboardService
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем родителя
        self.parent = User.objects.create_user(
            username='parent@test.com',
            email='parent@test.com',
            first_name='Иван',
            last_name='Иванов',
            role=User.Role.PARENT
        )
        
        # Создаем детей
        self.child1 = User.objects.create_user(
            username='child1@test.com',
            email='child1@test.com',
            first_name='Петр',
            last_name='Иванов',
            role=User.Role.STUDENT
        )
        
        self.child2 = User.objects.create_user(
            username='child2@test.com',
            email='child2@test.com',
            first_name='Мария',
            last_name='Иванова',
            role=User.Role.STUDENT
        )
        
        # Создаем преподавателя
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            first_name='Анна',
            last_name='Петрова',
            role=User.Role.TEACHER
        )
        
        # Создаем предметы
        self.subject1 = Subject.objects.create(
            name='Математика',
            description='Основы математики',
            color='#FF5733'
        )
        
        self.subject2 = Subject.objects.create(
            name='Физика',
            description='Основы физики',
            color='#33FF57'
        )
        
        # Создаем профили
        from accounts.models import ParentProfile, StudentProfile
        self.parent_profile = ParentProfile.objects.create(user=self.parent)
        self.parent_profile.children.add(self.child1, self.child2)
        
        StudentProfile.objects.create(user=self.child1, parent=self.parent)
        StudentProfile.objects.create(user=self.child2, parent=self.parent)
        
        # Создаем зачисления
        self.enrollment1 = SubjectEnrollment.objects.create(
            student=self.child1,
            subject=self.subject1,
            teacher=self.teacher
        )
        
        self.enrollment2 = SubjectEnrollment.objects.create(
            student=self.child2,
            subject=self.subject2,
            teacher=self.teacher
        )
        
        # Создаем материалы
        self.material1 = Material.objects.create(
            title='Урок 1: Сложение',
            description='Основы сложения',
            content='Содержание урока',
            author=self.teacher,
            subject=self.subject1,
            status=Material.Status.ACTIVE
        )
        
        self.material2 = Material.objects.create(
            title='Урок 1: Механика',
            description='Основы механики',
            content='Содержание урока',
            author=self.teacher,
            subject=self.subject2,
            status=Material.Status.ACTIVE
        )
        
        # Создаем прогресс
        MaterialProgress.objects.create(
            student=self.child1,
            material=self.material1,
            progress_percentage=75,
            time_spent=30
        )
        
        MaterialProgress.objects.create(
            student=self.child2,
            material=self.material2,
            progress_percentage=50,
            time_spent=20,
            is_completed=True
        )
    
    def test_service_initialization(self):
        """Тест инициализации сервиса"""
        service = ParentDashboardService(self.parent)
        self.assertEqual(service.parent_user, self.parent)
        self.assertEqual(service.parent_profile, self.parent_profile)
    
    def test_service_initialization_with_wrong_role(self):
        """Тест инициализации сервиса с неправильной ролью"""
        with self.assertRaises(ValueError):
            ParentDashboardService(self.child1)
    
    def test_get_children(self):
        """Тест получения детей"""
        service = ParentDashboardService(self.parent)
        children = service.get_children()
        
        self.assertEqual(children.count(), 2)
        self.assertIn(self.child1, children)
        self.assertIn(self.child2, children)
    
    def test_get_child_subjects(self):
        """Тест получения предметов ребенка"""
        service = ParentDashboardService(self.parent)
        subjects = service.get_child_subjects(self.child1)
        
        self.assertEqual(subjects.count(), 1)
        self.assertEqual(subjects.first().subject, self.subject1)
    
    def test_get_child_subjects_wrong_parent(self):
        """Тест получения предметов чужого ребенка"""
        service = ParentDashboardService(self.parent)
        
        # Создаем другого родителя и ребенка
        other_parent = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            role=User.Role.PARENT
        )
        other_child = User.objects.create_user(
            username='other_child@test.com',
            email='other_child@test.com',
            role=User.Role.STUDENT
        )
        
        with self.assertRaises(ValueError):
            service.get_child_subjects(other_child)
    
    def test_get_child_progress(self):
        """Тест получения прогресса ребенка"""
        service = ParentDashboardService(self.parent)
        progress = service.get_child_progress(self.child1)
        
        self.assertEqual(progress['total_materials'], 1)
        self.assertEqual(progress['completed_materials'], 0)
        self.assertEqual(progress['average_progress'], 75.0)
        self.assertEqual(progress['total_study_time'], 30)
        self.assertEqual(len(progress['subject_progress']), 1)
    
    def test_get_payment_status(self):
        """Тест получения статуса платежей"""
        service = ParentDashboardService(self.parent)
        
        # Создаем платеж
        payment = Payment.objects.create(
            amount=Decimal('1000.00'),
            service_name='Тестовая услуга'
        )
        
        SubjectPayment.objects.create(
            enrollment=self.enrollment1,
            payment=payment,
            amount=Decimal('1000.00'),
            status=SubjectPayment.Status.PENDING
        )
        
        payment_status = service.get_payment_status(self.child1)
        
        self.assertEqual(len(payment_status), 1)
        self.assertEqual(payment_status[0]['subject'], 'Математика')
        self.assertEqual(payment_status[0]['status'], 'pending')
    
    def test_initiate_payment(self):
        """Тест инициации платежа"""
        service = ParentDashboardService(self.parent)
        
        payment_data = service.initiate_payment(
            child=self.child1,
            subject_id=self.subject1.id,
            amount=Decimal('1500.00'),
            description='Оплата за математику'
        )
        
        self.assertIn('payment_id', payment_data)
        self.assertEqual(payment_data['amount'], Decimal('1500.00'))
        self.assertEqual(payment_data['subject'], 'Математика')
        
        # Проверяем, что платеж создан в базе
        payment = Payment.objects.get(id=payment_data['payment_id'])
        self.assertEqual(payment.amount, Decimal('1500.00'))
        
        # Проверяем, что создан SubjectPayment
        subject_payment = SubjectPayment.objects.get(payment=payment)
        self.assertEqual(subject_payment.amount, Decimal('1500.00'))
        self.assertEqual(subject_payment.enrollment, self.enrollment1)
    
    def test_get_dashboard_data(self):
        """Тест получения полных данных дашборда"""
        service = ParentDashboardService(self.parent)
        dashboard_data = service.get_dashboard_data()
        
        self.assertIn('parent', dashboard_data)
        self.assertIn('children', dashboard_data)
        self.assertIn('total_children', dashboard_data)
        
        self.assertEqual(dashboard_data['total_children'], 2)
        self.assertEqual(len(dashboard_data['children']), 2)
        
        # Проверяем данные первого ребенка
        child1_data = next(c for c in dashboard_data['children'] if c['id'] == self.child1.id)
        self.assertEqual(child1_data['name'], 'Петр Иванов')
        self.assertIn('progress', child1_data)
        self.assertIn('payments', child1_data)


class ParentDashboardAPITest(APITestCase):
    """
    Тесты для API родительского дашборда
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем родителя
        self.parent = User.objects.create_user(
            username='parent@test.com',
            email='parent@test.com',
            first_name='Иван',
            last_name='Иванов',
            role=User.Role.PARENT
        )
        
        # Создаем ребенка
        self.child = User.objects.create_user(
            username='child@test.com',
            email='child@test.com',
            first_name='Петр',
            last_name='Иванов',
            role=User.Role.STUDENT
        )
        
        # Создаем преподавателя
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            first_name='Анна',
            last_name='Петрова',
            role=User.Role.TEACHER
        )
        
        # Создаем предмет
        self.subject = Subject.objects.create(
            name='Математика',
            description='Основы математики',
            color='#FF5733'
        )
        
        # Создаем профили
        from accounts.models import ParentProfile, StudentProfile
        self.parent_profile = ParentProfile.objects.create(user=self.parent)
        self.parent_profile.children.add(self.child)
        
        StudentProfile.objects.create(user=self.child, parent=self.parent)
        
        # Создаем зачисление
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.child,
            subject=self.subject,
            teacher=self.teacher
        )
    
    def test_parent_dashboard_authenticated(self):
        """Тест доступа к дашборду родителя для аутентифицированного пользователя"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('parent-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('parent', response.data)
        self.assertIn('children', response.data)
    
    def test_parent_dashboard_unauthenticated(self):
        """Тест доступа к дашборду родителя для неаутентифицированного пользователя"""
        url = reverse('parent-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_parent_dashboard_wrong_role(self):
        """Тест доступа к дашборду родителя с неправильной ролью"""
        self.client.force_authenticate(user=self.child)
        url = reverse('parent-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_children(self):
        """Тест получения списка детей"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('parent-children')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Петр Иванов')
    
    def test_get_child_subjects(self):
        """Тест получения предметов ребенка"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('child-subjects', kwargs={'child_id': self.child.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['subject']['name'], 'Математика')
    
    def test_get_child_progress(self):
        """Тест получения прогресса ребенка"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('child-progress', kwargs={'child_id': self.child.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_materials', response.data)
        self.assertIn('completed_materials', response.data)
    
    def test_get_payment_status(self):
        """Тест получения статуса платежей"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('child-payments', kwargs={'child_id': self.child.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_child_teachers(self):
        """Тест получения преподавателей ребенка"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('child-teachers', kwargs={'child_id': self.child.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_parent_payments(self):
        """Тест истории платежей родителя"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('parent-payments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_parent_pending_payments(self):
        """Тест ожидающих платежей родителя"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('parent-pending-payments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_initiate_payment(self):
        """Тест инициации платежа"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('initiate-payment', kwargs={
            'child_id': self.child.id,
            'subject_id': self.subject.id
        })
        
        data = {
            'amount': '1500.00',
            'description': 'Оплата за математику'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('payment_id', response.data)
        self.assertEqual(response.data['amount'], '1500.00')
    
    def test_initiate_payment_invalid_amount(self):
        """Тест инициации платежа с неверной суммой"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('initiate-payment', kwargs={
            'child_id': self.child.id,
            'subject_id': self.subject.id
        })
        
        data = {
            'amount': '-100.00',
            'description': 'Неверная сумма'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_reports(self):
        """Тест получения отчетов"""
        self.client.force_authenticate(user=self.parent)
        url = reverse('parent-reports')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])  # Пока пустой список
    
    def test_access_other_parents_child(self):
        """Тест доступа к чужому ребенку"""
        # Создаем другого родителя и ребенка
        other_parent = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            role=User.Role.PARENT
        )
        other_child = User.objects.create_user(
            username='other_child@test.com',
            email='other_child@test.com',
            role=User.Role.STUDENT
        )
        
        self.client.force_authenticate(user=self.parent)
        url = reverse('child-subjects', kwargs={'child_id': other_child.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
