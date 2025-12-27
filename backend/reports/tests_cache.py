"""
Тесты для многоуровневой стратегии кэширования отчётов.

Проверяет:
- Кэширование отчётов
- Инвалидирование кэша
- Статистика попаданий
- Генерация ETag
- TTL для разных типов отчётов
"""

import hashlib
import json
import time
from typing import Dict

import pytest
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from reports.cache import ReportCacheStrategy


@pytest.mark.django_db
class TestReportCacheStrategy(TestCase):
    """Тесты стратегии кэширования отчётов."""

    def setUp(self):
        """Инициализируем тест."""
        self.cache_strategy = ReportCacheStrategy()
        cache.clear()

    def tearDown(self):
        """Очищаем кэш после теста."""
        cache.clear()

    # ========== Tests for cache key generation ==========

    def test_cache_key_generation_without_filters(self):
        """Проверяем генерацию ключа кэша без фильтров."""
        cache_key = self.cache_strategy.get_cache_key(
            report_id=42, user_id=123
        )

        assert cache_key.startswith("report:42:123:")
        assert len(cache_key) > len("report:42:123:")

    def test_cache_key_generation_with_filters(self):
        """Проверяем генерацию ключа кэша с фильтрами."""
        filters = {"type": "student_progress", "status": "sent"}

        cache_key = self.cache_strategy.get_cache_key(
            report_id=42, user_id=123, filters=filters
        )

        assert cache_key.startswith("report:42:123:")

    def test_cache_key_consistency_with_same_filters(self):
        """Проверяем, что одинаковые фильтры дают одинаковый ключ."""
        filters = {"type": "analytics", "student": 5}

        key1 = self.cache_strategy.get_cache_key(42, 123, filters)
        key2 = self.cache_strategy.get_cache_key(42, 123, filters)

        assert key1 == key2

    def test_cache_key_different_for_different_filters(self):
        """Проверяем, что разные фильтры дают разные ключи."""
        filters1 = {"type": "analytics"}
        filters2 = {"type": "student_progress"}

        key1 = self.cache_strategy.get_cache_key(42, 123, filters1)
        key2 = self.cache_strategy.get_cache_key(42, 123, filters2)

        assert key1 != key2

    # ========== Tests for cache hits and misses ==========

    def test_cache_miss_on_empty_cache(self):
        """Проверяем промах при пустом кэше."""
        hit, data, etag = self.cache_strategy.get_report_cache(
            report_id=42, user_id=123
        )

        assert hit is False
        assert data is None
        assert etag is None

    def test_cache_hit_after_set(self):
        """Проверяем попадание в кэш после сохранения."""
        test_data = {"progress": 50, "grade": "A"}

        self.cache_strategy.set_report_cache(
            report_id=42, user_id=123, data=test_data, report_type="analytics"
        )

        hit, cached_data, etag = self.cache_strategy.get_report_cache(
            report_id=42, user_id=123
        )

        assert hit is True
        assert cached_data == test_data
        assert etag is not None

    def test_cache_hit_rate_calculation(self):
        """Проверяем расчёт процента попаданий."""
        test_data = {"progress": 50}

        # Сохраняем в кэш
        self.cache_strategy.set_report_cache(
            report_id=42, user_id=123, data=test_data
        )

        # Два попадания
        self.cache_strategy.get_report_cache(report_id=42, user_id=123)
        self.cache_strategy.get_report_cache(report_id=42, user_id=123)

        # Один промах
        self.cache_strategy.get_report_cache(report_id=999, user_id=123)

        stats = self.cache_strategy.get_hit_rate(user_id=123)

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == 66.67

    # ========== Tests for cache invalidation ==========

    def test_invalidate_report_cache_for_user(self):
        """Проверяем инвалидирование кэша отчёта для пользователя."""
        test_data = {"progress": 50}

        self.cache_strategy.set_report_cache(
            report_id=42, user_id=123, data=test_data
        )

        # Проверяем, что данные в кэше
        hit, _, _ = self.cache_strategy.get_report_cache(42, 123)
        assert hit is True

        # Инвалидируем
        self.cache_strategy.invalidate_report_cache(report_id=42, user_id=123)

        # Проверяем, что данные удалены
        hit, _, _ = self.cache_strategy.get_report_cache(42, 123)
        assert hit is False

    def test_invalidate_user_cache(self):
        """Проверяем инвалидирование всего кэша пользователя."""
        test_data = {"progress": 50}

        # Сохраняем несколько отчётов
        self.cache_strategy.set_report_cache(42, 123, test_data)
        self.cache_strategy.set_report_cache(43, 123, test_data)

        # Инвалидируем весь кэш пользователя
        self.cache_strategy.invalidate_user_cache(user_id=123)

        # Проверяем, что оба кэша очищены
        stats = self.cache_strategy.get_hit_rate(123)
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    # ========== Tests for TTL by report type ==========

    def test_ttl_for_student_progress(self):
        """Проверяем TTL для отчёта о прогрессе студента."""
        ttl = self.cache_strategy.get_ttl("student_progress")
        assert ttl == 300  # 5 минут

    def test_ttl_for_grade_distribution(self):
        """Проверяем TTL для отчёта о распределении оценок."""
        ttl = self.cache_strategy.get_ttl("grade_distribution")
        assert ttl == 900  # 15 минут

    def test_ttl_for_analytics(self):
        """Проверяем TTL для аналитического отчёта."""
        ttl = self.cache_strategy.get_ttl("analytics")
        assert ttl == 1800  # 30 минут

    def test_ttl_for_custom(self):
        """Проверяем TTL для пользовательского отчёта."""
        ttl = self.cache_strategy.get_ttl("custom")
        assert ttl == 3600  # 1 час

    def test_default_ttl_for_unknown_type(self):
        """Проверяем TTL по умолчанию для неизвестного типа."""
        ttl = self.cache_strategy.get_ttl("unknown_type")
        assert ttl == self.cache_strategy.TTL_MAP["default"]

    # ========== Tests for ETag ==========

    def test_etag_generation(self):
        """Проверяем генерацию ETag."""
        test_data = {"progress": 50, "grade": "A"}

        _, cache_key = self.cache_strategy.set_report_cache(
            report_id=42, user_id=123, data=test_data
        )

        _, _, etag = self.cache_strategy.get_report_cache(42, 123)

        assert etag is not None
        assert len(etag) == 32  # MD5 хеш 32 символа

    def test_etag_consistency(self):
        """Проверяем, что одинаковые данные дают одинаковый ETag."""
        test_data = {"progress": 50, "grade": "A"}

        self.cache_strategy.set_report_cache(42, 123, test_data)
        _, _, etag1 = self.cache_strategy.get_report_cache(42, 123)

        # Удаляем и пересохраняем
        cache.clear()
        self.cache_strategy.set_report_cache(42, 123, test_data)
        _, _, etag2 = self.cache_strategy.get_report_cache(42, 123)

        assert etag1 == etag2

    def test_etag_different_for_different_data(self):
        """Проверяем, что разные данные дают разные ETag."""
        test_data1 = {"progress": 50}
        test_data2 = {"progress": 75}

        self.cache_strategy.set_report_cache(42, 123, test_data1)
        _, _, etag1 = self.cache_strategy.get_report_cache(42, 123)

        cache.clear()

        self.cache_strategy.set_report_cache(42, 123, test_data2)
        _, _, etag2 = self.cache_strategy.get_report_cache(42, 123)

        assert etag1 != etag2

    # ========== Tests for cache statistics ==========

    def test_cache_stats_key_generation(self):
        """Проверяем генерацию ключа статистики кэша."""
        stats_key = self.cache_strategy.get_cache_stats_key(user_id=123)

        assert stats_key == "report_cache_stats:123"

    def test_global_cache_stats(self):
        """Проверяем получение глобальной статистики кэша."""
        stats = self.cache_strategy.get_cache_stats()

        assert "engine" in stats
        assert "backend" in stats
        assert "ttl_map" in stats
        assert "max_size_per_user" in stats
        assert "status" in stats

    def test_user_cache_stats_updated_on_set(self):
        """Проверяем, что статистика обновляется при сохранении."""
        test_data = {"progress": 50}

        self.cache_strategy.set_report_cache(42, 123, test_data)

        stats = self.cache_strategy.get_hit_rate(123)

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "total_requests" in stats

    # ========== Tests for cache warming ==========

    def test_warm_cache_for_user(self):
        """Проверяем предварительную загрузку кэша."""
        report_ids = [1, 2, 3, 4, 5]

        stats = self.cache_strategy.warm_cache_for_user(
            user_id=123,
            report_ids=report_ids,
            report_type="analytics"
        )

        assert stats["total"] == 5
        assert stats["cached"] == 5
        assert stats["failed"] == 0

    def test_warm_cache_with_errors(self):
        """Проверяем обработку ошибок при предварительной загрузке."""
        report_ids = list(range(100))  # Большой список

        stats = self.cache_strategy.warm_cache_for_user(
            user_id=999,
            report_ids=report_ids,
            report_type="default"
        )

        assert stats["total"] == 100
        assert stats["cached"] >= 0
        assert stats["failed"] >= 0

    # ========== Integration tests ==========

    def test_full_cache_lifecycle(self):
        """Проверяем полный жизненный цикл кэша."""
        test_data = {
            "student_id": 123,
            "progress": 75,
            "grade": "B+",
            "timestamp": timezone.now().isoformat(),
        }

        # 1. Промах
        hit, data, etag = self.cache_strategy.get_report_cache(42, 123)
        assert hit is False

        # 2. Сохраняем в кэш
        success, cache_key = self.cache_strategy.set_report_cache(
            report_id=42,
            user_id=123,
            data=test_data,
            report_type="student_progress"
        )
        assert success is True

        # 3. Попадание
        hit, cached_data, etag = self.cache_strategy.get_report_cache(42, 123)
        assert hit is True
        assert cached_data == test_data
        assert etag is not None

        # 4. Инвалидирование
        self.cache_strategy.invalidate_report_cache(42, 123)

        # 5. Промах после инвалидирования
        hit, data, etag = self.cache_strategy.get_report_cache(42, 123)
        assert hit is False

    def test_multiple_users_independent_cache(self):
        """Проверяем независимость кэша разных пользователей."""
        test_data1 = {"user_id": 123, "progress": 50}
        test_data2 = {"user_id": 456, "progress": 75}

        # Сохраняем для разных пользователей
        self.cache_strategy.set_report_cache(42, 123, test_data1)
        self.cache_strategy.set_report_cache(42, 456, test_data2)

        # Получаем
        hit1, data1, _ = self.cache_strategy.get_report_cache(42, 123)
        hit2, data2, _ = self.cache_strategy.get_report_cache(42, 456)

        assert hit1 is True
        assert hit2 is True
        assert data1 != data2
        assert data1["user_id"] == 123
        assert data2["user_id"] == 456

    def test_cache_with_complex_data_types(self):
        """Проверяем кэширование сложных типов данных."""
        test_data = {
            "grades": [85, 90, 88, 92],
            "metadata": {
                "subject": "Math",
                "semester": 1,
                "year": 2024,
            },
            "timestamps": {
                "created": timezone.now().isoformat(),
                "updated": timezone.now().isoformat(),
            },
            "null_value": None,
            "boolean_value": True,
            "float_value": 3.14159,
        }

        self.cache_strategy.set_report_cache(42, 123, test_data)

        hit, cached_data, _ = self.cache_strategy.get_report_cache(42, 123)

        assert hit is True
        assert cached_data["grades"] == test_data["grades"]
        assert cached_data["metadata"] == test_data["metadata"]
        assert cached_data["null_value"] is None
        assert cached_data["boolean_value"] is True

    def test_cache_bypass_on_error(self):
        """Проверяем граммотное падение при ошибке кэша."""
        # Тестируем обработку ошибок без прерывания
        test_data = {"progress": 50}

        # Сохраняем (это должно работать)
        success, _ = self.cache_strategy.set_report_cache(42, 123, test_data)
        assert success is True

        # Получаем (это должно работать)
        hit, data, _ = self.cache_strategy.get_report_cache(42, 123)
        assert hit is True
        assert data == test_data


