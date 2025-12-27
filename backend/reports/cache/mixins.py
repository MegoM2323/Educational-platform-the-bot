"""
Mixins для интеграции кэширования в Django REST viewsets.

Добавляет поддержку:
- Cache-Control headers
- ETag для условных запросов (304 Not Modified)
- X-Cache header (HIT, MISS, BYPASS)
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from django.http import HttpResponse
from rest_framework.response import Response

from .strategy import cache_strategy

logger = logging.getLogger(__name__)


class CacheHeadersMixin:
    """
    Миксин для добавления кэш-заголовков в ответы.

    Добавляет:
    - Cache-Control header (указывает время кэширования в браузере)
    - ETag header (для условных запросов)
    - X-Cache header (статус кэша: HIT, MISS, BYPASS)
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Переопределяем финализацию ответа для добавления кэш-заголовков.

        Args:
            request: HTTP request
            response: REST response
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response with cache headers
        """
        response = super().finalize_response(request, response, *args, **kwargs)

        # Не кэшируем ошибки и POST/PUT/DELETE запросы
        if (
            request.method in ["GET", "HEAD"]
            and response.status_code in [200, 206, 304]
        ):
            # Определяем TTL в зависимости от action
            ttl = self._get_cache_ttl()

            # Cache-Control header (для браузера и CDN)
            response["Cache-Control"] = f"max-age={ttl}, must-revalidate"

            # ETag (для условных запросов)
            etag = self._generate_etag(response)
            response["ETag"] = f'"{etag}"'

            # Проверяем If-None-Match
            if_none_match = request.META.get("HTTP_IF_NONE_MATCH", "").strip('"')
            if if_none_match == etag:
                # Возвращаем 304 Not Modified
                response.status_code = 304
                response.data = None

            # X-Cache header (для отладки)
            response["X-Cache"] = "HIT" if self._is_cache_hit else "MISS"

        return response

    def _get_cache_ttl(self) -> int:
        """
        Определяет TTL для кэша в зависимости от action.

        Returns:
            TTL в секундах
        """
        action = getattr(self, "action", None)

        ttl_map = {
            "list": 300,  # 5 минут
            "retrieve": 600,  # 10 минут
            "stats": 300,  # 5 минут
            "available_students": 1800,  # 30 минут
            "export": 3600,  # 1 час (экспорт долго кэшируется)
        }

        return ttl_map.get(action, 600)

    def _generate_etag(self, response: Response) -> str:
        """
        Генерирует ETag для ответа.

        Args:
            response: REST response

        Returns:
            ETag (MD5 хеш)
        """
        try:
            data = response.data
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True, default=str)
            else:
                data_str = str(data)

            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception:
            # Если не получилось сгенерировать, используем пустую строку
            return "unknown"

    @property
    def _is_cache_hit(self) -> bool:
        """
        Проверяет, был ли попадание в кэш.

        Returns:
            True если был попадание
        """
        return getattr(self, "_cache_hit", False)

    @_is_cache_hit.setter
    def _is_cache_hit(self, value: bool) -> None:
        """Устанавливает флаг попадания кэша."""
        self._cache_hit = value


class RedisCacheMixin(CacheHeadersMixin):
    """
    Миксин для кэширования ответов в Redis.

    Автоматически кэширует GET запросы и инвалидирует при
    POST/PUT/DELETE.

    Использование:
        class ReportViewSet(RedisCacheMixin, viewsets.ViewSet):
            cache_enabled = True  # Включить кэширование
            cache_report_types = {
                'list': 'analytics',
                'retrieve': 'custom',
            }
    """

    cache_enabled = True
    cache_report_types = {
        "list": "default",
        "retrieve": "custom",
        "stats": "analytics",
    }

    def list(self, request, *args, **kwargs):
        """
        Переопределяем list для кэширования.

        Args:
            request: HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response (из кэша или свежий)
        """
        if not self.cache_enabled:
            return super().list(request, *args, **kwargs)

        # Генерируем ключ кэша
        cache_key = self._get_list_cache_key(request)

        # Пытаемся получить из кэша
        hit, cached_data, etag = cache_strategy.get_report_cache(
            report_id=0,  # Для list используем 0
            user_id=request.user.id,
            filters=self._get_filter_params(request),
        )

        if hit and cached_data:
            self._is_cache_hit = True
            return Response(cached_data)

        # Получаем свежие данные
        response = super().list(request, *args, **kwargs)

        # Кэшируем ответ
        if response.status_code == 200:
            report_type = self.cache_report_types.get("list", "default")
            cache_strategy.set_report_cache(
                report_id=0,
                user_id=request.user.id,
                data=response.data,
                report_type=report_type,
                filters=self._get_filter_params(request),
                etag=etag,
            )

        self._is_cache_hit = False
        return response

    def retrieve(self, request, *args, **kwargs):
        """
        Переопределяем retrieve для кэширования.

        Args:
            request: HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response (из кэша или свежий)
        """
        if not self.cache_enabled:
            return super().retrieve(request, *args, **kwargs)

        # Получаем ID объекта
        report_id = kwargs.get("pk")

        # Пытаемся получить из кэша
        hit, cached_data, etag = cache_strategy.get_report_cache(
            report_id=report_id,
            user_id=request.user.id,
        )

        if hit and cached_data:
            self._is_cache_hit = True
            return Response(cached_data)

        # Получаем свежие данные
        response = super().retrieve(request, *args, **kwargs)

        # Кэшируем ответ
        if response.status_code == 200:
            report_type = self.cache_report_types.get("retrieve", "default")
            cache_strategy.set_report_cache(
                report_id=report_id,
                user_id=request.user.id,
                data=response.data,
                report_type=report_type,
                etag=etag,
            )

        self._is_cache_hit = False
        return response

    def create(self, request, *args, **kwargs):
        """
        Переопределяем create для инвалидации кэша.

        Args:
            request: HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response
        """
        response = super().create(request, *args, **kwargs)

        # Инвалидируем кэш пользователя
        cache_strategy.invalidate_user_cache(request.user.id)

        return response

    def update(self, request, *args, **kwargs):
        """
        Переопределяем update для инвалидации кэша.

        Args:
            request: HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response
        """
        report_id = kwargs.get("pk")
        response = super().update(request, *args, **kwargs)

        # Инвалидируем кэш пользователя и отчёта
        cache_strategy.invalidate_report_cache(report_id, request.user.id)

        return response

    def destroy(self, request, *args, **kwargs):
        """
        Переопределяем destroy для инвалидации кэша.

        Args:
            request: HTTP request
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response
        """
        report_id = kwargs.get("pk")
        response = super().destroy(request, *args, **kwargs)

        # Инвалидируем кэш пользователя и отчёта
        cache_strategy.invalidate_report_cache(report_id, request.user.id)

        return response

    @staticmethod
    def _get_list_cache_key(request) -> str:
        """
        Генерирует ключ кэша для list endpoint.

        Args:
            request: HTTP request

        Returns:
            Cache key
        """
        filters = RedisCacheMixin._get_filter_params(request)
        filters_str = json.dumps(filters, sort_keys=True, default=str)
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:12]

        return f"report_list:{request.user.id}:{filters_hash}"

    @staticmethod
    def _get_filter_params(request) -> Dict[str, Any]:
        """
        Получает параметры фильтрации из запроса.

        Args:
            request: HTTP request

        Returns:
            Dictionary of filters
        """
        filters = {}

        # Стандартные параметры фильтрации
        for param in ["type", "status", "student", "subject", "week_start"]:
            value = request.query_params.get(param)
            if value:
                filters[param] = value

        # Параметры поиска
        search = request.query_params.get("search")
        if search:
            filters["search"] = search

        # Параметры сортировки
        ordering = request.query_params.get("ordering")
        if ordering:
            filters["ordering"] = ordering

        return filters
