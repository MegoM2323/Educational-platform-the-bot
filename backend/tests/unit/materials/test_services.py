"""
Unit tests for materials service layer

Покрытие:
- StudentDashboardService
- TeacherDashboardService
- ParentDashboardService
"""
import pytest
from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch

from materials.student_dashboard_service import StudentDashboardService
from materials.teacher_dashboard_service import TeacherDashboardService
from materials.parent_dashboard_service import ParentDashboardService
from materials.models import (
    Subject, SubjectEnrollment, Material, MaterialProgress, StudyPlan,
    SubjectPayment, SubjectSubscription
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentDashboardService:
    """Тесты StudentDashboardService"""

    @pytest.fixture
    def student_service(self, student_user):
        """Фикстура сервиса студента"""
        return StudentDashboardService(student=student_user)

    def test_service_initialization(self, student_user):
        """Тест инициализации сервиса"""
        service = StudentDashboardService(student=student_user)
        assert service.student == student_user

    def test_service_requires_student_role(self, teacher_user):
        """Тест что сервис требует роль STUDENT"""
        with pytest.raises(ValueError, match="Пользователь должен иметь роль 'student'"):
            StudentDashboardService(student=teacher_user)

    def test_get_assigned_materials(self, student_service, student_user, teacher_user, subject):
        """Тест получения назначенных материалов"""
        # Создаем материалы
        material1 = Material.objects.create(
            title="Урок 1",
            content="Содержание 1",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material1.assigned_to.add(student_user)

        material2 = Material.objects.create(
            title="Урок 2",
            content="Содержание 2",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE,
            is_public=True
        )

        materials = student_service.get_assigned_materials()

        assert len(materials) == 2
        assert materials[0]['title'] == "Урок 2"  # Сортировка по -created_at
        assert materials[1]['title'] == "Урок 1"

    def test_get_assigned_materials_with_subject_filter(
        self, student_service, student_user, teacher_user
    ):
        """Тест фильтрации материалов по предмету"""
        subject1 = Subject.objects.create(name="Математика")
        subject2 = Subject.objects.create(name="Физика")

        material1 = Material.objects.create(
            title="Урок математики",
            content="Содержание",
            author=teacher_user,
            subject=subject1,
            status=Material.Status.ACTIVE
        )
        material1.assigned_to.add(student_user)

        material2 = Material.objects.create(
            title="Урок физики",
            content="Содержание",
            author=teacher_user,
            subject=subject2,
            status=Material.Status.ACTIVE
        )
        material2.assigned_to.add(student_user)

        # Фильтруем по subject1
        materials = student_service.get_assigned_materials(subject_id=subject1.id)

        assert len(materials) == 1
        assert materials[0]['title'] == "Урок математики"

    def test_get_assigned_materials_with_progress(
        self, student_service, student_user, teacher_user, subject
    ):
        """Тест получения материалов с прогрессом"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        # Создаем прогресс
        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=50,
            time_spent=30
        )

        materials = student_service.get_assigned_materials()

        assert len(materials) == 1
        assert materials[0]['progress']['progress_percentage'] == 50
        assert materials[0]['progress']['time_spent'] == 30

    def test_get_progress_statistics(self, student_service, student_user, teacher_user, subject):
        """Тест получения статистики прогресса"""
        # Создаем материалы
        for i in range(5):
            material = Material.objects.create(
                title=f"Урок {i}",
                content="Содержание",
                author=teacher_user,
                subject=subject,
                status=Material.Status.ACTIVE
            )
            material.assigned_to.add(student_user)

            # Создаем прогресс
            MaterialProgress.objects.create(
                student=student_user,
                material=material,
                progress_percentage=100 if i < 3 else 50,
                is_completed=i < 3,
                time_spent=30
            )

        stats = student_service.get_progress_statistics()

        assert stats['total_materials'] == 5
        assert stats['completed_materials'] == 3
        assert stats['in_progress_materials'] == 2
        assert stats['not_started_materials'] == 0
        assert stats['completion_percentage'] == 60.0  # 3/5 * 100
        assert stats['total_time_spent'] == 150  # 5 * 30

    def test_get_materials_by_subject(self, student_service, student_user, teacher_user):
        """Тест группировки материалов по предметам"""
        subject1 = Subject.objects.create(name="Математика")
        subject2 = Subject.objects.create(name="Физика")

        # Создаем материалы для разных предметов
        material1 = Material.objects.create(
            title="Урок математики",
            content="Содержание",
            author=teacher_user,
            subject=subject1,
            status=Material.Status.ACTIVE
        )
        material1.assigned_to.add(student_user)

        material2 = Material.objects.create(
            title="Урок физики",
            content="Содержание",
            author=teacher_user,
            subject=subject2,
            status=Material.Status.ACTIVE
        )
        material2.assigned_to.add(student_user)

        grouped = student_service.get_materials_by_subject()

        assert "Математика" in grouped
        assert "Физика" in grouped
        assert len(grouped["Математика"]['materials']) == 1
        assert len(grouped["Физика"]['materials']) == 1

    def test_get_subjects(self, student_service, student_user, teacher_user):
        """Тест получения предметов студента"""
        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        subjects = student_service.get_subjects()

        assert len(subjects) == 1
        assert subjects[0]['name'] == "Математика"
        assert subjects[0]['teacher']['id'] == teacher_user.id

    def test_get_recent_activity(self, student_service, student_user, teacher_user, subject):
        """Тест получения недавней активности"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        # Создаем завершенный прогресс
        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=100,
            is_completed=True,
            completed_at=timezone.now()
        )

        activities = student_service.get_recent_activity(days=7)

        assert len(activities) > 0
        assert activities[0]['type'] == 'material_completed'
        assert activities[0]['title'] == "Урок 1"

    def test_get_dashboard_data(self, student_service, student_user, teacher_user, subject):
        """Тест получения полных данных дашборда"""
        # Создаем enrollment
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материал
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        dashboard_data = student_service.get_dashboard_data()

        assert 'student_info' in dashboard_data
        assert 'subjects' in dashboard_data
        assert 'materials_by_subject' in dashboard_data
        assert 'stats' in dashboard_data
        assert 'recent_activity' in dashboard_data


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherDashboardService:
    """Тесты TeacherDashboardService"""

    @pytest.fixture
    def teacher_service(self, teacher_user):
        """Фикстура сервиса преподавателя"""
        return TeacherDashboardService(teacher=teacher_user)

    def test_service_initialization(self, teacher_user):
        """Тест инициализации сервиса"""
        service = TeacherDashboardService(teacher=teacher_user)
        assert service.teacher == teacher_user

    def test_service_requires_teacher_role(self, student_user):
        """Тест что сервис требует роль TEACHER"""
        with pytest.raises(ValueError, match="Пользователь должен иметь роль 'teacher'"):
            TeacherDashboardService(teacher=student_user)

    def test_get_teacher_students(self, teacher_service, teacher_user):
        """Тест получения студентов преподавателя"""
        subject = Subject.objects.create(name="Математика")

        # Создаем студентов
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student1 = StudentUserFactory()
        StudentProfile.objects.create(user=student1)

        student2 = StudentUserFactory()
        StudentProfile.objects.create(user=student2)

        # Создаем зачисления
        SubjectEnrollment.objects.create(
            student=student1,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        SubjectEnrollment.objects.create(
            student=student2,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        students = teacher_service.get_teacher_students()

        assert len(students) == 2
        assert students[0]['subjects'][0]['name'] == "Математика"

    def test_get_teacher_materials(self, teacher_service, teacher_user, subject):
        """Тест получения материалов преподавателя"""
        material1 = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )

        material2 = Material.objects.create(
            title="Урок 2",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.DRAFT
        )

        materials = teacher_service.get_teacher_materials()

        assert len(materials) == 2

    def test_get_teacher_materials_with_subject_filter(self, teacher_service, teacher_user):
        """Тест фильтрации материалов по предмету"""
        subject1 = Subject.objects.create(name="Математика")
        subject2 = Subject.objects.create(name="Физика")

        Material.objects.create(
            title="Урок математики",
            content="Содержание",
            author=teacher_user,
            subject=subject1
        )

        Material.objects.create(
            title="Урок физики",
            content="Содержание",
            author=teacher_user,
            subject=subject2
        )

        materials = teacher_service.get_teacher_materials(subject_id=subject1.id)

        assert len(materials) == 1
        assert materials[0]['title'] == "Урок математики"

    def test_distribute_material(self, teacher_service, teacher_user, subject):
        """Тест распределения материала среди студентов"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student1 = StudentUserFactory()
        StudentProfile.objects.create(user=student1)

        student2 = StudentUserFactory()
        StudentProfile.objects.create(user=student2)

        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        result = teacher_service.distribute_material(
            material_id=material.id,
            student_ids=[student1.id, student2.id]
        )

        assert result['success'] is True
        assert result['assigned_count'] == 2
        assert material.assigned_to.count() == 2

    def test_get_all_subjects(self, teacher_service, teacher_user):
        """Тест получения всех предметов"""
        from materials.models import TeacherSubject

        subject1 = Subject.objects.create(name="Математика")
        subject2 = Subject.objects.create(name="Физика")

        # Назначаем один предмет преподавателю
        TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject1,
            is_active=True
        )

        subjects = teacher_service.get_all_subjects()

        assert len(subjects) == 2
        assert any(s['name'] == "Математика" and s['is_assigned'] for s in subjects)
        assert any(s['name'] == "Физика" and not s['is_assigned'] for s in subjects)


@pytest.mark.unit
@pytest.mark.django_db
class TestParentDashboardService:
    """Тесты ParentDashboardService"""

    @pytest.fixture
    def parent_service(self, parent_user):
        """Фикстура сервиса родителя"""
        return ParentDashboardService(parent_user=parent_user)

    def test_service_initialization(self, parent_user):
        """Тест инициализации сервиса"""
        service = ParentDashboardService(parent_user=parent_user)
        assert service.parent_user == parent_user

    def test_service_requires_parent_role(self, student_user):
        """Тест что сервис требует роль PARENT"""
        with pytest.raises(ValueError):
            ParentDashboardService(parent_user=student_user)

    def test_get_children(self, parent_service, parent_user):
        """Тест получения детей родителя"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child1 = StudentUserFactory()
        profile1 = StudentProfile.objects.create(user=child1, parent=parent_user)

        child2 = StudentUserFactory()
        profile2 = StudentProfile.objects.create(user=child2, parent=parent_user)

        children = parent_service.get_children()

        assert children.count() == 2

    def test_get_child_subjects(self, parent_service, parent_user, teacher_user):
        """Тест получения предметов ребенка"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        enrollments = parent_service.get_child_subjects(child)

        assert enrollments.count() == 1
        assert enrollments[0].subject.name == "Математика"

    def test_get_child_progress(self, parent_service, parent_user, teacher_user):
        """Тест получения прогресса ребенка"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материалы и прогресс
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(child)

        MaterialProgress.objects.create(
            student=child,
            material=material,
            progress_percentage=75,
            is_completed=False
        )

        progress = parent_service.get_child_progress(child)

        assert progress['total_materials'] == 1
        assert progress['completed_materials'] == 0
        assert progress['average_progress'] == 75.0

    def test_get_payment_status(self, parent_service, parent_user, teacher_user, payment):
        """Тест получения статуса платежей"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        enrollment = SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PAID,
            due_date=timezone.now() + timedelta(days=7)
        )

        payment_info = parent_service.get_payment_status(child)

        assert len(payment_info) == 1
        assert payment_info[0]['status'] == 'paid'
        assert payment_info[0]['amount'] == '100.00'

    @patch('materials.parent_dashboard_service.Payment')
    def test_initiate_payment(self, mock_payment_model, parent_service, parent_user, teacher_user, settings):
        """Тест инициации платежа"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        enrollment = SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Mock request
        mock_request = Mock()
        mock_request.build_absolute_uri.return_value = "http://localhost:8000/payment/confirm"

        result = parent_service.initiate_payment(
            child=child,
            enrollment=enrollment,
            amount=Decimal('100.00'),
            create_subscription=False,
            request=None  # Не используем request для теста
        )

        assert 'payment_id' in result
        assert result['amount'] == Decimal('100.00')
        assert result['subject'] == "Математика"

    def test_get_dashboard_data(self, parent_service, parent_user, teacher_user):
        """Тест получения данных дашборда родителя"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        dashboard_data = parent_service.get_dashboard_data()

        assert 'parent' in dashboard_data
        assert 'children' in dashboard_data
        assert 'statistics' in dashboard_data
        assert len(dashboard_data['children']) == 1
        assert dashboard_data['total_children'] == 1
