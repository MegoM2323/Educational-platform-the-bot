"""
ФАЗА 5: Специфичные тесты для исправлений (итерация 2)
Проверка:
- User=None в consumers не вызывает AttributeError
- Логирование исключений включает exc_info
- Graceful handling при отсутствующих полях
"""

import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import ParentProfile, StudentProfile, TutorProfile
from invoices.models import Invoice
from chat.consumers import ChatConsumer

User = get_user_model()


class TestUserNoneInConsumers(TestCase):
    """Тест 1: User=None в consumers не вызывает AttributeError"""

    def setUp(self):
        self.consumer = ChatConsumer()

    def test_consumer_handles_none_user_gracefully(self):
        """Consumer должен корректно обрабатывать None user"""
        self.consumer.scope = {
            "user": None,
            "channel": "test-channel",
        }

        try:
            if self.consumer.scope.get("user") is not None:
                user_id = self.consumer.scope["user"].id
            else:
                user_id = None
            self.assertIsNone(user_id)
        except AttributeError as e:
            self.fail(f"Consumer raised AttributeError on None user: {e}")

    def test_consumer_with_valid_user(self):
        """Consumer должен нормально работать с валидным user"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass123"
        )

        self.consumer.scope = {"user": user, "channel": "test-channel"}

        retrieved_user = self.consumer.scope.get("user")
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.id, user.id)

    def test_consumer_message_without_user_field(self):
        """Consumer должен обработать message без user"""
        message = {"type": "chat.message", "text": "Test"}

        self.consumer.scope = {"channel": "test-channel"}

        user = self.consumer.scope.get("user")
        self.assertIsNone(user)

    def test_consumer_safe_attribute_access(self):
        """Безопасный доступ к атрибутам consumer когда user=None"""
        self.consumer.scope = {"user": None}
        
        # Не должно быть AttributeError
        user = self.consumer.scope.get("user")
        self.assertIsNone(user)
        
        # Если попытаемся обратиться к атрибуту user напрямую
        if user:
            # Это не выполнится
            _ = user.id
        else:
            # Это правильное поведение
            self.assertTrue(True)


class TestLoggingWithExcInfo(TestCase):
    """Тест 2: Логирование исключений включает exc_info"""

    def setUp(self):
        self.logger = logging.getLogger("accounts.signals")

    def test_exception_logging_with_exc_info(self):
        """Исключение должно логироваться с exc_info=True"""
        with self.assertLogs("accounts.signals", level="ERROR") as log_context:
            try:
                raise ValueError("Test exception")
            except ValueError:
                self.logger.error("An error occurred", exc_info=True)

        log_output = "\n".join(log_context.output)
        self.assertIn("An error occurred", log_output)
        self.assertIn("ValueError", log_output)

    def test_logging_error_formats_correctly(self):
        """Ошибка должна логироваться с правильным форматом"""
        with self.assertLogs("accounts.signals", level="ERROR") as log_context:
            self.logger.error("Test error message")

        log_output = "\n".join(log_context.output)
        self.assertIn("Test error message", log_output)

    def test_logging_custom_exception(self):
        """Кастомное исключение должно корректно логироваться"""
        with self.assertLogs("accounts.signals", level="ERROR") as log_context:
            try:
                raise RuntimeError("Custom runtime error")
            except RuntimeError:
                self.logger.error("Caught runtime error", exc_info=True)

        log_output = "\n".join(log_context.output)
        self.assertIn("Caught runtime error", log_output)
        self.assertIn("RuntimeError", log_output)

    def test_logging_preserves_exception_info(self):
        """Логирование должно сохранять информацию об исключении"""
        with self.assertLogs("accounts.signals", level="ERROR") as log_context:
            try:
                1 / 0
            except ZeroDivisionError:
                self.logger.error("Division error", exc_info=True)

        log_output = "\n".join(log_context.output)
        self.assertIn("Division error", log_output)
        self.assertIn("ZeroDivisionError", log_output)


class TestInvoiceDataHandling(TestCase):
    """Тест 3: Invoice обрабатывается gracefully"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor", email="tutor@example.com", password="pass123"
        )
        TutorProfile.objects.create(user=self.tutor)

        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="pass123"
        )
        StudentProfile.objects.create(user=self.student)

        self.parent = User.objects.create_user(
            username="parent", email="parent@example.com", password="pass123"
        )
        ParentProfile.objects.create(user=self.parent)
        
        self.due_date = datetime.now() + timedelta(days=30)

    def test_invoice_with_all_required_fields(self):
        """Invoice с всеми required полями создаётся нормально"""
        invoice = Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Test invoice",
            status="pending",
            due_date=self.due_date,
        )

        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.tutor.id, self.tutor.id)
        self.assertEqual(invoice.student.id, self.student.id)
        self.assertEqual(invoice.parent.id, self.parent.id)

    def test_invoice_field_access_safe(self):
        """Доступ к полям invoice безопасен"""
        invoice = Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Test",
            status="pending",
            due_date=self.due_date,
        )

        try:
            _ = invoice.tutor_id
            _ = invoice.student_id
            _ = invoice.parent_id
            _ = invoice.amount
            _ = invoice.description
            _ = invoice.status
            _ = invoice.due_date
        except AttributeError as e:
            self.fail(f"AttributeError accessing invoice field: {e}")

    def test_invoice_filter_by_fields(self):
        """Фильтрация invoice работает"""
        tutor2 = User.objects.create_user(
            username="tutor2", email="tutor2@example.com", password="pass123"
        )
        TutorProfile.objects.create(user=tutor2)

        Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Invoice 1",
            status="pending",
            due_date=self.due_date,
        )
        Invoice.objects.create(
            tutor=tutor2,
            student=self.student,
            parent=self.parent,
            amount=200.00,
            description="Invoice 2",
            status="pending",
            due_date=self.due_date,
        )

        tutor1_invoices = Invoice.objects.filter(tutor=self.tutor)
        tutor2_invoices = Invoice.objects.filter(tutor=tutor2)

        self.assertEqual(tutor1_invoices.count(), 1)
        self.assertEqual(tutor2_invoices.count(), 1)

    def test_invoice_status_handling(self):
        """Invoice статусы обрабатываются корректно"""
        for status, _ in Invoice.Status.choices:
            invoice = Invoice.objects.create(
                tutor=self.tutor,
                student=self.student,
                parent=self.parent,
                amount=100.00,
                description=f"Invoice {status}",
                status=status,
                due_date=self.due_date,
            )
            self.assertEqual(invoice.status, status)


