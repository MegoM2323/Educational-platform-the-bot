"""
API endpoints for bulk material assignment operations.
Provides endpoints for bulk assign, bulk unassign, and bulk operations.
"""
import logging
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.response import Response
from django.db import transaction

from .bulk_operations_service import BulkAssignmentService
from .serializers import BulkAssignmentAuditLogSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([JWTAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def bulk_assign_endpoint(request):
    """
    Bulk assign material to multiple students.

    POST /api/materials/bulk-assign/

    Request body:
    {
        "material_id": 1,
        "student_ids": [1, 2, 3],
        "skip_existing": true,
        "notify": true
    }

    Response:
    {
        "preflight_valid": true,
        "preflight": {
            "total_items": 3,
            "affected_students": [1, 2, 3],
            "affected_materials": [1]
        },
        "result": {
            "created": 2,
            "skipped": 1,
            "failed": 0,
            "failed_items": []
        }
    }
    """
    try:
        material_id = request.data.get("material_id")
        student_ids = request.data.get("student_ids", [])
        skip_existing = request.data.get("skip_existing", True)
        notify = request.data.get("notify", True)

        # Validate required fields
        if not material_id or not student_ids:
            return Response(
                {"error": "material_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize service
        service = BulkAssignmentService(request.user)

        # Pre-flight validation
        preflight_result = service.preflight_check(
            material_id=material_id, student_ids=student_ids
        )

        if not preflight_result["valid"]:
            return Response(
                {
                    "preflight_valid": False,
                    "preflight": preflight_result,
                    "error": "Preflight validation failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute bulk assignment
        try:
            with transaction.atomic():
                result = service.bulk_assign_students(
                    material_id=material_id,
                    student_ids=student_ids,
                    skip_existing=skip_existing,
                    notify=notify,
                )

            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "result": result,
                    "success": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Bulk assign failed: {str(e)}")
            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "error": str(e),
                    "success": False,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Bulk assign endpoint error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([JWTAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def bulk_unassign_endpoint(request):
    """
    Bulk remove material assignments.

    POST /api/materials/bulk-unassign/

    Request body:
    {
        "material_ids": [1, 2],
        "student_ids": [1, 2, 3]
    }

    At least one of material_ids or student_ids must be provided.

    Response:
    {
        "preflight_valid": true,
        "result": {
            "removed": 6,
            "not_found": 0,
            "failed": 0
        }
    }
    """
    try:
        material_ids = request.data.get("material_ids")
        student_ids = request.data.get("student_ids")

        # Validate at least one is provided
        if not material_ids and not student_ids:
            return Response(
                {"error": "At least one of material_ids or student_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize service
        service = BulkAssignmentService(request.user)

        # Pre-flight validation
        preflight_result = service.preflight_check(
            material_ids=material_ids, student_ids=student_ids
        )

        # Execute bulk remove (don't fail on preflight for remove operations)
        try:
            with transaction.atomic():
                result = service.bulk_remove(
                    material_ids=material_ids, student_ids=student_ids
                )

            return Response(
                {
                    "preflight_valid": preflight_result.get("valid", True),
                    "preflight": preflight_result,
                    "result": result,
                    "success": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Bulk unassign failed: {str(e)}")
            return Response(
                {"error": str(e), "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Bulk unassign endpoint error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([JWTAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def bulk_assign_class_endpoint(request):
    """
    Bulk assign materials to all students in a class.

    POST /api/materials/bulk-assign-class/

    Request body:
    {
        "material_ids": [1, 2, 3],
        "class_id": 5,
        "skip_existing": true,
        "notify": true
    }

    Response:
    {
        "preflight_valid": true,
        "preflight": {
            "total_items": 15,
            "affected_students": [1, 2, 3, 4, 5],
            "affected_materials": [1, 2, 3]
        },
        "result": {
            "created": 14,
            "skipped": 1,
            "failed": 0,
            "failed_items": []
        }
    }
    """
    try:
        material_ids = request.data.get("material_ids", [])
        class_id = request.data.get("class_id")
        skip_existing = request.data.get("skip_existing", True)
        notify = request.data.get("notify", True)

        # Validate required fields
        if not material_ids or not class_id:
            return Response(
                {"error": "material_ids and class_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize service
        service = BulkAssignmentService(request.user)

        # Pre-flight validation
        preflight_result = service.preflight_check(
            material_ids=material_ids, class_id=class_id
        )

        if not preflight_result["valid"]:
            return Response(
                {
                    "preflight_valid": False,
                    "preflight": preflight_result,
                    "error": "Preflight validation failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute bulk assignment
        try:
            with transaction.atomic():
                result = service.bulk_assign_class(
                    material_ids=material_ids,
                    class_id=class_id,
                    skip_existing=skip_existing,
                    notify=notify,
                )

            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "result": result,
                    "success": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Bulk assign class failed: {str(e)}")
            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "error": str(e),
                    "success": False,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Bulk assign class endpoint error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([JWTAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def bulk_assign_materials_endpoint(request):
    """
    Bulk assign multiple materials to a single student.

    POST /api/materials/bulk-assign-materials/

    Request body:
    {
        "material_ids": [1, 2, 3],
        "student_id": 10,
        "skip_existing": true,
        "notify": true
    }

    Response:
    {
        "preflight_valid": true,
        "preflight": {
            "total_items": 3,
            "affected_students": [10],
            "affected_materials": [1, 2, 3]
        },
        "result": {
            "created": 3,
            "skipped": 0,
            "failed": 0,
            "failed_items": []
        }
    }
    """
    try:
        material_ids = request.data.get("material_ids", [])
        student_id = request.data.get("student_id")
        skip_existing = request.data.get("skip_existing", True)
        notify = request.data.get("notify", True)

        # Validate required fields
        if not material_ids or not student_id:
            return Response(
                {"error": "material_ids and student_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize service
        service = BulkAssignmentService(request.user)

        # Pre-flight validation
        preflight_result = service.preflight_check(
            material_ids=material_ids, student_id=student_id
        )

        if not preflight_result["valid"]:
            return Response(
                {
                    "preflight_valid": False,
                    "preflight": preflight_result,
                    "error": "Preflight validation failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute bulk assignment
        try:
            with transaction.atomic():
                result = service.bulk_assign_materials(
                    material_ids=material_ids,
                    student_id=student_id,
                    skip_existing=skip_existing,
                    notify=notify,
                )

            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "result": result,
                    "success": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Bulk assign materials failed: {str(e)}")
            return Response(
                {
                    "preflight_valid": True,
                    "preflight": preflight_result,
                    "error": str(e),
                    "success": False,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Bulk assign materials endpoint error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
