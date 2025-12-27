"""
Simple cache strategy tests without Django dependencies.

Тесты для многоуровневой стратегии кэширования отчётов.
"""

import hashlib
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reports.cache.strategy import ReportCacheStrategy


def test_cache_key_generation_without_filters():
    """Проверяем генерацию ключа кэша без фильтров."""
    strategy = ReportCacheStrategy()

    cache_key = strategy.get_cache_key(report_id=42, user_id=123)

    assert cache_key.startswith("report:42:123:"), f"Cache key: {cache_key}"
    assert len(cache_key) > len("report:42:123:")
    print("✓ Cache key generation without filters")


def test_cache_key_generation_with_filters():
    """Проверяем генерацию ключа кэша с фильтрами."""
    strategy = ReportCacheStrategy()
    filters = {"type": "student_progress", "status": "sent"}

    cache_key = strategy.get_cache_key(
        report_id=42, user_id=123, filters=filters
    )

    assert cache_key.startswith("report:42:123:")
    print("✓ Cache key generation with filters")


def test_cache_key_consistency():
    """Проверяем, что одинаковые фильтры дают одинаковый ключ."""
    strategy = ReportCacheStrategy()
    filters = {"type": "analytics", "student": 5}

    key1 = strategy.get_cache_key(42, 123, filters)
    key2 = strategy.get_cache_key(42, 123, filters)

    assert key1 == key2
    print("✓ Cache key consistency")


def test_cache_key_different_for_different_filters():
    """Проверяем, что разные фильтры дают разные ключи."""
    strategy = ReportCacheStrategy()
    filters1 = {"type": "analytics"}
    filters2 = {"type": "student_progress"}

    key1 = strategy.get_cache_key(42, 123, filters1)
    key2 = strategy.get_cache_key(42, 123, filters2)

    assert key1 != key2
    print("✓ Different cache keys for different filters")


def test_ttl_for_student_progress():
    """Проверяем TTL для отчёта о прогрессе студента."""
    strategy = ReportCacheStrategy()

    ttl = strategy.get_ttl("student_progress")

    assert ttl == 300  # 5 минут
    print("✓ TTL for student_progress")


def test_ttl_for_grade_distribution():
    """Проверяем TTL для отчёта о распределении оценок."""
    strategy = ReportCacheStrategy()

    ttl = strategy.get_ttl("grade_distribution")

    assert ttl == 900  # 15 минут
    print("✓ TTL for grade_distribution")


def test_ttl_for_analytics():
    """Проверяем TTL для аналитического отчёта."""
    strategy = ReportCacheStrategy()

    ttl = strategy.get_ttl("analytics")

    assert ttl == 1800  # 30 минут
    print("✓ TTL for analytics")


def test_ttl_for_custom():
    """Проверяем TTL для пользовательского отчёта."""
    strategy = ReportCacheStrategy()

    ttl = strategy.get_ttl("custom")

    assert ttl == 3600  # 1 час
    print("✓ TTL for custom")


def test_default_ttl_for_unknown_type():
    """Проверяем TTL по умолчанию для неизвестного типа."""
    strategy = ReportCacheStrategy()

    ttl = strategy.get_ttl("unknown_type")

    assert ttl == strategy.TTL_MAP["default"]
    print("✓ Default TTL for unknown type")


def test_cache_stats_key_generation():
    """Проверяем генерацию ключа статистики кэша."""
    strategy = ReportCacheStrategy()

    stats_key = strategy.get_cache_stats_key(user_id=123)

    assert stats_key == "report_cache_stats:123"
    print("✓ Cache stats key generation")


def test_etag_generation():
    """Проверяем генерацию ETag."""
    strategy = ReportCacheStrategy()
    test_data = {"progress": 50, "grade": "A"}

    # Mock the private method
    etag = strategy._generate_etag(test_data)

    assert etag is not None
    assert len(etag) == 32  # MD5 хеш 32 символа
    print("✓ ETag generation")


def test_etag_consistency():
    """Проверяем, что одинаковые данные дают одинаковый ETag."""
    strategy = ReportCacheStrategy()
    test_data = {"progress": 50, "grade": "A"}

    etag1 = strategy._generate_etag(test_data)
    etag2 = strategy._generate_etag(test_data)

    assert etag1 == etag2
    print("✓ ETag consistency")


def test_etag_different_for_different_data():
    """Проверяем, что разные данные дают разные ETag."""
    strategy = ReportCacheStrategy()
    test_data1 = {"progress": 50}
    test_data2 = {"progress": 75}

    etag1 = strategy._generate_etag(test_data1)
    etag2 = strategy._generate_etag(test_data2)

    assert etag1 != etag2
    print("✓ Different ETags for different data")


