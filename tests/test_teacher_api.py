import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from backend.materials.models import Subject, Material


@pytest.mark.django_db
def test_teacher_pending_and_feedback_flow():
    User = get_user_model()
    teacher = User.objects.create_user(username='t1', password='pass', role=User.Role.TEACHER)
    student = User.objects.create_user(username='s1', password='pass', role=User.Role.STUDENT)

    subject = Subject.objects.create(name='Math')
    material = Material.objects.create(
        title='HW1', description='desc', content='content', author=teacher, subject=subject, status=Material.Status.ACTIVE,
        type=Material.Type.HOMEWORK
    )
    material.assigned_to.add(student)

    client = APIClient()
    client.login(username='s1', password='pass')

    # student submits answer
    resp = client.post(reverse('materialsubmission-list') + 'submit_answer/', {
        'material_id': material.id,
        'submission_text': 'my answer'
    }, format='multipart')
    assert resp.status_code in (200, 201)

    client.logout()
    client.login(username='t1', password='pass')

    # teacher gets pending submissions
    resp = client.get(reverse('teacher-pending-submissions'))
    assert resp.status_code == 200
    pending = resp.data['pending']
    assert len(pending) == 1
    submission_id = pending[0]['id']

    # teacher posts feedback
    resp = client.post(reverse('teacher-submission-feedback', args=[submission_id]), {
        'feedback_text': 'good job',
        'grade': 5
    })
    assert resp.status_code in (200, 201)

    # teacher updates status
    resp = client.put(reverse('teacher-submission-status', args=[submission_id]), {
        'status': 'reviewed'
    })
    assert resp.status_code == 200


@pytest.mark.django_db
def test_teacher_material_assignments_update():
    User = get_user_model()
    teacher = User.objects.create_user(username='t2', password='pass', role=User.Role.TEACHER)
    s1 = User.objects.create_user(username='s2', password='pass', role=User.Role.STUDENT)
    s2 = User.objects.create_user(username='s3', password='pass', role=User.Role.STUDENT)
    subject = Subject.objects.create(name='Physics')
    material = Material.objects.create(
        title='L1', description='desc', content='content', author=teacher, subject=subject, status=Material.Status.ACTIVE,
    )

    client = APIClient()
    client.login(username='t2', password='pass')

    # Update assignments
    url = reverse('teacher-material-assignments', args=[material.id])
    resp = client.put(url, {'student_ids': [s1.id, s2.id]}, format='json')
    assert resp.status_code == 200
    assert resp.data['assigned_count'] == 2

    # Get assignments
    resp = client.get(url)
    assert resp.status_code == 200
    assert len(resp.data['assigned_students']) == 2


