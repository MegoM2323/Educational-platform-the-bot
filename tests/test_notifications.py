import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.notification_service import NotificationService
from notifications.models import Notification


User = get_user_model()


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.tutor = User.objects.create_user(username='tutor1', role='tutor')
        self.student = User.objects.create_user(username='student1', role='student')
        self.teacher = User.objects.create_user(username='teacher1', role='teacher')
        self.parent = User.objects.create_user(username='parent1', role='parent')
        self.service = NotificationService()

    def test_notify_student_created(self):
        notif = self.service.notify_student_created(tutor=self.tutor, student=self.student)
        self.assertIsInstance(notif, Notification)
        self.assertEqual(notif.recipient, self.tutor)
        self.assertEqual(notif.type, Notification.Type.STUDENT_CREATED)

    def test_notify_subject_assigned(self):
        notif = self.service.notify_subject_assigned(student=self.student, subject_id=1, teacher=self.teacher)
        self.assertEqual(notif.recipient, self.student)
        self.assertEqual(notif.type, Notification.Type.SUBJECT_ASSIGNED)

    def test_notify_homework_submitted(self):
        notif = self.service.notify_homework_submitted(teacher=self.teacher, submission_id=10, student=self.student)
        self.assertEqual(notif.recipient, self.teacher)
        self.assertEqual(notif.type, Notification.Type.HOMEWORK_SUBMITTED)

    def test_notify_payment_processed_success(self):
        notif = self.service.notify_payment_processed(parent=self.parent, status='success', amount='100.00', enrollment_id=5)
        self.assertIn(notif.type, [Notification.Type.PAYMENT_SUCCESS, Notification.Type.PAYMENT_FAILED])


