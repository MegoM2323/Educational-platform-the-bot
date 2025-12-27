"""
Фильтры для Material API endpoints.

Предоставляет расширенные возможности фильтрации и поиска материалов:
- Полнотекстовый поиск по title, description, content, tags (PostgreSQL)
- Фильтрация по subject, type, status, difficulty_level
- Фильтрация по диапазону дат (created_date)
- Фильтрация по рейтингу/популярности
- Фасетированный поиск (результаты по типам, предметам и т.д.)
- Поиск с релевантностью и рангированием
"""

from django.contrib.postgres.search import SearchQuery, SearchVector, SearchRank, SearchHeadline
from django.db.models import F, Q, Value, IntegerField, Count
from django_filters import rest_framework as filters

from .models import Material


class MaterialFilterSet(filters.FilterSet):
    """
    Фильтр для материалов с поддержкой полнотекстового поиска.

    Параметры:
    - search: полнотекстовый поиск по title, description, content, tags
    - subject: ID предмета или название
    - type: тип материала (lesson, presentation, video, document, test, homework)
    - status: статус (draft, active, archived)
    - difficulty_level: уровень сложности (1-5)
    - created_date_from: дата создания от (YYYY-MM-DD)
    - created_date_to: дата создания до (YYYY-MM-DD)
    - is_public: только публичные (true/false)
    - author_id: ID автора/преподавателя

    Примеры:
    GET /api/materials/?search=Python&subject=1&difficulty_level=3
    GET /api/materials/?search=algebra&type=lesson&created_date_from=2024-01-01
    """

    # Полнотекстовый поиск
    search = filters.CharFilter(method="filter_search", label="Полнотекстовый поиск")

    # Простые фильтры
    subject = filters.NumberFilter(field_name="subject_id", label="Предмет")
    type = filters.ChoiceFilter(
        choices=Material.Type.choices,
        field_name="type",
        label="Тип материала"
    )
    status = filters.ChoiceFilter(
        choices=Material.Status.choices,
        field_name="status",
        label="Статус"
    )
    difficulty_level = filters.NumberFilter(
        field_name="difficulty_level",
        label="Уровень сложности"
    )
    author_id = filters.NumberFilter(field_name="author_id", label="ID автора")
    is_public = filters.BooleanFilter(field_name="is_public", label="Публичный")

    # Диапазон дат
    created_date_from = filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Дата создания от"
    )
    created_date_to = filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Дата создания до"
    )

    class Meta:
        model = Material
        fields = [
            "search",
            "subject",
            "type",
            "status",
            "difficulty_level",
            "author_id",
            "is_public",
            "created_date_from",
            "created_date_to",
        ]

    def filter_search(self, queryset, name, value):
        """
        Полнотекстовый поиск по title, description, content, tags.

        Использует PostgreSQL SearchVector и SearchRank для релевантности.
        Дает больший вес совпадениям в title, затем description.

        Args:
            queryset: исходный queryset
            name: имя фильтра ('search')
            value: поисковый запрос

        Returns:
            QuerySet с отсортированными по релевантности результатами
        """
        if not value:
            return queryset

        # Создаем SearchVector с разными весами для разных полей
        search_vector = (
            SearchVector("title", weight="A")  # Максимальный вес для title
            + SearchVector("description", weight="B")  # Средний вес для description
            + SearchVector("tags", weight="B")  # Средний вес для tags
            + SearchVector("content", weight="C")  # Меньший вес для content
        )

        # Создаем SearchQuery с поддержкой OR, AND, NOT операторов
        search_query = SearchQuery(value, search_type="websearch")

        # Фильтруем по поисковому запросу
        queryset = queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query)

        # Сортируем по релевантности (убывание)
        queryset = queryset.order_by("-rank")

        return queryset
