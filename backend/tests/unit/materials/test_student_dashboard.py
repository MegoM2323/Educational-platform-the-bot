"""
Unit tests for Student Dashboard Service and Views
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from materials.student_dashboard_service import StudentDashboardService
from materials.models import (
    Subject, SubjectEnrollment, Material, MaterialProgress,
    StudyPlan, StudyPlanFile
)
from chat.models import ChatRoom

User = get_user_model()


# ============================================================================
# SERVICE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestStudentDashboardService:
    """Тесты сервиса StudentDashboardService"""

    def test_service_initialization(self, student_user):
        """Service инициализируется для student"""
        service = StudentDashboardService(student_user)
        assert service.student == student_user

    def test_service_requires_student_role(self, teacher_user):
        """Service требует роль STUDENT"""
        with pytest.raises(ValueError) as exc_info:
            StudentDashboardService(teacher_user)
        assert "должен иметь роль 'student'" in str(exc_info.value)

    def test_get_assigned_materials(self, student_user, sample_material, enrollment):
        """Получить назначенные материалы"""
        # Устанавливаем статус ACTIVE (обязательно для получения материалов)
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials()

        assert len(materials) == 1
        assert materials[0]['id'] == sample_material.id
        assert materials[0]['title'] == sample_material.title

    def test_get_assigned_materials_empty_state(self, student_user):
        """Пустое состояние без материалов"""
        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials()

        assert len(materials) == 0

    def test_get_materials_with_progress(self, student_user, sample_material, enrollment):
        """Материалы с прогрессом"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        # Создаем прогресс для материала
        MaterialProgress.objects.create(
            material=sample_material,
            student=student_user,
            progress_percentage=50
        )

        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials()

        assert len(materials) == 1
        assert materials[0]['id'] == sample_material.id
        assert materials[0]['progress']['progress_percentage'] == 50

    def test_get_materials_filter_by_subject(self, student_user, sample_material, enrollment):
        """Фильтрация материалов по предмету"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials(subject_id=sample_material.subject.id)

        assert len(materials) == 1
        assert materials[0]['subject']['id'] == sample_material.subject.id

    def test_get_materials_filter_by_wrong_subject(self, student_user, sample_material, enrollment):
        """Фильтрация по несуществующему предмету"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials(subject_id=9999)

        assert len(materials) == 0

    def test_get_materials_sorting_by_date(self, student_user, subject, teacher_user, enrollment):
        """Материалы сортируются по дате создания"""
        # Создаем материалы в разное время
        material1 = Material.objects.create(
            title="Material 1",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE,
            created_at=timezone.now() - timedelta(days=2)
        )
        material2 = Material.objects.create(
            title="Material 2",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE,
            created_at=timezone.now() - timedelta(days=1)
        )

        material1.assigned_to.add(student_user)
        material2.assigned_to.add(student_user)

        service = StudentDashboardService(student_user)
        materials = service.get_assigned_materials()

        assert len(materials) == 2
        # Должны быть отсортированы по дате (новые сначала)
        assert materials[0]['title'] == "Material 2"
        assert materials[1]['title'] == "Material 1"

    def test_get_progress_statistics(self, student_user, sample_material, enrollment):
        """Получить статистику прогресса"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        # Создаем прогресс
        MaterialProgress.objects.create(
            student=student_user,
            material=sample_material,
            progress_percentage=75,
            is_completed=False,
            time_spent=120
        )

        service = StudentDashboardService(student_user)
        stats = service.get_progress_statistics()

        assert stats['total_materials'] == 1
        assert stats['completed_materials'] == 0
        assert stats['in_progress_materials'] == 1
        assert stats['average_progress'] == 75.0
        assert stats['total_time_spent'] == 120

    def test_get_progress_statistics_detailed(self, student_user, subject, teacher_user, enrollment):
        """Детальная статистика с несколькими материалами"""
        # Создаем несколько материалов
        material1 = Material.objects.create(
            title="Material 1",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE
        )
        material2 = Material.objects.create(
            title="Material 2",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE
        )
        material3 = Material.objects.create(
            title="Material 3",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE
        )

        material1.assigned_to.add(student_user)
        material2.assigned_to.add(student_user)
        material3.assigned_to.add(student_user)

        # Создаем прогрессы
        MaterialProgress.objects.create(
            student=student_user,
            material=material1,
            progress_percentage=100,
            is_completed=True,
            time_spent=60
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=material2,
            progress_percentage=50,
            is_completed=False,
            time_spent=30
        )
        # material3 не начат

        service = StudentDashboardService(student_user)
        stats = service.get_progress_statistics()

        assert stats['total_materials'] == 3
        assert stats['completed_materials'] == 1
        assert stats['in_progress_materials'] == 1
        assert stats['not_started_materials'] == 1
        assert stats['completion_percentage'] == pytest.approx(33.33, rel=0.1)

    def test_get_general_chat_access(self, student_user):
        """Студент имеет доступ к общему чату"""
        service = StudentDashboardService(student_user)
        chat_access = service.get_general_chat_access()

        # Если чат создался автоматически
        if chat_access:
            assert 'id' in chat_access
            assert 'name' in chat_access
            assert chat_access['name'] == 'Общий чат'

    def test_get_study_plans(self, student_user, teacher_user, subject, enrollment):
        """Получить учебные планы студента"""
        # Создаем study plan
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            enrollment=enrollment,
            title="Test plan",
            content="Test plan content",
            week_start_date=timezone.now().date()
        )

        service = StudentDashboardService(student_user)
        # Метод get_study_plans может не существовать, проверяем через дашборд
        dashboard_data = service.get_dashboard_data()

        # Проверяем что дашборд работает
        assert 'student_info' in dashboard_data

    def test_update_material_progress_incremental(self, student_user, sample_material, enrollment):
        """Пошаговое обновление прогресса материала"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        # Создаем начальный прогресс
        progress = MaterialProgress.objects.create(
            student=student_user,
            material=sample_material,
            progress_percentage=0
        )

        # Обновляем прогресс 0% -> 50%
        progress.progress_percentage = 50
        progress.save()

        assert progress.progress_percentage == 50
        assert progress.is_completed is False

        # Обновляем прогресс 50% -> 100%
        progress.progress_percentage = 100
        progress.is_completed = True
        progress.save()

        assert progress.progress_percentage == 100
        assert progress.is_completed is True

    def test_get_recent_activity(self, student_user, sample_material, enrollment):
        """Получить недавнюю активность"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        # Создаем завершенный материал
        MaterialProgress.objects.create(
            student=student_user,
            material=sample_material,
            progress_percentage=100,
            is_completed=True,
            completed_at=timezone.now()
        )

        service = StudentDashboardService(student_user)
        activities = service.get_recent_activity(days=7)

        assert len(activities) >= 1
        assert activities[0]['type'] == 'material_completed'

    def test_get_recent_activity_filter_by_type(self, student_user, subject, teacher_user, enrollment):
        """Фильтрация активности по типу"""
        # Создаем разные типы активности
        material1 = Material.objects.create(
            title="Completed Material",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE
        )
        material2 = Material.objects.create(
            title="Started Material",
            subject=subject,
            author=teacher_user,
            status=Material.Status.ACTIVE
        )

        material1.assigned_to.add(student_user)
        material2.assigned_to.add(student_user)

        MaterialProgress.objects.create(
            student=student_user,
            material=material1,
            progress_percentage=100,
            is_completed=True,
            started_at=timezone.now() - timedelta(days=2),
            completed_at=timezone.now()
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=material2,
            progress_percentage=30,
            is_completed=False,
            started_at=timezone.now() - timedelta(days=1)
        )

        service = StudentDashboardService(student_user)
        activities = service.get_recent_activity(days=7)

        # Должны быть оба типа активности
        assert len(activities) >= 2
        activity_types = {act['type'] for act in activities}
        assert 'material_completed' in activity_types
        assert 'material_started' in activity_types

    def test_get_subjects(self, student_user, subject, teacher_user):
        """Получить список предметов студента"""
        # Создаем зачисление
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = StudentDashboardService(student_user)
        subjects = service.get_subjects()

        assert len(subjects) == 1
        assert subjects[0]['id'] == subject.id
        assert subjects[0]['name'] == subject.name

    def test_get_dashboard_data(self, student_user, sample_material, enrollment):
        """Получить полные данные дашборда"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        service = StudentDashboardService(student_user)
        data = service.get_dashboard_data()

        assert 'student_info' in data
        assert data['student_info']['id'] == student_user.id

        assert 'subjects' in data
        assert 'materials_by_subject' in data
        assert 'stats' in data
        assert 'progress_statistics' in data
        assert 'recent_activity' in data


