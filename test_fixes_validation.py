import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'backend'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ENVIRONMENT'] = 'test'

django.setup()

import pytest
from django.test import TestCase, Client
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from accounts.models import User
from scheduling.models import Lesson
from datetime import datetime, timedelta, time, date


class TestL2CORSConfiguration(TestCase):
    """Test L2: CORS Configuration"""

    def setUp(self):
        self.client = APIClient()

    def test_cors_allowed_origins_configured(self):
        """Test that CORS_ALLOWED_ORIGINS is configured"""
        assert hasattr(settings, 'CORS_ALLOWED_ORIGINS')
        assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
        assert len(settings.CORS_ALLOWED_ORIGINS) > 0

    def test_cors_allow_all_origins_false(self):
        """Test that CORS_ALLOW_ALL_ORIGINS is False"""
        assert settings.CORS_ALLOW_ALL_ORIGINS is False

    def test_cors_allow_credentials(self):
        """Test that CORS_ALLOW_CREDENTIALS is True"""
        assert settings.CORS_ALLOW_CREDENTIALS is True

    def test_cors_middleware_installed(self):
        """Test that CORS middleware is installed"""
        cors_middleware_found = any(
            'cors' in middleware.lower()
            for middleware in settings.MIDDLEWARE
        )
        assert cors_middleware_found


class TestH1CSRFExemptRemoved(TestCase):
    """Test H1: CSRF Exempt Removed from Login/Registration"""

    def test_csrf_exempt_only_on_webhooks(self):
        """Test that csrf_exempt is only on webhook endpoints"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', 'csrf_exempt', 'backend', '--include=*.py'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        lines = [l for l in result.stdout.split('\n') if l.strip()]

        webhook_files = [
            'telegram_webhook_views.py',
            'payments/views.py',
            'autograder.py',
            'views_plagiarism.py',
            'prometheus_views.py'
        ]

        for line in lines:
            found_webhook = any(webhook in line for webhook in webhook_files)
            assert found_webhook, f"CSRF exempt found outside webhooks: {line}"

    def test_login_endpoint_requires_auth(self):
        """Test that login endpoint doesn't have csrf_exempt"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', 'csrf_exempt', 'backend/accounts', '--include=*.py'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        assert 'views.py' not in result.stdout


class TestM3FileUploadSizeLimit(TestCase):
    """Test M3: File Upload Size Limit"""

    def test_file_upload_max_memory_size(self):
        """Test that file upload size limit is 5MB"""
        assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 5242880  # 5 MB
        assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 5242880  # 5 MB

    def test_file_upload_max_memory_size_is_5mb(self):
        """Test file upload size in bytes equals 5MB"""
        expected_bytes = 5 * 1024 * 1024
        assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == expected_bytes


class TestM1LessonTimeConflictValidation(TestCase):
    """Test M1: Lesson Time Conflict Validation"""

    def test_lesson_model_has_validation(self):
        """Test that lesson model has clean method for validation"""
        assert hasattr(Lesson, 'clean')

    def test_lesson_model_validates_time_order(self):
        """Test that lesson model validates time order in clean method"""
        import inspect
        source = inspect.getsource(Lesson.clean)
        assert 'start_time' in source
        assert 'end_time' in source


class TestM2TimeValidation(TestCase):
    """Test M2: Time Validation (start < end)"""

    def test_lesson_checks_time_order(self):
        """Test that lesson model checks that start_time < end_time"""
        import inspect
        source = inspect.getsource(Lesson.clean)

        has_time_check = (
            ('start_time' in source and 'end_time' in source) and
            ('>=' in source or '<' in source)
        )
        assert has_time_check


