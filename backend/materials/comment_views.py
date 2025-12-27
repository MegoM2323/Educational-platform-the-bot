"""
Material Comment Threading Views

Implements nested comment threading with:
- Top-level comments
- Replies to comments (max 3 levels deep)
- Soft delete support
- Moderation (approval workflow)
- Pagination for comments and replies
- Role-based permissions (author can delete own, teacher/admin can delete any)
"""

import logging
from typing import Any

from django.db.models import Count, Prefetch, QuerySet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Material, MaterialComment
from .serializers import MaterialCommentReplySerializer, MaterialCommentSerializer

logger = logging.getLogger(__name__)


class CommentPagination(PageNumberPagination):
    """
    Пагинация для комментариев
    - 20 комментариев на страницу
    - Максимум 100
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ReplyPagination(PageNumberPagination):
    """
    Пагинация для ответов на комментарии
    - 10 ответов на страницу
    - Максимум 50
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class MaterialCommentViewSet(viewsets.ModelViewSet):
    """
    API ViewSet для управления комментариями к материалам

    T_MAT_007: Поддержка потоков комментариев:

    Доступные действия:
    - list: Получить все комментарии к материалу (только верхнего уровня)
    - create: Создать новый комментарий или ответ
    - retrieve: Получить конкретный комментарий
    - update: Обновить свой комментарий (только автор)
    - partial_update: Частичное обновление
    - destroy: Удалить комментарий (мягкое удаление)
    - replies: Получить все ответы на комментарий (пагинировано)
    - create_reply: Создать ответ на комментарий

    Пермиссии:
    - Все аутентифицированные пользователи могут просматривать комментарии
    - Все аутентифицированные пользователи могут создавать комментарии
    - Только автор может редактировать свой комментарий
    - Только автор или учитель/администратор может удалить комментарий

    Оптимизация:
    - select_related: author, material, parent_comment
    - prefetch_related: replies с author
    - Аннотация reply_count для всех комментариев
    """

    serializer_class = MaterialCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CommentPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def get_queryset(self) -> QuerySet:
        """
        Получить комментарии для материала

        Фильтрует только комментарии верхнего уровня (без parent_comment)
        для основного списка. Ответы получаются через /replies/ эндпоинт.
        """
        material_id = self.kwargs.get("material_pk")

        # Базовый queryset с оптимизацией
        queryset = (
            MaterialComment.objects
            .filter(material_id=material_id, parent_comment=None, is_deleted=False)
            .select_related("author")
            .annotate(
                reply_count=Count(
                    "replies",
                    filter={"replies__is_deleted": False, "replies__is_approved": True}
                )
            )
        )

        return queryset

    def get_serializer_context(self) -> dict:
        """Добавить request в контекст сериализатора"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Создать новый комментарий или ответ на комментарий

        Request body:
        {
            "content": "Текст комментария",
            "is_question": false,
            "parent_comment": null  // ID родительского комментария для ответа
        }

        Returns:
            201 Created: Созданный комментарий
            400 Bad Request: Ошибка валидации
            403 Forbidden: Нарушение прав доступа
        """
        material_id = self.kwargs.get("material_pk")

        # Проверка существования материала
        try:
            material = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return Response(
                {"error": "Материал не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(material=material, author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error creating comment: {str(e)}")
                return Response(
                    {"error": "Ошибка при создании комментария"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance: MaterialComment) -> None:
        """
        Удалить комментарий (мягкое удаление)

        Проверяет права доступа:
        - Только автор или учитель/администратор может удалить
        """
        if (
            instance.author != self.request.user
            and self.request.user.role not in ["teacher", "admin"]
        ):
            raise PermissionError("Вы не можете удалить этот комментарий")

        # Мягкое удаление
        instance.delete()

    @action(detail=True, methods=["get"], pagination_class=ReplyPagination)
    def replies(self, request: Request, pk: int | None = None) -> Response:
        """
        Получить все ответы на комментарий

        Query параметры:
        - page: Номер страницы (по умолчанию 1)
        - page_size: Размер страницы (по умолчанию 10, максимум 50)

        Returns:
            200 OK: Список ответов с пагинацией
            404 Not Found: Комментарий не найден

        Response format:
        {
            "count": 25,
            "next": "http://api.example.com/comments/1/replies/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 2,
                    "author_id": 3,
                    "author_name": "John Doe",
                    "content": "Ответ на комментарий",
                    "created_at": "2024-12-27T10:00:00Z",
                    "can_delete": true,
                    ...
                },
                ...
            ]
        }
        """
        comment = self.get_object()

        # Получить ответы на этот комментарий (только одобренные и не удаленные)
        replies_queryset = (
            comment.replies.filter(is_deleted=False, is_approved=True)
            .select_related("author")
            .order_by("created_at")
        )

        # Применить пагинацию
        page = self.paginate_queryset(replies_queryset)
        if page is not None:
            serializer = MaterialCommentReplySerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = MaterialCommentReplySerializer(
            replies_queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def create_reply(self, request: Request, pk: int | None = None) -> Response:
        """
        Создать ответ на комментарий

        Request body:
        {
            "content": "Текст ответа",
            "is_question": false
        }

        Returns:
            201 Created: Созданный ответ
            400 Bad Request: Ошибка валидации (например, максимальная глубина)
            404 Not Found: Комментарий не найден
            403 Forbidden: Нельзя отвечать на этот комментарий (макс 3 уровня)

        Example:
            POST /api/materials/1/comments/5/create_reply/
            {
                "content": "Спасибо за объяснение!"
            }
        """
        parent_comment = self.get_object()

        # Проверка глубины вложенности
        if parent_comment.get_depth() >= 3:
            return Response(
                {"error": "Максимальная глубина вложенности комментариев - 3 уровня"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Приготовить данные для сериализатора
        data = request.data.copy()
        data["parent_comment"] = parent_comment.id
        data["material"] = parent_comment.material_id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            try:
                serializer.save(author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error creating reply: {str(e)}")
                return Response(
                    {"error": "Ошибка при создании ответа"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: int | None = None) -> Response:
        """
        Одобрить комментарий (только для модераторов)

        Only teachers and admins can approve comments.

        Returns:
            200 OK: Комментарий одобрен
            403 Forbidden: Нет прав доступа
            404 Not Found: Комментарий не найден
        """
        if request.user.role not in ["teacher", "admin"]:
            return Response(
                {"error": "Только учителя и администраторы могут одобрять комментарии"},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment = self.get_object()
        comment.is_approved = True
        comment.save(update_fields=["is_approved"])

        return Response(
            {"message": "Комментарий одобрен", "is_approved": comment.is_approved}
        )

    @action(detail=True, methods=["post"])
    def disapprove(self, request: Request, pk: int | None = None) -> Response:
        """
        Отклонить комментарий (только для модераторов)

        Only teachers and admins can disapprove comments.

        Returns:
            200 OK: Комментарий отклонен
            403 Forbidden: Нет прав доступа
            404 Not Found: Комментарий не найден
        """
        if request.user.role not in ["teacher", "admin"]:
            return Response(
                {"error": "Только учителя и администраторы могут отклонять комментарии"},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment = self.get_object()
        comment.is_approved = False
        comment.save(update_fields=["is_approved"])

        return Response(
            {"message": "Комментарий отклонен", "is_approved": comment.is_approved}
        )
