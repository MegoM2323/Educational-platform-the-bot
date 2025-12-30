"""
Views for Element CRUD API (T201)
"""
from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import Element
from .element_serializers import ElementSerializer, ElementListSerializer
from .permissions import IsOwnerOrReadOnly

logger = logging.getLogger(__name__)


class ElementListCreateView(generics.ListCreateAPIView):
    """
    GET /api/knowledge-graph/elements/ - список элементов с фильтрами
    POST /api/knowledge-graph/elements/ - создать элемент

    Query параметры:
    - type: фильтр по типу (text_problem, quick_question, theory, video)
    - created_by: фильтр по автору (me - текущий пользователь, user_id - конкретный пользователь)
    - search: поиск по названию
    - page: номер страницы (пагинация по 20 элементов)
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "difficulty", "estimated_time_minutes"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Получить список элементов с фильтрацией:
        - Публичные элементы (is_public=True)
        - Элементы созданные текущим пользователем
        """
        user = self.request.user
        # T006: prefetch files to avoid N+1 queries for files_count
        queryset = (
            Element.objects.select_related("created_by")
            .prefetch_related("files")
            .filter(Q(is_public=True) | Q(created_by=user))
        )

        # Фильтр по типу
        element_type = self.request.query_params.get("type")
        if element_type:
            queryset = queryset.filter(element_type=element_type)

        # Фильтр по автору
        created_by = self.request.query_params.get("created_by")
        if created_by == "me":
            queryset = queryset.filter(created_by=user)
        elif created_by and created_by.isdigit():
            queryset = queryset.filter(created_by_id=int(created_by))

        return queryset

    def get_serializer_class(self):
        """Использовать разные serializers для list и create"""
        if self.request.method == "GET":
            return ElementListSerializer
        return ElementSerializer

    def list(self, request, *args, **kwargs):
        """Получить список элементов с пагинацией"""
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Пагинация
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data, "count": queryset.count()},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in ElementListCreateView.list: {e}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": f"Ошибка при получении элементов: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        """Создать новый элемент"""
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"success": False, "error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_create(serializer)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error in ElementListCreateView.create: {e}", exc_info=True)
            return Response(
                {"success": False, "error": f"Ошибка при создании элемента: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ElementRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/knowledge-graph/elements/{id}/ - получить элемент
    PATCH /api/knowledge-graph/elements/{id}/ - обновить элемент (только владелец)
    DELETE /api/knowledge-graph/elements/{id}/ - удалить элемент (только владелец)
    """

    # T006: prefetch files to include in detail view
    queryset = Element.objects.select_related("created_by").prefetch_related("files")
    serializer_class = ElementSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        """Получить детали элемента"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Element.DoesNotExist:
            return Response(
                {"success": False, "error": "Элемент не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in ElementRetrieveUpdateDestroyView.retrieve: {e}",
                exc_info=True,
            )
            return Response(
                {"success": False, "error": f"Ошибка при получении элемента: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        """Обновить элемент (только владелец)"""
        try:
            partial = kwargs.pop("partial", True)  # По умолчанию PATCH
            instance = self.get_object()

            # Проверка прав
            if instance.created_by != request.user and not request.user.is_staff:
                return Response(
                    {
                        "success": False,
                        "error": "Только владелец может редактировать элемент",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            if not serializer.is_valid():
                return Response(
                    {"success": False, "error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_update(serializer)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Element.DoesNotExist:
            return Response(
                {"success": False, "error": "Элемент не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in ElementRetrieveUpdateDestroyView.update: {e}", exc_info=True
            )
            return Response(
                {
                    "success": False,
                    "error": f"Ошибка при обновлении элемента: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """Удалить элемент (только владелец)"""
        try:
            instance = self.get_object()

            # Проверка прав
            if instance.created_by != request.user and not request.user.is_staff:
                return Response(
                    {
                        "success": False,
                        "error": "Только владелец может удалить элемент",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Проверка что элемент не используется в уроках
            if instance.lessons.exists():
                return Response(
                    {
                        "success": False,
                        "error": "Элемент используется в уроках и не может быть удален",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Element.DoesNotExist:
            return Response(
                {"success": False, "error": "Элемент не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in ElementRetrieveUpdateDestroyView.destroy: {e}", exc_info=True
            )
            return Response(
                {"success": False, "error": f"Ошибка при удалении элемента: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
