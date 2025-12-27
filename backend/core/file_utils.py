"""
Утилиты для работы с файлами в приложении.

Этот модуль предоставляет централизованные функции для работы с файлами,
включая генерацию безопасных URL с правильной схемой (HTTP/HTTPS).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def build_secure_file_url(file_field, request=None):
    """
    Генерирует абсолютный URL для файла с правильной схемой (HTTP/HTTPS).

    Эта функция обрабатывает случаи, когда приложение работает за reverse proxy
    (например, Nginx) и нужно правильно определить схему протокола.

    Args:
        file_field: Django FileField/ImageField объект (может быть None)
        request: Django request object (опционально)

    Returns:
        str: Абсолютный URL файла с правильной схемой, или None если файл не существует

    Examples:
        >>> build_secure_file_url(material.file, request)
        'https://example.com/media/materials/files/document.pdf'

        >>> build_secure_file_url(None, request)
        None

        >>> build_secure_file_url(material.file)  # без request
        '/media/materials/files/document.pdf'
    """
    # Если файл не существует, возвращаем None
    if not file_field:
        return None

    # Если нет request объекта, возвращаем относительный URL
    if not request:
        try:
            return file_field.url
        except Exception as e:
            logger.warning(f"Could not get file URL without request: {e}")
            return None

    try:
        # Получаем абсолютный URL
        url = request.build_absolute_uri(file_field.url)

        # Проверяем, нужно ли изменить схему на HTTPS
        # Это важно для случаев, когда Django работает за reverse proxy (Nginx)
        # и получает HTTP запросы, но фактически клиент подключается по HTTPS
        if _should_use_https(request):
            url = url.replace('http://', 'https://')

        return url

    except Exception as e:
        # В случае ошибки логируем и возвращаем относительный URL
        logger.error(f"Error building secure file URL: {e}", exc_info=True)
        try:
            return file_field.url
        except:
            return None


def _should_use_https(request) -> bool:
    """
    Определяет, следует ли использовать HTTPS схему для URL.

    Проверяет:
    1. request.is_secure() - встроенная Django проверка
    2. HTTP_X_FORWARDED_PROTO заголовок - для reverse proxy (Nginx, Apache)

    Args:
        request: Django request object

    Returns:
        bool: True если следует использовать HTTPS, False иначе
    """
    # Проверяем встроенный метод Django
    if request.is_secure():
        return True

    # Проверяем заголовок от reverse proxy
    forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO')
    if forwarded_proto == 'https':
        return True

    return False


def get_file_extension(filename: str) -> Optional[str]:
    """
    Извлекает расширение файла из имени файла.

    Args:
        filename: Имя файла или путь к файлу

    Returns:
        str: Расширение файла в нижнем регистре (без точки), или None если расширения нет

    Examples:
        >>> get_file_extension('document.pdf')
        'pdf'

        >>> get_file_extension('archive.tar.gz')
        'gz'

        >>> get_file_extension('README')
        None
    """
    if not filename or not isinstance(filename, str):
        return None

    if '.' not in filename:
        return None

    return filename.rsplit('.', 1)[-1].lower()


def is_allowed_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Проверяет, разрешено ли расширение файла.

    Args:
        filename: Имя файла
        allowed_extensions: Список разрешенных расширений (без точки)

    Returns:
        bool: True если расширение разрешено, False иначе

    Examples:
        >>> is_allowed_file_extension('document.pdf', ['pdf', 'doc', 'docx'])
        True

        >>> is_allowed_file_extension('script.exe', ['pdf', 'doc', 'docx'])
        False
    """
    extension = get_file_extension(filename)
    if not extension:
        return False

    # Нормализуем allowed_extensions к нижнему регистру
    allowed_extensions_lower = [ext.lower() for ext in allowed_extensions]

    return extension in allowed_extensions_lower
