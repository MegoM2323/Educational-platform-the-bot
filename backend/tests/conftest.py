"""
Pytest configuration and fixtures for THE_BOT platform tests
"""
import os
import sys

# ============================================================================
# КРИТИЧЕСКАЯ ЗАЩИТА: Принудительно устанавливаем тестовое окружение
# ============================================================================
#
# ОБЯЗАТЕЛЬНО устанавливаем ENVIRONMENT=test ДО импорта Django
# Это обеспечивает использование SQLite in-memory вместо продакшн БД
#
# ============================================================================

# Set ENVIRONMENT=test FIRST and IMMEDIATELY
os.environ['ENVIRONMENT'] = 'test'
# Remove any production database settings
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']
if 'DIRECT_URL' in os.environ:
    del os.environ['DIRECT_URL']

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Disable Daphne/Twisted during tests to avoid SSL issues
os.environ['DISABLE_DAPHNE_SSL'] = 'true'

# Убедиться что не используется продакшн БД
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if 'supabase' in DATABASE_URL.lower():
    raise RuntimeError(
        f"\n"
        f"{'='*70}\n"
        f"🚨🚨🚨 КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL указывает на Supabase! 🚨🚨🚨\n"
        f"{'='*70}\n"
        f"\n"
        f"Тесты НЕ ДОЛЖНЫ использовать продакшн БД!\n"
        f"\n"
        f"РЕШЕНИЕ:\n"
        f"1. Удалите DATABASE_URL из окружения при запуске pytest\n"
        f"2. Или используйте: unset DATABASE_URL && pytest\n"
        f"3. Или используйте скрипт: ./scripts/run_tests.sh\n"
        f"\n"
        f"DATABASE_URL будет проигнорирован для тестов.\n"
        f"{'='*70}\n"
    )
    # Удаляем опасную переменную
    del os.environ['DATABASE_URL']

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
import factory
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

# Add tests directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import fixture modules
from fixtures import yookassa, supabase, websocket, celery

User = get_user_model()


# ===== Model Factories =====

class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""
    class Meta:
        model = User

    username = Faker('user_name')
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to set password properly using set_password()"""
        # Extract password or use default
        password = kwargs.pop('password', 'testpass123')
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class StudentUserFactory(UserFactory):
    """Factory for creating Student users"""
    role = User.Role.STUDENT


class ParentUserFactory(UserFactory):
    """Factory for creating Parent users"""
    role = User.Role.PARENT


class TeacherUserFactory(UserFactory):
    """Factory for creating Teacher users"""
    role = User.Role.TEACHER


class TutorUserFactory(UserFactory):
    """Factory for creating Tutor users"""
    role = User.Role.TUTOR


@pytest.fixture
def student_user(db):
    """Create a student user with StudentProfile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = StudentUserFactory()
    from accounts.models import StudentProfile
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user(db):
    """Create a parent user with ParentProfile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = ParentUserFactory()
    from accounts.models import ParentProfile
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user with TeacherProfile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = TeacherUserFactory()
    from accounts.models import TeacherProfile
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def tutor_user(db):
    """Create a tutor user with TutorProfile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = TutorUserFactory()
    from accounts.models import TutorProfile
    TutorProfile.objects.create(user=user)
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


# ===== YooKassa API Mocks =====

@pytest.fixture
def mock_yookassa_payment_response():
    """Mock successful YooKassa payment creation response"""
    return {
        'id': 'test-payment-id-123',
        'status': 'pending',
        'amount': {
            'value': '100.00',
            'currency': 'RUB'
        },
        'description': 'Test payment',
        'confirmation': {
            'type': 'redirect',
            'confirmation_url': 'https://yookassa.ru/checkout/test-123'
        },
        'metadata': {
            'test': True
        },
        'created_at': timezone.now().isoformat(),
        'paid': False
    }


