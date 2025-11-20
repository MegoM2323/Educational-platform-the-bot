"""
Комплексные unit-тесты для TutorDashboardService

Покрывает:
- get_students() с различными фильтрами
- assign_subject() с edge cases
- get_student_progress() с различными сценариями
- create_student_report() с валидацией
- get_tutor_reports()
- get_dashboard_data()
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from materials.tutor_dashboard_service import TutorDashboardService
from materials.models import (
    Subject,
    SubjectEnrollment,
    Material,
    MaterialProgress
)
from reports.models import Report, ReportRecipient

User = get_user_model()


# ===== Service Initialization Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorDashboardServiceInit:
    """Тесты инициализации сервиса"""

    def test_init_with_tutor_user(self, tutor_user):
        """Успешная инициализация с пользователем-тьютором"""
        service = TutorDashboardService(tutor_user)
        assert service.tutor == tutor_user

    def test_init_with_non_tutor_user(self, student_user):
        """Ошибка при инициализации с не-тьютором"""
        with pytest.raises(PermissionDenied):
            TutorDashboardService(student_user)

    def test_init_with_request(self, tutor_user, rf):
        """Инициализация с request объектом"""
        request = rf.get('/')
        service = TutorDashboardService(tutor_user, request=request)
        assert service.request == request


# ===== get_students() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestGetStudents:
    """Тесты для получения списка студентов"""

    def test_get_students_empty_list(self, tutor_user):
        """Получение пустого списка когда нет студентов"""
        service = TutorDashboardService(tutor_user)
        students = service.get_students()
        assert students == []

    def test_get_students_with_one_student(self, tutor_user, student_user):
        """Получение списка с одним студентом"""
        # Привязываем студента к тьютору
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert students[0]['id'] == student_user.id
        assert students[0]['username'] == student_user.username

    def test_get_students_with_subjects(self, tutor_user, student_user, subject, teacher_user):
        """Список студентов включает их предметы"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert len(students[0]['subjects']) == 1
        assert students[0]['subjects'][0]['name'] == subject.name
        assert students[0]['subjects'][0]['enrollment_id'] == enrollment.id

    def test_get_students_with_parent(self, tutor_user, student_user, parent_user):
        """Список студентов включает информацию о родителе"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert students[0]['parent'] is not None
        assert students[0]['parent']['id'] == parent_user.id
        assert students[0]['parent']['name'] == parent_user.get_full_name()

    def test_get_students_excludes_inactive_students(self, tutor_user, student_user):
        """Неактивные студенты не включаются в список"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()
        student_user.is_active = False
        student_user.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 0

    def test_get_students_only_own_students(self, tutor_user, student_user):
        """Тьютор видит только своих студентов"""
        # Создаем другого тьютора
        other_tutor = User.objects.create_user(
            username='other_tutor',
            email='other@test.com',
            role=User.Role.TUTOR
        )

        # Студент принадлежит другому тьютору
        student_user.student_profile.tutor = other_tutor
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 0

    def test_get_students_profile_data_included(self, tutor_user, student_user):
        """Список включает данные профиля студента"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.grade = '8 класс'
        student_user.student_profile.goal = 'Подготовка к ОГЭ'
        student_user.student_profile.progress_percentage = 75
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        profile = students[0]['profile']
        assert profile['grade'] == '8 класс'
        assert profile['goal'] == 'Подготовка к ОГЭ'
        assert profile['progress_percentage'] == 75


# ===== assign_subject() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestAssignSubject:
    """Тесты для назначения предмета студенту"""

    def test_assign_subject_success(self, tutor_user, student_user, subject, teacher_user):
        """Успешное назначение предмета"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is True
        assert 'enrollment_id' in result

        # Проверяем создание enrollment
        enrollment = SubjectEnrollment.objects.get(id=result['enrollment_id'])
        assert enrollment.student == student_user
        assert enrollment.subject == subject
        assert enrollment.teacher == teacher_user
        assert enrollment.assigned_by == tutor_user

    def test_assign_subject_with_custom_name(self, tutor_user, student_user, subject, teacher_user):
        """Назначение предмета с кастомным названием"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id,
            custom_subject_name='Математика (углубленная)'
        )

        assert result['success'] is True
        enrollment = SubjectEnrollment.objects.get(id=result['enrollment_id'])
        assert enrollment.custom_subject_name == 'Математика (углубленная)'

    def test_assign_subject_already_assigned(self, tutor_user, student_user, subject, teacher_user):
        """Ошибка при попытке назначить уже назначенный предмет"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем существующий enrollment
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is False
        assert 'уже назначен' in result['message']

    def test_assign_subject_not_own_student(self, tutor_user, student_user, subject, teacher_user):
        """Ошибка при попытке назначить предмет не своему студенту"""
        # Студент не привязан к тьютору
        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is False
        assert 'не принадлежит' in result['message']

    def test_assign_subject_nonexistent_subject(self, tutor_user, student_user, teacher_user):
        """Ошибка при несуществующем предмете"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=99999,  # Несуществующий ID
            teacher_id=teacher_user.id
        )

        assert result['success'] is False
        assert 'не найден' in result['message']

    def test_assign_subject_nonexistent_teacher(self, tutor_user, student_user, subject):
        """Ошибка при несуществующем преподавателе"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=99999  # Несуществующий ID
        )

        assert result['success'] is False
        assert 'не найден' in result['message']