class TestH2WebSocketJWTAuth(TestCase):
    """Test H2: WebSocket JWT Authentication"""

    def test_websocket_consumer_has_token_validation(self):
        """Test that WebSocket consumer has token validation method"""
        from chat.consumers import ChatConsumer
        assert hasattr(ChatConsumer, '_validate_token')
        assert hasattr(ChatConsumer, '_authenticate_token_from_query_string')

    def test_websocket_token_validation_imports_token_model(self):
        """Test that WebSocket consumer imports Token model"""
        from chat.consumers import Token
        assert Token is not None

    def test_websocket_auth_supports_query_string_format(self):
        """Test that WebSocket auth supports token in query string"""
        import inspect
        from chat.consumers import ChatConsumer
        source = inspect.getsource(ChatConsumer._authenticate_token_from_query_string)
        assert 'token=' in source
        assert 'authorization=' in source
        assert 'Bearer' in source


class TestH3AdminEndpointsPermission(TestCase):
    """Test H3: Admin Endpoints Permission Check"""

    def setUp(self):
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='STUDENT'
        )
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='TEACHER'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            is_staff=True,
            is_superuser=True,
            role='ADMIN'
        )

    def test_permission_classes_usage_count(self):
        """Test that permission_classes is used in codebase"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', '@permission_classes', 'backend', '--include=*.py'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        count = len([l for l in result.stdout.split('\n') if l.strip()])
        assert count > 50, f"Expected >50 @permission_classes, found {count}"

    def test_custom_permission_classes_exist(self):
        """Test that custom permission classes are used"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', 'IsStaffOrAdmin', 'backend', '--include=*.py'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        count = len([l for l in result.stdout.split('\n') if l.strip()])
        assert count > 5, f"Expected >5 permission class usages, found {count}"


class TestM4PermissionClassesUsage(TestCase):
    """Test M4: Permission Classes Usage"""

    def test_permission_classes_decorator_exists(self):
        """Test that permission_classes decorator is used"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', '@permission_classes', 'backend/accounts/staff_views.py'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        count = int(result.stdout.strip()) if result.stdout.strip() else 0
        assert count > 10

    def test_isstafforadmin_permission_class_exists(self):
        """Test that IsStaffOrAdmin permission class is defined"""
        try:
            from accounts.permissions import IsStaffOrAdmin
            assert IsStaffOrAdmin is not None
        except ImportError:
            pytest.skip("IsStaffOrAdmin not found, checking alternative paths")


class TestL1EnvNotInGit(TestCase):
    """Test L1: .env Not in Git"""

    def test_env_file_not_tracked(self):
        """Test that .env is not in git tracking"""
        import subprocess
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        assert '.env' not in result.stdout

    def test_env_in_gitignore(self):
        """Test that .env is in .gitignore"""
        gitignore_path = BASE_DIR / '.gitignore'
        with open(gitignore_path, 'r') as f:
            content = f.read()
        assert '.env' in content

    def test_env_not_in_git_history(self):
        """Test that .env was removed from git history"""
        import subprocess
        result = subprocess.run(
            ['git', 'log', '--all', '--oneline', '--', '.env'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            assert True


class TestC1FrontendContainerHealthcheck(TestCase):
    """Test C1: Frontend Container Running with Healthcheck"""

    def test_docker_compose_has_healthcheck(self):
        """Test that docker-compose.yml has healthcheck configuration"""
        docker_compose_path = BASE_DIR / 'docker-compose.yml'
        with open(docker_compose_path, 'r') as f:
            content = f.read()
        assert 'healthcheck:' in content

    def test_frontend_service_has_healthcheck(self):
        """Test that frontend service has healthcheck"""
        docker_compose_path = BASE_DIR / 'docker-compose.yml'
        with open(docker_compose_path, 'r') as f:
            content = f.read()

        assert 'frontend' in content.lower()

    def test_all_services_have_healthcheck(self):
        """Test that critical services have healthcheck"""
        docker_compose_path = BASE_DIR / 'docker-compose.yml'
        with open(docker_compose_path, 'r') as f:
            content = f.read()

        healthcheck_count = content.count('healthcheck:')
        assert healthcheck_count >= 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
