import pytest
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment
from materials.teacher_dashboard_service import TeacherDashboardService

User = get_user_model()


@pytest.fixture(scope='function')
def teacher():
    """Создаем преподавателя"""
    return User.objects.create_user(
        username='teacher1',
        email='teacher1@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Преподаватель',
        last_name='Тест'
    )


@pytest.fixture(scope='function')
def students(teacher):
    """Создаем студентов"""
    student1 = User.objects.create_user(
        username='student1',
        email='student1@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Студент',
        last_name='Один'
    )
    student2 = User.objects.create_user(
        username='student2',
        email='student2@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Студент',
        last_name='Два'
    )
    return [student1, student2]


@pytest.fixture(scope='function')
def subjects():
    """Создаем предметы"""
    subject1 = Subject.objects.create(
        name='Математика',
        description='Математика для школьников',
        color='#3B82F6'
    )
    subject2 = Subject.objects.create(
        name='Физика',
        description='Физика для школьников',
        color='#10B981'
    )
    return [subject1, subject2]


@pytest.mark.django_db
def test_assign_subject_to_students(teacher, students, subjects):
    """Тест назначения предмета студентам"""
    service = TeacherDashboardService(teacher)
    subject = subjects[0]
    student_ids = [s.id for s in students]
    
    # Назначаем предмет
    result = service.assign_subject_to_students(subject.id, student_ids)
    
    assert result['success'] is True
    assert 'назначен студентам' in result['message']
    assert result['created_count'] == 2
    assert result['total'] == 2
    
    # Проверяем, что зачисления созданы
    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        teacher=teacher
    )
    assert enrollments.count() == 2


@pytest.mark.django_db
def test_assign_subject_duplicate(teacher, students, subjects):
    """Тест повторного назначения того же предмета"""
    service = TeacherDashboardService(teacher)
    subject = subjects[0]
    student_ids = [students[0].id]
    
    # Первое назначение
    result1 = service.assign_subject_to_students(subject.id, student_ids)
    assert result1['success'] is True
    assert result1['created_count'] == 1
    
    # Повторное назначение
    result2 = service.assign_subject_to_students(subject.id, student_ids)
    assert result2['success'] is True
    assert result2['already_exists_count'] == 1
    assert result2['created_count'] == 0
    
    # Должно быть только одно зачисление
    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        teacher=teacher,
        student=students[0]
    )
    assert enrollments.count() == 1


@pytest.mark.django_db
def test_assign_subject_invalid_subject(teacher, students):
    """Тест назначения несуществующего предмета"""
    service = TeacherDashboardService(teacher)
    student_ids = [s.id for s in students]
    
    result = service.assign_subject_to_students(9999, student_ids)
    
    assert result['success'] is False
    assert 'не найден' in result['message']


@pytest.mark.django_db
def test_assign_subject_invalid_students(teacher, subjects):
    """Тест назначения предмета несуществующим студентам"""
    service = TeacherDashboardService(teacher)
    subject = subjects[0]
    
    result = service.assign_subject_to_students(subject.id, [9999, 9998])
    
    assert result['success'] is False
    assert 'не является студентами' in result['message']


@pytest.mark.django_db
def test_get_all_subjects(teacher, subjects):
    """Тест получения всех предметов"""
    service = TeacherDashboardService(teacher)
    
    # Назначаем студента на один предмет для проверки счетчика
    student = User.objects.create_user(
        username='student3',
        email='student3@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Студент',
        last_name='Три'
    )
    SubjectEnrollment.objects.create(
        student=student,
        subject=subjects[0],
        teacher=teacher,
        is_active=True
    )
    
    result = service.get_all_subjects()
    
    assert len(result) == 2
    assert result[0]['name'] in ['Математика', 'Физика']
    assert 'student_count' in result[0]


@pytest.mark.django_db
def test_get_subject_students(teacher, students, subjects):
    """Тест получения студентов по предмету"""
    service = TeacherDashboardService(teacher)
    subject = subjects[0]
    student_ids = [s.id for s in students]
    
    # Назначаем предмет
    service.assign_subject_to_students(subject.id, student_ids)
    
    # Получаем студентов
    result = service.get_subject_students(subject.id)
    
    assert len(result) == 2
    assert all('id' in s for s in result)
    assert all('name' in s for s in result)
    assert all('email' in s for s in result)


@pytest.mark.django_db
def test_assign_subject_activates_inactive_enrollment(teacher, students, subjects):
    """Тест активации неактивного зачисления"""
    service = TeacherDashboardService(teacher)
    subject = subjects[0]
    
    # Создаем неактивное зачисление
    SubjectEnrollment.objects.create(
        student=students[0],
        subject=subject,
        teacher=teacher,
        is_active=False
    )
    
    # Назначаем предмет (должно активировать зачисление)
    result = service.assign_subject_to_students(subject.id, [students[0].id])
    
    assert result['success'] is True
    assert result['created_count'] == 1
    
    # Проверяем, что зачисление стало активным
    enrollment = SubjectEnrollment.objects.get(
        student=students[0],
        subject=subject,
        teacher=teacher
    )
    assert enrollment.is_active is True

