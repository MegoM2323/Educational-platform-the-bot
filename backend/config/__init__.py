"""
Настройки для предотвращения зависания подключений к БД
"""
import os
import signal
from django.db.backends.postgresql.base import DatabaseWrapper

# Устанавливаем таймаут подключения для psycopg2
_original_get_new_connection = DatabaseWrapper.get_new_connection

def get_new_connection_with_timeout(self, conn_params):
    """Обертка для установки таймаута подключения"""
    # Получаем таймаут из настроек
    connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '10'))
    
    # Устанавливаем таймаут в параметрах подключения
    if 'connect_timeout' not in conn_params:
        conn_params['connect_timeout'] = connect_timeout
    
    # Вызываем оригинальный метод
    return _original_get_new_connection(self, conn_params)

# Применяем патч только если не был применен ранее
if not hasattr(DatabaseWrapper, '_timeout_patched'):
    DatabaseWrapper.get_new_connection = get_new_connection_with_timeout
    DatabaseWrapper._timeout_patched = True