@pytest.fixture
def mock_yookassa_succeeded_payment():
    """Mock YooKassa payment succeeded response"""
    return {
        'id': 'test-payment-id-123',
        'status': 'succeeded',
        'amount': {
            'value': '100.00',
            'currency': 'RUB'
        },
        'description': 'Test payment',
        'metadata': {
            'test': True
        },
        'created_at': timezone.now().isoformat(),
        'paid': True,
        'captured_at': timezone.now().isoformat()
    }


@pytest.fixture
def mock_yookassa_webhook_succeeded(mock_yookassa_succeeded_payment):
    """Mock YooKassa webhook for payment.succeeded event"""
    return {
        'type': 'notification',
        'event': 'payment.succeeded',
        'object': mock_yookassa_succeeded_payment
    }


@pytest.fixture
def mock_yookassa_webhook_canceled():
    """Mock YooKassa webhook for payment.canceled event"""
    return {
        'type': 'notification',
        'event': 'payment.canceled',
        'object': {
            'id': 'test-payment-id-123',
            'status': 'canceled',
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'created_at': timezone.now().isoformat(),
            'paid': False
        }
    }


# ===== Request Mocks =====

@pytest.fixture
def mock_request(rf):
    """Create a mock Django request"""
    request = rf.get('/')
    request.META['HTTP_HOST'] = 'localhost:8000'
    return request


# ===== pytest-django settings =====

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Настройка и валидация тестовой БД.

    ЗАЩИТА: Проверяет что используется SQLite in-memory, не продакшн БД.
    """
    from django.conf import settings

    db = settings.DATABASES['default']

    # КРИТИЧЕСКАЯ ПРОВЕРКА: БД должна быть SQLite
    assert 'sqlite' in db['ENGINE'], (
        f"❌ Тесты должны использовать SQLite! "
        f"Текущий ENGINE: {db['ENGINE']}"
    )

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Не Supabase
    db_host = db.get('HOST', '')
    assert 'supabase' not in db_host.lower(), (
        f"❌ Тесты НЕ ДОЛЖНЫ использовать Supabase! "
        f"HOST: {db_host}"
    )

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Окружение = test
    assert os.getenv('ENVIRONMENT') == 'test', (
        f"❌ ENVIRONMENT должна быть 'test', получено: {os.getenv('ENVIRONMENT')}"
    )

    # Выполнить миграции
    with django_db_blocker.unblock():
        from django.core.management import call_command
        # Run migrations to create full DB schema
        call_command('migrate', '--run-syncdb', verbosity=0)

    print(f"\n✅ Тестовая БД: SQLite in-memory (изолирована от продакшн)")


@pytest.fixture(autouse=True)
def use_dummy_cache(settings):
    """Use dummy cache for all tests to avoid Redis dependency"""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'dashboard': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


@pytest.fixture(autouse=True)
def use_test_payment_settings(settings):
    """Override payment settings for tests"""
    settings.PAYMENT_DEVELOPMENT_MODE = True
    settings.DEVELOPMENT_PAYMENT_AMOUNT = Decimal('1.00')
    settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES = 10
    settings.PRODUCTION_PAYMENT_AMOUNT = Decimal('100.00')
    settings.PRODUCTION_RECURRING_INTERVAL_WEEKS = 1


@pytest.fixture
def mock_yookassa_client(mocker):
    """Mock YooKassa client to avoid real API calls"""
    mock_client = mocker.patch('payments.views.Configuration')
    mock_payment = mocker.patch('payments.views.Payment')
    return {
        'client': mock_client,
        'payment': mock_payment
    }


# ===== Admin and Additional User Fixtures =====

@pytest.fixture
def admin_user(db):
    """Create an admin/superuser"""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    return user


@pytest.fixture
def other_student_user(db):
    """Create another student user for testing access control.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = StudentUserFactory()
    from accounts.models import StudentProfile
    StudentProfile.objects.create(user=user)
    return user


# ===== Material and File Fixtures =====

@pytest.fixture
def sample_material(db, subject, teacher_user):
    """Create a sample material with file"""
    from materials.models import Material
    from django.core.files.uploadedfile import SimpleUploadedFile

    test_file = SimpleUploadedFile("test_material.pdf", b"test content", content_type="application/pdf")

    material = Material.objects.create(
        title="Test Material",
        subject=subject,
        author=teacher_user,
        file=test_file,
        is_public=False
    )
    return material


