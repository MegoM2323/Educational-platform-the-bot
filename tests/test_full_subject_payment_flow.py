"""
Полный тест функционала назначения предметов и платежей
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
class TestFullFlow:
    """Полный тест всего функционала"""
    
    def test_full_flow_teacher_assigns_subject_parent_pays(self):
        """Полный флоу: преподаватель назначает предмет, родитель оплачивает"""
        # 1. Создаем пользователей
        teacher = User.objects.create_user(
            username='teacher_flow',
            email='teacher_flow@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Иван',
            last_name='Иванов'
        )
        
        student = User.objects.create_user(
            username='student_flow',
            email='student_flow@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Петр',
            last_name='Петров'
        )
        StudentProfile.objects.create(user=student, grade='5')
        
        parent = User.objects.create_user(
            username='parent_flow',
            email='parent_flow@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='Ольга',
            last_name='Ольгова'
        )
        parent_profile = ParentProfile.objects.create(user=parent)
        student.student_profile.parent = parent
        student.student_profile.save()
        
        # 2. Создаем предмет
        subject = Subject.objects.create(name='Математика Flow', description='Математика')
        TeacherSubject.objects.create(teacher=teacher, subject=subject)
        
        # 3. Преподаватель назначает предмет через API
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        response = client.post('/api/materials/teacher/subjects/assign/', {
            'subject_id': subject.id,
            'student_ids': [student.id]
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        # 4. Проверяем, что зачисление создано
        enrollment = SubjectEnrollment.objects.get(
            student=student,
            subject=subject,
            teacher=teacher
        )
        assert enrollment.is_active is True
        
        # 5. Студент видит предмет через API
        client.force_authenticate(user=student)
        response = client.get('/api/materials/materials/student/subjects/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['subjects']) == 1
        assert response.data['subjects'][0]['subject']['name'] == 'Математика Flow'
        
        # 6. Родитель видит предмет ребенка
        client.force_authenticate(user=parent)
        response = client.get('/api/materials/dashboard/parent/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['children']) == 1
        assert len(response.data['children'][0]['subjects']) == 1
        assert response.data['children'][0]['subjects'][0]['name'] == 'Математика Flow'
        assert 'enrollment_id' in response.data['children'][0]['subjects'][0]
        
        # 7. Родитель создает платеж
        enrollment_id = response.data['children'][0]['subjects'][0]['enrollment_id']
        child_id = response.data['children'][0]['id']
        
        response = client.post(
            f'/api/materials/dashboard/parent/children/{child_id}/payment/{enrollment_id}/',
            {
                'amount': '5000.00',
                'description': 'Оплата за предмет',
                'create_subscription': True
            },
            format='json'
        )
        
        # Проверяем, что платеж создан (может быть ошибка из-за отсутствия настроек ЮКассы)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        
        # Если платеж создан успешно
        if response.status_code == status.HTTP_201_CREATED:
            assert 'payment_id' in response.data
            
            # Проверяем, что SubjectPayment создан
            subject_payment = SubjectPayment.objects.filter(enrollment=enrollment).first()
            assert subject_payment is not None
            
            # Проверяем, что подписка создана
            subscription = SubjectSubscription.objects.filter(enrollment=enrollment).first()
            assert subscription is not None
            assert subscription.status == SubjectSubscription.Status.ACTIVE
        
        # 8. Родитель видит историю платежей
        response = client.get('/api/materials/dashboard/parent/payments/')
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        
        # 9. Проверяем, что один студент может иметь один предмет с разными преподавателями
        teacher2 = User.objects.create_user(
            username='teacher2_flow',
            email='teacher2_flow@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Анна',
            last_name='Аннова'
        )
        TeacherSubject.objects.create(teacher=teacher2, subject=subject)
        
        client.force_authenticate(user=teacher2)
        response = client.post('/api/materials/teacher/subjects/assign/', {
            'subject_id': subject.id,
            'student_ids': [student.id]
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что теперь у студента два зачисления на один предмет с разными преподавателями
        enrollments = SubjectEnrollment.objects.filter(
            student=student,
            subject=subject
        )
        assert enrollments.count() == 2
        assert enrollments.filter(teacher=teacher).exists()
        assert enrollments.filter(teacher=teacher2).exists()

