from django.core.cache import caches
from django.conf import settings
from typing import Any, Optional, Callable
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Базовый менеджер кэширования"""
    
    def __init__(self, cache_name: str = 'default'):
        self.cache = caches[cache_name]
        self.timeouts = getattr(settings, 'CACHE_TIMEOUTS', {})
    
    def get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Генерирует ключ кэша"""
        key_parts = [prefix]
        
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(str(hash(str(arg))))
        
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}:{value}")
            else:
                key_parts.append(f"{key}:{hash(str(value))}")
        
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_string = hashlib.md5(key_string.encode()).hexdigest()
        
        return key_string
    
    def get_or_set(self, key: str, callable_func: Callable, timeout: Optional[int] = None) -> Any:
        """Получить значение из кэша или установить его через функцию"""
        try:
            value = self.cache.get(key)
            if value is None:
                value = callable_func()
                if timeout is None:
                    timeout = self.timeouts.get('default', 300)
                try:
                    self.cache.set(key, value, timeout)
                except Exception as e:
                    logger.warning(f"Cache set error for key {key}: {e}")
            return value
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return callable_func()


class DashboardCacheManager(CacheManager):
    """Менеджер кэширования для дашбордов"""
    
    def __init__(self):
        super().__init__('dashboard')
    
    def invalidate_student_cache(self, student_id: int) -> None:
        """Инвалидирует кэш студента"""
        patterns = [
            f"student_materials:{student_id}:*",
            f"student_progress:{student_id}",
            f"student_dashboard_data:{student_id}:*",
        ]
        for pattern in patterns:
            self._invalidate_pattern(pattern)
    
    def invalidate_teacher_cache(self, teacher_id: int) -> None:
        """Инвалидирует кэш преподавателя"""
        patterns = [
            f"teacher_students:{teacher_id}",
            f"teacher_materials:{teacher_id}:*",
            f"teacher_dashboard_data:{teacher_id}:*",
        ]
        for pattern in patterns:
            self._invalidate_pattern(pattern)
    
    def invalidate_parent_cache(self, parent_id: int) -> None:
        """Инвалидирует кэш родителя"""
        patterns = [
            f"parent_children:{parent_id}",
            f"parent_child_progress:{parent_id}:*",
            f"parent_dashboard_data:{parent_id}:*",
        ]
        for pattern in patterns:
            self._invalidate_pattern(pattern)
    
    def _invalidate_pattern(self, pattern: str) -> None:
        """Инвалидирует кэш по паттерну"""
        try:
            if hasattr(self.cache, 'delete_pattern'):
                self.cache.delete_pattern(pattern)
        except Exception:
            pass  # Игнорируем ошибки Redis


class ChatCacheManager(CacheManager):
    """Менеджер кэширования для чата"""
    
    def __init__(self):
        super().__init__('chat')


def cache_dashboard_data(timeout: Optional[int] = None):
    """Декоратор для кэширования данных дашборда"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            cache_manager = DashboardCacheManager()
            
            if hasattr(self, 'student'):
                user_id = self.student.id
                user_type = 'student'
            elif hasattr(self, 'teacher'):
                user_id = self.teacher.id
                user_type = 'teacher'
            elif hasattr(self, 'parent_user'):
                user_id = self.parent_user.id
                user_type = 'parent'
            else:
                return func(self, *args, **kwargs)
            
            cache_key = cache_manager.get_cache_key(
                f'{user_type}_dashboard_data',
                user_id,
                func.__name__,
                *args,
                **kwargs
            )
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: func(self, *args, **kwargs),
                timeout or cache_manager.timeouts.get('dashboard_data', 300)
            )
        return wrapper
    return decorator


def cache_material_data(timeout: Optional[int] = None):
    """Декоратор для кэширования данных материалов"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            cache_manager = DashboardCacheManager()
            
            if hasattr(self, 'student'):
                user_id = self.student.id
                user_type = 'student'
            elif hasattr(self, 'teacher'):
                user_id = self.teacher.id
                user_type = 'teacher'
            else:
                return func(self, *args, **kwargs)
            
            cache_key = cache_manager.get_cache_key(
                f'{user_type}_materials',
                user_id,
                func.__name__,
                *args,
                **kwargs
            )
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: func(self, *args, **kwargs),
                timeout or cache_manager.timeouts.get('student_materials', 600)
            )
        return wrapper
    return decorator


def cache_chat_data(timeout: Optional[int] = None):
    """Декоратор для кэширования данных чата"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            cache_manager = ChatCacheManager()
            
            cache_key = cache_manager.get_cache_key(
                'chat_data',
                func.__name__,
                *args,
                **kwargs
            )
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: func(self, *args, **kwargs),
                timeout or cache_manager.timeouts.get('chat_messages', 60)
            )
        return wrapper
    return decorator
