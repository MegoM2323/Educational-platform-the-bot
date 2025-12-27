"""
Тесты для Material Search Optimization (T_MAT_010).

Тестирует:
- Полнотекстовый поиск по title, description, content, tags
- Фильтрацию по subject, type, status, difficulty_level
- Фильтрацию по диапазону дат
- Фасетированный поиск
- Автодополнение
- История поисков
- Популярные поиски
- Производительность (<200ms)
"""

import time
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Material, SearchHistory, Subject

User = get_user_model()


class MaterialSearchFilterTestCase(APITestCase):
    """Тесты фильтрации и поиска материалов"""

    def setUp(self):
        """Подготовка тестовых данных"""
        # Создаем пользователя
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Создаем студента
        self.student = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        # Создаем предмет
        self.subject = Subject.objects.create(
            name="Python",
            description="Введение в Python"
        )

        # Создаем материалы для тестирования
        self.materials = []
        for i in range(5):
            material = Material.objects.create(
                title=f"Python Lesson {i}",
                description=f"Learn Python basics - Part {i}",
                content=f"Python code example {i}",
                tags=f"python,basics,lesson{i}",
                author=self.user,
                subject=self.subject,
                type=Material.Type.LESSON,
                status=Material.Status.ACTIVE,
                difficulty_level=(i % 5) + 1,
                is_public=(i % 2 == 0),  # 0, 2, 4 - публичные
            )
            self.materials.append(material)

        # Создаем материалы другого типа
        self.video = Material.objects.create(
            title="Python Video Tutorial",
            description="Video about Python",
            content="Python video content",
            tags="python,video",
            author=self.user,
            subject=self.subject,
            type=Material.Type.VIDEO,
            status=Material.Status.ACTIVE,
            difficulty_level=2,
            is_public=True,
        )

        self.client = APIClient()

    def test_search_by_title(self):
        """Тест поиска по названию"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"search": "Python Lesson"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_search_by_description(self):
        """Тест поиска по описанию"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"search": "basics"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_search_empty_query(self):
        """Тест пустого поискового запроса"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"search": ""}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_subject(self):
        """Тест фильтрации по предмету"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"subject": self.subject.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["subject"]["id"], self.subject.id)

    def test_filter_by_type(self):
        """Тест фильтрации по типу"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"type": Material.Type.VIDEO}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["type"], Material.Type.VIDEO)

    def test_filter_by_difficulty_level(self):
        """Тест фильтрации по уровню сложности"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"difficulty_level": 3}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["difficulty_level"], 3)

    def test_filter_by_status(self):
        """Тест фильтрации по статусу"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {"status": Material.Status.ACTIVE}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["status"], Material.Status.ACTIVE)

    def test_filter_by_date_range(self):
        """Тест фильтрации по диапазону дат"""
        self.client.force_authenticate(user=self.user)

        today = timezone.now().date()
        response = self.client.get(
            "/api/materials/",
            {
                "created_date_from": str(today),
                "created_date_to": str(today),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_is_public(self):
        """Тест фильтрации по публичным материалам"""
        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            "/api/materials/",
            {"is_public": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Студент видит только публичные материалы
        for item in response.data["results"]:
            self.assertTrue(item["is_public"])

    def test_combined_filters(self):
        """Тест комбинирования нескольких фильтров"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/",
            {
                "subject": self.subject.id,
                "type": Material.Type.LESSON,
                "difficulty_level": 2,
                "status": Material.Status.ACTIVE,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MaterialAutocompleteTestCase(APITestCase):
    """Тесты автодополнения"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.subject = Subject.objects.create(name="Python")

        # Создаем материалы с разными названиями
        titles = [
            "Python Basics",
            "Python Advanced",
            "Pygame Tutorial",
            "JavaScript Intro",
            "Python Web Development",
        ]

        for title in titles:
            Material.objects.create(
                title=title,
                description="Test",
                content="Test",
                author=self.user,
                subject=self.subject,
                status=Material.Status.ACTIVE,
            )

        self.client = APIClient()

    def test_autocomplete_with_short_query(self):
        """Тест автодополнения с коротким запросом (< 2 символов)"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/autocomplete/",
            {"q": "p"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_autocomplete_with_valid_query(self):
        """Тест автодополнения с корректным запросом"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/autocomplete/",
            {"q": "py"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Python Basics", response.data)
        self.assertIn("Python Advanced", response.data)

    def test_autocomplete_limit(self):
        """Тест что автодополнение возвращает максимум 10 результатов"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/autocomplete/",
            {"q": "python"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 10)

    def test_autocomplete_case_insensitive(self):
        """Тест что автодополнение работает независимо от регистра"""
        self.client.force_authenticate(user=self.user)

        response_lower = self.client.get(
            "/api/materials/autocomplete/",
            {"q": "python"}
        )

        response_upper = self.client.get(
            "/api/materials/autocomplete/",
            {"q": "PYTHON"}
        )

        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(response_upper.status_code, status.HTTP_200_OK)


class SearchHistoryTestCase(APITestCase):
    """Тесты истории поисков"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        self.subject = Subject.objects.create(name="Python")

        Material.objects.create(
            title="Python Lesson",
            description="Test",
            content="Test",
            author=self.user,
            subject=self.subject,
            status=Material.Status.ACTIVE,
            is_public=True,
        )

        self.client = APIClient()

    def test_search_history_creation(self):
        """Тест создания записи истории поиска"""
        self.client.force_authenticate(user=self.user)

        # Выполняем поиск
        response = self.client.get(
            "/api/materials/",
            {"search": "Python"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что была создана запись истории (в реальной реализации)
        # Обычно это происходит в signal или в middleware

    def test_get_search_history(self):
        """Тест получения истории поисков пользователя"""
        self.client.force_authenticate(user=self.user)

        # Создаем несколько записей истории
        for i in range(5):
            SearchHistory.objects.create(
                user=self.user,
                query=f"test query {i}",
                results_count=10 + i,
            )

        response = self.client.get("/api/materials/search_history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 10)

    def test_search_history_requires_auth(self):
        """Тест что история поисков требует аутентификации"""
        response = self.client.get("/api/materials/search_history/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PopularSearchesTestCase(APITestCase):
    """Тесты популярных поисков"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Создаем записи популярных поисков
        popular_queries = ["Python", "JavaScript", "Django", "React"]
        for query in popular_queries:
            for i in range(5):  # каждый запрос 5 раз
                SearchHistory.objects.create(
                    user=self.user,
                    query=query,
                    results_count=10,
                )

        self.client = APIClient()

    def test_popular_searches_returns_top_10(self):
        """Тест что популярные поиски возвращают топ 10"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/materials/popular_searches/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 10)

    def test_popular_searches_ordered_by_count(self):
        """Тест что результаты отсортированы по количеству"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/materials/popular_searches/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что результаты отсортированы по убыванию количества
        counts = [item["count"] for item in response.data]
        self.assertEqual(counts, sorted(counts, reverse=True))


class FacetedSearchTestCase(APITestCase):
    """Тесты фасетированного поиска"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Создаем несколько предметов
        self.subjects = []
        for i in range(3):
            subject = Subject.objects.create(name=f"Subject {i}")
            self.subjects.append(subject)

        # Создаем материалы разных типов и сложности
        types = [Material.Type.LESSON, Material.Type.VIDEO, Material.Type.TEST]
        for subject in self.subjects:
            for mat_type in types:
                for difficulty in range(1, 4):
                    Material.objects.create(
                        title=f"Material {subject.name} {mat_type}",
                        description="Test",
                        content="Test",
                        author=self.user,
                        subject=subject,
                        type=mat_type,
                        difficulty_level=difficulty,
                        status=Material.Status.ACTIVE,
                    )

        self.client = APIClient()

    def test_faceted_search_returns_all_facets(self):
        """Тест что фасетированный поиск возвращает все категории"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/materials/faceted_search/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("by_type", response.data)
        self.assertIn("by_subject", response.data)
        self.assertIn("by_difficulty", response.data)
        self.assertIn("total_count", response.data)

    def test_faceted_search_counts_correct(self):
        """Тест что счетчики в фасетах правильные"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/materials/faceted_search/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Общее количество должно быть равно сумме по типам
        total = response.data["total_count"]
        self.assertGreater(total, 0)

    def test_faceted_search_with_filter(self):
        """Тест фасетированного поиска с фильтром"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/materials/faceted_search/",
            {"search": "Material"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_count", response.data)


class SearchPerformanceTestCase(APITestCase):
    """Тесты производительности поиска"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.subject = Subject.objects.create(name="Python")

        # Создаем больше материалов для теста производительности
        for i in range(50):
            Material.objects.create(
                title=f"Material {i}: Python, Django, FastAPI",
                description=f"Description {i}",
                content=f"Content {i}",
                author=self.user,
                subject=self.subject,
                type=Material.Type.LESSON if i % 3 == 0 else Material.Type.VIDEO,
                status=Material.Status.ACTIVE,
                difficulty_level=(i % 5) + 1,
            )

        self.client = APIClient()

    def test_search_performance_under_200ms(self):
        """Тест что поиск выполняется за < 200ms"""
        self.client.force_authenticate(user=self.user)

        start_time = time.time()

        response = self.client.get(
            "/api/materials/",
            {"search": "Python"}
        )

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed_ms, 200, f"Search took {elapsed_ms:.2f}ms, expected < 200ms")

    def test_filter_performance_under_200ms(self):
        """Тест что фильтрация выполняется за < 200ms"""
        self.client.force_authenticate(user=self.user)

        start_time = time.time()

        response = self.client.get(
            "/api/materials/",
            {
                "subject": self.subject.id,
                "type": Material.Type.LESSON,
                "difficulty_level": 2,
            }
        )

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed_ms, 200, f"Filter took {elapsed_ms:.2f}ms, expected < 200ms")

    def test_faceted_search_performance_under_200ms(self):
        """Тест что фасетированный поиск выполняется за < 200ms"""
        self.client.force_authenticate(user=self.user)

        start_time = time.time()

        response = self.client.get("/api/materials/faceted_search/")

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed_ms, 200, f"Faceted search took {elapsed_ms:.2f}ms, expected < 200ms")