@pytest.fixture
def sample_study_plan(db, student_user, teacher_user, subject):
    """Create a sample study plan"""
    from materials.models import StudyPlan
    from datetime import timedelta

    week_start = timezone.now().date()
    plan = StudyPlan.objects.create(
        student=student_user,
        teacher=teacher_user,
        subject=subject,
        title="Test study plan",
        content="Test study plan content",
        week_start_date=week_start,
        week_end_date=week_start + timedelta(days=6)
    )
    return plan


@pytest.fixture
def sample_study_plan_file(db, sample_study_plan, teacher_user):
    """Create a sample study plan file"""
    from materials.models import StudyPlanFile
    from django.core.files.uploadedfile import SimpleUploadedFile

    test_content = b"test plan content"
    test_file = SimpleUploadedFile("test_plan.pdf", test_content, content_type="application/pdf")

    plan_file = StudyPlanFile.objects.create(
        study_plan=sample_study_plan,
        file=test_file,
        name="test_plan.pdf",
        file_size=len(test_content),
        uploaded_by=teacher_user
    )
    return plan_file


@pytest.fixture
def sample_enrollment(db, student_user, subject, teacher_user):
    """Create a sample enrollment"""
    from materials.models import SubjectEnrollment

    enrollment = SubjectEnrollment.objects.create(
        student=student_user,
        subject=subject,
        teacher=teacher_user,
        is_active=True
    )
    return enrollment


# ===== Lesson Testing Fixtures =====

@pytest.fixture
def another_student_user(db):
    """Create another student for testing multiple students."""
    user = StudentUserFactory()
    from accounts.models import StudentProfile
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def math_subject(db):
    """Create a test Math subject."""
    from materials.models import Subject
    return Subject.objects.create(
        name='Математика',
        description='Тестовый предмет математика'
    )


@pytest.fixture
def english_subject(db):
    """Create a test English subject."""
    from materials.models import Subject
    return Subject.objects.create(
        name='Английский язык',
        description='Тестовый предмет английский'
    )


@pytest.fixture
def subject_enrollment(db, student_user, teacher_user, math_subject):
    """Create an active SubjectEnrollment linking teacher to student."""
    from materials.models import SubjectEnrollment
    return SubjectEnrollment.objects.create(
        student=student_user,
        teacher=teacher_user,
        subject=math_subject,
        is_active=True
    )


@pytest.fixture
def another_enrollment(db, another_student_user, teacher_user, english_subject):
    """Create another SubjectEnrollment for different student."""
    from materials.models import SubjectEnrollment
    return SubjectEnrollment.objects.create(
        student=another_student_user,
        teacher=teacher_user,
        subject=english_subject,
        is_active=True
    )


@pytest.fixture
def lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a test lesson for future date."""
    from datetime import time
    from scheduling.models import Lesson

    future_date = timezone.now().date() + timedelta(days=3)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=future_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        description='Алгебра для 8 класса',
        telemost_link='https://telemost.yandex.ru/test',
        status='pending'
    )


@pytest.fixture
def confirmed_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a confirmed lesson."""
    from datetime import time
    from scheduling.models import Lesson

    future_date = timezone.now().date() + timedelta(days=5)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=future_date,
        start_time=time(14, 0),
        end_time=time(15, 0),
        description='Геометрия',
        status='confirmed'
    )


@pytest.fixture
def past_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a lesson in the past."""
    from datetime import time
    from scheduling.models import Lesson

    past_date = timezone.now().date() - timedelta(days=5)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=past_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        description='Прошлый урок',
        status='completed'
    )


@pytest.fixture
def near_future_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a lesson that is less than 2 hours away."""
    from datetime import time
    from scheduling.models import Lesson

    near_future = timezone.now() + timedelta(minutes=30)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=near_future.date(),
        start_time=near_future.time(),
        end_time=(near_future + timedelta(hours=1)).time(),
        description='Урок через 30 минут',
        status='confirmed'
    )
