"""
Views for Lesson CRUD API and Element Management (T202)
"""
from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Max
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
import logging

from django.db.models import Count
from .models import Lesson, LessonElement, Element
from .lesson_serializers import (
    LessonSerializer,
    LessonListSerializer,
    AddElementToLessonSerializer,
    LessonElementSerializer,
)
from .permissions import IsOwnerOrReadOnly

logger = logging.getLogger(__name__)


class LessonListCreateView(generics.ListCreateAPIView):
    """
    GET /api/knowledge-graph/lessons/ - список уроков с фильтрами
    POST /api/knowledge-graph/lessons/ - создать урок

    Query параметры:
    - subject: фильтр по предмету (ID)
    - created_by: фильтр по автору (me - текущий пользователь, user_id - конкретный пользователь)
    - search: поиск по названию
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "total_duration_minutes", "total_max_score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Получить список уроков с фильтрацией:
        - Публичные уроки (is_public=True)
        - Уроки созданные текущим пользователем
        """
        user = self.request.user
        queryset = (
            Lesson.objects.select_related("created_by", "subject")
            .prefetch_related("elements")
            .annotate(elements_count_annotated=Count("elements"))
            .filter(Q(is_public=True) | Q(created_by=user))
        )

        # Фильтр по предмету
        subject_id = self.request.query_params.get("subject")
        if subject_id and subject_id.isdigit():
            queryset = queryset.filter(subject_id=int(subject_id))

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
            return LessonListSerializer
        return LessonSerializer

    def list(self, request, *args, **kwargs):
        """Получить список уроков"""
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
            logger.error(f"Error in LessonListCreateView.list: {e}", exc_info=True)
            return Response(
                {"success": False, "error": f"Ошибка при получении уроков: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        """Создать новый урок"""
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
            logger.error(f"Error in LessonListCreateView.create: {e}", exc_info=True)
            return Response(
                {"success": False, "error": f"Ошибка при создании урока: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LessonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/knowledge-graph/lessons/{id}/ - получить урок с элементами
    PATCH /api/knowledge-graph/lessons/{id}/ - обновить урок (только владелец)
    DELETE /api/knowledge-graph/lessons/{id}/ - удалить урок (только владелец)
    """

    queryset = Lesson.objects.select_related("created_by", "subject").prefetch_related(
        "elements"
    )
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        """Получить детали урока с элементами"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Lesson.DoesNotExist:
            return Response(
                {"success": False, "error": "Урок не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in LessonRetrieveUpdateDestroyView.retrieve: {e}", exc_info=True
            )
            return Response(
                {"success": False, "error": f"Ошибка при получении урока: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        """Обновить урок (только владелец)"""
        try:
            partial = kwargs.pop("partial", True)
            instance = self.get_object()

            # Проверка прав
            if instance.created_by != request.user and not request.user.is_staff:
                return Response(
                    {
                        "success": False,
                        "error": "Только владелец может редактировать урок",
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

        except Lesson.DoesNotExist:
            return Response(
                {"success": False, "error": "Урок не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in LessonRetrieveUpdateDestroyView.update: {e}", exc_info=True
            )
            return Response(
                {"success": False, "error": f"Ошибка при обновлении урока: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """Удалить урок (только владелец)"""
        try:
            instance = self.get_object()

            # Проверка прав
            if instance.created_by != request.user and not request.user.is_staff:
                return Response(
                    {"success": False, "error": "Только владелец может удалить урок"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Проверка что урок не используется в графах
            if instance.graphs.exists():
                return Response(
                    {
                        "success": False,
                        "error": "Урок используется в графах знаний и не может быть удален",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Lesson.DoesNotExist:
            return Response(
                {"success": False, "error": "Урок не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f"Error in LessonRetrieveUpdateDestroyView.destroy: {e}", exc_info=True
            )
            return Response(
                {"success": False, "error": f"Ошибка при удалении урока: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AddElementToLessonView(APIView):
    """
    POST /api/knowledge-graph/lessons/{lesson_id}/elements/ - добавить элемент в урок

    Body:
    {
        "element_id": 123,
        "order": 5,  // опционально, если не указан - добавляется в конец
        "is_optional": false,
        "custom_instructions": "Дополнительные инструкции"
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        try:
            # Получить урок
            lesson = Lesson.objects.select_related("created_by").get(id=lesson_id)

            # Проверка прав
            if lesson.created_by != request.user and not request.user.is_staff:
                return Response(
                    {
                        "success": False,
                        "error": "Только владелец может добавлять элементы в урок",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Валидация данных
            serializer = AddElementToLessonSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"success": False, "error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            element_id = serializer.validated_data["element_id"]
            order = serializer.validated_data.get("order")
            is_optional = serializer.validated_data.get("is_optional", False)
            custom_instructions = serializer.validated_data.get(
                "custom_instructions", ""
            )

            # Получить элемент
            element = Element.objects.get(id=element_id)

            # Создать связь с транзакцией и проверкой на дубликат
            with transaction.atomic():
                # Проверка что элемент уже не добавлен (с блокировкой для предотвращения race condition)
                if (
                    LessonElement.objects.select_for_update()
                    .filter(lesson=lesson, element=element)
                    .exists()
                ):
                    return Response(
                        {"success": False, "error": "Элемент уже добавлен в урок"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Автоматически определить порядок если не указан
                if order is None:
                    max_order = LessonElement.objects.filter(lesson=lesson).aggregate(
                        max_order=Max("order")
                    )["max_order"]
                    order = (max_order or 0) + 1
                lesson_element = LessonElement.objects.create(
                    lesson=lesson,
                    element=element,
                    order=order,
                    is_optional=is_optional,
                    custom_instructions=custom_instructions,
                )

                # Пересчитать общую продолжительность и баллы
                lesson.recalculate_totals()

            # Вернуть созданную связь
            result_serializer = LessonElementSerializer(lesson_element)

            return Response(
                {"success": True, "data": result_serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except Lesson.DoesNotExist:
            return Response(
                {"success": False, "error": "Урок не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Element.DoesNotExist:
            return Response(
                {"success": False, "error": "Элемент не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error in AddElementToLessonView: {e}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": f"Ошибка при добавлении элемента: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RemoveElementFromLessonView(APIView):
    """
    DELETE /api/knowledge-graph/lessons/{lesson_id}/elements/{element_id}/ - удалить элемент из урока
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, lesson_id, element_id):
        try:
            # Получить урок
            lesson = Lesson.objects.select_related("created_by").get(id=lesson_id)

            # Проверка прав
            if lesson.created_by != request.user and not request.user.is_staff:
                return Response(
                    {
                        "success": False,
                        "error": "Только владелец может удалять элементы из урока",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Найти связь
            lesson_element = LessonElement.objects.filter(
                lesson=lesson, element_id=element_id
            ).first()

            if not lesson_element:
                return Response(
                    {"success": False, "error": "Элемент не найден в уроке"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Удалить с транзакцией
            with transaction.atomic():
                lesson_element.delete()

                # Пересчитать общую продолжительность и баллы
                lesson.recalculate_totals()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Lesson.DoesNotExist:
            return Response(
                {"success": False, "error": "Урок не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error in RemoveElementFromLessonView: {e}", exc_info=True)
            return Response(
                {"success": False, "error": f"Ошибка при удалении элемента: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
