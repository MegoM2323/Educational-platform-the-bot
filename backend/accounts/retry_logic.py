"""
Модуль для реализации retry логики при работе с Supabase sync операциями.

Обеспечивает надежность при сбоях сети и временных ошибок Supabase,
используя exponential backoff для минимизации нагрузки на сервис.
"""
import time
import logging
from typing import Callable, TypeVar, Any, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Конфигурация параметров retry."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        """
        Инициализация конфигурации retry.

        Args:
            max_attempts: Максимальное количество попыток (по умолчанию 3)
            initial_delay: Начальная задержка в секундах (по умолчанию 1.0)
            max_delay: Максимальная задержка в секундах (по умолчанию 10.0)
            exponential_base: База для exponential backoff (по умолчанию 2.0)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """
        Расчет задержки для текущей попытки.

        Args:
            attempt: Номер попытки (начиная с 0)

        Returns:
            Задержка в секундах
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class SupabaseSyncRetry:
    """Класс для управления retry операциями при Supabase sync."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Инициализация.

        Args:
            config: Конфигурация retry (используется дефолтная если не указана)
        """
        self.config = config or RetryConfig()

    def execute(
        self,
        func: Callable[..., T],
        *args,
        operation_name: str = "Supabase operation",
        **kwargs
    ) -> T:
        """
        Выполнение функции с retry логикой.

        Args:
            func: Функция для выполнения
            operation_name: Название операции для логирования
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции

        Returns:
            Результат функции

        Raises:
            Exception: Если все попытки исчерпаны
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                logger.info(
                    f"[{operation_name}] Попытка {attempt + 1}/{self.config.max_attempts}"
                )
                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"[{operation_name}] Успешно выполнено после {attempt} повторных попыток"
                    )
                else:
                    logger.info(f"[{operation_name}] Успешно выполнено")

                return result

            except Exception as exc:
                last_exception = exc
                is_last_attempt = attempt == self.config.max_attempts - 1

                if is_last_attempt:
                    logger.error(
                        f"[{operation_name}] Все {self.config.max_attempts} попытки исчерпаны. "
                        f"Последняя ошибка: {exc}"
                    )
                else:
                    delay = self.config.get_delay(attempt)
                    logger.warning(
                        f"[{operation_name}] Ошибка при попытке {attempt + 1}: {exc}. "
                        f"Повторная попытка через {delay:.1f}с..."
                    )
                    time.sleep(delay)

        # Если дошли сюда - все попытки исчерпаны
        raise last_exception or Exception(
            f"[{operation_name}] Не удалось выполнить операцию после {self.config.max_attempts} попыток"
        )


def retry_supabase_sync(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0
) -> Callable:
    """
    Декоратор для добавления retry логики к функции Supabase sync.

    Args:
        max_attempts: Максимальное количество попыток
        initial_delay: Начальная задержка
        max_delay: Максимальная задержка

    Returns:
        Декоратор функции

    Example:
        @retry_supabase_sync(max_attempts=3)
        def create_user_in_supabase(email, password):
            # код создания пользователя
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay
        )

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retry_manager = SupabaseSyncRetry(config)
            return retry_manager.execute(
                func,
                *args,
                operation_name=f"{func.__module__}.{func.__name__}",
                **kwargs
            )

        return wrapper

    return decorator


def create_fallback_user(
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Создание fallback данных для пользователя при сбое Supabase.

    Args:
        email: Email пользователя
        first_name: Имя
        last_name: Фамилия
        role: Роль
        logger: Logger для записи информации

    Returns:
        Словарь с данными пользователя для создания в Django
    """
    logger.info(
        f"[Supabase Fallback] Создаю пользователя только в Django: {email} (роль: {role})"
    )

    return {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'role': role,
        'supabase_sync_failed': True  # Флаг что синхронизация не удалась
    }
