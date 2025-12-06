"""
Тесты оптимизации запросов в dashboard сервисах
Проверяем отсутствие N+1 queries через pytest-django's django_assert_num_queries
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from materials.student_dashboard_service import StudentDashboardService
from materials.teacher_dashboard_service import TeacherDashboardService
from materials.tutor_dashboard_service import TutorDashboardService
from materials.parent_dashboard_service import ParentDashboardService
from materials.models import (
    Subject, SubjectEnrollment, Material, MaterialProgress
)
from accounts.models import StudentProfile, ParentProfile, TeacherProfile

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.performance
class TestStudentDashboardQueryOptimization:
    """Тесты оптимизации запросов для student dashboard"""

    @pytest.fixture
    def student_with_materials(self, db):
        """Создаем студента с 10 предметами и 50 материалами"""
        # Создаем студента
        student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade='10')

        # Создаем учителя
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher)

        # Создаем 10 предметов
        subjects = []
        for i in range(10):
            subject = Subject.objects.create(
                name=f'Subject {i+1}',
                description=f'Description {i+1}',
                color='#FF5733'
            )
            subjects.append(subject)

            # Создаем enrollment
            SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher,
                is_active=True
            )

        # Создаем 50 материалов (5 на каждый предмет)
        for subject in subjects:
            for j in range(5):
                material = Material.objects.create(
                    title=f'Material {subject.name} - {j+1}',
                    description=f'Description for material {j+1}',
                    type=Material.Type.DOCUMENT,
                    subject=subject,
                    author=teacher,
                    status=Material.Status.ACTIVE
                )
                material.assigned_to.add(student)

                # Создаем прогресс для материала
                MaterialProgress.objects.create(
                    material=material,
                    student=student,
                    progress_percentage=50,
                    is_completed=False
                )

        return student

    def test_get_assigned_materials_query_count(self, student_with_materials, django_assert_num_queries):
        """
        Проверяем количество запросов при получении материалов
        Должно быть не более 5 запросов независимо от количества материалов
        """
        service = StudentDashboardService(student_with_materials)

        with django_assert_num_queries(5):
            materials = service.get_assigned_materials()

        # Проверяем что получили все 50 материалов
        assert len(materials) == 50

        # Проверяем что прогресс загружен
        for material in materials:
            assert 'progress' in material
            assert material['progress']['progress_percentage'] == 50

    def test_get_progress_statistics_query_count(self, student_with_materials, django_assert_num_queries):
        """
        Проверяем количество запросов при получении статистики
        Должно быть не более 5 запросов
        """
        service = StudentDashboardService(student_with_materials)

        with django_assert_num_queries(5):
            stats = service.get_progress_statistics()

        # Проверяем корректность статистики
        assert stats['total_materials'] == 50
        assert stats['completed_materials'] == 0  # is_completed=False
        assert stats['in_progress_materials'] == 50  # progress > 0
        assert len(stats['subject_statistics']) == 10

    def test_get_subjects_query_count(self, student_with_materials, django_assert_num_queries):
        """
        Проверяем количество запросов при получении предметов
        Должно быть не более 2 запросов
        """
        service = StudentDashboardService(student_with_materials)

        with django_assert_num_queries(2):
            subjects = service.get_subjects()

        # Проверяем что получили все 10 предметов
        assert len(subjects) == 10


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.performance
class TestTeacherDashboardQueryOptimization:
    """Тесты оптимизации запросов для teacher dashboard"""

    @pytest.fixture
    def teacher_with_students(self, db):
        """Создаем преподавателя с 20 студентами"""
        teacher = User.objects.create_user(
            username='teacher_opt',
            email='teacher@opt.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher)

        # Создаем предмет
        subject = Subject.objects.create(
            name='Math',
            description='Mathematics',
            color='#0000FF'
        )

        # Создаем 20 студентов
        for i in range(20):
            student = User.objects.create_user(
                username=f'student_{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            StudentProfile.objects.create(user=student, grade='10')

            # Создаем enrollment
            SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher,
                is_active=True
            )

            # Создаем 3 материала для каждого студента
            for j in range(3):
                material = Material.objects.create(
                    title=f'Material {i}-{j}',
                    description='Description',
                    type=Material.Type.DOCUMENT,
                    subject=subject,
                    author=teacher,
                    status=Material.Status.ACTIVE
                )
                material.assigned_to.add(student)

                # Создаем прогресс
                MaterialProgress.objects.create(
                    material=material,
                    student=student,
                    progress_percentage=75,
                    is_completed=(j == 0)  # Первый материал завершен
                )

        return teacher

    def test_get_teacher_students_query_count(self, teacher_with_students, django_assert_num_queries):
        """
        Проверяем количество запросов при получении студентов
        Должно быть не более 10 запросов для 20 студентов
        """
        service = TeacherDashboardService(teacher_with_students)

        with django_assert_num_queries(10):
            students = service.get_teacher_students()

        # Проверяем количество студентов
        assert len(students) == 20

        # Проверяем что статистика загружена
        for student in students:
            assert 'assigned_materials_count' in student
            assert 'completed_materials_count' in student
            assert 'subjects' in student

    def test_get_teacher_materials_query_count(self, teacher_with_students, django_assert_num_queries):
        """
        Проверяем количество запросов при получении материалов
        Должно быть не более 3 запросов
        """
        service = TeacherDashboardService(teacher_with_students)

        with django_assert_num_queries(3):
            materials = service.get_teacher_materials()

        # Проверяем количество материалов (20 студентов * 3 материала)
        assert len(materials) == 60


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.performance
class TestTutorDashboardQueryOptimization:
    """Тесты оптимизации запросов для tutor dashboard"""

    @pytest.fixture
    def tutor_with_students(self, db):
        """Создаем тьютора с 5 студентами и 15 предметами"""
        tutor = User.objects.create_user(
            username='tutor_opt',
            email='tutor@opt.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        # Создаем учителя
        teacher = User.objects.create_user(
            username='teacher_tutor',
            email='teacher@tutor.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher)

        # Создаем 3 предмета
        subjects = []
        for i in range(3):
            subject = Subject.objects.create(
                name=f'Subject {i+1}',
                description='Description',
                color='#00FF00'
            )
            subjects.append(subject)

        # Создаем 5 студентов с 3 предметами каждый
        for i in range(5):
            student = User.objects.create_user(
                username=f'student_tutor_{i}',
                email=f'student{i}@tutor.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            profile = StudentProfile.objects.create(
                user=student,
                tutor=tutor,
                grade='10'
            )

            # Зачисляем на все предметы
            for subject in subjects:
                SubjectEnrollment.objects.create(
                    student=student,
                    subject=subject,
                    teacher=teacher,
                    assigned_by=tutor,
                    is_active=True
                )

                # Создаем материалы
                material = Material.objects.create(
                    title=f'Material {subject.name} for {student.username}',
                    description='Description',
                    type=Material.Type.DOCUMENT,
                    subject=subject,
                    author=teacher,
                    status=Material.Status.ACTIVE
                )
                material.assigned_to.add(student)

                # Создаем прогресс
                MaterialProgress.objects.create(
                    material=material,
                    student=student,
                    progress_percentage=60,
                    is_completed=False
                )

        return tutor

    def test_get_students_query_count(self, tutor_with_students, django_assert_num_queries):
        """
        Проверяем количество запросов при получении студентов
        Должно быть не более 8 запросов для 5 студентов с 15 предметами
        """
        service = TutorDashboardService(tutor_with_students)

        with django_assert_num_queries(8):
            students = service.get_students()

        # Проверяем количество студентов
        assert len(students) == 5

        # Проверяем что предметы загружены
        for student in students:
            assert 'subjects' in student
            assert len(student['subjects']) == 3

    def test_get_student_progress_query_count(self, tutor_with_students, django_assert_num_queries):
        """
        Проверяем количество запросов при получении прогресса студента
        Должно быть не более 5 запросов
        """
        service = TutorDashboardService(tutor_with_students)
        students = User.objects.filter(role=User.Role.STUDENT).first()

        with django_assert_num_queries(5):
            progress = service.get_student_progress(students.id)

        # Проверяем структуру прогресса
        assert 'total_materials' in progress
        assert 'subject_progress' in progress
        assert len(progress['subject_progress']) == 3


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.performance
class TestParentDashboardQueryOptimization:
    """Тесты оптимизации запросов для parent dashboard"""

    @pytest.fixture
    def parent_with_children(self, db):
        """Создаем родителя с 3 детьми"""
        parent = User.objects.create_user(
            username='parent_opt',
            email='parent@opt.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        parent_profile = ParentProfile.objects.create(user=parent)

        # Создаем учителя
        teacher = User.objects.create_user(
            username='teacher_parent',
            email='teacher@parent.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher)

        # Создаем 2 предмета
        subjects = []
        for i in range(2):
            subject = Subject.objects.create(
                name=f'Subject {i+1}',
                description='Description',
                color='#FF00FF'
            )
            subjects.append(subject)

        # Создаем 3 детей
        for i in range(3):
            child = User.objects.create_user(
                username=f'child_{i}',
                email=f'child{i}@parent.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            StudentProfile.objects.create(
                user=child,
                parent=parent,
                grade='10'
            )

            # Зачисляем на предметы
            for subject in subjects:
                SubjectEnrollment.objects.create(
                    student=child,
                    subject=subject,
                    teacher=teacher,
                    is_active=True
                )

                # Создаем материалы
                material = Material.objects.create(
                    title=f'Material {subject.name} for {child.username}',
                    description='Description',
                    type=Material.Type.DOCUMENT,
                    subject=subject,
                    author=teacher,
                    status=Material.Status.ACTIVE
                )
                material.assigned_to.add(child)

                # Создаем прогресс
                MaterialProgress.objects.create(
                    material=material,
                    student=child,
                    progress_percentage=80,
                    is_completed=False
                )

        return parent

    def test_get_children_query_count(self, parent_with_children, django_assert_num_queries):
        """
        Проверяем количество запросов при получении детей
        Должно быть не более 2 запросов
        """
        service = ParentDashboardService(parent_with_children)

        with django_assert_num_queries(2):
            children = service.get_children()

        # Проверяем количество детей
        assert children.count() == 3

    def test_get_child_progress_query_count(self, parent_with_children, django_assert_num_queries):
        """
        Проверяем количество запросов при получении прогресса ребенка
        Должно быть не более 6 запросов
        """
        service = ParentDashboardService(parent_with_children)
        children = service.get_children()
        child = children.first()

        with django_assert_num_queries(6):
            progress = service.get_child_progress(child)

        # Проверяем структуру прогресса
        assert 'total_materials' in progress
        assert 'subject_progress' in progress
        assert len(progress['subject_progress']) == 2
