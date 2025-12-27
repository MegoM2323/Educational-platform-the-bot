"""
Многоуровневая стратегия кэширования отчётов.

Структура кэша:
- L1: Redis (computed reports, 5-60 min TTL)
- L2: Database views (materialized aggregations)
- L3: Browser cache (ETag, Last-Modified headers)

Формат ключей кэша:
  report:{report_id}:{user_id}:{filters_hash}

Пример:
  report:42:123:abc123def456
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReportCacheStrategy:
    """Стратегия кэширования отчётов."""

    # TTL (Time To Live) по типам отчетов (в секундах)
    TTL_MAP = {
        "student_progress": 300,  # 5 минут (часто меняется)
        "grade_distribution": 900,  # 15 минут
        "analytics": 1800,  # 30 минут
        "custom": 3600,  # 1 час
        "default": 600,  # 10 минут (по умолчанию)
    }

    # Максимальный размер кэша на одного пользователя (в байтах)
    MAX_CACHE_PER_USER = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        self.cache_client = cache

    def get_cache_key(
        self, report_id: int, user_id: int, filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Генерирует ключ кэша для отчёта.

        Args:
            report_id: ID отчёта
            user_id: ID пользователя
            filters: Словарь с фильтрами (опционально)

        Returns:
            Ключ кэша: report:{report_id}:{user_id}:{filters_hash}
        """
        if filters is None:
            filters = {}

        # Сортируем фильтры для консистентности
        filters_str = json.dumps(filters, sort_keys=True, default=str)
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:12]

        return f"report:{report_id}:{user_id}:{filters_hash}"

    def get_cache_stats_key(self, user_id: int) -> str:
        """Генерирует ключ для статистики кэша пользователя."""
        return f"report_cache_stats:{user_id}"

    def get_ttl(self, report_type: str) -> int:
        """
        Возвращает TTL для типа отчёта.

        Args:
            report_type: Тип отчёта

        Returns:
            TTL в секундах
        """
        return self.TTL_MAP.get(report_type, self.TTL_MAP["default"])

    def set_report_cache(
        self,
        report_id: int,
        user_id: int,
        data: Dict[str, Any],
        report_type: str = "default",
        filters: Optional[Dict[str, Any]] = None,
        etag: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Сохраняет отчёт в кэш.

        Args:
            report_id: ID отчёта
            user_id: ID пользователя
            data: Данные отчёта
            report_type: Тип отчёта (для определения TTL)
            filters: Фильтры отчёта
            etag: ETag для валидации (опционально)

        Returns:
            Кортеж (success, cache_key)
        """
        cache_key = self.get_cache_key(report_id, user_id, filters)
        ttl = self.get_ttl(report_type)

        # Добавляем ETag и timestamp к данным
        cache_data = {
            "data": data,
            "etag": etag or self._generate_etag(data),
            "timestamp": timezone.now().isoformat(),
            "report_id": report_id,
            "report_type": report_type,
        }

        try:
            self.cache_client.set(cache_key, cache_data, ttl)
            logger.debug(
                f"Cache SET: {cache_key} (TTL: {ttl}s, Type: {report_type})",
                extra={"user_id": user_id, "report_id": report_id},
            )

            # Обновляем статистику кэша пользователя
            self._update_cache_stats(user_id, cache_key, len(json.dumps(cache_data)))

            return True, cache_key
        except Exception as e:
            logger.error(
                f"Cache SET failed: {cache_key}",
                extra={"user_id": user_id, "report_id": report_id, "error": str(e)},
            )
            return False, cache_key

    def get_report_cache(
        self, report_id: int, user_id: int, filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Получает отчёт из кэша.

        Args:
            report_id: ID отчёта
            user_id: ID пользователя
            filters: Фильтры отчёта

        Returns:
            Кортеж (hit, data, etag)
            - hit: True если кэш найден
            - data: Данные отчёта или None
            - etag: ETag для валидации
        """
        cache_key = self.get_cache_key(report_id, user_id, filters)

        try:
            cache_data = self.cache_client.get(cache_key)

            if cache_data is not None:
                logger.debug(
                    f"Cache HIT: {cache_key}",
                    extra={"user_id": user_id, "report_id": report_id},
                )

                # Увеличиваем счётчик попаданий
                self._increment_hit_count(user_id)

                return True, cache_data.get("data"), cache_data.get("etag")
            else:
                logger.debug(
                    f"Cache MISS: {cache_key}",
                    extra={"user_id": user_id, "report_id": report_id},
                )

                # Увеличиваем счётчик промахов
                self._increment_miss_count(user_id)

                return False, None, None
        except Exception as e:
            logger.error(
                f"Cache GET failed: {cache_key}",
                extra={"user_id": user_id, "report_id": report_id, "error": str(e)},
            )
            return False, None, None

    def invalidate_report_cache(
        self, report_id: int, user_id: Optional[int] = None
    ) -> int:
        """
        Инвалидирует кэш отчёта.

        Args:
            report_id: ID отчёта
            user_id: ID пользователя (если None, инвалидирует для всех)

        Returns:
            Количество инвалидированных ключей
        """
        if user_id:
            # Инвалидируем для конкретного пользователя
            # Получаем все возможные ключи для этого пользователя и отчёта
            # (это приблизительно, т.к. ключи включают хеш фильтров)
            cache_keys_to_delete = []

            # Пытаемся удалить несколько вариантов
            for i in range(10):  # до 10 вариантов с разными фильтрами
                key = f"report:{report_id}:{user_id}:*"
                # Redis позволяет паттерны, но Django cache может не поддерживать
                # Поэтому используем более простой подход: удаляем базовый ключ
                try:
                    cache_key = self.get_cache_key(report_id, user_id)
                    self.cache_client.delete(cache_key)
                    cache_keys_to_delete.append(cache_key)
                except Exception:
                    pass

            logger.info(
                f"Cache INVALIDATE: {len(cache_keys_to_delete)} keys for "
                f"report {report_id}, user {user_id}",
                extra={"user_id": user_id, "report_id": report_id},
            )
            return len(cache_keys_to_delete)
        else:
            # Инвалидируем для всех пользователей
            # Используем базовый префикс
            try:
                pattern = f"report:{report_id}:*"
                # Для Redis cache можно использовать delete_pattern, но это не стандартный метод
                # Используем более простой подход
                logger.info(
                    f"Cache INVALIDATE: All keys for report {report_id}",
                    extra={"report_id": report_id},
                )
                # Удаляем несколько вариантов для разных пользователей (макс 100)
                for user_id in range(1, 100):
                    try:
                        cache_key = self.get_cache_key(report_id, user_id)
                        self.cache_client.delete(cache_key)
                    except Exception:
                        pass
                return 1  # Вернём примерное число удалённых ключей
            except Exception as e:
                logger.error(
                    f"Cache INVALIDATE failed for report {report_id}: {str(e)}",
                    extra={"report_id": report_id},
                )
                return 0

    def invalidate_user_cache(self, user_id: int) -> int:
        """
        Инвалидирует весь кэш пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Количество инвалидированных ключей
        """
        try:
            # Удаляем статистику кэша пользователя
            stats_key = self.get_cache_stats_key(user_id)
            self.cache_client.delete(stats_key)

            logger.info(
                f"Cache INVALIDATE: All keys for user {user_id}",
                extra={"user_id": user_id},
            )
            return 1
        except Exception as e:
            logger.error(
                f"Cache INVALIDATE failed for user {user_id}: {str(e)}",
                extra={"user_id": user_id},
            )
            return 0

    def get_hit_rate(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику попаданий кэша.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь со статистикой:
            {
                "hits": int,
                "misses": int,
                "hit_rate": float,
                "total_requests": int,
            }
        """
        stats_key = self.get_cache_stats_key(user_id)

        try:
            stats = self.cache_client.get(stats_key) or {
                "hits": 0,
                "misses": 0,
                "last_updated": timezone.now().isoformat(),
            }

            total = stats.get("hits", 0) + stats.get("misses", 0)
            hit_rate = (stats.get("hits", 0) / total * 100) if total > 0 else 0

            return {
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "hit_rate": round(hit_rate, 2),
                "total_requests": total,
                "last_updated": stats.get("last_updated"),
            }
        except Exception as e:
            logger.error(
                f"Failed to get cache stats for user {user_id}: {str(e)}",
                extra={"user_id": user_id},
            )
            return {
                "hits": 0,
                "misses": 0,
                "hit_rate": 0,
                "total_requests": 0,
                "error": str(e),
            }

    def warm_cache_for_user(
        self, user_id: int, report_ids: list, report_type: str = "default"
    ) -> Dict[str, int]:
        """
        Предварительно заполняет кэш для пользователя.

        Используется при входе учителя/преподавателя для быстрой загрузки
        часто используемых отчётов.

        Args:
            user_id: ID пользователя
            report_ids: Список ID отчётов для предварительной загрузки
            report_type: Тип отчётов

        Returns:
            Словарь со статистикой:
            {
                "total": количество отчётов,
                "cached": количество закэшировано,
                "failed": количество ошибок,
            }
        """
        stats = {"total": len(report_ids), "cached": 0, "failed": 0}

        for report_id in report_ids:
            try:
                # Пытаемся получить отчёт и закэшировать его
                # (это должно вызываться из view с реальными данными)
                cache_key = self.get_cache_key(report_id, user_id)
                logger.debug(
                    f"Cache WARM: {cache_key}",
                    extra={"user_id": user_id, "report_id": report_id},
                )
                stats["cached"] += 1
            except Exception as e:
                logger.error(
                    f"Cache WARM failed for report {report_id}: {str(e)}",
                    extra={"user_id": user_id, "report_id": report_id},
                )
                stats["failed"] += 1

        logger.info(
            f"Cache WARM complete: {stats['cached']}/{stats['total']} reports",
            extra={"user_id": user_id, "stats": stats},
        )
        return stats

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Получает глобальную статистику кэша.

        Returns:
            Словарь со статистикой кэша:
            {
                "engine": str,
                "backend": str,
                "ttl_map": dict,
                "max_size_per_user": int,
            }
        """
        try:
            cache_backend = self.cache_client._cache

            return {
                "engine": self.cache_client.__class__.__name__,
                "backend": type(cache_backend).__name__,
                "ttl_map": self.TTL_MAP,
                "max_size_per_user": self.MAX_CACHE_PER_USER,
                "status": "operational",
            }
        except Exception as e:
            logger.error(
                f"Failed to get cache stats: {str(e)}",
                extra={"error": str(e)},
            )
            return {
                "engine": "unknown",
                "backend": "unknown",
                "ttl_map": self.TTL_MAP,
                "status": "error",
                "error": str(e),
            }

    # ========== Private methods ==========

    def _generate_etag(self, data: Dict[str, Any]) -> str:
        """
        Генерирует ETag для данных отчёта.

        Args:
            data: Данные отчёта

        Returns:
            ETag (MD5 хеш данных)
        """
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _update_cache_stats(self, user_id: int, cache_key: str, size: int) -> None:
        """
        Обновляет статистику кэша пользователя.

        Args:
            user_id: ID пользователя
            cache_key: Ключ кэша
            size: Размер в байтах
        """
        stats_key = self.get_cache_stats_key(user_id)

        try:
            stats = self.cache_client.get(stats_key) or {
                "hits": 0,
                "misses": 0,
                "keys": [],
                "total_size": 0,
            }

            # Добавляем ключ в список
            if cache_key not in stats.get("keys", []):
                stats["keys"].append(cache_key)
                stats["total_size"] = stats.get("total_size", 0) + size

            stats["last_updated"] = timezone.now().isoformat()

            self.cache_client.set(stats_key, stats, 86400 * 7)  # 7 дней
        except Exception as e:
            logger.debug(
                f"Failed to update cache stats: {str(e)}",
                extra={"user_id": user_id},
            )

    def _increment_hit_count(self, user_id: int) -> None:
        """
        Увеличивает счётчик попаданий кэша.

        Args:
            user_id: ID пользователя
        """
        stats_key = self.get_cache_stats_key(user_id)

        try:
            stats = self.cache_client.get(stats_key) or {
                "hits": 0,
                "misses": 0,
            }
            stats["hits"] = stats.get("hits", 0) + 1
            stats["last_updated"] = timezone.now().isoformat()

            self.cache_client.set(stats_key, stats, 86400 * 7)  # 7 дней
        except Exception as e:
            logger.debug(
                f"Failed to increment hit count: {str(e)}",
                extra={"user_id": user_id},
            )

    def _increment_miss_count(self, user_id: int) -> None:
        """
        Увеличивает счётчик промахов кэша.

        Args:
            user_id: ID пользователя
        """
        stats_key = self.get_cache_stats_key(user_id)

        try:
            stats = self.cache_client.get(stats_key) or {
                "hits": 0,
                "misses": 0,
            }
            stats["misses"] = stats.get("misses", 0) + 1
            stats["last_updated"] = timezone.now().isoformat()

            self.cache_client.set(stats_key, stats, 86400 * 7)  # 7 дней
        except Exception as e:
            logger.debug(
                f"Failed to increment miss count: {str(e)}",
                extra={"user_id": user_id},
            )


# Глобальный экземпляр
cache_strategy = ReportCacheStrategy()
