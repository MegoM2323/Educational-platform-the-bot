"""
Сервис архивирования уведомлений
"""
from datetime import timedelta
from django.utils import timezone
from .models import Notification


class NotificationArchiveService:
    """
    Сервис для управления архивом уведомлений
    """

    @staticmethod
    def archive_old_notifications(days=30, batch_size=1000):
        """
        Архивирует старые уведомления (старше указанного количества дней)

        Args:
            days: количество дней (по умолчанию 30)
            batch_size: размер пакета для массового обновления

        Returns:
            dict: информация о архивировании {
                'archived_count': количество архивированных,
                'total_processed': всего обработано,
                'errors': список ошибок
            }
        """
        now = timezone.now()
        archive_before = now - timedelta(days=days)

        # Находим уведомления для архивирования
        notifications_to_archive = Notification.objects.filter(
            created_at__lt=archive_before,
            is_archived=False
        ).values_list('id', flat=True)

        total_to_archive = len(notifications_to_archive)

        if total_to_archive == 0:
            return {
                'archived_count': 0,
                'total_processed': 0,
                'errors': []
            }

        archived_count = 0
        errors = []

        # Обновляем в пакетах для оптимизации памяти
        for i in range(0, total_to_archive, batch_size):
            batch_ids = list(notifications_to_archive[i:i + batch_size])

            try:
                # Получаем объекты для обновления
                batch = Notification.objects.filter(id__in=batch_ids)

                # Обновляем в пакете
                updated = batch.update(
                    is_archived=True,
                    archived_at=now
                )

                archived_count += updated
            except Exception as e:
                errors.append(f"Ошибка при обновлении пакета {i}-{i + batch_size}: {str(e)}")

        return {
            'archived_count': archived_count,
            'total_processed': total_to_archive,
            'errors': errors
        }

    @staticmethod
    def get_archive_statistics(user=None):
        """
        Получает статистику архива

        Args:
            user: если указан, получает статистику для конкретного пользователя

        Returns:
            dict: статистика архива
        """
        query = Notification.objects.filter(is_archived=True)

        if user:
            query = query.filter(recipient=user)

        total_archived = query.count()

        # Статистика по типам
        archived_by_type = {}
        for type_choice in Notification.Type.choices:
            type_value = type_choice[0]
            count = query.filter(type=type_value).count()
            if count > 0:
                archived_by_type[type_value] = count

        # Статистика по приоритетам
        archived_by_priority = {}
        for priority_choice in Notification.Priority.choices:
            priority_value = priority_choice[0]
            count = query.filter(priority=priority_value).count()
            if count > 0:
                archived_by_priority[priority_value] = count

        # Дата самого старого архивированного уведомления
        oldest_archived = query.order_by('archived_at').first()
        oldest_archived_at = oldest_archived.archived_at if oldest_archived else None

        return {
            'total_archived': total_archived,
            'archived_by_type': archived_by_type,
            'archived_by_priority': archived_by_priority,
            'oldest_archived_at': oldest_archived_at,
            'storage_estimate_mb': (total_archived * 0.001)  # Примерная оценка в МБ
        }

    @staticmethod
    def restore_notification(notification_id, user=None):
        """
        Восстанавливает архивированное уведомление

        Args:
            notification_id: ID уведомления
            user: пользователь (для проверки прав)

        Returns:
            Notification: восстановленное уведомление или None

        Raises:
            Notification.DoesNotExist: если уведомление не найдено
            ValueError: если уведомление не архивировано или не принадлежит пользователю
        """
        query = Notification.objects.filter(id=notification_id, is_archived=True)

        if user:
            query = query.filter(recipient=user)

        try:
            notification = query.get()
        except Notification.DoesNotExist:
            raise ValueError("Уведомление не найдено или не архивировано")

        notification.is_archived = False
        notification.archived_at = None
        notification.save()

        return notification

    @staticmethod
    def bulk_restore_notifications(notification_ids, user=None):
        """
        Восстанавливает несколько архивированных уведомлений

        Args:
            notification_ids: список ID уведомлений
            user: пользователь (для проверки прав)

        Returns:
            dict: результаты восстановления {
                'restored_count': количество восстановленных,
                'not_found': количество не найденных,
                'errors': список ошибок
            }
        """
        query = Notification.objects.filter(
            id__in=notification_ids,
            is_archived=True
        )

        if user:
            query = query.filter(recipient=user)

        try:
            restored_count = query.update(
                is_archived=False,
                archived_at=None
            )

            return {
                'restored_count': restored_count,
                'not_found': len(notification_ids) - restored_count,
                'errors': []
            }
        except Exception as e:
            return {
                'restored_count': 0,
                'not_found': len(notification_ids),
                'errors': [str(e)]
            }

    @staticmethod
    def bulk_delete_archived(days=90, batch_size=1000):
        """
        Полностью удаляет архивированные уведомления старше указанного срока
        (используется для очистки базы данных)

        Args:
            days: минимальный возраст архивированного уведомления для удаления
            batch_size: размер пакета для удаления

        Returns:
            dict: информация об удалении {
                'deleted_count': количество удаленных,
                'errors': список ошибок
            }
        """
        now = timezone.now()
        delete_before = now - timedelta(days=days)

        # Находим уведомления для удаления
        notifications_to_delete = Notification.objects.filter(
            archived_at__lt=delete_before,
            is_archived=True
        ).values_list('id', flat=True)

        total_to_delete = len(notifications_to_delete)

        if total_to_delete == 0:
            return {
                'deleted_count': 0,
                'errors': []
            }

        deleted_count = 0
        errors = []

        # Удаляем в пакетах
        for i in range(0, total_to_delete, batch_size):
            batch_ids = list(notifications_to_delete[i:i + batch_size])

            try:
                batch = Notification.objects.filter(id__in=batch_ids)
                deleted, _ = batch.delete()
                deleted_count += deleted
            except Exception as e:
                errors.append(f"Ошибка при удалении пакета {i}-{i + batch_size}: {str(e)}")

        return {
            'deleted_count': deleted_count,
            'errors': errors
        }
