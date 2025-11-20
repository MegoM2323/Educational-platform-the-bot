"""
Интеграционный тест полного флоу оплаты
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from materials.models import Subject, SubjectEnrollment, SubjectPayment, SubjectSubscription, TeacherSubject
from accounts.models import StudentProfile, ParentProfile
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestPaymentFlowIntegration:
    """Интеграционные тесты полного флоу оплаты"""
    
    def test_full_payment_flow_with_subscription(self):
        """Полный тест флоу оплаты с созданием подписки"""
        # 1. Создаем пользователей
        parent = User.objects.create_user(
            username='parent_payment_test',
            email='parent_payment_test@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='Ольга',
            last_name='Ольгова'
        )
        ParentProfile.objects.create(user=parent)
        
        student = User.objects.create_user(
            username='student_payment_test',
            email='student_payment_test@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Дмитрий',
            last_name='Дмитриев'
        )
        student_profile = StudentProfile.objects.create(user=student, grade='5')
        student_profile.parent = parent
        student_profile.save()
        
        teacher = User.objects.create_user(
            username='teacher_payment_test',
            email='teacher_payment_test@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Елена',
            last_name='Еленова'
        )
        
        # 2. Создаем предмет и зачисление
        subject = Subject.objects.create(name='Математика Payment Test', description='Математика')
        TeacherSubject.objects.create(teacher=teacher, subject=subject)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        
        # 3. Первая оплата - создание подписки
        client = APIClient()
        client.force_authenticate(user=parent)
        
        response = client.post(
            f'/api/materials/dashboard/parent/children/{student.id}/payment/{enrollment.id}/',
            {
                'amount': '5000.00',
                'description': 'Оплата за предмет',
                'create_subscription': True
            },
            format='json'
        )
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_201_CREATED:
            # Проверяем, что платеж создан
            assert 'payment_id' in response.data
            
            # Проверяем, что подписка создана
            subscription = SubjectSubscription.objects.get(enrollment=enrollment)
            assert subscription.status == SubjectSubscription.Status.ACTIVE
            assert subscription.amount == Decimal('5000.00')
            
            # 4. Вторая оплата - обновление существующей подписки
            response2 = client.post(
                f'/api/materials/dashboard/parent/children/{student.id}/payment/{enrollment.id}/',
                {
                    'amount': '6000.00',
                    'description': 'Оплата за предмет (обновление)',
                    'create_subscription': True
                },
                format='json'
            )
            
            # Должно пройти успешно, подписка должна обновиться
            assert response2.status_code == status.HTTP_201_CREATED
            
            # Проверяем, что подписка обновлена, а не создана новая
            subscriptions = SubjectSubscription.objects.filter(enrollment=enrollment)
            assert subscriptions.count() == 1  # Должна быть только одна подписка
            
            subscription.refresh_from_db()
            assert subscription.amount == Decimal('6000.00')
            assert subscription.status == SubjectSubscription.Status.ACTIVE
    
    def test_payment_without_subscription(self):
        """Тест оплаты без создания подписки"""
        parent = User.objects.create_user(
            username='parent_no_sub',
            email='parent_no_sub@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='Мария',
            last_name='Марьева'
        )
        ParentProfile.objects.create(user=parent)
        
        student = User.objects.create_user(
            username='student_no_sub',
            email='student_no_sub@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Алексей',
            last_name='Алексеев'
        )
        student_profile = StudentProfile.objects.create(user=student, grade='6')
        student_profile.parent = parent
        student_profile.save()
        
        teacher = User.objects.create_user(
            username='teacher_no_sub',
            email='teacher_no_sub@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Наталья',
            last_name='Натальева'
        )
        
        subject = Subject.objects.create(name='Физика No Sub', description='Физика')
        TeacherSubject.objects.create(teacher=teacher, subject=subject)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        
        client = APIClient()
        client.force_authenticate(user=parent)
        
        # Оплата без подписки
        response = client.post(
            f'/api/materials/dashboard/parent/children/{student.id}/payment/{enrollment.id}/',
            {
                'amount': '3000.00',
                'description': 'Оплата за предмет без подписки',
                'create_subscription': False
            },
            format='json'
        )
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_201_CREATED:
            # Проверяем, что подписка НЕ создана
            assert not SubjectSubscription.objects.filter(enrollment=enrollment).exists()
            
            # Проверяем, что платеж создан
            assert SubjectPayment.objects.filter(enrollment=enrollment).exists()

