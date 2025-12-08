"""
Tests for N+1 Query Fixes (T019)
Verify that query optimization eliminates N+1 queries
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.test.utils import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

from knowledge_graph.models import (
    KnowledgeGraph, GraphLesson, Lesson, LessonProgress,
    Element, LessonElement
)
from materials.models import Subject

User = get_user_model()


@pytest.mark.django_db
class TestN1QueryFixes:
    """Test N+1 query fixes in knowledge graph views"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Создать тестовые данные"""
        # Создать пользователей
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='test123',
            first_name='Teacher',
            last_name='Test'
        )
        self.teacher.role = 'teacher'
        self.teacher.save()

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='test123',
            first_name='Student',
            last_name='Test'
        )
        self.student.role = 'student'
        self.student.save()

        # Создать предмет
        self.subject = Subject.objects.create(
            name='Mathematics',
            description='Math subject'
        )

        # Создать граф
        self.graph = KnowledgeGraph.objects.create(
            student=self.student,
            subject=self.subject,
            created_by=self.teacher,
            is_active=True
        )

        # Создать несколько уроков
        self.lessons = []
        for i in range(10):
            lesson = Lesson.objects.create(
                title=f'Lesson {i+1}',
                description=f'Description {i+1}',
                subject=self.subject,
                created_by=self.teacher
            )
            self.lessons.append(lesson)

            # Добавить урок в граф
            graph_lesson = GraphLesson.objects.create(
                graph=self.graph,
                lesson=lesson,
                position_x=100 * i,
                position_y=100 * i,
                is_unlocked=(i == 0)  # Первый урок разблокирован
            )

            # Создать прогресс для первых 5 уроков
            if i < 5:
                LessonProgress.objects.create(
                    student=self.student,
                    graph_lesson=graph_lesson,
                    status='in_progress' if i < 4 else 'completed',
                    completion_percent=50 if i < 4 else 100,
                    total_elements=10,
                    completed_elements=5 if i < 4 else 10
                )

        self.client = APIClient()

    def test_graph_lessons_list_no_n1_queries(self):
        """
        Проверить что GET /api/knowledge-graph/{graph_id}/lessons/
        не имеет N+1 запросов
        """
        # Авторизоваться как студент
        self.client.force_authenticate(user=self.student)

        url = f'/api/knowledge-graph/{self.graph.id}/lessons/'

        # Замерить количество запросов
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)

        # Проверить успешность запроса
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['count'] == 10

        # Проверить количество запросов
        # Ожидаемые запросы:
        # 1. SAVEPOINT (transaction start)
        # 2. SELECT graph
        # 3. SELECT graph_lessons с JOIN lesson + prefetch progress
        # 4. SELECT lesson elements (prefetch)
        # 5. SELECT progress (prefetch)
        # 6. RELEASE SAVEPOINT (transaction end)
        # Итого: <= 7 запросов (вместо 1 + 10N = 11+ запросов)
        num_queries = len(context.captured_queries)
        print(f"\n[TEST] Graph lessons list queries: {num_queries}")
        for i, query in enumerate(context.captured_queries, 1):
            print(f"  {i}. {query['sql'][:100]}...")

        # CRITICAL: должно быть <= 7 запросов (без N+1)
        # До исправления: 1 + 10*N = 11+ запросов
        # После исправления: 6-7 постоянных запросов независимо от N
        assert num_queries <= 7, f"Expected <= 7 queries, got {num_queries} (N+1 issue!)"

    def test_student_detailed_progress_no_n1_queries(self):
        """
        Проверить что GET /api/knowledge-graph/{graph_id}/students/{student_id}/progress/
        не имеет N+1 запросов
        """
        # Авторизоваться как учитель
        self.client.force_authenticate(user=self.teacher)

        url = f'/api/knowledge-graph/{self.graph.id}/students/{self.student.id}/progress/'

        # Замерить количество запросов
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)

        # Проверить успешность запроса
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']['lessons']) == 10

        # Проверить количество запросов
        # Ожидаемые запросы:
        # 1. SAVEPOINT
        # 2. SELECT graph
        # 3. SELECT graph_lessons с JOIN + prefetch progress
        # 4. SELECT lesson elements (count)
        # 5. SELECT progress (prefetch)
        # 6. RELEASE SAVEPOINT
        # Итого: <= 7 запросов (вместо 1 + 10N)
        num_queries = len(context.captured_queries)
        print(f"\n[TEST] Student detailed progress queries: {num_queries}")
        for i, query in enumerate(context.captured_queries, 1):
            print(f"  {i}. {query['sql'][:100]}...")

        # CRITICAL: должно быть <= 7 запросов
        # До исправления: 1 + 10*N
        # После исправления: 6-7 постоянных запросов
        assert num_queries <= 7, f"Expected <= 7 queries, got {num_queries} (N+1 issue!)"

    def test_lesson_detail_view_no_n1_queries(self):
        """
        Проверить что GET /api/knowledge-graph/{graph_id}/students/{student_id}/lesson/{lesson_id}/
        не имеет N+1 запросов при большом количестве элементов
        """
        # Создать урок с 20 элементами
        lesson = self.lessons[0]
        for i in range(20):
            element = Element.objects.create(
                title=f'Element {i+1}',
                description=f'Description {i+1}',
                element_type='theory',
                content={'text': f'Content {i+1}'},
                created_by=self.teacher
            )
            LessonElement.objects.create(
                lesson=lesson,
                element=element,
                order=i + 1
            )

        # Обновить totals
        lesson.recalculate_totals()

        # Авторизоваться как учитель
        self.client.force_authenticate(user=self.teacher)

        graph_lesson = GraphLesson.objects.get(graph=self.graph, lesson=lesson)
        url = f'/api/knowledge-graph/{self.graph.id}/students/{self.student.id}/lesson/{lesson.id}/'

        # Замерить количество запросов
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)

        # Проверить успешность запроса
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']['elements']) == 20

        # Проверить количество запросов
        # Ожидаемые запросы:
        # 1. SAVEPOINT
        # 2. SELECT graph
        # 3. SELECT graph_lesson + lesson
        # 4. SELECT lesson_elements с JOIN element + prefetch progress
        # 5. SELECT progress (prefetch)
        # 6. RELEASE SAVEPOINT
        # Итого: <= 7 запросов (вместо 1 + 20N)
        num_queries = len(context.captured_queries)
        print(f"\n[TEST] Lesson detail queries: {num_queries}")
        for i, query in enumerate(context.captured_queries, 1):
            print(f"  {i}. {query['sql'][:100]}...")

        # CRITICAL: должно быть <= 7 запросов
        # До исправления: 1 + 20*N = 21+ запросов
        # После исправления: 6-7 постоянных запросов
        assert num_queries <= 7, f"Expected <= 7 queries, got {num_queries} (N+1 issue!)"
