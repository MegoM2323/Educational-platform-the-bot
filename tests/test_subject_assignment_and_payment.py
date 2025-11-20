"""
Тесты для проверки функционала назначения предметов и платежей
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from materials.models import Subject, SubjectEnrollment, SubjectPayment, SubjectSubscription, TeacherSubject
from accounts.models import StudentProfile, ParentProfile
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestSubjectAssignment:
    """Тесты для назначения предметов"""
    
    def test_teacher_can_assign_subject_to_student(self):
        """Преподаватель может назначить предмет ученику"""
        # Создаем пользователей
        teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Иван',
            last_name='Иванов'
        )
        
        student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Петр',
            last_name='Петров'
        )
        StudentProfile.objects.create(user=student, grade='5')
        
        # Создаем предмет
        subject = Subject.objects.create(name='Математика', description='Математика для 5 класса')
        
        # Преподаватель ведет этот предмет
        TeacherSubject.objects.create(teacher=teacher, subject=subject)
        
        # Назначаем предмет
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        
        assert enrollment.student == student
        assert enrollment.subject == subject
        assert enrollment.teacher == teacher
        assert enrollment.is_active is True
    
    def test_same_student_can_have_same_subject_with_different_teachers(self):
        """Один студент может иметь один предмет с разными преподавателями"""
        student = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Сергей',
            last_name='Сергеев'
        )
        StudentProfile.objects.create(user=student, grade='5')
        
        teacher1 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Анна',
            last_name='Аннова'
        )
        
        teacher2 = User.objects.create_user(
            username='teacher3',
            email='teacher3@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Марьева'
        )
        
        subject = Subject.objects.create(name='Русский язык', description='Русский язык')
        
        # Создаем два зачисления с разными преподавателями
        enrollment1 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher1,
            assigned_by=teacher1,
            is_active=True
        )
        
        enrollment2 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher2,
            assigned_by=teacher2,
            is_active=True
        )
        
        assert enrollment1.teacher != enrollment2.teacher
        assert enrollment1.student == enrollment2.student
        assert enrollment1.subject == enrollment2.subject


@pytest.mark.django_db
class TestPaymentFlow:
    """Тесты для платежей"""
    
    def test_parent_can_create_payment_for_subject(self):
        """Родитель может создать платеж за предмет"""
        # Создаем пользователей
        parent = User.objects.create_user(
            username='parent1',
            email='parent1@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='Ольга',
            last_name='Ольгова'
        )
        ParentProfile.objects.create(user=parent)
        
        student = User.objects.create_user(
            username='student3',
            email='student3@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Дмитрий',
            last_name='Дмитриев'
        )
        student_profile = StudentProfile.objects.create(user=student, grade='5')
        student_profile.parent = parent
        student_profile.save()
        
        teacher = User.objects.create_user(
            username='teacher4',
            email='teacher4@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Елена',
            last_name='Еленова'
        )
        
        subject = Subject.objects.create(name='Физика', description='Физика')
        
        # Создаем зачисление
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        
        # Создаем платеж
        payment = Payment.objects.create(
            amount=Decimal('5000.00'),
            service_name=f'Оплата за предмет: {subject.name}',
            customer_fio=f'{parent.first_name} {parent.last_name}',
            description=f'Оплата за предмет {subject.name}',
            metadata={
                'enrollment_id': enrollment.id,
                'student_id': student.id,
                'teacher_id': teacher.id,
            }
        )
        
        # Создаем платеж по предмету
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('5000.00'),
            due_date=timezone.now() + timezone.timedelta(days=7)
        )
        
        assert subject_payment.enrollment == enrollment
        assert subject_payment.amount == Decimal('5000.00')
        assert subject_payment.status == SubjectPayment.Status.PENDING
    
    def test_subscription_creation(self):
        """Создание подписки для регулярных платежей"""
        student = User.objects.create_user(
            username='student4',
            email='student4@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Алексей',
            last_name='Алексеев'
        )
        StudentProfile.objects.create(user=student, grade='6')
        
        teacher = User.objects.create_user(
            username='teacher5',
            email='teacher5@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Наталья',
            last_name='Натальева'
        )
        
        subject = Subject.objects.create(name='Химия', description='Химия')
        
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        
        # Создаем подписку
        subscription = SubjectSubscription.objects.create(
            enrollment=enrollment,
            amount=Decimal('5000.00'),
            status=SubjectSubscription.Status.ACTIVE,
            next_payment_date=timezone.now() + timezone.timedelta(weeks=1),
            payment_interval_weeks=1
        )
        
        assert subscription.enrollment == enrollment
        assert subscription.amount == Decimal('5000.00')
        assert subscription.status == SubjectSubscription.Status.ACTIVE
        assert subscription.payment_interval_weeks == 1