@patch('reports.cache.strategy.cache')
def test_set_report_cache_success(mock_cache):
    """Проверяем сохранение отчёта в кэш."""
    strategy = ReportCacheStrategy()
    test_data = {"progress": 50}

    success, cache_key = strategy.set_report_cache(
        report_id=42, user_id=123, data=test_data, report_type="analytics"
    )

    assert success is True
    assert "report:42:123:" in cache_key
    assert mock_cache.set.called
    print("✓ Set report cache (success)")


@patch('reports.cache.strategy.cache')
def test_get_report_cache_from_mock(mock_cache):
    """Проверяем получение отчёта из кэша."""
    strategy = ReportCacheStrategy()
    test_data = {"progress": 50}

    # Simulate cache hit
    mock_cache.get.return_value = {
        "data": test_data,
        "etag": "abc123",
        "timestamp": "2024-01-15T10:00:00Z",
    }

    hit, cached_data, etag = strategy.get_report_cache(42, 123)

    assert hit is True
    assert cached_data == test_data
    assert etag == "abc123"
    print("✓ Get report cache (hit)")


@patch('reports.cache.strategy.cache')
def test_cache_miss(mock_cache):
    """Проверяем промах при пустом кэше."""
    strategy = ReportCacheStrategy()

    mock_cache.get.return_value = None

    hit, data, etag = strategy.get_report_cache(42, 123)

    assert hit is False
    assert data is None
    assert etag is None
    print("✓ Cache miss")


@patch('reports.cache.strategy.cache')
def test_invalidate_report_cache(mock_cache):
    """Проверяем инвалидирование кэша отчёта."""
    strategy = ReportCacheStrategy()

    invalidated = strategy.invalidate_report_cache(report_id=42, user_id=123)

    assert invalidated >= 0
    assert mock_cache.delete.called
    print("✓ Invalidate report cache")


@patch('reports.cache.strategy.cache')
def test_invalidate_user_cache(mock_cache):
    """Проверяем инвалидирование кэша пользователя."""
    strategy = ReportCacheStrategy()

    invalidated = strategy.invalidate_user_cache(user_id=123)

    assert invalidated >= 0
    assert mock_cache.delete.called
    print("✓ Invalidate user cache")


@patch('reports.cache.strategy.cache')
def test_warm_cache_for_user(mock_cache):
    """Проверяем предварительную загрузку кэша."""
    strategy = ReportCacheStrategy()
    report_ids = [1, 2, 3, 4, 5]

    stats = strategy.warm_cache_for_user(
        user_id=123,
        report_ids=report_ids,
        report_type="analytics"
    )

    assert stats["total"] == 5
    assert stats["cached"] >= 0
    assert stats["failed"] >= 0
    assert stats["total"] == stats["cached"] + stats["failed"]
    print("✓ Warm cache for user")


@patch('reports.cache.strategy.cache')
def test_get_cache_stats(mock_cache):
    """Проверяем получение глобальной статистики кэша."""
    strategy = ReportCacheStrategy()

    stats = strategy.get_cache_stats()

    assert "engine" in stats
    assert "backend" in stats
    assert "ttl_map" in stats
    assert "max_size_per_user" in stats
    assert "status" in stats
    print("✓ Get cache stats")


@patch('reports.cache.strategy.cache')
def test_get_hit_rate(mock_cache):
    """Проверяем получение статистики попаданий."""
    strategy = ReportCacheStrategy()

    # Mock return value
    mock_cache.get.return_value = {
        "hits": 10,
        "misses": 5,
        "last_updated": "2024-01-15T10:00:00Z",
    }

    stats = strategy.get_hit_rate(user_id=123)

    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats
    assert "total_requests" in stats
    print("✓ Get hit rate")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("REPORT CACHE STRATEGY TESTS")
    print("="*60 + "\n")

    # Run all tests
    tests = [
        test_cache_key_generation_without_filters,
        test_cache_key_generation_with_filters,
        test_cache_key_consistency,
        test_cache_key_different_for_different_filters,
        test_ttl_for_student_progress,
        test_ttl_for_grade_distribution,
        test_ttl_for_analytics,
        test_ttl_for_custom,
        test_default_ttl_for_unknown_type,
        test_cache_stats_key_generation,
        test_etag_generation,
        test_etag_consistency,
        test_etag_different_for_different_data,
        test_set_report_cache_success,
        test_get_report_cache_from_mock,
        test_cache_miss,
        test_invalidate_report_cache,
        test_invalidate_user_cache,
        test_warm_cache_for_user,
        test_get_cache_stats,
        test_get_hit_rate,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {str(e)}")
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60 + "\n")

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
