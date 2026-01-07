"""
Invoice Service Layer - Business Logic
Handles invoice creation, status management, payment processing, and notifications
"""
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import date, datetime
import logging

from django.db import transaction
from django.db.models import QuerySet, Q, Prefetch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Invoice, InvoiceStatusHistory
from .exceptions import (
    InvoicePermissionDenied,
    InvoiceNotFound,
    InvalidInvoiceStatus,
    InvalidStudentEnrollment,
    DuplicateInvoiceError,
)
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment
from payments.models import Payment

User = get_user_model()
logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Сервисный слой для управления счетами

    Функциональность:
    - Создание счетов с валидацией
    - Управление статусами счета
    - Проверка прав доступа
    - Интеграция с платежами
    - Триггеринг уведомлений
    - Оптимизация запросов
    - Реалтайм обновления через WebSocket
    """

    # ==================== WebSocket Broadcast Methods ====================

    @staticmethod
    def _get_invoice_data_for_broadcast(invoice: Invoice) -> Dict[str, Any]:
        """
        Формирование данных счета для трансляции через WebSocket

        Возвращает минимальный набор данных для обновления UI
        """
        return {
            "id": invoice.id,
            "student_name": invoice.student.get_full_name(),
            "parent_name": invoice.parent.get_full_name(),
            "tutor_name": invoice.tutor.get_full_name(),
            "amount": str(invoice.amount),
            "status": invoice.status,
            "status_display": invoice.get_status_display(),
            "due_date": invoice.due_date.isoformat(),
            "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
            "viewed_at": invoice.viewed_at.isoformat() if invoice.viewed_at else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
            "is_overdue": invoice.is_overdue,
        }

    @staticmethod
    def broadcast_invoice_created(invoice: Invoice) -> None:
        """
        Трансляция события создания нового счета через WebSocket

        Отправляет уведомление в комнату тьютора (создателя счета)

        Args:
            invoice: Созданный счет

        Raises:
            Exception: Логируются но не пробрасываются (non-blocking)
        """
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning(
                    "[InvoiceService] Channel layer not configured, skipping WebSocket broadcast"
                )
                return

            # Формируем данные для трансляции
            data = InvoiceService._get_invoice_data_for_broadcast(invoice)

            # Отправляем в комнату тьютора
            tutor_room = f"tutor_{invoice.tutor.id}"

            try:
                async_to_sync(channel_layer.group_send)(
                    tutor_room,
                    {
                        "type": "invoice.created",
                        "invoice_id": invoice.id,
                        "data": data,
                        "timestamp": timezone.now().isoformat(),
                    },
                )
                logger.info(
                    f"[InvoiceService] Invoice #{invoice.id} created event broadcasted "
                    f"to room {tutor_room}"
                )
            except Exception as broadcast_error:
                logger.error(
                    f"[InvoiceService] Failed to send broadcast to {tutor_room}: {broadcast_error}",
                    exc_info=True,
                )
                return

        except Exception as e:
            logger.error(
                f"[InvoiceService] Error in broadcast_invoice_created for invoice #{invoice.id}: {e}",
                exc_info=True,
            )

    @staticmethod
    def broadcast_invoice_status_change(
        invoice: Invoice, old_status: str, new_status: str
    ) -> None:
        """
        Трансляция события изменения статуса счета через WebSocket

        Отправляет уведомления:
        - В комнату тьютора (создатель счета)
        - В комнату родителя (получатель счета - только если это ребенок родителя)

        Args:
            invoice: Счет с обновленным статусом
            old_status: Предыдущий статус
            new_status: Новый статус

        Raises:
            Exception: Логируются но не пробрасываются (non-blocking)
        """
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning(
                    "[InvoiceService] Channel layer not configured, skipping WebSocket broadcast"
                )
                return

            # Формируем данные для трансляции
            data = InvoiceService._get_invoice_data_for_broadcast(invoice)

            # Подготавливаем сообщение
            message = {
                "type": "invoice.status_update",
                "invoice_id": invoice.id,
                "old_status": old_status,
                "new_status": new_status,
                "data": data,
                "timestamp": timezone.now().isoformat(),
            }

            # Отправляем в комнату тьютора
            tutor_room = f"tutor_{invoice.tutor.id}"
            try:
                async_to_sync(channel_layer.group_send)(tutor_room, message)
                logger.info(
                    f"[InvoiceService] Status change broadcast to tutor room {tutor_room}"
                )
            except Exception as tutor_broadcast_error:
                logger.error(
                    f"[InvoiceService] Failed to send status change to tutor room {tutor_room}: {tutor_broadcast_error}",
                    exc_info=True,
                )

            # CRITICAL FIX 2 & 7: Проверяем что родитель видит только счета своих детей
            if InvoiceService._check_parent_student_relationship(
                invoice.parent, invoice.student
            ):
                parent_room = f"parent_{invoice.parent.id}"
                try:
                    async_to_sync(channel_layer.group_send)(parent_room, message)
                    logger.info(
                        f"[InvoiceService] Status change broadcast to parent room {parent_room}"
                    )
                except Exception as parent_broadcast_error:
                    logger.error(
                        f"[InvoiceService] Failed to send status change to parent room {parent_room}: {parent_broadcast_error}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"[InvoiceService] Parent {invoice.parent.id} not authorized for student {invoice.student.id}, "
                    f"skipping broadcast to parent room"
                )

            logger.info(
                f"[InvoiceService] Invoice #{invoice.id} status change "
                f"({old_status} → {new_status}) broadcasted"
            )

        except Exception as e:
            logger.error(
                f"[InvoiceService] Error in broadcast_invoice_status_change for invoice #{invoice.id}: {e}",
                exc_info=True,
            )

    @staticmethod
    def broadcast_invoice_paid(invoice: Invoice) -> None:
        """
        Трансляция события оплаты счета через WebSocket

        Отправляет уведомления:
        - В комнату тьютора (уведомление о получении оплаты)
        - В комнату родителя (подтверждение оплаты - только если это ребенок родителя)

        Args:
            invoice: Оплаченный счет

        Raises:
            Exception: Логируются но не пробрасываются (non-blocking)
        """
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning(
                    "[InvoiceService] Channel layer not configured, skipping WebSocket broadcast"
                )
                return

            # Формируем данные для трансляции
            data = InvoiceService._get_invoice_data_for_broadcast(invoice)

            # Добавляем информацию о платеже если есть
            if invoice.payment:
                data["payment"] = {
                    "id": invoice.payment.id,
                    "amount": str(invoice.payment.amount),
                    "status": invoice.payment.status,
                    "yookassa_payment_id": invoice.payment.yookassa_payment_id,
                    "paid_at": invoice.payment.paid_at.isoformat()
                    if invoice.payment.paid_at
                    else None,
                }

            # Подготавливаем сообщение
            message = {
                "type": "invoice.paid",
                "invoice_id": invoice.id,
                "data": data,
                "timestamp": timezone.now().isoformat(),
            }

            # Отправляем в комнату тьютора
            tutor_room = f"tutor_{invoice.tutor.id}"
            try:
                async_to_sync(channel_layer.group_send)(tutor_room, message)
                logger.info(
                    f"[InvoiceService] Payment broadcast to tutor room {tutor_room}"
                )
            except Exception as tutor_broadcast_error:
                logger.error(
                    f"[InvoiceService] Failed to send payment to tutor room {tutor_room}: {tutor_broadcast_error}",
                    exc_info=True,
                )

            # CRITICAL FIX 2 & 7: Проверяем что родитель видит только счета своих детей
            if InvoiceService._check_parent_student_relationship(
                invoice.parent, invoice.student
            ):
                parent_room = f"parent_{invoice.parent.id}"
                try:
                    async_to_sync(channel_layer.group_send)(parent_room, message)
                    logger.info(
                        f"[InvoiceService] Payment broadcast to parent room {parent_room}"
                    )
                except Exception as parent_broadcast_error:
                    logger.error(
                        f"[InvoiceService] Failed to send payment to parent room {parent_room}: {parent_broadcast_error}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"[InvoiceService] Parent {invoice.parent.id} not authorized for student {invoice.student.id}, "
                    f"skipping broadcast to parent room"
                )

            logger.info(
                f"[InvoiceService] Invoice #{invoice.id} payment event broadcasted"
            )

        except Exception as e:
            logger.error(
                f"[InvoiceService] Error in broadcast_invoice_paid for invoice #{invoice.id}: {e}",
                exc_info=True,
            )

    # ==================== Validation & Helper Methods ====================

    @staticmethod
    def _check_tutor_student_relationship(tutor: User, student: User) -> bool:
        """
        Проверка что студент принадлежит тьютору
        Студент должен быть в списке студентов тьютора через StudentProfile.tutor
        """
        if tutor.role != "tutor":
            return False

        if student.role != "student":
            return False

        # Проверяем что у студента есть профиль и тьютор совпадает
        if not hasattr(student, "student_profile"):
            return False

        return student.student_profile.tutor == tutor

    @staticmethod
    def _check_parent_student_relationship(parent: User, student: User) -> bool:
        """
        Проверка что студент является ребенком родителя
        """
        if parent.role != "parent":
            return False

        if student.role != "student":
            return False

        if not hasattr(student, "student_profile"):
            return False

        return student.student_profile.parent == parent

    @staticmethod
    def _check_duplicate_invoice(
        tutor: User, student: User, amount: Decimal, description: str
    ) -> Optional[Invoice]:
        """
        Проверка на существование неоплаченного счета с такими же параметрами
        Возвращает найденный счет или None
        """
        # Ищем неоплаченные/неотмененные счета с теми же параметрами
        existing = Invoice.objects.filter(
            tutor=tutor,
            student=student,
            amount=amount,
            description=description,
            status__in=[
                Invoice.Status.DRAFT,
                Invoice.Status.SENT,
                Invoice.Status.VIEWED,
                Invoice.Status.OVERDUE,
            ],
        ).first()

        return existing

    @staticmethod
    @transaction.atomic
    def create_invoice(
        tutor: User,
        student_id: int,
        amount: Decimal,
        description: str,
        due_date: date,
        enrollment_id: Optional[int] = None,
    ) -> Invoice:
        """
        Создание нового счета

        Валидация:
        - Тьютор может создавать счета только для своих студентов
        - Сумма должна быть положительной
        - due_date не должна быть в прошлом
        - Описание не должно превышать 2000 символов
        - Проверка на дубликаты неоплаченных счетов

        Args:
            tutor: Пользователь с ролью 'tutor'
            student_id: ID студента
            amount: Сумма счета
            description: Описание услуг
            due_date: Срок оплаты
            enrollment_id: Опционально - ID зачисления на предмет

        Returns:
            Созданный Invoice объект

        Raises:
            InvoicePermissionDenied: Если студент не принадлежит тьютору
            InvalidStudentEnrollment: Если enrollment некорректный
            ValidationError: Если данные невалидны
            DuplicateInvoiceError: Если существует идентичный неоплаченный счет
        """
        # Валидация роли
        if tutor.role != "tutor":
            raise InvoicePermissionDenied("Только тьюторы могут создавать счета")

        # Получаем студента
        try:
            student = User.objects.select_related("student_profile__parent").get(
                id=student_id, role="student"
            )
        except User.DoesNotExist:
            raise ValidationError(f"Студент с ID {student_id} не найден")

        # Проверка что студент принадлежит тьютору
        if not InvoiceService._check_tutor_student_relationship(tutor, student):
            raise InvoicePermissionDenied(
                f"Студент {student.get_full_name()} не является вашим студентом"
            )

        # Валидация суммы
        if amount <= 0:
            raise ValidationError("Сумма должна быть положительной")

        # Валидация due_date
        if due_date < timezone.now().date():
            raise ValidationError("Срок оплаты не может быть в прошлом")

        # Валидация описания
        if len(description) > 2000:
            raise ValidationError("Описание не должно превышать 2000 символов")

        if not description.strip():
            raise ValidationError("Описание не может быть пустым")

        # Проверка на дубликаты
        duplicate = InvoiceService._check_duplicate_invoice(
            tutor, student, amount, description
        )
        if duplicate:
            raise DuplicateInvoiceError(
                f"Существует неоплаченный счет #{duplicate.id} с такими же параметрами"
            )

        # Валидация enrollment если указан
        enrollment = None
        if enrollment_id:
            try:
                enrollment = SubjectEnrollment.objects.select_related(
                    "subject", "teacher", "student"
                ).get(id=enrollment_id)

                # Проверяем что enrollment относится к этому студенту и тьютору
                if enrollment.student != student:
                    raise InvalidStudentEnrollment(
                        "Зачисление не относится к указанному студенту"
                    )

                # Проверяем что тьютор студента совпадает
                if hasattr(student, "student_profile"):
                    if student.student_profile.tutor != tutor:
                        raise InvalidStudentEnrollment(
                            "Зачисление не относится к вашему студенту"
                        )

            except SubjectEnrollment.DoesNotExist:
                raise InvalidStudentEnrollment(
                    f"Зачисление с ID {enrollment_id} не найдено"
                )

        # Получаем родителя из student.student_profile.parent
        if (
            not hasattr(student, "student_profile")
            or not student.student_profile.parent
        ):
            raise ValidationError("У студента не указан родитель в профиле")

        parent = student.student_profile.parent

        # Создаем счет
        invoice = Invoice(
            tutor=tutor,
            student=student,
            parent=parent,  # Устанавливаем явно
            amount=amount,
            description=description,
            due_date=due_date,
            enrollment=enrollment,
            status=Invoice.Status.DRAFT,
        )

        # Запускаем валидацию модели
        invoice.full_clean()
        invoice.save()

        # Создаем запись в истории
        InvoiceStatusHistory.objects.create(
            invoice=invoice,
            old_status=Invoice.Status.DRAFT,
            new_status=Invoice.Status.DRAFT,
            changed_by=tutor,
            reason="Счет создан",
        )

        # Транслируем создание счета через WebSocket
        InvoiceService.broadcast_invoice_created(invoice)

        # Инвалидируем кеш статистики тьютора
        try:
            from .reports import InvoiceReportService

            InvoiceReportService.invalidate_cache(tutor)
        except ImportError:
            pass

        return invoice

    @staticmethod
    def get_tutor_invoices(
        tutor: User, filters: Optional[Dict[str, Any]] = None
    ) -> QuerySet[Invoice]:
        """
        Получение всех счетов тьютора с оптимизацией запросов

        Поддерживаемые фильтры:
        - status: статус счета
        - student_id: ID студента
        - date_from: начальная дата создания
        - date_to: конечная дата создания
        - overdue_only: только просроченные счета

        Args:
            tutor: Пользователь с ролью 'tutor'
            filters: Опциональные фильтры

        Returns:
            QuerySet с оптимизированными запросами (select_related/prefetch_related)

        Raises:
            InvoicePermissionDenied: Если пользователь не тьютор
        """
        if tutor.role != "tutor":
            raise InvoicePermissionDenied(
                "Только тьюторы могут просматривать свои счета"
            )

        # Базовый queryset с оптимизацией
        queryset = (
            Invoice.objects.filter(tutor=tutor)
            .select_related(
                "tutor",
                "student",
                "student__student_profile",
                "parent",
                "parent__parent_profile",
                "enrollment",
                "enrollment__subject",
                "enrollment__teacher",
                "payment",
            )
            .prefetch_related(
                Prefetch(
                    "status_history",
                    queryset=InvoiceStatusHistory.objects.select_related(
                        "changed_by"
                    ).order_by("-changed_at"),
                )
            )
        )

        if not filters:
            return queryset.order_by("-created_at")

        # Применяем фильтры
        if "status" in filters:
            queryset = queryset.filter(status=filters["status"])

        if "student_id" in filters:
            queryset = queryset.filter(student_id=filters["student_id"])

        if "date_from" in filters:
            queryset = queryset.filter(created_at__gte=filters["date_from"])

        if "date_to" in filters:
            queryset = queryset.filter(created_at__lte=filters["date_to"])

        if filters.get("overdue_only", False):
            today = timezone.now().date()
            queryset = queryset.filter(
                due_date__lt=today,
                status__in=[
                    Invoice.Status.SENT,
                    Invoice.Status.VIEWED,
                    Invoice.Status.OVERDUE,
                ],
            )

        return queryset.order_by("-created_at")

    @staticmethod
    def get_parent_invoices(
        parent: User, filters: Optional[Dict[str, Any]] = None
    ) -> QuerySet[Invoice]:
        """
        Получение всех счетов родителя с оптимизацией запросов

        Поддерживаемые фильтры:
        - status: статус счета
        - child_id: ID ребенка
        - date_from: начальная дата создания
        - date_to: конечная дата создания
        - unpaid_only: только неоплаченные счета

        Args:
            parent: Пользователь с ролью 'parent'
            filters: Опциональные фильтры

        Returns:
            QuerySet с оптимизированными запросами

        Raises:
            InvoicePermissionDenied: Если пользователь не родитель
        """
        if parent.role != "parent":
            raise InvoicePermissionDenied(
                "Только родители могут просматривать свои счета"
            )

        # Базовый queryset с оптимизацией
        queryset = (
            Invoice.objects.filter(parent=parent)
            .select_related("tutor", "student", "parent", "payment")
            .prefetch_related(
                Prefetch(
                    "status_history",
                    queryset=InvoiceStatusHistory.objects.select_related(
                        "changed_by"
                    ).order_by("-changed_at"),
                )
            )
        )

        if not filters:
            return queryset.order_by("-created_at")

        # Применяем фильтры
        if "status" in filters:
            queryset = queryset.filter(status=filters["status"])

        if "child_id" in filters:
            queryset = queryset.filter(student_id=filters["child_id"])

        if "date_from" in filters:
            queryset = queryset.filter(created_at__gte=filters["date_from"])

        if "date_to" in filters:
            queryset = queryset.filter(created_at__lte=filters["date_to"])

        if filters.get("unpaid_only", False):
            queryset = queryset.filter(
                status__in=[
                    Invoice.Status.SENT,
                    Invoice.Status.VIEWED,
                    Invoice.Status.OVERDUE,
                ]
            )

        return queryset.order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def send_invoice(invoice_id: int, tutor: User) -> Invoice:
        """
        Отправка счета родителю

        Изменяет статус с DRAFT → SENT
        Устанавливает sent_at timestamp
        Создает запись в истории
        Триггерит уведомления

        Args:
            invoice_id: ID счета
            tutor: Тьютор, отправляющий счет

        Returns:
            Обновленный Invoice объект

        Raises:
            InvoiceNotFound: Если счет не найден
            InvoicePermissionDenied: Если счет не принадлежит тьютору
            InvalidInvoiceStatus: Если статус не DRAFT
        """
        try:
            invoice = Invoice.objects.select_related(
                "tutor", "student", "parent", "enrollment"
            ).get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFound(f"Счет с ID {invoice_id} не найден")

        # Проверка прав доступа
        if invoice.tutor != tutor:
            raise InvoicePermissionDenied("Этот счет не принадлежит вам")

        # Проверка статуса
        if invoice.status != Invoice.Status.DRAFT:
            raise InvalidInvoiceStatus(
                f"Невозможно отправить счет со статусом {invoice.get_status_display()}"
            )

        # Сохраняем старый статус для истории
        old_status = invoice.status

        # Обновляем статус
        invoice.status = Invoice.Status.SENT
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=["status", "sent_at", "updated_at"])

        # Создаем запись в истории
        InvoiceStatusHistory.objects.create(
            invoice=invoice,
            old_status=old_status,
            new_status=invoice.status,
            changed_by=tutor,
            reason="Счет отправлен родителю",
        )

        # Транслируем изменение статуса через WebSocket
        InvoiceService.broadcast_invoice_status_change(
            invoice, old_status, invoice.status
        )

        # Триггерим уведомления асинхронно через Celery (email, Telegram, in-app)
        # Выполняется вне транзакции для надежности
        try:
            from invoices.tasks import send_invoice_notification

            # Отправляем задачу в очередь (не блокируем основной процесс)
            send_invoice_notification.delay(invoice.id, "sent")
        except ImportError:
            # Celery недоступен - пытаемся отправить синхронно только in-app
            logger.warning("Celery not available, sending in-app notification only")
            try:
                from notifications.notification_service import NotificationService

                ns = NotificationService()
                ns.notify_invoice_sent(invoice)
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {e}")
        except Exception as e:
            logger.error(f"Failed to queue invoice notification: {e}")

        return invoice

    @staticmethod
    @transaction.atomic
    def mark_invoice_viewed(invoice_id: int, parent: User) -> Invoice:
        """
        Отметка просмотра счета родителем

        Изменяет статус с SENT → VIEWED
        Устанавливает viewed_at timestamp
        Создает запись в истории

        Args:
            invoice_id: ID счета
            parent: Родитель, просматривающий счет

        Returns:
            Обновленный Invoice объект

        Raises:
            InvoiceNotFound: Если счет не найден
            InvoicePermissionDenied: Если счет не принадлежит родителю
            InvalidInvoiceStatus: Если статус не SENT
        """
        try:
            invoice = Invoice.objects.select_related("tutor", "student", "parent").get(
                id=invoice_id
            )
        except Invoice.DoesNotExist:
            raise InvoiceNotFound(f"Счет с ID {invoice_id} не найден")

        # Проверка прав доступа
        if invoice.parent != parent:
            raise InvoicePermissionDenied("Этот счет не принадлежит вам")

        # Проверка статуса (можем отметить просмотренным только отправленный счет)
        if invoice.status != Invoice.Status.SENT:
            # Если уже viewed или paid - просто возвращаем
            if invoice.status in [Invoice.Status.VIEWED, Invoice.Status.PAID]:
                return invoice
            raise InvalidInvoiceStatus(
                f"Невозможно отметить просмотренным счет со статусом {invoice.get_status_display()}"
            )

        # Сохраняем старый статус для истории
        old_status = invoice.status

        # Обновляем статус
        invoice.status = Invoice.Status.VIEWED
        invoice.viewed_at = timezone.now()
        invoice.save(update_fields=["status", "viewed_at", "updated_at"])

        # Создаем запись в истории
        InvoiceStatusHistory.objects.create(
            invoice=invoice,
            old_status=old_status,
            new_status=invoice.status,
            changed_by=parent,
            reason="Счет просмотрен родителем",
        )

        # Транслируем изменение статуса через WebSocket
        InvoiceService.broadcast_invoice_status_change(
            invoice, old_status, invoice.status
        )

        # Триггерим уведомление тьютору через Celery
        try:
            from invoices.tasks import send_invoice_notification

            send_invoice_notification.delay(invoice.id, "viewed")
        except ImportError:
            logger.warning("Celery not available, sending in-app notification only")
            try:
                from notifications.notification_service import NotificationService

                ns = NotificationService()
                ns.notify_invoice_viewed(invoice)
            except Exception as e:
                logger.error(f"Failed to send viewed notification: {e}")
        except Exception as e:
            logger.error(f"Failed to queue viewed notification: {e}")

        return invoice

    @staticmethod
    @transaction.atomic
    def process_payment(invoice_id: int, payment: Payment) -> Invoice:
        """
        Обработка платежа по счету

        Изменяет статус в PAID
        Устанавливает paid_at timestamp
        Связывает с Payment объектом
        Создает запись в истории
        Триггерит уведомления

        Args:
            invoice_id: ID счета
            payment: Payment объект (оплаченный)

        Returns:
            Обновленный Invoice объект

        Raises:
            InvoiceNotFound: Если счет не найден
            InvalidInvoiceStatus: Если счет уже оплачен или отменен
            ValidationError: Если платеж не успешен
        """
        try:
            invoice = Invoice.objects.select_related(
                "tutor", "student", "parent", "payment"
            ).get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFound(f"Счет с ID {invoice_id} не найден")

        # Проверка статуса счета
        if invoice.status == Invoice.Status.PAID:
            raise InvalidInvoiceStatus("Счет уже оплачен")

        if invoice.status == Invoice.Status.CANCELLED:
            raise InvalidInvoiceStatus("Невозможно оплатить отмененный счет")

        # Проверка статуса платежа
        if payment.status != Payment.Status.SUCCEEDED:
            raise ValidationError(
                f"Платеж не успешен. Статус: {payment.get_status_display()}"
            )

        # Проверка что платеж еще не связан с другим счетом
        if hasattr(payment, "invoice") and payment.invoice != invoice:
            raise ValidationError("Платеж уже связан с другим счетом")

        # Сохраняем старый статус для истории
        old_status = invoice.status

        # Обновляем счет
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = payment.paid_at or timezone.now()
        invoice.payment = payment
        invoice.save(update_fields=["status", "paid_at", "payment", "updated_at"])

        # Создаем запись в истории
        InvoiceStatusHistory.objects.create(
            invoice=invoice,
            old_status=old_status,
            new_status=invoice.status,
            changed_by=invoice.parent,  # Родитель оплатил
            reason=f"Счет оплачен через платеж {payment.yookassa_payment_id or payment.id}",
        )

        # Транслируем оплату счета через WebSocket
        InvoiceService.broadcast_invoice_paid(invoice)

        # Триггерим уведомление тьютору через Celery
        try:
            from invoices.tasks import send_invoice_notification

            send_invoice_notification.delay(invoice.id, "paid")
        except ImportError:
            logger.warning("Celery not available, sending in-app notification only")
            try:
                from notifications.notification_service import NotificationService

                ns = NotificationService()
                ns.notify_invoice_paid(invoice)
            except Exception as e:
                logger.error(f"Failed to send payment notification: {e}")
        except Exception as e:
            logger.error(f"Failed to queue payment notification: {e}")

        # Обновляем сообщение в Telegram о статусе оплаты
        try:
            from invoices.telegram_service import invoice_telegram_service

            # Обновляем существующее сообщение
            if invoice.telegram_message_id:
                success = invoice_telegram_service.update_invoice_message(invoice)
                if success:
                    logger.info(
                        f"Invoice #{invoice.id} Telegram message updated to PAID status"
                    )

                # Отправляем дополнительное подтверждение
                invoice_telegram_service.send_payment_confirmation(invoice)
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to update Telegram message after payment: {e}")

        # Инвалидируем кеш статистики тьютора
        try:
            from .reports import InvoiceReportService

            InvoiceReportService.invalidate_cache(invoice.tutor)
        except ImportError:
            pass

        return invoice

    @staticmethod
    def get_invoice_detail(invoice_id: int, user: User) -> Invoice:
        """
        Получение детальной информации о счете

        Проверяет права доступа:
        - Тьютор может видеть свои счета
        - Родитель может видеть счета для своих детей
        - Студент НЕ может видеть счета (только тьютор и родитель)

        Args:
            invoice_id: ID счета
            user: Пользователь, запрашивающий данные

        Returns:
            Invoice объект с оптимизированными запросами

        Raises:
            InvoiceNotFound: Если счет не найден
            InvoicePermissionDenied: Если нет прав доступа
        """
        try:
            invoice = (
                Invoice.objects.select_related(
                    "tutor",
                    "tutor__tutor_profile",
                    "student",
                    "student__student_profile",
                    "parent",
                    "parent__parent_profile",
                    "enrollment",
                    "enrollment__subject",
                    "enrollment__teacher",
                    "payment",
                )
                .prefetch_related(
                    Prefetch(
                        "status_history",
                        queryset=InvoiceStatusHistory.objects.select_related(
                            "changed_by"
                        ).order_by("-changed_at"),
                    )
                )
                .get(id=invoice_id)
            )
        except Invoice.DoesNotExist:
            raise InvoiceNotFound(f"Счет с ID {invoice_id} не найден")

        # Проверка прав доступа
        if user.role == "tutor":
            if invoice.tutor != user:
                raise InvoicePermissionDenied("Этот счет не принадлежит вам")
        elif user.role == "parent":
            if invoice.parent != user:
                raise InvoicePermissionDenied("Этот счет не принадлежит вам")
        elif user.role == "student":
            # Студенты НЕ могут видеть счета
            raise InvoicePermissionDenied("Студенты не могут просматривать счета")
        else:
            # Admin или другие роли - разрешаем
            pass

        return invoice

    @staticmethod
    @transaction.atomic
    def cancel_invoice(invoice_id: int, user: User, reason: str = "") -> Invoice:
        """
        Отмена счета

        Только тьютор может отменить свой счет
        Нельзя отменить оплаченный счет

        Args:
            invoice_id: ID счета
            user: Пользователь (должен быть тьютор)
            reason: Причина отмены

        Returns:
            Обновленный Invoice объект

        Raises:
            InvoiceNotFound: Если счет не найден
            InvoicePermissionDenied: Если нет прав
            InvalidInvoiceStatus: Если счет уже оплачен
        """
        try:
            invoice = Invoice.objects.select_related("tutor", "student", "parent").get(
                id=invoice_id
            )
        except Invoice.DoesNotExist:
            raise InvoiceNotFound(f"Счет с ID {invoice_id} не найден")

        # Проверка прав доступа
        if user.role != "tutor" or invoice.tutor != user:
            raise InvoicePermissionDenied("Только тьютор может отменить свой счет")

        # Проверка статуса
        if invoice.status == Invoice.Status.PAID:
            raise InvalidInvoiceStatus("Невозможно отменить оплаченный счет")

        if invoice.status == Invoice.Status.CANCELLED:
            # Уже отменен - просто возвращаем
            return invoice

        # Сохраняем старый статус для истории
        old_status = invoice.status

        # Обновляем статус
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])

        # Создаем запись в истории
        InvoiceStatusHistory.objects.create(
            invoice=invoice,
            old_status=old_status,
            new_status=invoice.status,
            changed_by=user,
            reason=reason or "Счет отменен тьютором",
        )

        # Транслируем изменение статуса через WebSocket
        InvoiceService.broadcast_invoice_status_change(
            invoice, old_status, invoice.status
        )

        # Инвалидируем кеш статистики тьютора
        try:
            from .reports import InvoiceReportService

            InvoiceReportService.invalidate_cache(invoice.tutor)
        except ImportError:
            pass

        return invoice
