"""
API ViewSet для системы рассылок (Broadcast System)

Предоставляет endpoints для создания и управления массовыми рассылками
через Telegram для различных групп пользователей.
Включает отслеживание прогресса, отмену и повторную отправку.
"""
import logging
from typing import List

from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminUser
from accounts.models import User
from materials.models import Subject, TeacherSubject, SubjectEnrollment
from .models import Broadcast, BroadcastRecipient
from .serializers import (
    BroadcastListSerializer,
    BroadcastDetailSerializer,
    CreateBroadcastSerializer,
    BroadcastRecipientSerializer,
)
from .services.broadcast import BroadcastService

logger = logging.getLogger(__name__)


class BroadcastViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления рассылками (Broadcast System).

    Endpoints:
    - GET /api/admin/broadcasts/ - список рассылок с фильтрами и пагинацией
    - POST /api/admin/broadcasts/ - создать новую рассылку
    - GET /api/admin/broadcasts/{id}/ - детальная информация о рассылке
    - POST /api/admin/broadcasts/{id}/resend/ - повторная отправка failed recipients
    - GET /api/admin/broadcasts/{id}/recipients/ - список получателей с пагинацией

    Фильтры:
    - status: draft|sending|sent|failed|cancelled
    - date_from: YYYY-MM-DD (фильтр по created_at >= date_from)
    - date_to: YYYY-MM-DD (фильтр по created_at <= date_to)
    - search: поиск по тексту сообщения

    Пагинация:
    - page: номер страницы (по умолчанию 1)
    - page_size: размер страницы (по умолчанию 20)
    """

    permission_classes = [IsAdminUser]
    queryset = Broadcast.objects.all()

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от action"""
        if self.action == "list":
            return BroadcastListSerializer
        elif self.action == "create":
            return CreateBroadcastSerializer
        elif self.action == "recipients":
            return BroadcastRecipientSerializer
        return BroadcastDetailSerializer

    def get_queryset(self):
        """Получение queryset с фильтрацией и оптимизацией запросов"""
        queryset = Broadcast.objects.select_related("created_by").order_by("-created_at")

        # Фильтр по статусу
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Фильтр по дате (date_from)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        # Фильтр по дате (date_to)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Поиск по тексту сообщения
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(message__icontains=search)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Список рассылок с пагинацией.

        GET /api/admin/broadcasts/?status=sent&page=1&page_size=20
        """
        queryset = self.get_queryset()

        # Пагинация
        page_size = int(request.query_params.get("page_size", 20))
        page_number = int(request.query_params.get("page", 1))

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        serializer = self.get_serializer(page_obj.object_list, many=True)

        logger.info(
            f"[list_broadcasts] User {request.user.email} listed {len(page_obj.object_list)} "
            f"broadcasts (total: {paginator.count}, page: {page_number})"
        )

        return Response(
            {
                "count": paginator.count,
                "next": page_obj.has_next() and page_obj.next_page_number() or None,
                "previous": page_obj.has_previous() and page_obj.previous_page_number() or None,
                "results": serializer.data,
                "page": page_number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
            }
        )

    def create(self, request, *args, **kwargs):
        """
        Создание новой рассылки.

        POST /api/admin/broadcasts/
        {
            "target_group": "all_students",
            "target_filter": {"subject_id": 5},  // optional
            "message": "Важное уведомление для всех студентов!",
            "send_immediately": true  // optional, default: false
        }
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"[create_broadcast] Validation error: {serializer.errors}")
            return Response(
                {"success": False, "error": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_group = serializer.validated_data["target_group"]
        target_filter = serializer.validated_data.get("target_filter", {})
        message = serializer.validated_data["message"]
        send_immediately = request.data.get("send_immediately", False)

        # Получить получателей
        recipients = _get_recipients_by_group(target_group, target_filter)

        if not recipients:
            logger.warning(
                f"[create_broadcast] No recipients found for target_group={target_group}"
            )
            return Response(
                {
                    "success": False,
                    "error": "Не найдено получателей для указанной группы",
                    "code": "NO_RECIPIENTS",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Определить статус
        broadcast_status = Broadcast.Status.SENDING if send_immediately else Broadcast.Status.DRAFT

        # Создать Broadcast
        broadcast = Broadcast.objects.create(
            created_by=request.user,
            target_group=target_group,
            target_filter=target_filter,
            message=message,
            recipient_count=len(recipients),
            status=broadcast_status,
        )

        # Создать BroadcastRecipient записи
        _create_broadcast_recipients(broadcast, recipients)

        logger.info(
            f"[create_broadcast] Broadcast {broadcast.id} created by {request.user.email} "
            f"with {len(recipients)} recipients"
        )

        # Отправить немедленно если нужно
        if send_immediately:
            try:
                _send_telegram_broadcasts(broadcast)
                broadcast.status = Broadcast.Status.SENT
                broadcast.sent_at = timezone.now()
                broadcast.completed_at = timezone.now()
                broadcast.save()
                logger.info(f"[create_broadcast] Broadcast {broadcast.id} sent successfully")
            except Exception as e:
                broadcast.status = Broadcast.Status.FAILED
                broadcast.save()
                logger.error(
                    f"[create_broadcast] Failed to send broadcast {broadcast.id}: {str(e)}"
                )

        # Обновить данные из БД
        broadcast.refresh_from_db()

        output_serializer = BroadcastDetailSerializer(broadcast)
        return Response(
            {
                "success": True,
                "data": output_serializer.data,
                "message": "Рассылка успешно создана"
                + (" и отправлена" if send_immediately else ""),
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        """
        Получить детальную информацию о рассылке.

        GET /api/admin/broadcasts/{id}/
        """
        try:
            broadcast = (
                Broadcast.objects.select_related("created_by")
                .prefetch_related("recipients__recipient")
                .get(id=pk)
            )
        except Broadcast.DoesNotExist:
            logger.warning(f"[get_broadcast] Broadcast {pk} not found")
            return Response(
                {"success": False, "error": "Рассылка не найдена", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(broadcast)
        logger.info(f"[get_broadcast] User {request.user.email} viewed broadcast {pk}")
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request, pk=None):
        """
        Получить информацию о прогрессе рассылки.

        GET /api/admin/broadcasts/{id}/progress/

        Returns: {
            'status': 'pending|processing|completed|failed|cancelled',
            'total_recipients': 500,
            'sent_count': 450,
            'failed_count': 50,
            'pending_count': 0,
            'progress_pct': 90,
            'error_summary': '50 failed: network error'
        }
        """
        try:
            progress_data = BroadcastService.get_progress(pk)
            logger.info(f"[progress] User {request.user.email} viewed progress for broadcast {pk}")
            return Response({"success": True, "data": progress_data})
        except ValueError as e:
            logger.warning(f"[progress] {str(e)}")
            return Response(
                {"success": False, "error": str(e), "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"[progress] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": "Ошибка при получении прогресса", "code": "ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Отменить рассылку и остановить дальнейшую отправку.

        POST /api/admin/broadcasts/{id}/cancel/

        Returns:
        {
            'success': True,
            'message': 'Рассылка успешно отменена',
            'broadcast_id': 1,
            'cancelled_at': '2024-01-01T00:00:00Z'
        }
        """
        try:
            result = BroadcastService.cancel_broadcast(pk)
            logger.info(f"[cancel] User {request.user.email} cancelled broadcast {pk}")
            return Response({"success": True, "data": result})
        except ValueError as e:
            logger.warning(f"[cancel] {str(e)}")
            return Response(
                {"success": False, "error": str(e), "code": "INVALID_REQUEST"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"[cancel] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": "Ошибка при отмене рассылки", "code": "ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        """
        Повторить отправку для неудачных получателей.

        POST /api/admin/broadcasts/{id}/retry/

        Retries failed recipient sends (max 3 times).

        Returns:
        {
            'success': True,
            'message': 'Повторная отправка запущена для X получателей',
            'retried_count': 50,
            'broadcast_id': 1,
            'task_id': 'celery-task-id'
        }
        """
        try:
            result = BroadcastService.retry_failed(pk)
            logger.info(f"[retry] User {request.user.email} retried broadcast {pk}")
            return Response({"success": True, "data": result})
        except ValueError as e:
            logger.warning(f"[retry] {str(e)}")
            return Response(
                {"success": False, "error": str(e), "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"[retry] Error: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "error": "Ошибка при повторной отправке", "code": "ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        """
        Отправить рассылку всем получателям.

        POST /api/admin/broadcasts/{id}/send/

        Returns:
        {
            "status": "sent",
            "broadcast_id": 1,
            "recipients_count": 10,
            "sent_at": "2024-01-01T00:00:00Z"
        }
        """
        try:
            broadcast = Broadcast.objects.select_for_update().get(id=pk)
        except Broadcast.DoesNotExist:
            logger.warning(f"[send_broadcast] Broadcast {pk} not found")
            return Response(
                {"success": False, "error": "Рассылка не найдена", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if broadcast.status != Broadcast.Status.DRAFT:
            logger.warning(
                f"[send_broadcast] Broadcast {pk} already {broadcast.status}, cannot send"
            )
            return Response(
                {
                    "success": False,
                    "error": f"Рассылка уже {broadcast.get_status_display()}, отправка невозможна",
                    "code": "INVALID_STATUS",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            broadcast.status = Broadcast.Status.SENDING
            broadcast.save()

            from .telegram_broadcast_service import TelegramBroadcastService

            service = TelegramBroadcastService()
            result = service.send_broadcast(broadcast, broadcast.message)

            broadcast.refresh_from_db()
            broadcast.completed_at = timezone.now()
            broadcast.save()

            logger.info(
                f"[send_broadcast] Broadcast {pk} sent: sent={result.get('sent')}, failed={result.get('failed')}"
            )

            return Response(
                {
                    "status": "sent",
                    "broadcast_id": broadcast.id,
                    "recipients_count": broadcast.recipient_count,
                    "sent_at": broadcast.sent_at,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            broadcast.status = Broadcast.Status.FAILED
            broadcast.save()
            logger.error(f"[send_broadcast] Failed to send broadcast {pk}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": f"Ошибка при отправке: {str(e)}",
                    "code": "TELEGRAM_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="resend")
    def resend(self, request, pk=None):
        """
        Повторная отправка неудачных сообщений.

        POST /api/admin/broadcasts/{id}/resend/

        Находит всех получателей с telegram_sent=False и повторно отправляет им сообщения.
        """
        try:
            broadcast = Broadcast.objects.get(id=pk)
        except Broadcast.DoesNotExist:
            logger.warning(f"[resend_broadcast] Broadcast {pk} not found")
            return Response(
                {"success": False, "error": "Рассылка не найдена", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Получить неудачных получателей
        failed_recipients = BroadcastRecipient.objects.filter(
            broadcast=broadcast, telegram_sent=False
        ).select_related("recipient")

        if not failed_recipients.exists():
            logger.info(f"[resend_broadcast] No failed recipients for broadcast {pk}")
            return Response(
                {
                    "success": True,
                    "data": {
                        "resent_count": 0,
                        "error_count": 0,
                        "message": "Нет неудачных отправок для повторной попытки",
                    },
                }
            )

        # Обновить статус на sending
        broadcast.status = Broadcast.Status.SENDING
        broadcast.save()

        # Отправить через Telegram
        try:
            from .telegram_broadcast_service import TelegramBroadcastService

            service = TelegramBroadcastService()
            result = service.send_broadcast(broadcast, broadcast.message)

            resent_count = result["sent"]
            error_count = result["failed"]

            logger.info(
                f"[resend_broadcast] Broadcast {pk} resent: sent={resent_count}, failed={error_count}"
            )

            return Response(
                {
                    "success": True,
                    "data": {
                        "resent_count": resent_count,
                        "error_count": error_count,
                        "message": f"Повторно отправлено {resent_count} сообщений",
                    },
                }
            )

        except Exception as e:
            broadcast.status = Broadcast.Status.FAILED
            broadcast.save()
            logger.error(f"[resend_broadcast] Failed to resend broadcast {pk}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": f"Ошибка при повторной отправке: {str(e)}",
                    "code": "TELEGRAM_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="recipients")
    def recipients(self, request, pk=None):
        """
        Список получателей рассылки с фильтрацией и пагинацией.

        GET /api/admin/broadcasts/{id}/recipients/?status=sent&page=1

        Query params:
        - status: sent|failed|pending
        - page: номер страницы
        - page_size: размер страницы (default: 20)
        """
        try:
            broadcast = Broadcast.objects.get(id=pk)
        except Broadcast.DoesNotExist:
            logger.warning(f"[broadcast_recipients] Broadcast {pk} not found")
            return Response(
                {"success": False, "error": "Рассылка не найдена", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Получить queryset получателей
        recipients_qs = BroadcastRecipient.objects.filter(broadcast=broadcast).select_related(
            "recipient"
        )

        # Фильтр по статусу
        status_filter = request.query_params.get("status")
        if status_filter == "sent":
            recipients_qs = recipients_qs.filter(telegram_sent=True)
        elif status_filter == "failed":
            recipients_qs = recipients_qs.filter(telegram_sent=False, telegram_error__isnull=False)
        elif status_filter == "pending":
            recipients_qs = recipients_qs.filter(telegram_sent=False, telegram_error__isnull=True)

        # Пагинация
        page_size = int(request.query_params.get("page_size", 20))
        page_number = int(request.query_params.get("page", 1))

        paginator = Paginator(recipients_qs, page_size)
        page_obj = paginator.get_page(page_number)

        serializer = BroadcastRecipientSerializer(page_obj.object_list, many=True)

        logger.info(
            f"[broadcast_recipients] User {request.user.email} viewed recipients for broadcast {pk} "
            f"(page {page_number}, total: {paginator.count})"
        )

        return Response(
            {
                "count": paginator.count,
                "next": page_obj.has_next() and page_obj.next_page_number() or None,
                "previous": page_obj.has_previous() and page_obj.previous_page_number() or None,
                "results": serializer.data,
                "page": page_number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
            }
        )


# ============= HELPER FUNCTIONS =============


def _get_recipients_by_group(target_group: str, target_filter: dict = None) -> List[User]:
    """
    Получить список получателей по группе и фильтрам.

    Args:
        target_group: тип группы (all_students, by_subject, etc.)
        target_filter: дополнительные фильтры

    Returns:
        Список пользователей-получателей
    """
    target_filter = target_filter or {}

    if target_group == Broadcast.TargetGroup.ALL_STUDENTS:
        return list(User.objects.filter(role="student", is_active=True))

    elif target_group == Broadcast.TargetGroup.ALL_TEACHERS:
        return list(User.objects.filter(role="teacher", is_active=True))

    elif target_group == Broadcast.TargetGroup.ALL_TUTORS:
        return list(User.objects.filter(role="tutor", is_active=True))

    elif target_group == Broadcast.TargetGroup.ALL_PARENTS:
        return list(User.objects.filter(role="parent", is_active=True))

    elif target_group == Broadcast.TargetGroup.BY_SUBJECT:
        subject_id = target_filter.get("subject_id")
        if not subject_id:
            logger.warning("[_get_recipients_by_group] BY_SUBJECT requires subject_id")
            return []

        # Получить всех студентов и учителей по предмету
        enrollments = SubjectEnrollment.objects.filter(subject_id=subject_id).select_related(
            "student"
        )

        teacher_subjects = TeacherSubject.objects.filter(subject_id=subject_id).select_related(
            "teacher"
        )

        recipients = []
        for enrollment in enrollments:
            recipients.append(enrollment.student)
        for ts in teacher_subjects:
            recipients.append(ts.teacher)

        return list(set(recipients))  # Убираем дубликаты

    elif target_group == Broadcast.TargetGroup.BY_TUTOR:
        tutor_id = target_filter.get("tutor_id")
        if not tutor_id:
            logger.warning("[_get_recipients_by_group] BY_TUTOR requires tutor_id")
            return []

        # Получить всех студентов этого тьютора
        from accounts.models import StudentProfile

        student_profiles = StudentProfile.objects.filter(tutor_id=tutor_id).select_related("user")
        return [profile.user for profile in student_profiles]

    elif target_group == Broadcast.TargetGroup.BY_TEACHER:
        teacher_id = target_filter.get("teacher_id")
        if not teacher_id:
            logger.warning("[_get_recipients_by_group] BY_TEACHER requires teacher_id")
            return []

        # Получить всех студентов этого учителя через SubjectEnrollment
        enrollments = SubjectEnrollment.objects.filter(teacher_id=teacher_id).select_related(
            "student"
        )

        return [enrollment.student for enrollment in enrollments]

    elif target_group == Broadcast.TargetGroup.CUSTOM:
        user_ids = target_filter.get("user_ids", [])
        if not user_ids:
            logger.warning("[_get_recipients_by_group] CUSTOM requires user_ids")
            return []

        return list(User.objects.filter(id__in=user_ids, is_active=True))

    logger.warning(f"[_get_recipients_by_group] Unknown target_group: {target_group}")
    return []


def _create_broadcast_recipients(broadcast: Broadcast, users: List[User]):
    """
    Создать BroadcastRecipient записи для списка пользователей.

    Args:
        broadcast: объект рассылки
        users: список пользователей-получателей
    """
    broadcast_recipients = [
        BroadcastRecipient(broadcast=broadcast, recipient=user) for user in users
    ]
    BroadcastRecipient.objects.bulk_create(broadcast_recipients)
    logger.info(
        f"[_create_broadcast_recipients] Created {len(broadcast_recipients)} recipient records"
    )


def _send_telegram_broadcasts(broadcast: Broadcast):
    """
    Отправить рассылку через Telegram всем получателям.

    Args:
        broadcast: объект рассылки

    Raises:
        Exception: если отправка не удалась
    """
    from .telegram_broadcast_service import TelegramBroadcastService

    service = TelegramBroadcastService()
    result = service.send_broadcast(broadcast, broadcast.message)

    logger.info(
        f"[_send_telegram_broadcasts] Broadcast {broadcast.id}: sent={result['sent']}, "
        f"failed={result['failed']}"
    )

    if result["failed"] > 0 and result["sent"] == 0:
        raise Exception(f"Все отправки не удались: {result['failed']} ошибок")
