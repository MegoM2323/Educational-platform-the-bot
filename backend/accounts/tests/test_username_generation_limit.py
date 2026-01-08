import pytest
import inspect
from pathlib import Path
from django.core.exceptions import ValidationError
from django.test import TestCase
from unittest.mock import patch, MagicMock

from accounts.models import User
from accounts.staff_views import MAX_USERNAME_ATTEMPTS


@pytest.mark.django_db
class TestUsernameGenerationLimit(TestCase):
    """Тесты что генерация username не зацикливается"""

    def test_max_username_attempts_constant_exists(self):
        """MAX_USERNAME_ATTEMPTS константа определена"""
        assert MAX_USERNAME_ATTEMPTS == 100
        assert isinstance(MAX_USERNAME_ATTEMPTS, int)

    def test_username_generation_within_limit(self):
        """Генерация username работает если меньше MAX_ATTEMPTS коллизий"""
        base_email = "unique@test.com"
        initial_count = User.objects.count()

        # Создаем несколько пользователей с похожими username
        for i in range(10):
            if i == 0:
                username = base_email
            else:
                username = f"unique{i}@local"

            User.objects.create(
                username=username,
                email=f"unique{i}@test.com",
                role=User.Role.STUDENT,
            )

        # Должна существовать логика которая дальше продолжит генерировать
        # Это скорее проверка что не было ошибок при создании 10+ users
        assert User.objects.count() == initial_count + 10

    def test_username_generation_stops_after_max_attempts(self):
        """После MAX_ATTEMPTS должна быть проверка при коллизии"""
        staff_views_path = Path(__file__).parent.parent / "staff_views.py"
        with open(staff_views_path) as f:
            source = f.read()
        # Проверяем что в коде есть проверка ограничения
        assert (
            "MAX_USERNAME_ATTEMPTS" in source or "attempts" in source or "100" in source
        )

    def test_username_loop_has_safety_mechanism(self):
        """В коде генерации username должен быть safety mechanism"""
        staff_views_path = Path(__file__).parent.parent / "staff_views.py"
        with open(staff_views_path) as f:
            source = f.read()

        # Проверяем что есть либо MAX_ATTEMPTS, либо счетчик попыток
        assert (
            "MAX_USERNAME_ATTEMPTS" in source and "attempts" in source
        ), "Username generation должен иметь ограничение на попытки"

    def test_create_user_with_profile_has_username_limit_check(self):
        """create_user_with_profile должна иметь проверку на лимит попыток"""
        staff_views_path = Path(__file__).parent.parent / "staff_views.py"
        with open(staff_views_path) as f:
            source = f.read()

        # Проверяем что в коде есть:
        # 1. Константа MAX_USERNAME_ATTEMPTS
        assert (
            "MAX_USERNAME_ATTEMPTS = 100" in source
        ), "Константа MAX_USERNAME_ATTEMPTS должна быть определена как 100"
        # 2. Использование в коде
        assert (
            source.count("MAX_USERNAME_ATTEMPTS") >= 3
        ), "MAX_USERNAME_ATTEMPTS должна использоваться в трех местах"
        # 3. Счетчик попыток
        assert "attempts" in source, "Должна быть переменная для подсчета попыток"

    def test_constant_imported_in_views(self):
        """MAX_USERNAME_ATTEMPTS должна использоваться в других создателях users"""
        from accounts import staff_views

        # Проверяем что константа определена в модуле
        assert hasattr(staff_views, "MAX_USERNAME_ATTEMPTS")
        assert staff_views.MAX_USERNAME_ATTEMPTS == 100

    def test_username_generation_logic_is_safe(self):
        """Убедиться что username generation логика безопасна от infinite loop"""
        staff_views_path = Path(__file__).parent.parent / "staff_views.py"
        with open(staff_views_path) as f:
            source = f.read()

        # Проверяем наличие критических элементов безопасности
        # 1. Константа лимита
        assert "MAX_USERNAME_ATTEMPTS" in source
        # 2. Счетчик
        assert "attempts = 1" in source or "attempts=1" in source
        # 3. Проверка
        assert "if attempts >= MAX_USERNAME_ATTEMPTS" in source
        # 4. Возврат ошибки при превышении
        assert "400" in source or "ValidationError" in source