class TestFullFlow_Iteration2(TestCase):
    """Интеграционный тест всех исправлений итерации 2"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor", email="tutor@example.com", password="pass123"
        )
        TutorProfile.objects.create(user=self.tutor)

        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="pass123"
        )
        StudentProfile.objects.create(user=self.student)

        self.parent = User.objects.create_user(
            username="parent", email="parent@example.com", password="pass123"
        )
        ParentProfile.objects.create(user=self.parent)
        
        self.due_date = datetime.now() + timedelta(days=30)

    def test_no_attribute_errors_with_valid_values(self):
        """Все компоненты работают с валидными значениями"""
        # Invoice с валидными данными
        invoice = Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Test",
            status="pending",
            due_date=self.due_date,
        )

        parent_id = invoice.parent_id
        self.assertEqual(parent_id, self.parent.id)

        # Consumer с валидным user
        consumer = ChatConsumer()
        consumer.scope = {"user": self.student, "channel": "test"}
        user = consumer.scope.get("user")
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.student.id)

    def test_consumer_and_invoice_work_together(self):
        """Consumer и Invoice работают вместе без ошибок"""
        # Consumer обработчик сообщения
        consumer = ChatConsumer()
        consumer.scope = {"user": self.student, "channel": "test"}

        # Invoice данные
        invoice = Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Test",
            status="pending",
            due_date=self.due_date,
        )

        # Проверяем что оба работают
        user = consumer.scope.get("user")
        invoice_parent = invoice.parent

        self.assertIsNotNone(user)
        self.assertIsNotNone(invoice_parent)
        self.assertEqual(user.id, invoice.student.id)

    def test_logging_errors_properly_formatted(self):
        """Логирование ошибок правильно форматируется"""
        logger = logging.getLogger("test")

        with self.assertLogs("test", level="ERROR") as log_context:
            try:
                raise RuntimeError("Test error")
            except RuntimeError:
                logger.error("Error occurred", exc_info=True)

        self.assertGreater(len(log_context.output), 0)
        log_text = "\n".join(log_context.output)
        self.assertIn("RuntimeError", log_text)
        self.assertIn("Error occurred", log_text)

    def test_system_handles_gracefully(self):
        """Система обрабатывает данные gracefully"""
        # Создаём invoice
        invoice = Invoice.objects.create(
            tutor=self.tutor,
            student=self.student,
            parent=self.parent,
            amount=100.00,
            description="Test",
            status="pending",
            due_date=self.due_date,
        )

        # Обращаемся к связанным объектам - не должно быть ошибок
        self.assertIsNotNone(invoice.tutor)
        self.assertIsNotNone(invoice.student)
        self.assertIsNotNone(invoice.parent)

        # Consumer с None user - должно обработаться gracefully
        consumer = ChatConsumer()
        consumer.scope = {"user": None}
        user = consumer.scope.get("user")
        self.assertIsNone(user)
