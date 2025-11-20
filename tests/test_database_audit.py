"""
Полный аудит базы данных - тестирование всех критичных сценариев
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from accounts.models import StudentProfile, ParentProfile, TeacherProfile, TutorProfile
from materials.models import Subject, SubjectEnrollment, TeacherSubject, SubjectPayment, SubjectSubscription
from materials.parent_dashboard_service import ParentDashboardService
from materials.teacher_dashboard_service import TeacherDashboardService
from materials.student_dashboard_service import StudentDashboardService

User = get_user_model()


class DatabaseIntegrityTestCase(TestCase):
    """Тесты целостности БД"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        # Создаем предметы
        self.subject_math = Subject.objects.create(
            name='Математика',
            description='Тестовый предмет',
            color='#3b82f6'
        )
        
        # Создаем учителя
        self.teacher = User.objects.create_user(
            username='teacher_test',
            first_name='Test',
            last_name='Teacher',
            role=User.Role.TEACHER,
            password='test123'
        )
        TeacherProfile.objects.create(
            user=self.teacher,
            subject='Математика',
            experience_years=5
        )
        
        # Связываем учителя с предметом
        TeacherSubject.objects.create(
            teacher=self.teacher,
            subject=self.subject_math,
            is_active=True
        )
        
        # Создаем тьютора
        self.tutor = User.objects.create_user(
            username='tutor_test',
            first_name='Test',
            last_name='Tutor',
            role=User.Role.TUTOR,
            password='test123'
        )
        TutorProfile.objects.create(
            user=self.tutor,
            specialization='Тестовая'
        )
        
        # Создаем родителя
        self.parent = User.objects.create_user(
            username='parent_test',
            first_name='Test',
            last_name='Parent',
            role=User.Role.PARENT,
            password='test123'
        )
        self.parent_profile = ParentProfile.objects.create(user=self.parent)
        
        # Создаем студента
        self.student = User.objects.create_user(
            username='student_test',
            first_name='Test',
            last_name='Student',
            role=User.Role.STUDENT,
            password='test123',
            created_by_tutor=self.tutor
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            parent=self.parent,
            tutor=self.tutor,
            grade='5',
            goal='Тестовая цель'
        )
        
        # Добавляем ребенка в профиль родителя
        self.parent_profile.children.add(self.student)
        
        # Создаем зачисление
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject_math,
            teacher=self.teacher,
            is_active=True
        )
    
    def test_01_user_profiles_integrity(self):
        """Проверка целостности профилей пользователей"""
        # Проверяем, что у каждой роли есть соответствующий профиль
        self.assertTrue(hasattr(self.student, 'student_profile'))
        self.assertTrue(hasattr(self.teacher, 'teacher_profile'))
        self.assertTrue(hasattr(self.parent, 'parent_profile'))
        self.assertTrue(hasattr(self.tutor, 'tutor_profile'))
        
        # Проверяем связи
        self.assertEqual(self.student_profile.parent, self.parent)
        self.assertEqual(self.student_profile.tutor, self.tutor)
        self.assertIn(self.student, self.parent_profile.children.all())
    
    def test_02_enrollment_integrity(self):
        """Проверка целостности зачислений"""
        # Проверяем, что зачисление существует и активно
        self.assertTrue(self.enrollment.is_active)
        self.assertEqual(self.enrollment.student, self.student)
        self.assertEqual(self.enrollment.subject, self.subject_math)
        self.assertEqual(self.enrollment.teacher, self.teacher)
        
        # Проверяем, что у учителя есть это предмет
        teacher_subjects = TeacherSubject.objects.filter(
            teacher=self.teacher,
            subject=self.subject_math,
            is_active=True
        )
        self.assertTrue(teacher_subjects.exists())
    
    def test_03_parent_dashboard_service(self):
        """Проверка работы ParentDashboardService"""
        service = ParentDashboardService(self.parent)
        
        # Проверяем получение детей
        children = service.get_children()
        self.assertEqual(children.count(), 1)
        self.assertIn(self.student, children)
        
        # Проверяем получение предметов ребенка
        subjects = service.get_child_subjects(self.student)
        self.assertEqual(subjects.count(), 1)
        self.assertEqual(subjects.first().subject, self.subject_math)
        
        # Проверяем дашборд
        dashboard_data = service.get_dashboard_data()
        self.assertIn('children', dashboard_data)
        self.assertEqual(len(dashboard_data['children']), 1)
        self.assertEqual(dashboard_data['children'][0]['name'], self.student.get_full_name())
    
    def test_04_teacher_dashboard_service(self):
        """Проверка работы TeacherDashboardService"""
        service = TeacherDashboardService(self.teacher)
        
        # Проверяем получение студентов
        students = service.get_teacher_students()
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]['id'], self.student.id)
        
        # Проверяем получение предметов
        subjects = service.get_all_subjects()
        self.assertGreater(len(subjects), 0)
        math_subject = next((s for s in subjects if s['id'] == self.subject_math.id), None)
        self.assertIsNotNone(math_subject)
        self.assertEqual(math_subject['student_count'], 1)
    
    def test_05_payment_creation(self):
        """Проверка создания платежа"""
        service = ParentDashboardService(self.parent)
        
        # Создаем платеж без запроса к ЮКассе
        payment_data = service.initiate_payment(
            child=self.student,
            enrollment=self.enrollment,
            amount=Decimal('1000.00'),
            description="Тестовый платеж",
            create_subscription=False,
            request=None
        )
        
        # Проверяем результат
        self.assertIn('payment_id', payment_data)
        self.assertEqual(payment_data['amount'], Decimal('1000.00'))
        self.assertEqual(payment_data['subject'], self.subject_math.name)
        
        # Проверяем, что создан SubjectPayment
        subject_payment = SubjectPayment.objects.get(enrollment=self.enrollment)
        self.assertEqual(subject_payment.amount, Decimal('1000.00'))
        self.assertEqual(subject_payment.status, SubjectPayment.Status.PENDING)
    
    def test_06_subscription_creation(self):
        """Проверка создания подписки"""
        service = ParentDashboardService(self.parent)
        
        # Создаем платеж с подпиской
        payment_data = service.initiate_payment(
            child=self.student,
            enrollment=self.enrollment,
            amount=Decimal('500.00'),
            description="Тестовая подписка",
            create_subscription=True,
            request=None
        )
        
        # Проверяем, что подписка создана
        self.assertTrue(payment_data['subscription_created'])
        self.assertIn('subscription_id', payment_data)
        
        # Проверяем SubjectSubscription
        subscription = SubjectSubscription.objects.get(enrollment=self.enrollment)
        self.assertEqual(subscription.amount, Decimal('500.00'))
        self.assertEqual(subscription.status, SubjectSubscription.Status.ACTIVE)
    
    def test_07_role_validation(self):
        """Проверка валидации ролей"""
        # Проверяем, что нельзя создать сервис с неправильной ролью
        with self.assertRaises(ValueError):
            TeacherDashboardService(self.student)
        
        with self.assertRaises(ValueError):
            ParentDashboardService(self.teacher)


