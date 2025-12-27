"""
T_ASSIGN_004: ViewSets for grading rubrics and criteria
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import GradingRubric, RubricCriterion
from .serializers import (
    GradingRubricCreateSerializer,
    GradingRubricDetailSerializer,
    GradingRubricListSerializer,
    RubricCriterionSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class StandardPagination(PageNumberPagination):
    """Standard pagination for rubric endpoints."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsTeacherOrTutor(permissions.BasePermission):
    """Permission to restrict access to teachers and tutors only."""

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["teacher", "tutor"]
        )


class GradingRubricViewSet(viewsets.ModelViewSet):
    """
    T_ASSIGN_004: ViewSet для рубрик оценки

    Позволяет преподавателям создавать, редактировать и использовать
    рубрики для оценки заданий.

    Permissions:
        - Only teachers/tutors can create, modify, delete rubrics
        - All authenticated users can list and view rubrics
        - Teachers can only modify their own rubrics
    """

    queryset = GradingRubric.objects.filter(is_deleted=False)
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["created_by", "is_template"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name", "total_points"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list:
        """
        T_ASSIGN_004: Determine permissions based on action.

        Write operations (create, update, destroy) require IsTeacherOrTutor.
        Read operations are available to all authenticated users.

        Returns:
            list: Permission classes for current action
        """
        if self.action in ["create"]:
            return [permissions.IsAuthenticated(), IsTeacherOrTutor()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsTeacherOrTutor()]
        elif self.action == "clone":
            return [permissions.IsAuthenticated(), IsTeacherOrTutor()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self) -> type:
        """
        Return appropriate serializer class based on action.

        Returns:
            type: GradingRubricListSerializer for list action,
                  GradingRubricCreateSerializer for create action,
                  GradingRubricDetailSerializer for other actions
        """
        if self.action == "list":
            return GradingRubricListSerializer
        elif self.action == "create":
            return GradingRubricCreateSerializer
        return GradingRubricDetailSerializer

    def get_queryset(self) -> QuerySet:
        """
        Filter rubrics based on user role.

        Teachers/tutors see all rubrics.
        Students see only template rubrics.

        Returns:
            QuerySet: Filtered rubric records
        """
        user = self.request.user
        queryset = GradingRubric.objects.filter(is_deleted=False)

        if user.role in ["teacher", "tutor"]:
            # Teachers/tutors see all rubrics
            return queryset
        elif user.role == "student":
            # Students see only template rubrics
            return queryset.filter(is_template=True)

        return queryset.filter(created_by=user)

    def perform_create(self, serializer: Any) -> None:
        """
        Save rubric with authenticated user as creator.

        Args:
            serializer: GradingRubricCreateSerializer instance
        """
        try:
            rubric = serializer.save(created_by=self.request.user)
            logger.info(
                f"Grading rubric created: id={rubric.id}, name='{rubric.name}', "
                f"creator={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create rubric: {str(e)}, user={self.request.user.email}"
            )
            raise

    def perform_update(self, serializer: Any) -> None:
        """
        Update rubric with permission check.

        Args:
            serializer: GradingRubricDetailSerializer instance
        """
        rubric = self.get_object()

        # Check if user is the rubric creator
        if rubric.created_by != self.request.user:
            raise PermissionDenied("You can only modify your own rubrics")

        try:
            serializer.save()
            logger.info(
                f"Grading rubric updated: id={rubric.id}, name='{rubric.name}', "
                f"updater={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to update rubric: {str(e)}, user={self.request.user.email}"
            )
            raise

    def perform_destroy(self, instance: Any) -> None:
        """
        Soft delete rubric (soft delete support).

        Args:
            instance: GradingRubric instance
        """
        # Check if user is the rubric creator
        if instance.created_by != self.request.user:
            raise PermissionDenied("You can only delete your own rubrics")

        try:
            instance.is_deleted = True
            instance.save()
            logger.info(
                f"Grading rubric deleted: id={instance.id}, name='{instance.name}', "
                f"deleter={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to delete rubric: {str(e)}, user={self.request.user.email}"
            )
            raise

    @action(detail=False, methods=["get"])
    def templates(self, request: Request) -> Response:
        """
        T_ASSIGN_004: List template rubrics that can be used as references.

        Returns:
            Response: List of template rubrics
        """
        queryset = self.get_queryset().filter(is_template=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def clone(self, request: Request, pk: int | None = None) -> Response:
        """
        T_ASSIGN_004: Clone a rubric for the current user.

        Creates a copy of the rubric with all its criteria for the requesting user.

        Args:
            request: HTTP POST request
            pk: Rubric ID

        Returns:
            Response: Cloned rubric details with 201 status
        """
        rubric = self.get_object()

        try:
            # Clone the rubric
            cloned_rubric = rubric.clone(request.user)

            serializer = GradingRubricDetailSerializer(cloned_rubric)
            logger.info(
                f"Rubric cloned: original_id={rubric.id}, cloned_id={cloned_rubric.id}, "
                f"cloner={request.user.email}"
            )
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(
                f"Failed to clone rubric: {str(e)}, user={request.user.email}"
            )
            return Response(
                {"error": "Failed to clone rubric"},
                status=status.HTTP_400_BAD_REQUEST
            )


class RubricCriterionViewSet(viewsets.ModelViewSet):
    """
    T_ASSIGN_004: ViewSet для критериев рубрики

    Permissions:
        - Only rubric creator can create, modify, delete criteria
        - All authenticated users can view criteria
    """

    queryset = RubricCriterion.objects.all()
    serializer_class = RubricCriterionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_permissions(self) -> list:
        """
        T_ASSIGN_004: Determine permissions based on action.

        Write operations require rubric ownership.
        Read operations are available to all authenticated users.

        Returns:
            list: Permission classes for current action
        """
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        """
        T_ASSIGN_004: Filter criteria based on rubric access.

        If rubric_id is provided in query params, filter by that rubric.

        Returns:
            QuerySet: Filtered criterion records
        """
        rubric_id = self.request.query_params.get("rubric")

        if rubric_id:
            try:
                rubric = GradingRubric.objects.get(
                    id=rubric_id, is_deleted=False
                )
                return RubricCriterion.objects.filter(rubric=rubric)
            except GradingRubric.DoesNotExist:
                return RubricCriterion.objects.none()

        return RubricCriterion.objects.filter(
            rubric__is_deleted=False
        ).select_related("rubric")

    def perform_create(self, serializer: Any) -> None:
        """
        Create criterion with permission check.

        Args:
            serializer: RubricCriterionSerializer instance
        """
        rubric_id = self.request.data.get("rubric")

        try:
            rubric = GradingRubric.objects.get(id=rubric_id)
        except GradingRubric.DoesNotExist:
            raise PermissionDenied("Rubric not found")

        # Check if user is the rubric creator
        if rubric.created_by != self.request.user:
            raise PermissionDenied("You can only add criteria to your own rubrics")

        try:
            serializer.save(rubric=rubric)
            logger.info(
                f"Criterion created: rubric_id={rubric.id}, name='{serializer.validated_data.get('name')}', "
                f"creator={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create criterion: {str(e)}, user={self.request.user.email}"
            )
            raise

    def perform_update(self, serializer: Any) -> None:
        """
        Update criterion with permission check.

        Args:
            serializer: RubricCriterionSerializer instance
        """
        criterion = self.get_object()

        # Check if user is the rubric creator
        if criterion.rubric.created_by != self.request.user:
            raise PermissionDenied("You can only update criteria in your own rubrics")

        try:
            serializer.save()
            logger.info(
                f"Criterion updated: criterion_id={criterion.id}, name='{criterion.name}', "
                f"updater={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to update criterion: {str(e)}, user={self.request.user.email}"
            )
            raise

    def perform_destroy(self, instance: Any) -> None:
        """
        Delete criterion with permission check.

        Args:
            instance: RubricCriterion instance
        """
        # Check if user is the rubric creator
        if instance.rubric.created_by != self.request.user:
            raise PermissionDenied("You can only delete criteria from your own rubrics")

        try:
            instance.delete()
            logger.info(
                f"Criterion deleted: criterion_id={instance.id}, rubric_id={instance.rubric.id}, "
                f"deleter={self.request.user.email}"
            )
        except Exception as e:
            logger.error(
                f"Failed to delete criterion: {str(e)}, user={self.request.user.email}"
            )
            raise
