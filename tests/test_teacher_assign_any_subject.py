"""
Тесты для проверки возможности преподавателя назначить любой предмет студенту
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from materials.models import Subject, TeacherSubject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db
class TestTeacherAssignAnySubject:
    """Тестирование назначения любого предмета преподавателем"""
    
    @pytest.fixture
    def setup_data(self):
        """Создание тестовых данных"""
        # Создаем преподавателя
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Учитель',
            last_name='Тестовый'
        )
        
        # Создаем студента
        student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Студент',
            last_name='Тестовый'
        )
        
        # Создаем предметы
        math = Subject.objects.create(
            name='Математика',
            description='Тестовая математика',
            color='#FF0000'
        )
        
        physics = Subject.objects.create(
            name='Физика',
            description='Тестовая физика',
            color='#00FF00'
        )
        
        chemistry = Subject.objects.create(
            name='Химия',
            description='Тестовая химия',
            color='#0000FF'
        )
        
        # Назначаем только математику преподавателю (через TeacherSubject)
        TeacherSubject.objects.create(
            teacher=teacher,
            subject=math,
            is_active=True
        )
        
        # Создаем токен для преподавателя
        token = Token.objects.create(user=teacher)
        
        return {
            'teacher': teacher,
            'student': student,
            'math': math,
            'physics': physics,
            'chemistry': chemistry,
            'token': token
        }
    
    def test_teacher_can_see_all_subjects(self, setup_data):
        """Тест: преподаватель видит ВСЕ предметы, не только свои"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {setup_data["token"].key}')
        
        response = client.get('/materials/teacher/subjects/')
        
        assert response.status_code == 200
        assert 'subjects' in response.data
        
        subjects = response.data['subjects']
        assert len(subjects) >= 3  # Минимум 3 тестовых предмета
        
        # Проверяем, что есть все три предмета
        subject_names = [s['name'] for s in subjects]
        assert 'Математика' in subject_names
        assert 'Физика' in subject_names
        assert 'Химия' in subject_names
        
        # Проверяем флаг is_assigned
        math_subject = next(s for s in subjects if s['name'] == 'Математика')
        physics_subject = next(s for s in subjects if s['name'] == 'Физика')
        
        assert math_subject['is_assigned'] is True  # Математика уже назначена
        assert physics_subject['is_assigned'] is False  # Физика не назначена
        
        print("✓ Преподаватель видит все предметы")
    
    def test_teacher_can_assign_non_assigned_subject(self, setup_data):
        """Тест: преподаватель может назначить предмет, который ему не назначен"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {setup_data["token"].key}')
        
        teacher = setup_data['teacher']
        student = setup_data['student']
        physics = setup_data['physics']
        
        # Проверяем, что связи TeacherSubject для физики нет
        assert not TeacherSubject.objects.filter(
            teacher=teacher,
            subject=physics
        ).exists()
        
        # Назначаем физику студенту
        response = client.post(
            '/materials/teacher/subjects/assign/',
            {
                'subject_id': physics.id,
                'student_ids': [student.id]
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert response.data['success'] is True
        
        # Проверяем, что создалась связь TeacherSubject
        teacher_subject = TeacherSubject.objects.filter(
            teacher=teacher,
            subject=physics,
            is_active=True
        ).first()
        
        assert teacher_subject is not None, "Связь TeacherSubject должна быть создана автоматически"
        
        # Проверяем, что создалось зачисление
        enrollment = SubjectEnrollment.objects.filter(
            student=student,
            subject=physics,
            teacher=teacher,
            is_active=True
        ).first()
        
        assert enrollment is not None, "Зачисление должно быть создано"
        
        print("✓ Преподаватель успешно назначил предмет, который ему не был назначен")
    
    def test_teacher_can_assign_multiple_subjects(self, setup_data):
        """Тест: преподаватель может назначить несколько разных предметов"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {setup_data["token"].key}')
        
        teacher = setup_data['teacher']
        student = setup_data['student']
        physics = setup_data['physics']
        chemistry = setup_data['chemistry']
        
        # Назначаем физику
        response1 = client.post(
            '/materials/teacher/subjects/assign/',
            {
                'subject_id': physics.id,
                'student_ids': [student.id]
            },
            format='json'
        )
        
        assert response1.status_code == 200
        assert response1.data['success'] is True
        
        # Назначаем химию
        response2 = client.post(
            '/materials/teacher/subjects/assign/',
            {
                'subject_id': chemistry.id,
                'student_ids': [student.id]
            },
            format='json'
        )
        
        assert response2.status_code == 200
        assert response2.data['success'] is True
        
        # Проверяем, что у преподавателя теперь 3 предмета
        teacher_subjects_count = TeacherSubject.objects.filter(
            teacher=teacher,
            is_active=True
        ).count()
        
        assert teacher_subjects_count == 3  # Математика + Физика + Химия
        
        # Проверяем, что у студента 3 зачисления
        enrollments_count = SubjectEnrollment.objects.filter(
            student=student,
            teacher=teacher,
            is_active=True
        ).count()
        
        assert enrollments_count == 3
        
        print("✓ Преподаватель успешно назначил несколько предметов")
    
    def test_teacher_cannot_assign_to_admin(self, setup_data):
        """Тест: преподаватель не может назначить предмет администратору"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {setup_data["token"].key}')
        
        # Создаем админа
        admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role=User.Role.STUDENT,  # Роль студента
            is_staff=True,  # Но является админом
            is_superuser=False
        )
        
        physics = setup_data['physics']
        
        # Пытаемся назначить предмет админу
        response = client.post(
            '/materials/teacher/subjects/assign/',
            {
                'subject_id': physics.id,
                'student_ids': [admin.id]
            },
            format='json'
        )
        
        # Backend должен отфильтровать админов
        assert response.status_code == 200
        assert response.data['success'] is False
        assert 'администратор' in response.data['message'].lower()
        
        print("✓ Преподаватель не может назначить предмет администратору")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

