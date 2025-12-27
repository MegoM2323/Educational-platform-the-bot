"""
Tests for parent report sharing functionality (T_REPORT_009)
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta

from .models import StudentReport, ParentReportPreference
from accounts.models import StudentProfile

User = get_user_model()


class ParentReportSharingTests(APITestCase):
    """Test parent access to student progress reports"""

    def setUp(self):
        """Set up test data"""
        # Create users
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.parent = User.objects.create_user(
            username='parent',
            email='parent@test.com',
            password='testpass123',
            role='parent'
        )

        self.other_parent = User.objects.create_user(
            username='other_parent',
            email='other_parent@test.com',
            password='testpass123',
            role='parent'
        )

        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

        # Create student profile with parent
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            parent=self.parent,
            grade='10A'
        )

        # Create test report
        self.report = StudentReport.objects.create(
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            title='Progress Report',
            description='Student progress for the month',
            report_type='progress',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            overall_grade='A',
            progress_percentage=85,
            attendance_percentage=95,
            behavior_rating=8,
            recommendations='Keep up the good work',
            show_to_parent=True
        )

        # Create hidden report
        self.hidden_report = StudentReport.objects.create(
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            title='Sensitive Report',
            description='Teacher notes',
            report_type='behavior',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            behavior_rating=7,
            show_to_parent=False
        )

        self.client = APIClient()

    def test_parent_view_own_childs_report(self):
        """Test parent can view their own child's report"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/reports/student-reports/{self.report.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.report.id)
        self.assertEqual(response.data['show_to_parent'], True)

    def test_parent_cannot_view_hidden_report(self):
        """Test parent cannot view report with show_to_parent=False"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/reports/student-reports/{self.hidden_report.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_parent_cannot_view_report(self):
        """Test parent cannot view other parent's child's report"""
        self.client.force_authenticate(user=self.other_parent)
        response = self.client.get(f'/api/reports/student-reports/{self.report.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_edit_report(self):
        """Test student has read-only access"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/reports/student-reports/{self.report.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to edit - should fail
        response = self.client.put(f'/api/reports/student-reports/{self.report.id}/', {
            'title': 'Hacked'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_manage_own_reports(self):
        """Test teacher can edit their own reports"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(f'/api/reports/student-reports/{self.report.id}/', {
            'title': 'Updated Report',
            'show_to_parent': False
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['show_to_parent'], False)

    def test_admin_can_view_all_reports(self):
        """Test admin can view all reports"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/reports/student-reports/{self.hidden_report.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_parent_acknowledge_report(self):
        """Test parent can acknowledge reading report"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.post(f'/api/reports/student-reports/{self.report.id}/acknowledge/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('report', response.data)

        # Verify in database
        self.report.refresh_from_db()
        self.assertTrue(self.report.parent_acknowledged)
        self.assertIsNotNone(self.report.parent_acknowledged_at)

    def test_parent_cannot_acknowledge_others_report(self):
        """Test parent cannot acknowledge other parent's report"""
        self.client.force_authenticate(user=self.other_parent)
        response = self.client.post(f'/api/reports/student-reports/{self.report.id}/acknowledge/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_acknowledge_report(self):
        """Test teacher cannot acknowledge report"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(f'/api/reports/student-reports/{self.report.id}/acknowledge/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_parent_my_children_endpoint(self):
        """Test parent can get reports for all their children"""
        # Create another student with same parent
        student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role='student'
        )

        StudentProfile.objects.create(
            user=student2,
            parent=self.parent,
            grade='9A'
        )

        report2 = StudentReport.objects.create(
            teacher=self.teacher,
            student=student2,
            parent=self.parent,
            title='Progress Report 2',
            report_type='progress',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            show_to_parent=True
        )

        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/student-reports/my_children/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        ids = [r['id'] for r in response.data]
        self.assertIn(self.report.id, ids)
        self.assertIn(report2.id, ids)

    def test_non_parent_cannot_access_my_children(self):
        """Test non-parent cannot access my_children endpoint"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/reports/student-reports/my_children/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ParentReportPreferenceTests(APITestCase):
    """Test parent report preference settings"""

    def setUp(self):
        """Set up test data"""
        self.parent = User.objects.create_user(
            username='parent',
            email='parent@test.com',
            password='testpass123',
            role='parent'
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.client = APIClient()

    def test_parent_get_preferences(self):
        """Test parent can get their report preferences"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent-preferences/my_settings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notify_on_report_created'], True)
        self.assertEqual(response.data['notify_on_grade_posted'], True)
        self.assertEqual(response.data['show_grades'], True)
        self.assertEqual(response.data['show_progress'], True)

    def test_parent_update_preferences(self):
        """Test parent can update their report preferences"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.put('/api/reports/parent-preferences/my_settings/', {
            'notify_on_report_created': False,
            'show_grades': False
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notify_on_report_created'], False)
        self.assertEqual(response.data['show_grades'], False)
        self.assertEqual(response.data['show_progress'], True)  # Unchanged

        # Verify in database
        preference = ParentReportPreference.objects.get(parent=self.parent)
        self.assertFalse(preference.notify_on_report_created)
        self.assertFalse(preference.show_grades)

    def test_non_parent_cannot_access_preferences(self):
        """Test non-parent cannot access preferences endpoint"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/reports/parent-preferences/my_settings/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_preferences_auto_create(self):
        """Test preferences are auto-created on first access"""
        self.assertFalse(ParentReportPreference.objects.filter(parent=self.parent).exists())

        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent-preferences/my_settings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ParentReportPreference.objects.filter(parent=self.parent).exists())


class ReportVisibilityTests(APITestCase):
    """Test report visibility and filtering based on parent access"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.parent1 = User.objects.create_user(
            username='parent1',
            email='parent1@test.com',
            password='testpass123',
            role='parent'
        )

        self.parent2 = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role='parent'
        )

        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role='student'
        )

        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role='student'
        )

        StudentProfile.objects.create(user=self.student1, parent=self.parent1)
        StudentProfile.objects.create(user=self.student2, parent=self.parent2)

        # Create reports
        self.report1 = StudentReport.objects.create(
            teacher=self.teacher,
            student=self.student1,
            parent=self.parent1,
            title='Report 1',
            report_type='progress',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            show_to_parent=True
        )

        self.report2 = StudentReport.objects.create(
            teacher=self.teacher,
            student=self.student2,
            parent=self.parent2,
            title='Report 2',
            report_type='progress',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            show_to_parent=True
        )

        self.client = APIClient()

    def test_parent_sees_only_own_childs_reports(self):
        """Test parent sees only their own child's visible reports"""
        self.client.force_authenticate(user=self.parent1)
        response = self.client.get('/api/reports/student-reports/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.report1.id)

    def test_teacher_sees_only_own_reports(self):
        """Test teacher sees only their own created reports"""
        other_teacher = User.objects.create_user(
            username='other_teacher',
            email='other@test.com',
            password='testpass123',
            role='teacher'
        )

        self.client.force_authenticate(user=other_teacher)
        response = self.client.get('/api/reports/student-reports/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_sees_all_reports(self):
        """Test admin sees all reports"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/reports/student-reports/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ReportAcknowledgmentTests(APITestCase):
    """Test report acknowledgment tracking"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.parent = User.objects.create_user(
            username='parent',
            email='parent@test.com',
            password='testpass123',
            role='parent'
        )

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        StudentProfile.objects.create(user=self.student, parent=self.parent)

        self.report = StudentReport.objects.create(
            teacher=self.teacher,
            student=self.student,
            parent=self.parent,
            title='Test Report',
            report_type='progress',
            status='sent',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            show_to_parent=True
        )

        self.client = APIClient()

    def test_report_initially_not_acknowledged(self):
        """Test report starts as not acknowledged"""
        self.assertFalse(self.report.parent_acknowledged)
        self.assertIsNone(self.report.parent_acknowledged_at)

    def test_acknowledge_sets_timestamp(self):
        """Test acknowledging sets the timestamp"""
        self.client.force_authenticate(user=self.parent)
        response = self.client.post(f'/api/reports/student-reports/{self.report.id}/acknowledge/')

        self.report.refresh_from_db()
        self.assertTrue(self.report.parent_acknowledged)
        self.assertIsNotNone(self.report.parent_acknowledged_at)

    def test_teacher_can_see_acknowledgment_status(self):
        """Test teacher can see if parent acknowledged"""
        self.client.force_authenticate(user=self.parent)
        self.client.post(f'/api/reports/student-reports/{self.report.id}/acknowledge/')

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/reports/student-reports/{self.report.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['parent_acknowledged'])
        self.assertIsNotNone(response.data['parent_acknowledged_at'])
