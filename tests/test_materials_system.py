import io
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from backend.materials.models import Subject, Material, SubjectEnrollment, MaterialSubmission
from backend.notifications.models import Notification


User = get_user_model()


class MaterialsSystemAPITests(APITestCase):
    def setUp(self):
        # Users
        self.teacher = User.objects.create_user(
            username='teacher1', password='pass', role=User.Role.TEACHER, first_name='T', last_name='One'
        )
        self.tutor = User.objects.create_user(
            username='tutor1', password='pass', role=User.Role.TUTOR
        )
        self.student = User.objects.create_user(
            username='student1', password='pass', role=User.Role.STUDENT, first_name='S', last_name='One'
        )

        # Subject
        self.subject = Subject.objects.create(name='Математика')

        # Enrollment (student-subject-teacher)
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            assigned_by=self.tutor,
        )

        # Material
        self.material = Material.objects.create(
            title='Домашнее задание #1',
            description='Список задач',
            content='Текст задания',
            author=self.teacher,
            subject=self.subject,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
            is_public=False,
        )

        self.client = APIClient()

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_assign_material_sends_notifications_to_students(self):
        self.authenticate(self.teacher)
        url = reverse('material-list')  # router base; we'll use custom action path directly
        assign_url = f"/api/materials/materials/{self.material.id}/assign/"

        resp = self.client.post(assign_url, {'student_ids': [self.student.id]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Check assigned
        self.material.refresh_from_db()
        self.assertTrue(self.material.assigned_to.filter(id=self.student.id).exists())

        # Check notification
        notif_exists = Notification.objects.filter(
            recipient=self.student,
            type=Notification.Type.MATERIAL_PUBLISHED,
            related_object_id=None  # data is stored in data field; ensure at least created
        ).exists()
        self.assertTrue(notif_exists)

    def test_student_submit_answer_creates_submission_and_notifies_teacher(self):
        # Ensure material is assigned
        self.material.assigned_to.set([self.student])
        self.authenticate(self.student)

        submit_url = "/api/materials/submissions/submit_answer/"
        # Prepare multipart form data
        file_content = io.BytesIO(b"answer content")
        file_content.name = 'answer.txt'

        data = {
            'material_id': str(self.material.id),
            'submission_text': 'Мой ответ',
            'submission_file': file_content,
        }

        resp = self.client.post(submit_url, data, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Submission exists
        self.assertTrue(MaterialSubmission.objects.filter(material=self.material, student=self.student).exists())

        # Teacher notified
        teacher_notified = Notification.objects.filter(
            recipient=self.teacher,
            type=Notification.Type.HOMEWORK_SUBMITTED,
        ).exists()
        self.assertTrue(teacher_notified)