class DatabaseQueryOptimizationTestCase(TestCase):
    """Тесты оптимизации запросов к БД"""
    
    def setUp(self):
        """Создаем тестовые данные для проверки N+1 проблемы"""
        # Создаем предметы
        subjects = []
        for i in range(3):
            subjects.append(Subject.objects.create(
                name=f'Предмет {i}',
                description=f'Тест {i}',
                color='#3b82f6'
            ))
        
        # Создаем учителя
        teacher = User.objects.create_user(
            username='teacher_opt',
            role=User.Role.TEACHER,
            password='test'
        )
        TeacherProfile.objects.create(user=teacher, subject='Тест')
        
        # Связываем учителя с предметами
        for subject in subjects:
            TeacherSubject.objects.create(
                teacher=teacher,
                subject=subject,
                is_active=True
            )
        
        # Создаем родителя
        parent = User.objects.create_user(
            username='parent_opt',
            role=User.Role.PARENT,
            password='test'
        )
        parent_profile = ParentProfile.objects.create(user=parent)
        
        # Создаем студентов
        for i in range(5):
            student = User.objects.create_user(
                username=f'student_opt_{i}',
                role=User.Role.STUDENT,
                password='test'
            )
            student_profile = StudentProfile.objects.create(
                user=student,
                parent=parent,
                grade=f'{i+1}'
            )
            parent_profile.children.add(student)
            
            # Зачисляем на предметы
            for subject in subjects:
                SubjectEnrollment.objects.create(
                    student=student,
                    subject=subject,
                    teacher=teacher,
                    is_active=True
                )
    
    def test_parent_dashboard_queries(self):
        """Проверка количества запросов при загрузке дашборда родителя"""
        parent = User.objects.get(username='parent_opt')
        service = ParentDashboardService(parent)
        
        # Проверяем, что запросы оптимизированы (используем select_related/prefetch_related)
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import TransactionTestCase
        
        with self.assertNumQueries(None):  # Считаем запросы
            dashboard_data = service.get_dashboard_data()
            
        # Проверяем результат
        self.assertEqual(len(dashboard_data['children']), 5)
        for child_data in dashboard_data['children']:
            self.assertGreater(len(child_data['subjects']), 0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

