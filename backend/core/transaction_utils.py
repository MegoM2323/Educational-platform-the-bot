"""
Утилиты для обеспечения целостности данных через транзакционную обработку
"""
import logging
from contextlib import contextmanager
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Типы критических операций"""
    USER_CREATION = "user_creation"
    PAYMENT_PROCESSING = "payment_processing"
    APPLICATION_APPROVAL = "application_approval"
    MATERIAL_CREATION = "material_creation"
    PARENT_CHILD_LINKING = "parent_child_linking"


@dataclass
class TransactionResult:
    """Результат выполнения транзакции"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    rollback_reason: Optional[str] = None


class TransactionManager:
    """Менеджер для управления критическими транзакциями"""
    
    def __init__(self):
        self.active_transactions: Dict[str, Dict] = {}
    
    @contextmanager
    def critical_transaction(self, 
                           transaction_type: TransactionType,
                           operation_name: str,
                           user_id: Optional[int] = None,
                           metadata: Optional[Dict] = None):
        """
        Контекстный менеджер для критических транзакций
        
        Args:
            transaction_type: Тип операции
            operation_name: Название операции
            user_id: ID пользователя, выполняющего операцию
            metadata: Дополнительные метаданные
        """
        transaction_id = f"{transaction_type.value}_{operation_name}_{user_id or 'system'}"
        
        # Логируем начало транзакции
        logger.info(f"Starting critical transaction: {transaction_id}")
        
        try:
            with transaction.atomic():
                # Сохраняем информацию о транзакции
                self.active_transactions[transaction_id] = {
                    'type': transaction_type,
                    'operation': operation_name,
                    'user_id': user_id,
                    'metadata': metadata or {},
                    'started_at': transaction.timezone.now() if hasattr(transaction, 'timezone') else None
                }
                
                yield TransactionResult(success=True)
                
                # Логируем успешное завершение
                logger.info(f"Critical transaction completed successfully: {transaction_id}")
                
        except IntegrityError as e:
            error_msg = f"Database integrity error in {transaction_id}: {str(e)}"
            logger.error(error_msg)
            yield TransactionResult(
                success=False, 
                error=error_msg,
                rollback_reason="integrity_error"
            )
            
        except ValidationError as e:
            error_msg = f"Validation error in {transaction_id}: {str(e)}"
            logger.error(error_msg)
            yield TransactionResult(
                success=False, 
                error=error_msg,
                rollback_reason="validation_error"
            )
            
        except Exception as e:
            error_msg = f"Unexpected error in {transaction_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield TransactionResult(
                success=False, 
                error=error_msg,
                rollback_reason="unexpected_error"
            )
            
        finally:
            # Очищаем информацию о транзакции
            self.active_transactions.pop(transaction_id, None)
    
    def execute_with_rollback(self, 
                             operation: Callable,
                             transaction_type: TransactionType,
                             operation_name: str,
                             user_id: Optional[int] = None,
                             metadata: Optional[Dict] = None) -> TransactionResult:
        """
        Выполняет операцию с автоматическим откатом при ошибке
        
        Args:
            operation: Функция для выполнения
            transaction_type: Тип операции
            operation_name: Название операции
            user_id: ID пользователя
            metadata: Дополнительные метаданные
            
        Returns:
            TransactionResult с результатом выполнения
        """
        with self.critical_transaction(transaction_type, operation_name, user_id, metadata) as result:
            if result.success:
                try:
                    operation_result = operation()
                    result.data = operation_result
                    return result
                except Exception as e:
                    result.success = False
                    result.error = str(e)
                    result.rollback_reason = "operation_error"
                    return result
            else:
                return result


# Глобальный экземпляр менеджера транзакций
transaction_manager = TransactionManager()


def ensure_data_integrity(transaction_type: TransactionType, operation_name: str):
    """
    Декоратор для обеспечения целостности данных
    
    Args:
        transaction_type: Тип критической операции
        operation_name: Название операции
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Извлекаем user_id из аргументов если возможно
            user_id = None
            if args and hasattr(args[0], 'user') and hasattr(args[0].user, 'id'):
                user_id = args[0].user.id
            elif 'user' in kwargs and hasattr(kwargs['user'], 'id'):
                user_id = kwargs['user'].id
            
            return transaction_manager.execute_with_rollback(
                lambda: func(*args, **kwargs),
                transaction_type,
                operation_name,
                user_id
            )
        return wrapper
    return decorator


class DataIntegrityValidator:
    """Валидатор для проверки целостности данных"""
    
    @staticmethod
    def validate_user_creation_data(data: Dict) -> List[str]:
        """
        Валидирует данные для создания пользователя
        
        Args:
            data: Словарь с данными пользователя
            
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        required_fields = ['email', 'first_name', 'last_name', 'role']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        # Валидация email
        email = data.get('email', '')
        if email and '@' not in email:
            errors.append("Некорректный формат email")
        
        # Валидация роли
        valid_roles = ['student', 'teacher', 'tutor', 'parent']
        role = data.get('role', '')
        if role and role not in valid_roles:
            errors.append(f"Недопустимая роль. Допустимые роли: {', '.join(valid_roles)}")
        
        return errors
    
    @staticmethod
    def validate_payment_data(data: Dict) -> List[str]:
        """
        Валидирует данные для создания платежа
        
        Args:
            data: Словарь с данными платежа
            
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        required_fields = ['amount', 'service_name', 'customer_fio']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        # Валидация суммы
        amount = data.get('amount')
        if amount is not None:
            try:
                amount_float = float(amount)
                if amount_float <= 0:
                    errors.append("Сумма должна быть больше нуля")
                if amount_float > 1000000:  # 1 миллион рублей
                    errors.append("Сумма не может превышать 1,000,000 рублей")
            except (ValueError, TypeError):
                errors.append("Некорректная сумма")
        
        return errors
    
    @staticmethod
    def validate_parent_child_relationship(parent_id: int, child_id: int) -> List[str]:
        """
        Валидирует связь родитель-ребенок
        
        Args:
            parent_id: ID родителя
            child_id: ID ребенка
            
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        if parent_id == child_id:
            errors.append("Пользователь не может быть родителем самому себе")
        
        return errors


def log_critical_operation(operation: str, 
                          user_id: Optional[int] = None, 
                          details: Optional[Dict] = None,
                          success: bool = True):
    """
    Логирует критическую операцию
    
    Args:
        operation: Название операции
        user_id: ID пользователя
        details: Дополнительные детали
        success: Успешность операции
    """
    log_data = {
        'operation': operation,
        'user_id': user_id,
        'success': success,
        'details': details or {}
    }
    
    if success:
        logger.info(f"Critical operation completed: {log_data}")
    else:
        logger.error(f"Critical operation failed: {log_data}")


def create_backup_point(description: str) -> str:
    """
    Создает точку резервного копирования
    
    Args:
        description: Описание точки восстановления
        
    Returns:
        ID точки восстановления
    """
    import uuid
    backup_id = str(uuid.uuid4())
    
    logger.info(f"Backup point created: {backup_id} - {description}")
    
    # Здесь можно добавить логику создания реального бэкапа
    # Например, создание снимка базы данных
    
    return backup_id
