import io
import json
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from backend.materials.models import Subject, SubjectEnrollment, Material, MaterialSubmission, MaterialFeedback


User = get_user_model()


def create_student_with_enrollment(db):
    teacher = User.objects.create_user(username="teacher1", password="pass", role=User.Role.TEACHER)
    student = User.objects.create_user(username="student1", password="pass", role=User.Role.STUDENT)
    subject = Subject.objects.create(name="Math")
    SubjectEnrollment.objects.create(student=student, subject=subject, teacher=teacher, is_active=True)
    return student, teacher, subject


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_student_list_subjects(db):
    student, teacher, subject = create_student_with_enrollment(db)
    client = auth_client(student)
    url = "/api/student/subjects/"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["subject"]["id"] == subject.id for item in data)


def test_student_subject_materials_and_teacher(db):
    student, teacher, subject = create_student_with_enrollment(db)
    material = Material.objects.create(
        title="M1", description="d", content="c", author=teacher, subject=subject, status=Material.Status.ACTIVE, is_public=True
    )
    material.assigned_to.add(student)
    client = auth_client(student)

    # materials
    m_url = f"/api/student/subjects/{subject.id}/materials/"
    resp = client.get(m_url)
    assert resp.status_code == 200
    assert any(m["id"] == material.id for m in resp.json())

    # teacher
    t_url = f"/api/student/subjects/{subject.id}/teacher/"
    resp = client.get(t_url)
    assert resp.status_code == 200
    assert resp.json()["id"] == teacher.id


def test_student_submit_and_get_feedback(db):
    student, teacher, subject = create_student_with_enrollment(db)
    material = Material.objects.create(
        title="M1", description="d", content="c", author=teacher, subject=subject, status=Material.Status.ACTIVE, is_public=True
    )
    material.assigned_to.add(student)
    client = auth_client(student)

    # submit
    submit_url = f"/api/student/materials/{material.id}/submissions/"
    resp = client.post(submit_url, {"submission_text": "answer"}, format="multipart")
    assert resp.status_code == 201
    submission_id = resp.json()["id"]

    # teacher leaves feedback
    t_client = auth_client(teacher)
    feedback_create_url = "/api/materials/submissions/"  # router base
    # Find created submission
    submission = MaterialSubmission.objects.get(id=submission_id)
    feedback = MaterialFeedback.objects.create(
        submission=submission,
        teacher=teacher,
        feedback_text="ok",
        grade=5,
    )

    # student fetches feedback
    fb_url = f"/api/student/submissions/{submission_id}/feedback/"
    resp = client.get(fb_url)
    assert resp.status_code == 200
    assert resp.json()["grade"] == 5


