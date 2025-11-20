import re
from typing import Iterable, List
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

import pytest

User = get_user_model()


MANDATORY_FILE_PATTERNS: List[str] = [
    # Аутентификация и базовые флоу
    r"tests/test_auth_flow\.py$",
    r"tests/test_api_integration\.py$",
    r"tests/test_unified_api_integration\.py$",
    r"tests/test_e2e_unified_api\.py$",

    # Основные CRUD и домены
    r"tests/test_application_service\.py$",
    r"tests/test_student_api\.py$",
    r"tests/test_teacher_api\.py$",
    r"tests/test_tutor_api\.py$",
    r"tests/test_tutor_create_student\.py$",
    r"tests/test_tutor_create_student_full\.py$",
    r"tests/test_direct_student_creation\.py$",

    # Назначения предметов и связанные флоу
    r"tests/test_assign_subject_flow\.py$",
    r"tests/test_subject_assignment\.py$",
    r"tests/test_teacher_subject_assignment\.py$",

    # Материалы и отчёты
    r"tests/test_materials_system\.py$",
    r"tests/test_student_materials\.py$",
    r"tests/test_student_report_api\.py$",
    r"tests/test_student_report_service\.py$",

    # Платежи и уведомления
    r"tests/test_payment_integration\.py$",
    r"tests/test_notifications\.py$",

    # Чат и вебсокеты
    r"tests/test_general_chat\.py$",
    r"tests/test_websocket_integration\.py$",

    # Ключевые E2E сценарии (покрывают связки компонентов)
    r"tests/test_e2e_integration\.py$",
    r"tests/test_user_scenarios_e2e\.py$",

    # Дашборды (роли)
    r"tests/test_parent_dashboard\.py$",
    r"tests/test_student_dashboard\.py$",
    r"tests/test_teacher_dashboard\.py$",
]


EXCLUDED_FROM_MANDATORY: List[str] = [
    # Нагрузочные и перформанс-тесты
    r"tests/test_performance_.*\.py$",
    r"tests/test_chat_performance\.py$",
    r"tests/run_performance_tests\.py$",
    r"tests/run_all_performance_tests\.py$",

    # Телеграм-тесты
    r"tests/test_telegram_.*\.py$",

    # Утилиты запуска
    r"tests/run_.*\.py$",

    # UI (Playwright) в этом наборе не запускаем через pytest
    r"tests/test_login_form_ui\.spec\.ts$",
]


def _any_match(patterns: Iterable[str], text: str) -> bool:
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    """Динамически помечаем обязательные тесты маркером 'mandatory'.

    Логика:
    - Если тест совпадает с одним из MANDATORY_FILE_PATTERNS и не входит в исключения,
      помечаем его как mandatory.
    - Остальные тесты остаются без маркера и не запускаются по умолчанию
      (из-за addopts = -m mandatory в pytest.ini).
    """

    for item in items:
        nodeid = item.nodeid

        # Исключения имеют приоритет
        if _any_match(EXCLUDED_FROM_MANDATORY, nodeid):
            continue

        if _any_match(MANDATORY_FILE_PATTERNS, nodeid):
            item.add_marker(pytest.mark.mandatory)


# ===== Common Test Fixtures =====

@pytest.fixture
def student_user(db):
    """Create a student user"""
    user = User.objects.create_user(
        username='student_test',
        email='student@test.com',
        first_name='Test',
        last_name='Student',
        role=User.Role.STUDENT
    )
    # Create student profile
    from accounts.models import StudentProfile
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user(db):
    """Create a parent user"""
    user = User.objects.create_user(
        username='parent_test',
        email='parent@test.com',
        first_name='Test',
        last_name='Parent',
        role=User.Role.PARENT
    )
    # Create parent profile
    from accounts.models import ParentProfile
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user"""
    user = User.objects.create_user(
        username='teacher_test',
        email='teacher@test.com',
        first_name='Test',
        last_name='Teacher',
        role=User.Role.TEACHER
    )
    # Create teacher profile
    from accounts.models import TeacherProfile
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_with_parent(db, student_user, parent_user):
    """Create a student with linked parent"""
    student_user.student_profile.parent = parent_user
    student_user.student_profile.save()
    return student_user


@pytest.fixture
def subject(db):
    """Create a subject"""
    from materials.models import Subject
    return Subject.objects.create(
        name="Математика",
        description="Курс математики для 8 класса"
    )


@pytest.fixture
def enrollment(db, student_with_parent, subject, teacher_user):
    """Create an enrollment"""
    from materials.models import SubjectEnrollment
    return SubjectEnrollment.objects.create(
        student=student_with_parent,
        subject=subject,
        teacher=teacher_user,
        is_active=True
    )


@pytest.fixture
def payment(db):
    """Create a basic payment"""
    from payments.models import Payment
    return Payment.objects.create(
        amount=Decimal('100.00'),
        service_name="Тестовый платеж",
        customer_fio="Иванов Иван Иванович",
        description="Тестовое описание",
        status=Payment.Status.PENDING,
        metadata={
            'test': True
        }
    )


@pytest.fixture
def subject_payment(db, enrollment, payment):
    """Create a subject payment linked to enrollment and payment"""
    from materials.models import SubjectPayment
    return SubjectPayment.objects.create(
        enrollment=enrollment,
        payment=payment,
        amount=payment.amount,
        status=SubjectPayment.Status.PENDING,
        due_date=timezone.now() + timedelta(days=7)
    )


@pytest.fixture
def subscription(db, enrollment):
    """Create an active subscription"""
    from materials.models import SubjectSubscription
    return SubjectSubscription.objects.create(
        enrollment=enrollment,
        amount=Decimal('100.00'),
        status=SubjectSubscription.Status.ACTIVE,
        next_payment_date=timezone.now() + timedelta(days=7),
        payment_interval_weeks=1
    )

