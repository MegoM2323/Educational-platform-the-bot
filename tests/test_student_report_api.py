from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from materials.models import Subject, SubjectEnrollment


class StudentReportAPITest(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.teacher = User.objects.create_user(username='teach', role='teacher')
        self.student = User.objects.create_user(username='stud', role='student')
        self.parent = User.objects.create_user(username='par', role='parent')

        # Subject enrollment binds student to teacher
        self.subject = Subject.objects.create(name='Biology')
        SubjectEnrollment.objects.create(student=self.student, subject=self.subject, teacher=self.teacher)

        self.client.force_authenticate(self.teacher)

    def test_available_students(self):
        url = '/api/reports/student-reports/available_students/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['students']), 1)
        self.assertEqual(resp.data['students'][0]['id'], self.student.id)

    def test_create_and_list_student_reports(self):
        # Create
        url = '/api/reports/student-reports/'
        payload = {
            'student': self.student.id,
            'title': 'Weekly report',
            'description': '',
            'report_type': 'progress',
            'period_start': '2024-01-01',
            'period_end': '2024-01-07',
            'content': {'summary': 'ok'}
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        report_id = resp.data['id']

        # List for teacher
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data['count'] if isinstance(resp.data, dict) and 'results' in resp.data else len(resp.data), 1)

        # Retrieve
        detail_url = f"/api/reports/student-reports/{report_id}/"
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['id'], report_id)


