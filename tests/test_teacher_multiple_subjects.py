"""
Тесты для проверки отображения всех предметов студента у преподавателя
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from backend.materials.models import Subject, SubjectEnrollment
from backend.materials.teacher_dashboard_service import TeacherDashboardService

User = get_user_model()


@pytest.mark.django_db
class TestTeacherMultipleSubjects:
    """Тесты отображения всех предметов студента у преподавателя"""

    @pytest.fixture
    def setup_teacher_and_student(self):
        """Создаем преподавателя и студента для тестирования"""
        teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher',
            last_name='One'
        )
        teacher_token = Token.objects.create(user=teacher)

        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='One',
            is_staff=False,
            is_superuser=False
        )

        return {
            'teacher': teacher,
            'teacher_token': teacher_token,
            'student': student
        }

    def test_teacher_sees_all_student_subjects(self, setup_teacher_and_student):
        """Тест: преподаватель видит все предметы студента, которые он назначил"""
        teacher = setup_teacher_and_student['teacher']
        student = setup_teacher_and_student['student']

        # Создаем 2 предмета
        subject1 = Subject.objects.create(
            name='Математика',
            description='Математика предмет',
            color='#FF0000'
        )
        subject2 = Subject.objects.create(
            name='Физика',
            description='Физика предмет',
            color='#00FF00'
        )

        # Назначаем оба предмета студенту этим преподавателем
        enrollment1 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject1,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )
        enrollment2 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject2,
            teacher=teacher,
            assigned_by=teacher,
            is_active=True
        )

        # Проверяем через сервис
        service = TeacherDashboardService(teacher)
        students = service.get_teacher_students()

        assert len(students) == 1
        student_data = students[0]

        # Проверяем, что студент есть в списке
        assert student_data['id'] == student.id
        assert student_data['username'] == student.username

        # Проверяем, что у студента есть список предметов
        assert 'subjects' in student_data
        assert isinstance(student_data['subjects'], list)

        # Проверяем, что оба предмета отображаются
        assert len(student_data['subjects']) == 2

        subject_ids = [s['id'] for s in student_data['subjects']]
        assert subject1.id in subject_ids
        assert subject2.id in subject_ids

        # Проверяем, что данные предметов корректны
        subject1_data = next(s for s in student_data['subjects'] if s['id'] == subject1.id)
        subject2_data = next(s for s in student_data['subjects'] if s['id'] == subject2.id)

        assert subject1_data['name'] == 'Математика'
        assert subject1_data['color'] == '#FF0000'
        assert subject1_data['enrollment_id'] == enrollment1.id

        assert subject2_data['name'] == 'Физика'
        assert subject2_data['color'] == '#00FF00'
        assert subject2_data['enrollment_id'] == enrollment2.id

        print(f"✅ Преподаватель {teacher.username} видит {len(student_data['subjects'])} предметов студента {student.username}")

    def test_teacher_sees_only_his_subjects(self, setup_teacher_and_student):
        """Тест: преподаватель видит только предметы, которые он назначил"""
        teacher1 = setup_teacher_and_student['teacher']
        student = setup_teacher_and_student['student']

        # Создаем второго преподавателя
        teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher',
            last_name='Two'
        )

        # Создаем предметы
        subject1 = Subject.objects.create(
            name='Математика',
            description='Математика предмет',
            color='#FF0000'
        )
        subject2 = Subject.objects.create(
            name='Физика',
            description='Физика предмет',
            color='#00FF00'
        )

        # Преподаватель 1 назначает предмет 1
        SubjectEnrollment.objects.create(
            student=student,
            subject=subject1,
            teacher=teacher1,
            assigned_by=teacher1,
            is_active=True
        )

        # Преподаватель 2 назначает предмет 2
        SubjectEnrollment.objects.create(
            student=student,
            subject=subject2,
            teacher=teacher2,
            assigned_by=teacher2,
            is_active=True
        )

        # Проверяем, что teacher1 видит только свой предмет
        service1 = TeacherDashboardService(teacher1)
        students1 = service1.get_teacher_students()

        assert len(students1) == 1
        student_data1 = students1[0]
        assert len(student_data1['subjects']) == 1
        assert student_data1['subjects'][0]['id'] == subject1.id

        # Проверяем, что teacher2 видит только свой предмет
        service2 = TeacherDashboardService(teacher2)
        students2 = service2.get_teacher_students()

        assert len(students2) == 1
        student_data2 = students2[0]
        assert len(student_data2['subjects']) == 1
        assert student_data2['subjects'][0]['id'] == subject2.id

        print(f"✅ Преподаватель 1 видит {len(student_data1['subjects'])} предмет, преподаватель 2 видит {len(student_data2['subjects'])} предмет")

    def test_teacher_api_returns_all_subjects(self, setup_teacher_and_student):
        """Тест: API возвращает все предметы студента"""
        teacher = setup_teacher_and_student['teacher']
        teacher_token = setup_teacher_and_student['teacher_token']
        student = setup_teacher_and_student['student']

        # Создаем 3 предмета
        subject1 = Subject.objects.create(name='Математика', description='Математика', color='#FF0000')
        subject2 = Subject.objects.create(name='Физика', description='Физика', color='#00FF00')
        subject3 = Subject.objects.create(name='Химия', description='Химия', color='#0000FF')

        # Назначаем все предметы студенту
        SubjectEnrollment.objects.create(student=student, subject=subject1, teacher=teacher, assigned_by=teacher, is_active=True)
        SubjectEnrollment.objects.create(student=student, subject=subject2, teacher=teacher, assigned_by=teacher, is_active=True)
        SubjectEnrollment.objects.create(student=student, subject=subject3, teacher=teacher, assigned_by=teacher, is_active=True)

        # Проверяем через API
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {teacher_token.key}')

        response = client.get('/materials/dashboard/teacher/')

        assert response.status_code == 200
        assert 'students' in response.data

        students = response.data['students']
        assert len(students) == 1

        student_data = students[0]
        assert 'subjects' in student_data
        assert len(student_data['subjects']) == 3

        subject_ids = [s['id'] for s in student_data['subjects']]
        assert subject1.id in subject_ids
        assert subject2.id in subject_ids
        assert subject3.id in subject_ids

        print(f"✅ API возвращает {len(student_data['subjects'])} предметов студента")