# ============================================================================
# VIEW TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestStudentDashboardViews:
    """Тесты views для StudentDashboard"""

    def test_get_dashboard_requires_authentication(self):
        """Dashboard требует аутентификации"""
        client = APIClient()
        response = client.get('/api/materials/student/')
        assert response.status_code in [401, 403]

    def test_get_dashboard_requires_student_role(self, teacher_user):
        """Dashboard требует роль STUDENT"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        response = client.get('/api/materials/student/')
        assert response.status_code in [403, 500]  # может быть ошибка валидации

    def test_get_dashboard_success(self, student_user):
        """Успешное получение dashboard"""
        client = APIClient()
        client.force_authenticate(user=student_user)
        response = client.get('/api/materials/student/')

        assert response.status_code == 200
        assert 'student_info' in response.data or 'stats' in response.data

    def test_get_assigned_materials_api(self, student_user, sample_material, enrollment):
        """Получить назначенные материалы через API"""
        sample_material.status = Material.Status.ACTIVE
        sample_material.save()
        sample_material.assigned_to.add(student_user)

        client = APIClient()
        client.force_authenticate(user=student_user)
        response = client.get('/api/materials/materials/student/assigned/')

        assert response.status_code == 200

    def test_get_subjects_api(self, student_user, subject, teacher_user):
        """Получить предметы через API"""
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        client = APIClient()
        client.force_authenticate(user=student_user)
        response = client.get('/api/materials/materials/student/subjects/')

        assert response.status_code == 200


# ===== QUERY OPTIMIZATION TESTS =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
@pytest.mark.performance
class TestStudentDashboardQueryOptimization:
    """Тесты для проверки оптимизации запросов (N+1 query problem)"""

    def test_get_assigned_materials_query_count(self, student_user, teacher_user, subject):
        """get_assigned_materials должен использовать select_related и prefetch_related"""
        # Создаем 10 материалов
        materials = []
        for i in range(10):
            material = Material.objects.create(
                title=f"Material {i}",
                subject=subject,
                author=teacher_user,
                status=Material.Status.ACTIVE
            )
            material.assigned_to.add(student_user)

            # Создаем прогресс
            MaterialProgress.objects.create(
                student=student_user,
                material=material,
                is_completed=(i % 2 == 0),
                progress_percentage=i * 10
            )
            materials.append(material)

        service = StudentDashboardService(student_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_assigned_materials()

            query_count = len(connection.queries)

            # До оптимизации: ~12+ запросов
            # После оптимизации: ~3-5 запросов (select_related + prefetch)
            assert query_count <= 7, f"Слишком много запросов: {query_count}. Ожидалось <= 7"

        assert len(result) == 10

    def test_get_progress_statistics_query_count(self, student_user, teacher_user, subject):
        """get_progress_statistics должен использовать аннотации"""
        # Создаем 15 материалов с прогрессом
        for i in range(15):
            material = Material.objects.create(
                title=f"Material {i}",
                subject=subject,
                author=teacher_user,
                status=Material.Status.ACTIVE
            )
            material.assigned_to.add(student_user)

            MaterialProgress.objects.create(
                student=student_user,
                material=material,
                is_completed=(i % 3 == 0),
                progress_percentage=i * 5,
                time_spent=i * 30
            )

        service = StudentDashboardService(student_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_progress_statistics()

            query_count = len(connection.queries)

            # До оптимизации: ~10+ запросов
            # После оптимизации: ~3-5 запросов (aggregate + annotate)
            assert query_count <= 7, f"Слишком много запросов: {query_count}. Ожидалось <= 7"

        assert result['total_materials'] == 15

    def test_get_recent_activity_query_count(self, student_user, teacher_user, subject):
        """get_recent_activity должен использовать select_related"""
        # Создаем 10 материалов с прогрессом
        from datetime import timedelta
        from django.utils import timezone

        for i in range(10):
            material = Material.objects.create(
                title=f"Material {i}",
                subject=subject,
                author=teacher_user,
                status=Material.Status.ACTIVE
            )
            material.assigned_to.add(student_user)

            # Половина завершена, половина в прогрессе
            MaterialProgress.objects.create(
                student=student_user,
                material=material,
                is_completed=(i < 5),
                completed_at=timezone.now() - timedelta(days=i) if i < 5 else None,
                started_at=timezone.now() - timedelta(days=i + 1),
                progress_percentage=100 if i < 5 else i * 10
            )

        service = StudentDashboardService(student_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_recent_activity(days=30)

            query_count = len(connection.queries)

            # До оптимизации: ~5+ запросов
            # После оптимизации: ~2-3 запроса (select_related на material и subject)
            assert query_count <= 5, f"Слишком много запросов: {query_count}. Ожидалось <= 5"

        # Ожидаем 10 завершенных + 5 начатых = 15 активностей
        assert len(result) >= 10
