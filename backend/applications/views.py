from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
import logging

from .models import Application
from .serializers import (
    ApplicationSerializer, 
    ApplicationCreateSerializer, 
    ApplicationStatusUpdateSerializer
)
from .telegram_service import telegram_service

logger = logging.getLogger(__name__)


class ApplicationCreateView(generics.CreateAPIView):
    """
    Создание новой заявки
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationCreateSerializer
    permission_classes = [AllowAny]  # Разрешаем создавать заявки без авторизации
    
    def perform_create(self, serializer):
        """
        Создает заявку и отправляет уведомление в Telegram
        """
        try:
            with transaction.atomic():
                # Создаем заявку
                application = serializer.save()
                
                # Отправляем уведомление в Telegram
                try:
                    message_id = telegram_service.send_application_notification(application)
                    if message_id:
                        application.telegram_message_id = message_id
                        application.save(update_fields=['telegram_message_id'])
                        logger.info(f"Уведомление о заявке #{application.id} отправлено в Telegram")
                    else:
                        logger.warning(f"Не удалось отправить уведомление о заявке #{application.id} в Telegram")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления в Telegram: {e}")
                    # Не прерываем создание заявки из-за ошибки Telegram
                
        except Exception as e:
            logger.error(f"Ошибка при создании заявки: {e}")
            raise


class ApplicationListView(generics.ListAPIView):
    """
    Список заявок (только для авторизованных пользователей)
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Фильтрация заявок по статусу
        """
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class ApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Детали, обновление и удаление заявки
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]


class ApplicationStatusUpdateView(generics.UpdateAPIView):
    """
    Обновление статуса заявки
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationStatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_update(self, serializer):
        """
        Обновляет статус заявки и отправляет уведомление в Telegram
        """
        old_status = self.get_object().status
        application = serializer.save()
        new_status = application.status
        
        # Отправляем уведомление об изменении статуса в Telegram
        if old_status != new_status:
            try:
                telegram_service.send_status_update(application, old_status, new_status)
                logger.info(f"Уведомление об изменении статуса заявки #{application.id} отправлено в Telegram")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления об изменении статуса: {e}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_statistics(request):
    """
    Статистика по заявкам
    """
    try:
        total_applications = Application.objects.count()
        new_applications = Application.objects.filter(status=Application.Status.NEW).count()
        processing_applications = Application.objects.filter(status=Application.Status.PROCESSING).count()
        approved_applications = Application.objects.filter(status=Application.Status.APPROVED).count()
        rejected_applications = Application.objects.filter(status=Application.Status.REJECTED).count()
        completed_applications = Application.objects.filter(status=Application.Status.COMPLETED).count()
        
        # Заявки за последние 7 дней
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        recent_applications = Application.objects.filter(created_at__gte=week_ago).count()
        
        statistics = {
            'total': total_applications,
            'new': new_applications,
            'processing': processing_applications,
            'approved': approved_applications,
            'rejected': rejected_applications,
            'completed': completed_applications,
            'recent_week': recent_applications
        }
        
        return Response(statistics)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return Response(
            {'error': 'Ошибка при получении статистики'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_telegram_connection(request):
    """
    Тестирование соединения с Telegram
    """
    try:
        is_connected = telegram_service.test_connection()
        
        if is_connected:
            return Response({
                'status': 'success',
                'message': 'Соединение с Telegram успешно'
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Не удалось подключиться к Telegram'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании Telegram: {e}")
        return Response({
            'status': 'error',
            'message': f'Ошибка при тестировании: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
