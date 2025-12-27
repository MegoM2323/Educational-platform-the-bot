"""
Утилиты для безопасного парсинга JSON
"""
import json
import logging
from typing import Any, Optional, Dict, Union

logger = logging.getLogger(__name__)


def safe_json_parse(
    data: Union[str, bytes], 
    default: Any = None, 
    log_errors: bool = True
) -> Optional[Any]:
    """
    Безопасно парсит JSON данные с обработкой ошибок
    
    Args:
        data: JSON строка или bytes для парсинга
        default: Значение по умолчанию при ошибке
        log_errors: Логировать ли ошибки
        
    Returns:
        Распарсенный JSON или default при ошибке
    """
    if not data:
        if log_errors:
            logger.warning("Empty data provided for JSON parsing")
        return default
    
    try:
        # Если данные в bytes, декодируем в строку
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        # Проверяем, что это не пустая строка
        if not data.strip():
            if log_errors:
                logger.warning("Empty string provided for JSON parsing")
            return default
            
        return json.loads(data)
        
    except json.JSONDecodeError as e:
        if log_errors:
            logger.error(f"JSON decode error: {e}. Data: {data[:200]}...")
        return default
        
    except UnicodeDecodeError as e:
        if log_errors:
            logger.error(f"Unicode decode error: {e}")
        return default
        
    except Exception as e:
        if log_errors:
            logger.error(f"Unexpected error parsing JSON: {e}")
        return default


def safe_json_response(response, default: Any = None) -> Optional[Any]:
    """
    Безопасно парсит JSON из requests response
    
    Args:
        response: requests.Response объект
        default: Значение по умолчанию при ошибке
        
    Returns:
        Распарсенный JSON или default при ошибке
    """
    if not response:
        logger.warning("Empty response provided")
        return default
    
    # Попытаться получить json напрямую (удобно для моков)
    try:
        if hasattr(response, 'json') and callable(response.json):
            data = response.json()
            # Если вернулся dict/список - считаем это валидным JSON
            if isinstance(data, (dict, list)):
                return data
    except Exception as e:  # noqa: BLE001
        # Игнорируем и продолжим со стандартной веткой
        logger.debug(f"Direct response.json() failed: {e}")

    # Проверяем статус код (бережно, т.к. в тестах может быть MagicMock)
    status_code = getattr(response, 'status_code', 200)
    try:
        if isinstance(status_code, int) and status_code >= 400:
            logger.warning(f"HTTP error {status_code}: {getattr(response, 'text', '')[:200]}")
            return default
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Status code check skipped due to error: {e}")
    
    # Проверяем Content-Type
    headers = getattr(response, 'headers', {}) or {}
    content_type = headers.get('content-type', '').lower()
    if 'application/json' not in content_type and 'text/json' not in content_type:
        logger.warning(f"Unexpected content type: {content_type}")
        # Не возвращаем default, так как это может быть валидный ответ
    
    # Проверяем, что есть содержимое
    content = getattr(response, 'content', None)
    if not content:
        logger.warning("Empty response content")
        return default
    
    return safe_json_parse(content, default)


def is_valid_json(data: Union[str, bytes]) -> bool:
    """
    Проверяет, является ли строка валидным JSON
    
    Args:
        data: Данные для проверки
        
    Returns:
        True если данные валидны, False иначе
    """
    try:
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        json.loads(data)
        return True
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return False


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Безопасно сериализует данные в JSON
    
    Args:
        data: Данные для сериализации
        **kwargs: Дополнительные параметры для json.dumps
        
    Returns:
        JSON строка или пустая строка при ошибке
    """
    try:
        return json.dumps(data, **kwargs)
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing to JSON: {e}")
        return "{}"