# ===== get_student_progress() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestGetStudentProgress:
    """Тесты для получения прогресса студента"""

    def test_get_progress_no_materials(self, tutor_user, student_user):
        """Прогресс студента без материалов"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        progress = service.get_student_progress(student_user.id)

        assert progress['total_materials'] == 0
        assert progress['completed_materials'] == 0
        assert progress['completion_percentage'] == 0
        assert progress['subject_progress'] == []

    def test_get_progress_with_materials(self, tutor_user, student_user, subject, teacher_user):
        """Прогресс студента с материалами"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материалы
        material1 = Material.objects.create(
            title='Material 1',
            subject=subject,
            author=teacher_user
        )
        material2 = Material.objects.create(
            title='Material 2',
            subject=subject,
            author=teacher_user
        )

        # Создаем прогресс
        MaterialProgress.objects.create(
            student=student_user,
            material=material1,
            progress_percentage=100,
            is_completed=True
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=material2,
            progress_percentage=50,
            is_completed=False
        )

        service = TutorDashboardService(tutor_user)
        progress = service.get_student_progress(student_user.id)

        assert progress['total_materials'] == 2
        assert progress['completed_materials'] == 1
        assert progress['completion_percentage'] == 50.0
        assert len(progress['subject_progress']) == 1

    def test_get_progress_not_own_student(self, tutor_user, student_user):
        """Ошибка при запросе прогресса не своего студента"""
        # Студент не привязан к тьютору
        service = TutorDashboardService(tutor_user)

        with pytest.raises(PermissionDenied):
            service.get_student_progress(student_user.id)

    def test_get_progress_by_subjects(self, tutor_user, student_user, teacher_user):
        """Прогресс разбит по предметам"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем два предмета
        subject1 = Subject.objects.create(name='Математика')
        subject2 = Subject.objects.create(name='Физика')

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user,
            is_active=True
        )
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материалы для каждого предмета
        mat1 = Material.objects.create(title='Math 1', subject=subject1, author=teacher_user)
        mat2 = Material.objects.create(title='Physics 1', subject=subject2, author=teacher_user)

        MaterialProgress.objects.create(
            student=student_user,
            material=mat1,
            progress_percentage=100,
            is_completed=True
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=mat2,
            progress_percentage=50,
            is_completed=False
        )

        service = TutorDashboardService(tutor_user)
        progress = service.get_student_progress(student_user.id)

        assert len(progress['subject_progress']) == 2

        # Проверяем прогресс по каждому предмету
        math_progress = next(s for s in progress['subject_progress'] if s['subject'] == 'Математика')
        assert math_progress['completed_materials'] == 1
        assert math_progress['average_progress'] == 100.0

        physics_progress = next(s for s in progress['subject_progress'] if s['subject'] == 'Физика')
        assert physics_progress['completed_materials'] == 0
        assert physics_progress['average_progress'] == 50.0


# ===== create_student_report() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateStudentReport:
    """Тесты для создания отчетов о студентах"""

    def test_create_report_success(self, tutor_user, student_user, parent_user):
        """Успешное создание отчета"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        report_data = {
            'title': 'Недельный отчет',
            'description': 'Отчет за неделю',
            'content': 'Студент хорошо занимался',
            'period_start': '2024-01-01',
            'period_end': '2024-01-07'
        }

        service = TutorDashboardService(tutor_user)
        result = service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data=report_data
        )

        assert result['success'] is True
        assert 'report_id' in result

        # Проверяем создание отчета
        report = Report.objects.get(id=result['report_id'])
        assert report.author == tutor_user
        assert report.title == 'Недельный отчет'

        # Проверяем получателя
        recipient = ReportRecipient.objects.get(report=report)
        assert recipient.recipient == parent_user

    def test_create_report_wrong_parent(self, tutor_user, student_user, parent_user):
        """Ошибка при несовпадении родителя и студента"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()
        # Не привязываем родителя

        # Создаем другого родителя
        other_parent = User.objects.create_user(
            username='other_parent',
            email='other@test.com',
            role=User.Role.PARENT
        )
        from accounts.models import ParentProfile
        ParentProfile.objects.create(user=other_parent)

        report_data = {'title': 'Test Report'}

        service = TutorDashboardService(tutor_user)
        result = service.create_student_report(
            student_id=student_user.id,
            parent_id=other_parent.id,
            report_data=report_data
        )

        assert result['success'] is False
        assert 'не является родителем' in result['message']

    def test_create_report_not_own_student(self, tutor_user, student_user, parent_user):
        """Ошибка при создании отчета для не своего студента"""
        # Студент не привязан к тьютору
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        report_data = {'title': 'Test Report'}

        service = TutorDashboardService(tutor_user)
        result = service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data=report_data
        )

        assert result['success'] is False


# ===== get_tutor_reports() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestGetTutorReports:
    """Тесты для получения отчетов тьютора"""

    def test_get_reports_empty_list(self, tutor_user):
        """Получение пустого списка отчетов"""
        service = TutorDashboardService(tutor_user)
        reports = service.get_tutor_reports()
        assert reports == []

    def test_get_reports_with_one_report(self, tutor_user, parent_user):
        """Получение списка с одним отчетом"""
        report = Report.objects.create(
            title='Test Report',
            author=tutor_user,
            type=Report.Type.CUSTOM,
            status=Report.Status.DRAFT
        )
        ReportRecipient.objects.create(
            report=report,
            recipient=parent_user
        )

        service = TutorDashboardService(tutor_user)
        reports = service.get_tutor_reports()

        assert len(reports) == 1
        assert reports[0]['title'] == 'Test Report'
        assert len(reports[0]['recipients']) == 1

    def test_get_reports_only_own_reports(self, tutor_user):
        """Тьютор видит только свои отчеты"""
        # Создаем другого тьютора
        other_tutor = User.objects.create_user(
            username='other_tutor',
            email='other@test.com',
            role=User.Role.TUTOR
        )

        # Отчет другого тьютора
        Report.objects.create(
            title='Other Report',
            author=other_tutor,
            type=Report.Type.CUSTOM,
            status=Report.Status.DRAFT
        )

        service = TutorDashboardService(tutor_user)
        reports = service.get_tutor_reports()

        assert len(reports) == 0


# ===== get_dashboard_data() Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestGetDashboardData:
    """Тесты для получения полных данных дашборда"""

    def test_dashboard_data_structure(self, tutor_user):
        """Структура данных дашборда"""
        service = TutorDashboardService(tutor_user)
        data = service.get_dashboard_data()

        assert 'tutor_info' in data
        assert 'statistics' in data
        assert 'students' in data
        assert 'reports' in data

    def test_dashboard_statistics(self, tutor_user, student_user, subject, teacher_user):
        """Статистика в дашборде корректна"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.progress_percentage = 80
        student_user.student_profile.save()

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        data = service.get_dashboard_data()

        stats = data['statistics']
        assert stats['total_students'] == 1
        assert stats['average_progress'] == 80.0
        assert stats['total_subjects_assigned'] == 1

    def test_dashboard_tutor_info(self, tutor_user):
        """Информация о тьюторе в дашборде"""
        tutor_user.first_name = 'Иван'
        tutor_user.last_name = 'Иванов'
        tutor_user.save()

        service = TutorDashboardService(tutor_user)
        data = service.get_dashboard_data()

        tutor_info = data['tutor_info']
        assert tutor_info['id'] == tutor_user.id
        assert tutor_info['name'] == 'Иван Иванов'
        assert tutor_info['role'] == User.Role.TUTOR
