"""
ViewSet for bulk user operations (admin only).

Endpoints for managing multiple users atomically:
- POST /api/admin/users/bulk-activate/
- POST /api/admin/users/bulk-deactivate/
- POST /api/admin/users/bulk-assign-role/
- POST /api/admin/users/bulk-reset-password/
- POST /api/admin/users/bulk-suspend/
- POST /api/admin/users/bulk-unsuspend/
- POST /api/admin/users/bulk-delete/
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

from .permissions import IsAdminUser
from .bulk_serializers import (
    BulkActivateSerializer,
    BulkDeactivateSerializer,
    BulkAssignRoleSerializer,
    BulkResetPasswordSerializer,
    BulkSuspendSerializer,
    BulkUnsuspendSerializer,
    BulkDeleteSerializer,
)
from .bulk_operations import BulkUserOperationService, BulkOperationError

logger = logging.getLogger(__name__)


class BulkUserOperationsViewSet(viewsets.ViewSet):
    """
    ViewSet for admin bulk user operations.

    All endpoints require admin/staff permissions and are atomic:
    - All-or-nothing transactions
    - Audit logging for compliance
    - Prevents admin self-modification
    - Rate limited (max 1000 users per operation)
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    @action(detail=False, methods=["post"])
    def bulk_activate(self, request):
        """
        Activate multiple users.

        Request body:
        {
            "user_ids": [1, 2, 3, ...]
        }

        Returns:
        {
            "operation_id": "uuid",
            "success": true,
            "successes": [
                {
                    "user_id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe"
                }
            ],
            "failures": [],
            "summary": {
                "total_requested": 3,
                "success_count": 3,
                "failure_count": 0
            }
        }
        """
        serializer = BulkActivateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_activate(
                serializer.validated_data["user_ids"], request=request
            )
            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk activate error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_deactivate(self, request):
        """
        Deactivate multiple users.

        Request body:
        {
            "user_ids": [1, 2, 3, ...]
        }

        Returns: Same as bulk_activate
        """
        serializer = BulkDeactivateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_deactivate(
                serializer.validated_data["user_ids"], request=request
            )
            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk deactivate error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_assign_role(self, request):
        """
        Assign role to multiple users.

        Request body:
        {
            "user_ids": [1, 2, 3, ...],
            "role": "teacher"
        }

        Role options: "student", "teacher", "tutor", "parent"

        Returns: Same as bulk_activate
        """
        serializer = BulkAssignRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_assign_role(
                serializer.validated_data["user_ids"],
                serializer.validated_data["role"],
                request=request,
            )
            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk assign role error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_reset_password(self, request):
        """
        Reset passwords for multiple users.

        Generates temporary passwords and sends notification emails.
        Admin can see temporary passwords in response.

        Request body:
        {
            "user_ids": [1, 2, 3, ...],
            "send_email": true
        }

        Returns:
        {
            "operation_id": "uuid",
            "success": true,
            "successes": [
                {
                    "user_id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "temp_password": "abc123!",
                    "email_sent": true
                }
            ],
            "failures": [],
            "summary": {
                "total_requested": 3,
                "success_count": 3,
                "failure_count": 0,
                "emails_sent": 3
            }
        }
        """
        serializer = BulkResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_reset_password(
                serializer.validated_data["user_ids"], request=request
            )
            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk reset password error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_suspend(self, request):
        """
        Suspend multiple users (deactivate them).

        Request body:
        {
            "user_ids": [1, 2, 3, ...],
            "reason": "Policy violation"  # optional
        }

        Returns: Same as bulk_activate
        """
        serializer = BulkSuspendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_suspend(
                serializer.validated_data["user_ids"], request=request
            )

            # Add reason to metadata if provided
            reason = serializer.validated_data.get("reason")
            if reason and result["success"]:
                result["reason"] = reason

            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk suspend error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_unsuspend(self, request):
        """
        Unsuspend multiple users (reactivate them).

        Request body:
        {
            "user_ids": [1, 2, 3, ...]
        }

        Returns: Same as bulk_activate
        """
        serializer = BulkUnsuspendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_unsuspend(
                serializer.validated_data["user_ids"], request=request
            )
            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk unsuspend error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        Delete (archive) multiple users.

        Marks users as inactive and logs deletion for audit trail.
        Does not permanently delete to preserve data for compliance.

        Request body:
        {
            "user_ids": [1, 2, 3, ...],
            "permanent": false,
            "reason": "Account closure"  # optional
        }

        Returns: Same as bulk_activate
        """
        serializer = BulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = BulkUserOperationService(request.user)
            result = service.bulk_delete(
                serializer.validated_data["user_ids"], request=request
            )

            # Add reason to metadata if provided
            reason = serializer.validated_data.get("reason")
            if reason and result["success"]:
                result["reason"] = reason

            return Response(result, status=status.HTTP_200_OK)
        except BulkOperationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Bulk delete error: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
