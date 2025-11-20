"""
Интеграционный тест полного потока назначения предметов
"""
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


@pytest.mark.django_db
def test_complete_subject_assignment_flow():
    """Тест полного потока назначения предмета"""
    # 1. Создаем преподавателя
    teacher = User.objects.create_user(
        username='test_teacher_flow',
        email='test_teacher_flow@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Преподаватель',
        last_name='Тест'
    )
    
    # 2. Создаем предмет
    subject = Subject.objects.create(
        name='Математика',
        description='Алгебра и геометрия',
        color='#3B82F6'
    )
    
    # 3. Создаем студентов
    students = []
    for i in range(3):
        student = User.objects.create_user(
            username=f'test_student_{i}',
            email=f'test_student_{i}@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Студент',
            last_name=f'Тест{i}'
        )
        students.append(student)
    
    # 4. Назначаем предмет студентам через сервис
    service = TeacherDashboardService(teacher)
    student_ids = [s.id for s in students]
    
    result = service.assign_subject_to_students(subject.id, student_ids)
    
    assert result['success'] is True
    assert result['created_count'] == 3
    
    # 5. Проверяем, что зачисления созданы
    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        teacher=teacher
    )
    assert enrollments.count() == 3
    
    # 6. Проверяем активность зачислений
    for enrollment in enrollments:
        assert enrollment.is_active is True
        assert enrollment.teacher == teacher
    
    # 7. Проверяем, что студенты зачислены на предмет
    for student in students:
        assert SubjectEnrollment.objects.filter(
            student=student,
            subject=subject,
            is_active=True
        ).exists()
    
    print("✓ Все проверки пройдены успешно!")


@pytest.mark.django_db
def test_get_teachers_for_subject():
    """Тест получения преподавателей для предмета"""
    import time
    timestamp = int(time.time())
    
    # Создаем два преподавателя
    teacher1 = User.objects.create_user(
        username=f'teacher1_{timestamp}',
        email=f'teacher1_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Преподаватель',
        last_name='Один'
    )
    
    teacher2 = User.objects.create_user(
        username=f'teacher2_{timestamp}',
        email=f'teacher2_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Преподаватель',
        last_name='Два'
    )
    
    # Создаем предмет
    subject = Subject.objects.create(
        name='Физика',
        description='Механика, оптика',
        color='#10B981'
    )
    
    # Создаем студента
    student = User.objects.create_user(
        username='student',
        email='student@test.com',
        password='testpass123',
        role=User.Role.STUDENT
    )
    
    # Назначаем предмет разными преподавателями
    service1 = TeacherDashboardService(teacher1)
    service1.assign_subject_to_students(subject.id, [student.id])
    
    service2 = TeacherDashboardService(teacher2)
    service2.assign_subject_to_students(subject.id, [student.id])
    
    # Проверяем, что оба преподавателя ведут этот предмет
    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        is_active=True
    )
    
    teacher_ids = set(e.teacher_id for e in enrollments)
    assert teacher1.id in teacher_ids
    assert teacher2.id in teacher_ids
    
    print("✓ Преподаватели для предмета получены успешно!")


@pytest.mark.django_db
def test_subject_list_with_student_count():
    """Тест получения списка предметов с количеством студентов"""
    # Создаем преподавателя
    teacher = User.objects.create_user(
        username='teacher_count',
        email='teacher_count@test.com',
        password='testpass123',
        role=User.Role.TEACHER
    )
    
    # Создаем два предмета
    subject1 = Subject.objects.create(name='Математика', description='Алгебра', color='#3B82F6')
    subject2 = Subject.objects.create(name='Физика', description='Механика', color='#10B981')
    
    # Создаем студентов
    students = []
    for i in range(5):
        student = User.objects.create_user(
            username=f'student_{i}',
            email=f'student_{i}@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        students.append(student)
    
    # Назначаем студентов на предметы
    service = TeacherDashboardService(teacher)
    
    # 3 студента на математику
    service.assign_subject_to_students(subject1.id, [s.id for s in students[:3]])
    
    # 2 студента на физику
    service.assign_subject_to_students(subject2.id, [s.id for s in students[3:]])
    
    # Получаем список предметов
    subjects = service.get_all_subjects()
    
    # Находим наши предметы в списке
    math_subject = next((s for s in subjects if s['name'] == 'Математика'), None)
    physics_subject = next((s for s in subjects if s['name'] == 'Физика'), None)
    
    assert math_subject is not None
    assert physics_subject is not None
    assert math_subject['student_count'] == 3
    assert physics_subject['student_count'] == 2
    
    print("✓ Список предметов с количеством студентов получен успешно!")


if __name__ == '__main__':
    print("Запуск интеграционных тестов назначения предметов...")
    pytest.main([__file__, '-v'])

