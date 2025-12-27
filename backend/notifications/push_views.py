"""
API views for push notification management.

Endpoints for device token registration, push sending, and delivery tracking.
"""

import logging
from typing import List

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.contrib.auth import get_user_model

from notifications.models import Notification, PushDeliveryLog
from notifications.channels.models import DeviceToken
from notifications.push_service import get_push_service
from notifications.batch_push_service import get_batch_push_service
from notifications.serializers import (
    DeviceTokenSerializer,
    PushDeliveryLogSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing device tokens.

    Handles registration, revocation, and listing of push notification device tokens.
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return device tokens for current user."""
        return DeviceToken.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        """Add user to serializer context."""
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context

    @action(detail=False, methods=['post'])
    def register(self, request: Request) -> Response:
        """
        Register a new device token.

        POST /api/push/devices/register/
        {
            "token": "fcm_token_here",
            "device_type": "ios|android|web",
            "device_name": "My iPhone"
        }

        Returns:
            201 Created with device token details
        """
        try:
            token = request.data.get('token')
            device_type = request.data.get('device_type')
            device_name = request.data.get('device_name', '')

            if not token or not device_type:
                return Response(
                    {'error': 'token and device_type are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = get_push_service()
            device, created = service.register_device_token(
                request.user,
                token,
                device_type,
                device_name
            )

            serializer = DeviceTokenSerializer(device)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error registering device token: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def revoke(self, request: Request) -> Response:
        """
        Revoke a device token.

        POST /api/push/devices/revoke/
        {
            "token": "fcm_token_to_revoke"
        }

        Returns:
            200 OK
        """
        try:
            token = request.data.get('token')
            if not token:
                return Response(
                    {'error': 'token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = get_push_service()
            revoked = service.revoke_device_token(request.user, token)

            if revoked:
                return Response({'status': 'revoked'})
            else:
                return Response(
                    {'error': 'Token not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def list_devices(self, request: Request) -> Response:
        """
        List all registered devices for the user.

        GET /api/push/devices/list_devices/

        Returns:
            200 OK with list of devices
        """
        try:
            service = get_push_service()
            devices = service.get_user_devices(request.user)
            return Response({'devices': devices})
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request: Request) -> Response:
        """
        Get push notification statistics for the user.

        GET /api/push/devices/stats/

        Returns:
            200 OK with device statistics
        """
        try:
            service = get_push_service()
            stats = service.get_push_stats(request.user)
            return Response(stats)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PushNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for sending push notifications.

    Handles single user, batch, and broadcast push notifications.
    """

    queryset = Notification.objects.all()
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def send_to_user(self, request: Request, pk=None) -> Response:
        """
        Send notification to a specific user.

        POST /api/notifications/{id}/send_to_user/
        {
            "user_id": 123,
            "device_types": ["ios", "android"]
        }

        Returns:
            200 OK with delivery result
        """
        try:
            notification = self.get_object()
            user_id = request.data.get('user_id')
            device_types = request.data.get('device_types')

            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(id=user_id)
            service = get_push_service()
            result = service.send_to_user(notification, user, device_types)

            return Response(result)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending to user: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_to_users(self, request: Request, pk=None) -> Response:
        """
        Send notification to multiple users.

        POST /api/notifications/{id}/send_to_users/
        {
            "user_ids": [1, 2, 3],
            "device_types": ["ios", "android"]
        }

        Returns:
            200 OK with batch delivery result
        """
        try:
            notification = self.get_object()
            user_ids = request.data.get('user_ids', [])
            device_types = request.data.get('device_types')

            if not user_ids:
                return Response(
                    {'error': 'user_ids is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            users = User.objects.filter(id__in=user_ids)
            service = get_push_service()
            result = service.send_to_users(notification, list(users), device_types)

            return Response(result)

        except Exception as e:
            logger.error(f"Error sending to users: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_batch(self, request: Request, pk=None) -> Response:
        """
        Send notification in batch with tracking.

        POST /api/notifications/{id}/send_batch/
        {
            "user_ids": [1, 2, 3],
            "device_types": ["ios"],
            "priority": "normal"
        }

        Returns:
            200 OK with batch statistics
        """
        try:
            notification = self.get_object()
            user_ids = request.data.get('user_ids', [])
            device_types = request.data.get('device_types')
            priority = request.data.get('priority', 'normal')

            if not user_ids:
                return Response(
                    {'error': 'user_ids is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            users = User.objects.filter(id__in=user_ids)
            batch_service = get_batch_push_service()
            result = batch_service.send_to_users(
                notification,
                list(users),
                device_types,
                priority
            )

            return Response(result)

        except Exception as e:
            logger.error(f"Error in batch send: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PushDeliveryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing push delivery logs.

    Allows administrators to track push notification delivery status.
    """

    queryset = PushDeliveryLog.objects.all()
    serializer_class = PushDeliveryLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Filter logs with optional parameters."""
        queryset = super().get_queryset()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by success
        success_filter = self.request.query_params.get('success')
        if success_filter:
            queryset = queryset.filter(
                success=(success_filter.lower() == 'true')
            )

        # Filter by notification
        notification_id = self.request.query_params.get('notification_id')
        if notification_id:
            queryset = queryset.filter(notification_id=notification_id)

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by device type
        device_type = self.request.query_params.get('device_type')
        if device_type:
            queryset = queryset.filter(device_type=device_type)

        return queryset.order_by('-sent_at')

    @action(detail=False, methods=['get'])
    def stats(self, request: Request) -> Response:
        """
        Get push delivery statistics.

        GET /api/push/delivery-logs/stats/

        Returns:
            200 OK with delivery statistics
        """
        try:
            batch_service = get_batch_push_service()
            stats = batch_service.get_batch_stats()
            return Response(stats)
        except Exception as e:
            logger.error(f"Error getting delivery stats: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def success_rate(self, request: Request) -> Response:
        """
        Get push notification success rate.

        GET /api/push/delivery-logs/success_rate/

        Returns:
            200 OK with success rate metrics
        """
        try:
            queryset = self.get_queryset()
            total = queryset.count()
            success = queryset.filter(success=True).count()

            if total == 0:
                return Response({
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'success_rate': 0.0
                })

            return Response({
                'total': total,
                'success': success,
                'failed': total - success,
                'success_rate': (success / total * 100)
            })

        except Exception as e:
            logger.error(f"Error getting success rate: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