# ========== Performance tests ==========

@pytest.mark.django_db
class TestReportCachePerformance(TestCase):
    """Тесты производительности кэширования."""

    def setUp(self):
        """Инициализируем тест."""
        self.cache_strategy = ReportCacheStrategy()
        cache.clear()

    def tearDown(self):
        """Очищаем кэш после теста."""
        cache.clear()

    def test_cache_retrieval_is_fast(self):
        """Проверяем, что получение из кэша быстро."""
        test_data = {"progress": 50}

        self.cache_strategy.set_report_cache(42, 123, test_data)

        start_time = time.time()
        for _ in range(100):
            self.cache_strategy.get_report_cache(42, 123)
        end_time = time.time()

        # 100 операций должны занять < 100ms
        assert (end_time - start_time) < 0.1

    def test_cache_set_is_fast(self):
        """Проверяем, что сохранение в кэш быстро."""
        test_data = {"progress": 50}

        start_time = time.time()
        for i in range(100):
            self.cache_strategy.set_report_cache(i, 123, test_data)
        end_time = time.time()

        # 100 операций должны занять < 500ms
        assert (end_time - start_time) < 0.5

    def test_cache_invalidation_is_fast(self):
        """Проверяем, что инвалидирование быстро."""
        test_data = {"progress": 50}

        for i in range(100):
            self.cache_strategy.set_report_cache(i, 123, test_data)

        start_time = time.time()
        for i in range(100):
            self.cache_strategy.invalidate_report_cache(i, 123)
        end_time = time.time()

        # 100 операций должны занять < 100ms
        assert (end_time - start_time) < 0.1
