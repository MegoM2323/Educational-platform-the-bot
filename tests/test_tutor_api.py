import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import StudentProfile
from materials.models import Subject


User = get_user_model()


@pytest.mark.django_db
def test_tutor_create_student_endpoint():
    tutor = User.objects.create_user(username='tutor1', password='pass', role=User.Role.TUTOR)

    client = APIClient()
    client.force_authenticate(user=tutor)

    payload = {
        'first_name': 'Ivan',
        'last_name': 'Petrov',
        'grade': '7',
        'goal': 'Improve math',
        'parent_first_name': 'Olga',
        'parent_last_name': 'Petrova',
        'parent_email': 'olga@example.com',
        'parent_phone': '+79990000000',
    }

    resp = client.post('/api/auth/tutor/students/', payload, format='json')
    assert resp.status_code == 201
    data = resp.json()
    assert 'student' in data and 'credentials' in data and 'parent' in data
    assert 'student' in data['credentials'] and 'parent' in data['credentials']
    assert 'username' in data['credentials']['student'] and 'password' in data['credentials']['student']


@pytest.mark.django_db
def test_tutor_assign_subject_endpoint():
    tutor = User.objects.create_user(username='tutor1', password='pass', role=User.Role.TUTOR)
    teacher = User.objects.create_user(username='teacher1', password='pass', role=User.Role.TEACHER)

    # Создадим ученика и профиль, привязанного к тьютору
    student = User.objects.create_user(username='student1', password='pass', role=User.Role.STUDENT)
    StudentProfile.objects.create(user=student, grade='7', goal='', tutor=tutor)
    subject = Subject.objects.create(name='Math', description='desc', color='#00ff00')

    client = APIClient()
    client.force_authenticate(user=tutor)

    # Найдем profile id
    profile_id = student.student_profile.id
    resp = client.post(f'/api/auth/tutor/students/{profile_id}/subjects/', {
        'subject_id': subject.id,
        'teacher_id': teacher.id,
    }, format='json')
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data['subject'] == subject.id
    assert data['teacher'] == teacher.id



@pytest.mark.django_db
def test_tutor_assign_subjects_bulk_and_list():
    tutor = User.objects.create_user(username='tutor2', password='pass', role=User.Role.TUTOR)
    teacher1 = User.objects.create_user(username='teacherA', password='pass', role=User.Role.TEACHER)
    teacher2 = User.objects.create_user(username='teacherB', password='pass', role=User.Role.TEACHER)

    student = User.objects.create_user(username='student2', password='pass', role=User.Role.STUDENT)
    StudentProfile.objects.create(user=student, grade='8', goal='', tutor=tutor)

    subj1 = Subject.objects.create(name='Physics', description='desc', color='#111111')
    subj2 = Subject.objects.create(name='Chemistry', description='desc', color='#222222')

    client = APIClient()
    client.force_authenticate(user=tutor)

    profile_id = student.student_profile.id

    # Bulk assign
    resp = client.post(
        f'/api/auth/tutor/students/{profile_id}/subjects/bulk/',
        {
            'items': [
                {'subject_id': subj1.id, 'teacher_id': teacher1.id},
                {'subject_id': subj2.id, 'teacher_id': teacher2.id},
            ]
        },
        format='json',
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data, list)
    teacher_ids = sorted([row['teacher'] for row in data])
    subject_ids = sorted([row['subject'] for row in data])
    assert teacher_ids == sorted([teacher1.id, teacher2.id])
    assert subject_ids == sorted([subj1.id, subj2.id])

    # List assigned
    resp_list = client.get(f'/api/auth/tutor/students/{profile_id}/subjects/')
    assert resp_list.status_code == 200
    listed = resp_list.json()
    assert len(listed) >= 2
    listed_subject_ids = {row['subject'] for row in listed}
    assert subj1.id in listed_subject_ids and subj2.id in listed_subject_ids

