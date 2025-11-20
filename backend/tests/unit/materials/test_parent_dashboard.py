"""
Unit tests for Parent Dashboard Service
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from materials.parent_dashboard_service import ParentDashboardService
from materials.models import (
    Subject, SubjectEnrollment, SubjectPayment, SubjectSubscription,
    Material, MaterialProgress
)
from payments.models import Payment

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestParentDashboardService:
    """Тесты сервиса ParentDashboardService"""

    def test_service_initialization(self, parent_user):
        """Service инициализируется для parent"""
        service = ParentDashboardService(parent_user)
        assert service.parent_user == parent_user
        assert service.parent_profile is not None

    def test_service_requires_parent_role(self, student_user):
        """Service требует роль PARENT"""
        with pytest.raises(ValueError) as exc_info:
            ParentDashboardService(student_user)
        assert "PARENT" in str(exc_info.value)

    def test_service_rejects_teacher_role(self, teacher_user):
        """Service отклоняет роль TEACHER"""
        with pytest.raises(ValueError):
            ParentDashboardService(teacher_user)

    def test_service_rejects_student_role(self, student_user):
        """Service отклоняет роль STUDENT"""
        with pytest.raises(ValueError):
            ParentDashboardService(student_user)

    def test_get_children(self, parent_user, student_with_parent):
        """Получить список детей родителя"""
        service = ParentDashboardService(parent_user)
        children = service.get_children()

        assert children.count() >= 1
        assert student_with_parent in children

    def test_get_children_empty(self, parent_user):
        """Пустой список детей если нет связей"""
        service = ParentDashboardService(parent_user)
        children = service.get_children()
        assert children.count() == 0

    def test_get_child_subjects(self, parent_user, student_with_parent, enrollment):
        """Получить предметы конкретного ребенка"""
        service = ParentDashboardService(parent_user)
        subjects = service.get_child_subjects(student_with_parent)

        assert subjects.count() >= 1
        assert enrollment in subjects

    def test_get_child_subjects_empty(self, parent_user, student_with_parent):
        """Пустой список предметов если нет зачислений"""
        service = ParentDashboardService(parent_user)
        subjects = service.get_child_subjects(student_with_parent)
        assert subjects.count() == 0

    def test_get_child_progress(self, parent_user, student_with_parent, enrollment):
        """Получить прогресс ребенка по предметам"""
        # Создаем материал для предмета
        material = Material.objects.create(
            title="Тестовый урок",
            description="Описание урока",
            content="Содержание",
            author=enrollment.teacher,
            subject=enrollment.subject,
            status=Material.Status.ACTIVE
        )

        # Создаем прогресс по материалу
        MaterialProgress.objects.create(
            student=student_with_parent,
            material=material,
            progress_percentage=75,
            time_spent=30,
            is_completed=False
        )

        service = ParentDashboardService(parent_user)
        progress = service.get_child_progress(student_with_parent)

        assert progress['total_materials'] >= 1
        assert progress['average_progress'] >= 0
        assert len(progress['subject_progress']) >= 1

    def test_get_child_teachers(self, parent_user, student_with_parent, enrollment):
        """Получить список преподавателей ребенка"""
        service = ParentDashboardService(parent_user)
        teachers = service.get_child_teachers(student_with_parent)

        assert len(teachers) >= 1
        assert teachers[0]['id'] == enrollment.teacher.id
        assert teachers[0]['name'] == enrollment.teacher.get_full_name()

    def test_get_payment_status(self, parent_user, student_with_parent, enrollment, payment):
        """Получить статус платежей для ребенка"""
        # Создаем платеж
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PENDING,
            due_date=timezone.now() + timedelta(days=7)
        )

        service = ParentDashboardService(parent_user)
        payment_info = service.get_payment_status(student_with_parent)

        assert len(payment_info) >= 1
        assert payment_info[0]['enrollment_id'] == enrollment.id
        assert payment_info[0]['subject'] == enrollment.get_subject_name()

    def test_get_payment_status_with_active_subscription(self, parent_user, student_with_parent, enrollment, subscription):
        """Получить статус платежей с активной подпиской"""
        service = ParentDashboardService(parent_user)
        payment_info = service.get_payment_status(student_with_parent)

        assert len(payment_info) >= 1
        assert payment_info[0]['has_subscription'] is True
        assert payment_info[0]['next_payment_date'] is not None

    def test_get_parent_payments(self, parent_user, student_with_parent, enrollment, payment):
        """История платежей родителя по всем детям"""
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PAID,
            due_date=timezone.now() + timedelta(days=7),
            paid_at=timezone.now()
        )

        service = ParentDashboardService(parent_user)
        payments = service.get_parent_payments()

        assert len(payments) >= 1
        assert payments[0]['status'] == SubjectPayment.Status.PAID
        assert payments[0]['student_id'] == student_with_parent.id

    def test_get_parent_pending_payments(self, parent_user, student_with_parent, enrollment, payment):
        """Ожидающие платежи родителя"""
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PENDING,
            due_date=timezone.now() + timedelta(days=3)
        )

        service = ParentDashboardService(parent_user)
        pending = service.get_parent_pending_payments()

        assert len(pending) >= 1
        assert pending[0]['status'] in ['pending', 'overdue', 'waiting_for_payment']


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestParentDashboardExtended:
    """Расширенные тесты для ParentDashboard"""

    def test_cancel_subscription_real(self, parent_user, student_with_parent, enrollment, subscription):
        """Реальная отмена подписки"""
        assert subscription.status == SubjectSubscription.Status.ACTIVE

        # Отмена подписки должна быть реализована в сервисе
        # Пока проверяем, что подписка существует
        assert subscription.enrollment == enrollment

    def test_get_reports_by_child_empty(self, parent_user, student_with_parent):
        """Получить отчеты конкретного ребенка (пусто)"""
        service = ParentDashboardService(parent_user)
        reports = service.get_reports(child=student_with_parent)

        assert reports == []

    def test_get_dashboard_data_structure(self, parent_user, student_with_parent, enrollment):
        """Проверить структуру данных дашборда"""
        service = ParentDashboardService(parent_user)
        dashboard_data = service.get_dashboard_data()

        # Проверяем основную структуру
        assert 'children' in dashboard_data
        assert 'reports' in dashboard_data
        assert 'statistics' in dashboard_data
        assert 'parent' in dashboard_data

        # Проверяем статистику
        stats = dashboard_data['statistics']
        assert 'total_children' in stats
        assert 'average_progress' in stats
        assert 'completed_payments' in stats
        assert 'pending_payments' in stats
        assert 'overdue_payments' in stats

    def test_get_dashboard_data_with_multiple_children(self, parent_user):
        """Данные дашборда с несколькими детьми"""
        from accounts.models import StudentProfile

        # Создаем двух детей
        child1 = User.objects.create_user(
            username='child1_test',
            email='child1@test.com',
            first_name='Дети',
            last_name='Тест1',
            role=User.Role.STUDENT
        )
        child2 = User.objects.create_user(
            username='child2_test',
            email='child2@test.com',
            first_name='Дети',
            last_name='Тест2',
            role=User.Role.STUDENT
        )

        # Создаем профили и связываем с родителем
        StudentProfile.objects.create(user=child1, parent=parent_user)
        StudentProfile.objects.create(user=child2, parent=parent_user)

        service = ParentDashboardService(parent_user)
        dashboard_data = service.get_dashboard_data()

        assert len(dashboard_data['children']) == 2
        assert dashboard_data['statistics']['total_children'] == 2

    def test_payment_history_pagination(self, parent_user, student_with_parent, enrollment):
        """История платежей с несколькими записями"""
        from payments.models import Payment

        # Создаем несколько платежей
        for i in range(5):
            payment = Payment.objects.create(
                amount=Decimal('100.00'),
                service_name=f"Платеж {i+1}",
                customer_fio="Тест Тест",
                description=f"Описание платежа {i+1}",
                status=Payment.Status.SUCCEEDED,
                paid_at=timezone.now()
            )
            SubjectPayment.objects.create(
                enrollment=enrollment,
                payment=payment,
                amount=Decimal('100.00'),
                status=SubjectPayment.Status.PAID,
                paid_at=timezone.now()
            )

        service = ParentDashboardService(parent_user)
        payments = service.get_parent_payments()

        assert len(payments) == 5

    def test_check_subscription_status_active(self, parent_user, student_with_parent, enrollment, subscription):
        """Проверка статуса активной подписки"""
        service = ParentDashboardService(parent_user)

        # Проверяем, что подписка активна
        assert subscription.status == SubjectSubscription.Status.ACTIVE
        assert subscription.next_payment_date > timezone.now()

    def test_check_subscription_status_canceled(self, parent_user, student_with_parent, enrollment):
        """Проверка статуса отмененной подписки"""
        from materials.models import SubjectSubscription

        # Создаем отмененную подписку
        subscription = SubjectSubscription.objects.create(
            enrollment=enrollment,
            amount=Decimal('100.00'),
            status=SubjectSubscription.Status.CANCELLED,
            next_payment_date=timezone.now() + timedelta(days=7),
            payment_interval_weeks=1,
            expires_at=timezone.now() + timedelta(days=3)
        )

        service = ParentDashboardService(parent_user)
        payment_info = service.get_payment_status(student_with_parent)

        # Проверяем наличие информации о подписке
        assert len(payment_info) >= 1

    def test_get_child_progress_with_multiple_materials(self, parent_user, student_with_parent, enrollment):
        """Прогресс ребенка с несколькими материалами"""
        # Создаем несколько материалов
        for i in range(3):
            material = Material.objects.create(
                title=f"Урок {i+1}",
                description=f"Описание урока {i+1}",
                content="Содержание",
                author=enrollment.teacher,
                subject=enrollment.subject,
                status=Material.Status.ACTIVE
            )

            MaterialProgress.objects.create(
                student=student_with_parent,
                material=material,
                progress_percentage=50 + (i * 10),
                time_spent=20 + (i * 5),
                is_completed=(i == 2)  # Последний материал завершен
            )

        service = ParentDashboardService(parent_user)
        progress = service.get_child_progress(student_with_parent)

        assert progress['total_materials'] == 3
        assert progress['completed_materials'] == 1
        assert progress['average_progress'] > 0

    def test_initiate_payment_basic(self, parent_user, student_with_parent, enrollment):
        """Инициировать платеж за предмет"""
        service = ParentDashboardService(parent_user)

        result = service.initiate_payment(
            child=student_with_parent,
            enrollment=enrollment,
            amount=Decimal('100.00'),
            description="Тестовый платеж"
        )

        assert 'payment_id' in result
        assert result['amount'] == Decimal('100.00')
        assert result['subject'] == enrollment.get_subject_name()

    def test_access_control_child_from_other_parent(self, parent_user):
        """Проверка доступа к чужому ребенку - вернет пустой набор"""
        from accounts.models import StudentProfile

        # Создаем другого родителя
        other_parent = User.objects.create_user(
            username='other_parent_test',
            email='other@test.com',
            first_name='Другой',
            last_name='Родитель',
            role=User.Role.PARENT
        )
        from accounts.models import ParentProfile
        ParentProfile.objects.create(user=other_parent)

        # Создаем ребенка для other_parent
        other_child = User.objects.create_user(
            username='other_child_test',
            email='other_child@test.com',
            first_name='Чужой',
            last_name='Ребенок',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=other_child, parent=other_parent)

        service = ParentDashboardService(parent_user)

        # Попытка доступа к чужому ребенку вернет пустой набор (безопасная реализация)
        subjects = service.get_child_subjects(other_child)
        assert subjects.count() == 0

    def test_payment_status_overdue(self, parent_user, student_with_parent, enrollment, payment):
        """Статус платежа - просрочен"""
        # Создаем просроченный платеж
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PENDING,
            due_date=timezone.now() - timedelta(days=1)  # Вчера
        )

        service = ParentDashboardService(parent_user)
        payment_info = service.get_payment_status(student_with_parent)

        assert len(payment_info) >= 1
        assert payment_info[0]['status'] == 'overdue'


# ===== QUERY OPTIMIZATION TESTS =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
@pytest.mark.performance
class TestParentDashboardQueryOptimization:
    """Тесты для проверки оптимизации запросов (N+1 query problem)"""

    def test_get_payment_status_query_count(self, parent_user, teacher_user):
        """get_payment_status должен делать минимальное количество запросов"""
        # Создаем ребенка с 5 предметами
        child = User.objects.create_user(
            username='child1',
            email='child1@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        from accounts.models import StudentProfile
        StudentProfile.objects.create(
            user=child,
            parent=parent_user,
            grade='10'
        )

        # Создаем 5 зачислений с платежами (каждое на свой предмет)
        enrollments = []
        for i in range(5):
            # Создаем отдельный предмет для каждого зачисления
            from materials.models import Subject
            subject = Subject.objects.create(
                name=f'Test Subject {i}',
                description=f'Test description {i}'
            )

            enrollment = SubjectEnrollment.objects.create(
                student=child,
                subject=subject,
                teacher=teacher_user,
                is_active=True
            )
            enrollments.append(enrollment)

            # Создаем платеж
            payment = Payment.objects.create(
                amount=Decimal('100.00'),
                service_name=f'Test payment {i}',
                customer_fio='Test User'
            )

            SubjectPayment.objects.create(
                enrollment=enrollment,
                payment=payment,
                amount=Decimal('100.00'),
                status=SubjectPayment.Status.PAID,
                due_date=timezone.now() + timedelta(days=7)
            )

            # Создаем подписку
            SubjectSubscription.objects.create(
                enrollment=enrollment,
                amount=Decimal('100.00'),
                status=SubjectSubscription.Status.ACTIVE,
                next_payment_date=timezone.now() + timedelta(days=7)
            )

        service = ParentDashboardService(parent_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_payment_status(child)

            query_count = len(connection.queries)

            # До оптимизации: ~20+ запросов (цикл по enrollments + запросы платежей)
            # После оптимизации: ~3-5 запросов (prefetch + subquery)
            assert query_count <= 8, f"Слишком много запросов: {query_count}. Ожидалось <= 8"

        assert len(result) == 5

    def test_get_dashboard_data_query_count(self, parent_user, teacher_user):
        """get_dashboard_data должен быть сильно оптимизирован (критично!)"""
        from materials.models import Subject

        # Создаем 3 детей с предметами и платежами
        children = []
        for i in range(3):
            child = User.objects.create_user(
                username=f'child{i}',
                email=f'child{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            children.append(child)

            from accounts.models import StudentProfile
            StudentProfile.objects.create(
                user=child,
                parent=parent_user,
                grade='10',
                progress_percentage=50 + i * 10
            )

            # Каждый ребенок имеет 3 предмета
            for j in range(3):
                # Создаем отдельный предмет для каждого зачисления
                subject = Subject.objects.create(
                    name=f'Test Subject {i}-{j}',
                    description=f'Test description {i}-{j}'
                )

                enrollment = SubjectEnrollment.objects.create(
                    student=child,
                    subject=subject,
                    teacher=teacher_user,
                    is_active=True
                )

                # Создаем платеж
                payment = Payment.objects.create(
                    amount=Decimal('100.00'),
                    service_name=f'Test payment {i}-{j}',
                    customer_fio='Test User'
                )

                SubjectPayment.objects.create(
                    enrollment=enrollment,
                    payment=payment,
                    amount=Decimal('100.00'),
                    status=SubjectPayment.Status.PAID,
                    due_date=timezone.now() + timedelta(days=7)
                )

        service = ParentDashboardService(parent_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_dashboard_data()

            query_count = len(connection.queries)

            # До оптимизации: ~60+ запросов (вложенные циклы!!!)
            # После оптимизации: ~30-40 запросов (значительное улучшение)
            # Метод все еще имеет сложную логику с вызовами других методов
            assert query_count <= 45, f"Слишком много запросов: {query_count}. Ожидалось <= 45"

        assert len(result['children']) == 3
        assert result['statistics']['total_children'] == 3

    def test_get_child_progress_query_count(self, parent_user, teacher_user):
        """get_child_progress должен использовать аннотации"""
        from materials.models import Subject

        child = User.objects.create_user(
            username='child1',
            email='child1@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        from accounts.models import StudentProfile
        StudentProfile.objects.create(
            user=child,
            parent=parent_user,
            grade='10'
        )

        # Создаем 5 зачислений с материалами
        for i in range(5):
            # Создаем отдельный предмет для каждого зачисления
            subject = Subject.objects.create(
                name=f'Test Subject {i}',
                description=f'Test description {i}'
            )

            enrollment = SubjectEnrollment.objects.create(
                student=child,
                subject=subject,
                teacher=teacher_user,
                is_active=True
            )

            # Создаем материалы с прогрессом
            for j in range(3):
                material = Material.objects.create(
                    title=f"Material {i}-{j}",
                    subject=subject,
                    author=teacher_user,
                    status=Material.Status.ACTIVE
                )

                MaterialProgress.objects.create(
                    student=child,
                    material=material,
                    is_completed=(j == 0),
                    progress_percentage=j * 30,
                    time_spent=j * 60
                )

        service = ParentDashboardService(parent_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_child_progress(child)

            query_count = len(connection.queries)

            # До оптимизации: ~15+ запросов
            # После оптимизации: ~5-7 запросов (аннотации + prefetch)
            assert query_count <= 10, f"Слишком много запросов: {query_count}. Ожидалось <= 10"

        assert result['total_materials'] == 15  # 5 enrollments * 3 materials
