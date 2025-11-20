from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from materials.models import Subject, SubjectEnrollment
from accounts.tutor_service import SubjectAssignmentService


User = get_user_model()


class SubjectAssignmentServiceTest(TestCase):
    def setUp(self):
        self.tutor = User.objects.create_user(username='tutor1', password='pass', role=User.Role.TUTOR)
        self.student = User.objects.create_user(username='student1', password='pass', role=User.Role.STUDENT)
        # Создаем профиль студента и привязываем к тьютору
        from accounts.models import StudentProfile
        self.student_profile = StudentProfile.objects.create(user=self.student, grade='10', tutor=self.tutor)

        self.teacher = User.objects.create_user(username='teacher1', password='pass', role=User.Role.TEACHER)
        self.subject = Subject.objects.create(name='Математика')

    def test_assign_with_explicit_teacher(self):
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
        )
        self.assertIsInstance(enrollment, SubjectEnrollment)
        self.assertEqual(enrollment.teacher, self.teacher)
        self.assertTrue(enrollment.is_active)

    def test_assign_with_auto_teacher(self):
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=None,
        )
        self.assertIsInstance(enrollment, SubjectEnrollment)
        self.assertEqual(enrollment.subject, self.subject)
        self.assertEqual(enrollment.student, self.student)
        self.assertIsNotNone(enrollment.teacher)


class SubjectAssignmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tutor = User.objects.create_user(username='tutor2', password='pass', role=User.Role.TUTOR)
        self.student = User.objects.create_user(username='student2', password='pass', role=User.Role.STUDENT)
        from accounts.models import StudentProfile
        self.student_profile = StudentProfile.objects.create(user=self.student, grade='9', tutor=self.tutor)

        self.teacher = User.objects.create_user(username='teacher2', password='pass', role=User.Role.TEACHER)
        self.subject = Subject.objects.create(name='Физика')

    def test_assign_subject_api_auto_teacher(self):
        self.client.force_authenticate(user=self.tutor)
        url = f"/api/tutor/students/{self.student_profile.id}/subjects/"
        resp = self.client.post(url, data={"subject_id": self.subject.id}, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['subject'], self.subject.id)
        self.assertTrue(data['is_active'])

    def test_assign_subject_api_with_teacher(self):
        self.client.force_authenticate(user=self.tutor)
        url = f"/api/tutor/students/{self.student_profile.id}/subjects/"
        resp = self.client.post(url, data={"subject_id": self.subject.id, "teacher_id": self.teacher.id}, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['teacher'], self.teacher.id)


