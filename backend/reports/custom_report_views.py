"""
Custom Report Views

ViewSets and views for custom report management and generation.
"""

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q as DBQ
import logging

from .models import CustomReport, CustomReportExecution, CustomReportBuilderTemplate
from .custom_report_serializers import (
    CustomReportListSerializer,
    CustomReportDetailSerializer,
    CustomReportCreateSerializer,
    CustomReportUpdateSerializer,
    CustomReportGenerateSerializer,
    CustomReportExecutionSerializer,
    ReportTemplateSerializer,
    ReportTemplateCloneSerializer,
    ShareReportSerializer,
)
from .services.report_builder import ReportBuilder, ReportBuilderException

try:
    from .permissions import IsTeacherOrAdmin
except ImportError:
    # Fallback if permissions module doesn't exist
    IsTeacherOrAdmin = permissions.IsAuthenticated

# Alias for backwards compatibility
ReportTemplate = CustomReportBuilderTemplate

User = get_user_model()
logger = logging.getLogger(__name__)


class IsReportOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to check if user is the report owner or admin.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        return obj.created_by == request.user


class IsReportOwnerOrSharedWith(permissions.BasePermission):
    """
    Permission to check if user owns the report or it's shared with them.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        if obj.created_by == request.user:
            return True
        if obj.is_shared and obj.shared_with.filter(id=request.user.id).exists():
            return True
        return False


class CustomReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing custom reports.

    Endpoints:
    - GET /api/custom-reports/ - List all reports
    - POST /api/custom-reports/ - Create new report
    - GET /api/custom-reports/{id}/ - Get report details
    - PATCH /api/custom-reports/{id}/ - Update report
    - DELETE /api/custom-reports/{id}/ - Delete report
    - POST /api/custom-reports/{id}/generate/ - Generate report
    - POST /api/custom-reports/{id}/clone/ - Clone as template
    - POST /api/custom-reports/{id}/share/ - Share with colleagues
    - GET /api/custom-reports/{id}/executions/ - Get execution history
    """

    queryset = CustomReport.objects.filter(deleted_at__isnull=True)
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "is_shared", "created_by"]
    search_fields = ["name", "description"]
    ordering_fields = ["-created_at", "-updated_at"]
    ordering = ["-created_at"]
    parser_classes = [JSONParser]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return CustomReportListSerializer
        elif self.action == "create":
            return CustomReportCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CustomReportUpdateSerializer
        elif self.action == "generate":
            return CustomReportGenerateSerializer
        elif self.action == "share":
            return ShareReportSerializer
        elif self.action == "clone":
            return ReportTemplateCloneSerializer
        return CustomReportDetailSerializer

    def get_queryset(self):
        """
        Filter reports based on user role and ownership.
        Teachers see their own reports and shared reports.
        Admins see all reports.
        """
        user = self.request.user

        if user.role == "admin":
            return self.queryset.all()

        # Teachers see their own reports and shared reports
        return self.queryset.filter(
            DBQ(created_by=user) | DBQ(is_shared=True, shared_with=user)
        ).distinct()

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsReportOwnerOrAdmin()]
        elif self.action == "generate":
            return [permissions.IsAuthenticated(), IsReportOwnerOrSharedWith()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="generate")
    def generate(self, request, pk=None):
        """
        Generate report based on current configuration.

        Returns:
            Generated report data with rows, counts, execution time, and optional chart.
        """
        report = self.get_object()

        # Check if user has permission to execute
        if not (
            request.user == report.created_by
            or request.user.role == "admin"
            or (report.is_shared and request.user in report.shared_with.all())
        ):
            return Response(
                {"error": "You do not have permission to generate this report"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            builder = ReportBuilder(report)
            result = builder.build()

            return Response(result, status=status.HTTP_200_OK)

        except ReportBuilderException as e:
            logger.error(f"Report generation error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                f"Unexpected error during report generation: {str(e)}", exc_info=True
            )
            return Response(
                {"error": "An unexpected error occurred during report generation"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, pk=None):
        """
        Clone this report as a new custom report template.

        Request body:
        {
            "name": "New report name",
            "description": "Optional description",
            "config_overrides": {}
        }

        Returns:
            Newly created custom report.
        """
        report = self.get_object()
        serializer = ReportTemplateCloneSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            config = report.config.copy()
            config.update(serializer.validated_data.get("config_overrides", {}))

            new_report = CustomReport.objects.create(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get(
                    "description", report.description
                ),
                created_by=request.user,
                config=config,
                status=CustomReport.Status.DRAFT,
            )

            return Response(
                CustomReportDetailSerializer(new_report).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Clone error: {str(e)}")
            return Response(
                {"error": f"Failed to clone report: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """
        Share report with other teachers.

        Request body:
        {
            "user_ids": [1, 2, 3]
        }

        Returns:
            Updated report with shared_with list.
        """
        report = self.get_object()

        # Check permission
        if report.created_by != request.user and request.user.role != "admin":
            return Response(
                {"error": "Only the report owner can share it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ShareReportSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_ids = serializer.validated_data["user_ids"]
            users = User.objects.filter(id__in=user_ids)

            report.shared_with.add(*users)
            report.is_shared = True
            report.save()

            return Response(
                {
                    "success": True,
                    "message": f"Report shared with {len(user_ids)} users",
                    "shared_with": [
                        {"id": u.id, "name": u.get_full_name()}
                        for u in report.shared_with.all()
                    ],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Share error: {str(e)}")
            return Response(
                {"error": f"Failed to share report: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="unshare")
    def unshare(self, request, pk=None):
        """
        Remove report sharing from specific users.

        Request body:
        {
            "user_ids": [1, 2]
        }

        Returns:
            Updated report.
        """
        report = self.get_object()

        # Check permission
        if report.created_by != request.user and request.user.role != "admin":
            return Response(
                {"error": "Only the report owner can unshare it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ShareReportSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_ids = serializer.validated_data["user_ids"]
            report.shared_with.remove(*user_ids)

            if report.shared_with.count() == 0:
                report.is_shared = False
                report.save()

            return Response(
                {
                    "success": True,
                    "message": f"Sharing removed for {len(user_ids)} users",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Unshare error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="executions")
    def executions(self, request, pk=None):
        """
        Get execution history for this report.

        Query parameters:
        - limit: Number of recent executions to return (default: 20)

        Returns:
            List of execution records.
        """
        report = self.get_object()
        limit = int(request.query_params.get("limit", 20))

        executions = report.executions.all()[:limit]
        serializer = CustomReportExecutionSerializer(executions, many=True)

        return Response(
            {
                "report_id": report.id,
                "report_name": report.name,
                "total_executions": report.executions.count(),
                "executions": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="soft-delete")
    def soft_delete(self, request, pk=None):
        """
        Soft-delete a report (can be restored).

        Returns:
            Success message.
        """
        report = self.get_object()

        report.soft_delete()

        return Response(
            {"success": True, "message": "Report soft-deleted"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        Restore a soft-deleted report.

        Returns:
            Restored report data.
        """
        # Get from all reports, including deleted
        report = get_object_or_404(CustomReport.objects.all(), pk=pk)

        if report.created_by != request.user and request.user.role != "admin":
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        report.restore()

        return Response(
            CustomReportDetailSerializer(report).data, status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a report. Performs soft delete instead of hard delete.

        Returns:
            Success message.
        """
        report = self.get_object()
        report.soft_delete()

        return Response(
            {"success": True, "message": "Report deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )


class ReportTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for pre-built report templates.

    Endpoints:
    - GET /api/templates/ - List all templates
    - GET /api/templates/{id}/ - Get template details
    - POST /api/templates/{id}/clone/ - Clone template as custom report
    """

    queryset = ReportTemplate.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportTemplateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["template_type", "is_system"]
    search_fields = ["name", "description"]
    ordering_fields = ["-created_at"]

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, pk=None):
        """
        Clone a template as a new custom report.

        Request body:
        {
            "name": "My custom report based on template",
            "description": "Optional description",
            "config_overrides": {}
        }

        Returns:
            Newly created custom report.
        """
        template = self.get_object()
        serializer = ReportTemplateCloneSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            custom_report = template.create_custom_report(
                user=request.user,
                name=serializer.validated_data["name"],
                **serializer.validated_data.get("config_overrides", {}),
            )

            return Response(
                CustomReportDetailSerializer(custom_report).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Template clone error: {str(e)}")
            return Response(
                {"error": f"Failed to clone template: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
