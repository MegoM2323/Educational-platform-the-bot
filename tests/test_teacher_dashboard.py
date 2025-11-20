import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from materials.teacher_dashboard_service import TeacherDashboardService
from materials.models import Material, MaterialProgress, Subject
from reports.models import StudentReport
from reports.report_service import ReportService

User = get_user_model()


class TeacherDashboardServiceTest(TestCase):
    """Тесты для TeacherDashboardService"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем пользователей
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            first_name='Teacher',
            last_name='One',
            role=User.Role.TEACHER
        )
        
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            first_name='Student',
            last_name='One',
            role=User.Role.STUDENT
        )
        
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            first_name='Student',
            last_name='Two',
            role=User.Role.STUDENT
        )
        
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent1@test.com',
            first_name='Parent',
            last_name='One',
            role=User.Role.PARENT
        )
        
        # Создаем предмет
        self.subject = Subject.objects.create(
            name='Математика',
            description='Математические дисциплины',
            color='#FF5733'
        )
        
        # Создаем материалы
        self.material1 = Material.objects.create(
            title='Алгебра',
            description='Основы алгебры',
            content='Содержание урока по алгебре',
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )
        
        self.material2 = Material.objects.create(
            title='Геометрия',
            description='Основы геометрии',
            content='Содержание урока по геометрии',
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )
        
        # Назначаем материалы студентам
        self.material1.assigned_to.add(self.student1, self.student2)
        self.material2.assigned_to.add(self.student1)
        
        # Создаем прогресс
        MaterialProgress.objects.create(
            student=self.student1,
            material=self.material1,
            is_completed=True,
            progress_percentage=100,
            time_spent=60
        )
        
        MaterialProgress.objects.create(
            student=self.student1,
            material=self.material2,
            is_completed=False,
            progress_percentage=50,
            time_spent=30
        )
        
        MaterialProgress.objects.create(
            student=self.student2,
            material=self.material1,
            is_completed=False,
            progress_percentage=75,
            time_spent=45
        )
        
        # Создаем сервис
        self.service = TeacherDashboardService(self.teacher)
    
    def test_get_teacher_students(self):
        """Тест получения списка студентов преподавателя"""
        students = self.service.get_teacher_students()
        
        self.assertEqual(len(students), 2)
        
        # Проверяем данные первого студента
        student1_data = next(s for s in students if s['id'] == self.student1.id)
        self.assertEqual(student1_data['name'], 'Student One')
        self.assertEqual(student1_data['assigned_materials_count'], 2)
        self.assertEqual(student1_data['completed_materials_count'], 1)
        self.assertEqual(student1_data['completion_percentage'], 50.0)
    
    def test_get_teacher_materials(self):
        """Тест получения материалов преподавателя"""
        materials = self.service.get_teacher_materials()
        
        self.assertEqual(len(materials), 2)
        
        # Проверяем данные первого материала
        material1_data = next(m for m in materials if m['id'] == self.material1.id)
        self.assertEqual(material1_data['title'], 'Алгебра')
        self.assertEqual(material1_data['assigned_count'], 2)
        self.assertEqual(material1_data['completed_count'], 1)
        self.assertEqual(material1_data['completion_percentage'], 50.0)
    
    def test_distribute_material(self):
        """Тест распределения материала"""
        # Создаем новый материал
        new_material = Material.objects.create(
            title='Тригонометрия',
            description='Основы тригонометрии',
            content='Содержание урока по тригонометрии',
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )
        
        # Распределяем материал
        result = self.service.distribute_material(
            new_material.id,
            [self.student1.id, self.student2.id]
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['assigned_count'], 2)
        
        # Проверяем, что материал назначен студентам
        new_material.refresh_from_db()
        self.assertEqual(new_material.assigned_to.count(), 2)
        
        # Проверяем, что созданы записи прогресса
        progress_count = MaterialProgress.objects.filter(
            material=new_material
        ).count()
        self.assertEqual(progress_count, 2)
    
    def test_get_student_progress_overview(self):
        """Тест получения обзора прогресса студентов"""
        # Общий обзор
        overview = self.service.get_student_progress_overview()
        
        self.assertEqual(overview['total_students'], 2)
        self.assertEqual(overview['total_materials'], 2)
        self.assertEqual(overview['completed_assignments'], 1)
        self.assertIn('subject_statistics', overview)
        
        # Детальный обзор студента
        student_overview = self.service.get_student_progress_overview(self.student1.id)
        
        self.assertEqual(student_overview['student']['id'], self.student1.id)
        self.assertEqual(student_overview['student']['name'], 'Student One')
        self.assertEqual(student_overview['total_materials'], 2)
        self.assertEqual(student_overview['completed_materials'], 1)
        self.assertIn('subject_progress', student_overview)
    
    def test_create_student_report(self):
        """Тест создания отчета о студенте"""
        report_data = {
            'title': 'Тестовый отчет',
            'description': 'Описание отчета',
            'type': StudentReport.ReportType.PROGRESS,
            'content': {'test': 'data'},
            'progress_percentage': 75,
            'overall_grade': 'Хорошо'
        }
        
        result = self.service.create_student_report(self.student1.id, report_data)
        
        self.assertTrue(result['success'])
        self.assertIn('report_id', result)
        
        # Проверяем, что отчет создан
        report = StudentReport.objects.get(id=result['report_id'])
        self.assertEqual(report.title, 'Тестовый отчет')
        self.assertEqual(report.teacher, self.teacher)
        self.assertEqual(report.student, self.student1)
        self.assertEqual(report.progress_percentage, 75)
    
    def test_get_teacher_reports(self):
        """Тест получения отчетов преподавателя"""
        # Создаем отчет
        StudentReport.objects.create(
            title='Отчет 1',
            description='Описание',
            teacher=self.teacher,
            student=self.student1,
            period_start=date.today(),
            period_end=date.today(),
            content={'test': 'data'}
        )
        
        reports = self.service.get_teacher_reports()
        
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['title'], 'Отчет 1')
        self.assertEqual(reports[0]['student']['id'], self.student1.id)
    
    def test_invalid_teacher_role(self):
        """Тест с неправильной ролью пользователя"""
        with self.assertRaises(ValueError):
            TeacherDashboardService(self.student1)
    
    def test_distribute_nonexistent_material(self):
        """Тест распределения несуществующего материала"""
        result = self.service.distribute_material(999, [self.student1.id])
        
        self.assertFalse(result['success'])
        self.assertIn('не найден', result['message'])
    
    def test_distribute_material_wrong_author(self):
        """Тест распределения материала другого преподавателя"""
        other_teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            first_name='Teacher',
            last_name='Two',
            role=User.Role.TEACHER
        )
        
        other_material = Material.objects.create(
            title='Другой материал',
            description='Описание',
            content='Содержание',
            author=other_teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )
        
        result = self.service.distribute_material(other_material.id, [self.student1.id])
        
        self.assertFalse(result['success'])
        self.assertIn('не найден', result['message'])


class ReportServiceTest(TestCase):
    """Тесты для ReportService"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем пользователей
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            first_name='Teacher',
            last_name='One',
            role=User.Role.TEACHER
        )
        
        self.student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            first_name='Student',
            last_name='One',
            role=User.Role.STUDENT
        )
        
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent1@test.com',
            first_name='Parent',
            last_name='One',
            role=User.Role.PARENT
        )
        
        # Создаем профили
        from accounts.models import StudentProfile, ParentProfile
        
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            grade='10',
            goal='Изучение математики',
            parent=self.parent
        )
        
        self.parent_profile = ParentProfile.objects.create(
            user=self.parent
        )
        
        # Создаем предмет и материал
        self.subject = Subject.objects.create(
            name='Математика',
            description='Математические дисциплины',
            color='#FF5733'
        )
        
        self.material = Material.objects.create(
            title='Алгебра',
            description='Основы алгебры',
            content='Содержание урока',
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE
        )
        
        self.material.assigned_to.add(self.student)
        
        # Создаем прогресс
        MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            is_completed=True,
            progress_percentage=85,
            time_spent=90
        )
        
        # Создаем сервис
        self.service = ReportService(self.teacher)
    
    @patch('reports.report_service.TelegramNotificationService')
    def test_create_student_report(self, mock_telegram):
        """Тест создания отчета о студенте"""
        mock_telegram.return_value.send_notification.return_value = True
        
        report_data = {
            'title': 'Отчет о прогрессе',
            'description': 'Описание отчета',
            'report_type': StudentReport.ReportType.PROGRESS,
            'progress_percentage': 85,
            'overall_grade': 'Хорошо',
            'recommendations': 'Продолжайте в том же духе',
            'achievements': 'Отличные результаты'
        }
        
        result = self.service.create_student_report(self.student.id, report_data)
        
        self.assertTrue(result['success'])
        self.assertIn('report_id', result)
        
        # Проверяем, что отчет создан
        report = StudentReport.objects.get(id=result['report_id'])
        self.assertEqual(report.title, 'Отчет о прогрессе')
        self.assertEqual(report.teacher, self.teacher)
        self.assertEqual(report.student, self.student)
        self.assertEqual(report.parent, self.parent)
        self.assertEqual(report.progress_percentage, 85)
        self.assertEqual(report.status, StudentReport.Status.SENT)
    
    def test_get_teacher_reports(self):
        """Тест получения отчетов преподавателя"""
        # Создаем отчет
        StudentReport.objects.create(
            title='Отчет 1',
            description='Описание',
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            period_start=date.today(),
            period_end=date.today(),
            content={'test': 'data'},
            status=StudentReport.Status.SENT
        )
        
        reports = self.service.get_teacher_reports()
        
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['title'], 'Отчет 1')
        self.assertEqual(reports[0]['student']['id'], self.student.id)
        self.assertEqual(reports[0]['parent']['id'], self.parent.id)
    
    def test_get_student_reports_for_parent(self):
        """Тест получения отчетов о детях для родителя"""
        # Создаем отчет
        StudentReport.objects.create(
            title='Отчет о ребенке',
            description='Описание',
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            period_start=date.today(),
            period_end=date.today(),
            content={'test': 'data'}
        )
        
        reports = self.service.get_student_reports_for_parent(self.parent.id)
        
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['title'], 'Отчет о ребенке')
        self.assertEqual(reports[0]['student']['id'], self.student.id)
        self.assertEqual(reports[0]['teacher']['id'], self.teacher.id)
    
    def test_mark_report_as_read(self):
        """Тест отметки отчета как прочитанного"""
        # Создаем отчет
        report = StudentReport.objects.create(
            title='Отчет',
            description='Описание',
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            period_start=date.today(),
            period_end=date.today(),
            content={'test': 'data'},
            status=StudentReport.Status.SENT
        )
        
        # Отмечаем как прочитанный родителем
        result = self.service.mark_report_as_read(report.id, self.parent.id)
        
        self.assertTrue(result['success'])
        
        # Проверяем, что статус обновлен
        report.refresh_from_db()
        self.assertEqual(report.status, StudentReport.Status.READ)
        self.assertIsNotNone(report.read_at)
    
    def test_generate_automatic_report(self):
        """Тест автоматической генерации отчета"""
        result = self.service.generate_automatic_report(self.student.id, 30)
        
        self.assertTrue(result['success'])
        self.assertIn('report_id', result)
        
        # Проверяем, что отчет создан
        report = StudentReport.objects.get(id=result['report_id'])
        self.assertIn('Автоматический отчет', report.title)
        self.assertEqual(report.teacher, self.teacher)
        self.assertEqual(report.student, self.student)
        self.assertEqual(report.parent, self.parent)
        self.assertGreater(report.progress_percentage, 0)
    
    def test_invalid_teacher_role(self):
        """Тест с неправильной ролью пользователя"""
        with self.assertRaises(ValueError):
            ReportService(self.student)
    
    def test_create_report_nonexistent_student(self):
        """Тест создания отчета для несуществующего студента"""
        result = self.service.create_student_report(999, {})
        
        self.assertFalse(result['success'])
        self.assertIn('не найден', result['message'])
    
    def test_mark_report_as_read_wrong_user(self):
        """Тест отметки отчета как прочитанного неправильным пользователем"""
        # Создаем отчет
        report = StudentReport.objects.create(
            title='Отчет',
            description='Описание',
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            period_start=date.today(),
            period_end=date.today(),
            content={'test': 'data'}
        )
        
        # Создаем другого родителя
        other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            first_name='Parent',
            last_name='Two',
            role=User.Role.PARENT
        )
        
        # Пытаемся отметить как прочитанный другим родителем
        result = self.service.mark_report_as_read(report.id, other_parent.id)
        
        self.assertFalse(result['success'])
        self.assertIn('нет прав', result['message'])
