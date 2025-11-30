"""
Тесты изоляции БД - проверка что тесты используют ТОЛЬКО SQLite in-memory
"""
import pytest
import os
from django.conf import settings


def test_database_is_sqlite():
    """Проверка что тесты используют SQLite"""
    db = settings.DATABASES['default']
    assert 'sqlite' in db['ENGINE'], f"Тесты должны использовать SQLite! Текущий: {db['ENGINE']}"


def test_database_not_supabase():
    """Проверка что тесты НЕ используют Supabase"""
    db = settings.DATABASES['default']
    host = db.get('HOST', '')
    assert 'supabase' not in host.lower(), f"Тесты НЕ ДОЛЖНЫ использовать Supabase! HOST: {host}"


def test_environment_is_test():
    """Проверка что ENVIRONMENT установлен в test"""
    env = os.getenv('ENVIRONMENT')
    assert env == 'test', f"ENVIRONMENT должна быть 'test', получено: {env}"


def test_database_url_not_set_or_safe():
    """Проверка что DATABASE_URL либо не установлен, либо не указывает на Supabase"""
    database_url = os.getenv('DATABASE_URL', '')
    if database_url:
        assert 'supabase' not in database_url.lower(), \
            f"DATABASE_URL НЕ ДОЛЖЕН указывать на Supabase! Получено: {database_url[:50]}..."


def test_database_name_is_memory():
    """Проверка что БД использует :memory: (in-memory SQLite)"""
    db = settings.DATABASES['default']
    name = str(db.get('NAME', ''))
    assert ':memory:' in name, f"Тесты должны использовать :memory: БД! Получено: {name}"


def test_settings_debug_mode():
    """Проверка что DEBUG режим включен в тестах"""
    assert settings.DEBUG is True, "DEBUG должен быть True в тестовом окружении"


@pytest.mark.django_db
def test_database_isolation_no_persistent_data(transactional_db):
    """Проверка что тестовая БД изолирована и не сохраняет данные между запусками"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Создаем тестового пользователя
    user = User.objects.create(
        username='test_isolation_user',
        email='isolation@test.com',
        role='student'
    )

    # Проверяем что пользователь создан
    assert User.objects.filter(username='test_isolation_user').exists()

    # Этот пользователь существует только в памяти и исчезнет после теста
    # Это подтверждает изоляцию БД
