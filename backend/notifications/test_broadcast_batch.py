"""
Tests for BroadcastBatchProcessor and batch operations

Тесты для оптимизированной пакетной обработки рассылок
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.models import Broadcast, BroadcastRecipient
from notifications.broadcast_batch import BroadcastBatchProcessor
from notifications.services.broadcast import BroadcastService

User = get_user_model()


class BroadcastBatchProcessorTestCase(TestCase):
    """
    Тесты для BroadcastBatchProcessor
    """

    def setUp(self):
        """Подготовка тестовых данных"""
        # Создать admin пользователя
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            first_name='Admin',
            last_name='User'
        )

        # Создать студентов
        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='testpass123',
                role='student',
                first_name=f'Student{i}',
                last_name='User'
            )
            for i in range(5)
        ]

        # Создать учителей
        self.teachers = [
            User.objects.create_user(
                email=f'teacher{i}@test.com',
                password='testpass123',
                role='teacher',
                first_name=f'Teacher{i}',
                last_name='User'
            )
            for i in range(3)
        ]

        # Создать рассылку
        self.broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test broadcast message',
            recipient_count=len(self.students),
            status=Broadcast.Status.DRAFT
        )

    def test_create_broadcast_recipients_batch_success(self):
        """Тест успешного создания BroadcastRecipient в батчах"""
        student_ids = [s.id for s in self.students]

        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            self.broadcast.id,
            student_ids,
            batch_size=2
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], len(self.students))
        self.assertEqual(result['total_count'], len(self.students))
        self.assertEqual(result['batches_processed'], 3)

        # Проверить, что BroadcastRecipient созданы
        recipients = BroadcastRecipient.objects.filter(broadcast=self.broadcast)
        self.assertEqual(recipients.count(), len(self.students))

    def test_create_broadcast_recipients_batch_with_large_batch_size(self):
        """Тест с большим размером батча"""
        student_ids = [s.id for s in self.students]

        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            self.broadcast.id,
            student_ids,
            batch_size=10
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], len(self.students))
        self.assertEqual(result['batches_processed'], 1)

    def test_create_broadcast_recipients_batch_broadcast_not_found(self):
        """Тест ошибки при несуществующей рассылке"""
        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            99999,
            [1, 2, 3]
        )

        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])

    def test_create_broadcast_recipients_batch_empty_list(self):
        """Тест с пустым списком получателей"""
        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            self.broadcast.id,
            []
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 0)
        self.assertEqual(result['total_count'], 0)

    def test_send_to_group_batch_all_students(self):
        """Тест отправки всем студентам"""
        result = BroadcastBatchProcessor.send_to_group_batch(
            self.broadcast.id,
            Broadcast.TargetGroup.ALL_STUDENTS,
            batch_size=2
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['total_count'], len(self.students))
        self.assertGreater(result['sent_count'], 0)

    def test_send_to_group_batch_all_teachers(self):
        """Тест отправки всем учителям"""
        teacher_broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.ALL_TEACHERS,
            message='Teacher broadcast',
            recipient_count=len(self.teachers),
            status=Broadcast.Status.DRAFT
        )

        result = BroadcastBatchProcessor.send_to_group_batch(
            teacher_broadcast.id,
            Broadcast.TargetGroup.ALL_TEACHERS
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['total_count'], len(self.teachers))

    def test_send_to_role_batch(self):
        """Тест отправки по роли"""
        result = BroadcastBatchProcessor.send_to_role_batch(
            self.broadcast.id,
            'student',
            batch_size=2
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['total_count'], len(self.students))

    def test_send_to_custom_list_batch(self):
        """Тест отправки кастомному списку"""
        custom_ids = [self.students[0].id, self.students[1].id]

        result = BroadcastBatchProcessor.send_to_custom_list_batch(
            self.broadcast.id,
            custom_ids
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['total_count'], 2)
        self.assertEqual(result['sent_count'], 2)

    def test_retry_failed_batch(self):
        """Тест повтора неудачных отправок"""
        # Создать BroadcastRecipient с ошибкой
        for student in self.students:
            BroadcastRecipient.objects.create(
                broadcast=self.broadcast,
                recipient=student,
                telegram_sent=False,
                telegram_error='Network error'
            )

        result = BroadcastBatchProcessor.retry_failed_batch(
            self.broadcast.id,
            batch_size=2
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['retried_count'], len(self.students))

        # Проверить, что ошибки очищены
        failed = BroadcastRecipient.objects.filter(
            broadcast=self.broadcast,
            telegram_error__isnull=False
        )
        self.assertEqual(failed.count(), 0)

    def test_retry_failed_batch_no_failed(self):
        """Тест повтора когда нет неудачных отправок"""
        # Создать успешные BroadcastRecipient
        for student in self.students:
            BroadcastRecipient.objects.create(
                broadcast=self.broadcast,
                recipient=student,
                telegram_sent=True
            )

        result = BroadcastBatchProcessor.retry_failed_batch(
            self.broadcast.id
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['retried_count'], 0)

    def test_get_batch_status(self):
        """Тест получения статуса батча"""
        # Создать BroadcastRecipient
        for i, student in enumerate(self.students):
            sent = i < 3  # 3 успешно, 2 неудачно
            BroadcastRecipient.objects.create(
                broadcast=self.broadcast,
                recipient=student,
                telegram_sent=sent,
                telegram_error=None if sent else 'Error'
            )

        status = BroadcastBatchProcessor.get_batch_status(self.broadcast.id)

        self.assertEqual(status['broadcast_id'], self.broadcast.id)
        self.assertEqual(status['total_recipients'], len(self.students))
        self.assertEqual(status['sent_count'], 3)
        self.assertEqual(status['failed_count'], 2)
        self.assertEqual(status['pending_count'], 0)
        self.assertEqual(status['progress_pct'], 100)

    def test_get_batch_status_not_found(self):
        """Тест получения статуса несуществующей рассылки"""
        with self.assertRaises(ValueError):
            BroadcastBatchProcessor.get_batch_status(99999)

    def test_batch_processor_batch_size_boundary(self):
        """Тест граничных условий размера батча"""
        # Создать ровно batch_size студентов
        broadcast = Broadcast.objects.create(
            created_by=self.admin_user,
            target_group=Broadcast.TargetGroup.CUSTOM,
            message='Boundary test',
            recipient_count=3,
            status=Broadcast.Status.DRAFT
        )

        student_ids = [s.id for s in self.students[:3]]

        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            broadcast.id,
            student_ids,
            batch_size=3
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 3)
        self.assertEqual(result['batches_processed'], 1)

    def test_batch_processor_with_inactive_users(self):
        """Тест что неактивные пользователи не включаются в рассылку"""
        # Деактивировать одного студента
        inactive_student = self.students[0]
        inactive_student.is_active = False
        inactive_student.save()

        result = BroadcastBatchProcessor.send_to_group_batch(
            self.broadcast.id,
            Broadcast.TargetGroup.ALL_STUDENTS
        )

        self.assertTrue(result['success'])
        # Должно быть на одного меньше
        self.assertEqual(result['total_count'], len(self.students) - 1)


class BroadcastServiceBatchTestCase(TestCase):
    """
    Тесты интеграции BroadcastService с batch операциями
    """

    def setUp(self):
        """Подготовка"""
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='pass123',
            role='admin'
        )

        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='pass123',
                role='student'
            )
            for i in range(3)
        ]

        self.broadcast = Broadcast.objects.create(
            created_by=self.admin,
            target_group=Broadcast.TargetGroup.ALL_STUDENTS,
            message='Test',
            recipient_count=3,
            status=Broadcast.Status.DRAFT
        )

    def test_service_send_to_group_batch(self):
        """Тест send_to_group_batch через сервис"""
        result = BroadcastService.send_to_group_batch(
            self.broadcast.id,
            Broadcast.TargetGroup.ALL_STUDENTS
        )

        self.assertTrue(result['success'])
        self.assertGreater(result['sent_count'], 0)

    def test_service_send_to_role_batch(self):
        """Тест send_to_role_batch через сервис"""
        result = BroadcastService.send_to_role_batch(
            self.broadcast.id,
            'student'
        )

        self.assertTrue(result['success'])

    def test_service_create_batch_recipients(self):
        """Тест create_batch_recipients через сервис"""
        student_ids = [s.id for s in self.students]
        result = BroadcastService.create_batch_recipients(
            self.broadcast.id,
            student_ids
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 3)

    def test_service_get_batch_status(self):
        """Тест get_batch_status через сервис"""
        status = BroadcastService.get_batch_status(self.broadcast.id)

        self.assertEqual(status['broadcast_id'], self.broadcast.id)
        self.assertIn('total_recipients', status)
        self.assertIn('progress_pct', status)

    def test_service_batch_error_handling(self):
        """Тест обработки ошибок в сервисе"""
        result = BroadcastService.send_to_group_batch(
            99999,
            'all_students'
        )

        self.assertFalse(result['success'])
        self.assertIn('error', result)


@pytest.mark.django_db
class BroadcastBatchProcessorPytestTestCase:
    """
    Pytest-style тесты для BroadcastBatchProcessor
    """

    def test_batch_processor_handles_duplicates(self, db):
        """Тест что дубликаты обрабатываются правильно"""
        admin = User.objects.create_user(
            email='admin@test.com',
            password='pass',
            role='admin'
        )
        student = User.objects.create_user(
            email='student@test.com',
            password='pass',
            role='student'
        )

        broadcast = Broadcast.objects.create(
            created_by=admin,
            target_group='custom',
            message='Test',
            recipient_count=1,
            status='draft'
        )

        # Попытаться создать дубликат
        student_ids = [student.id, student.id]

        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            broadcast.id,
            student_ids
        )

        self.assertTrue(result['success'])
        # Должен быть только один, благодаря ignore_conflicts
        recipients = BroadcastRecipient.objects.filter(broadcast=broadcast)
        assert recipients.count() == 1

    def test_batch_performance_with_large_dataset(self, db):
        """Тест производительности с большим набором данных"""
        admin = User.objects.create_user(
            email='admin@test.com',
            password='pass',
            role='admin'
        )

        # Создать много студентов
        students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='pass',
                role='student'
            )
            for i in range(100)
        ]

        broadcast = Broadcast.objects.create(
            created_by=admin,
            target_group='custom',
            message='Large broadcast',
            recipient_count=100,
            status='draft'
        )

        student_ids = [s.id for s in students]

        # Обработать в больших батчах
        result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
            broadcast.id,
            student_ids,
            batch_size=50
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 100)
        assert BroadcastRecipient.objects.filter(broadcast=broadcast).count() == 100
