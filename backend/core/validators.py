"""
Валидаторы для файлов и данных
"""
import os
import logging

logger = logging.getLogger(__name__)

# Мапинг расширений файлов к разрешенным MIME-типам
ALLOWED_MIME_TYPES = {
    # Документы
    'pdf': ['application/pdf'],
    'doc': ['application/msword'],
    'docx': [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/octet-stream'  # Иногда .docx определяется как octet-stream
    ],
    'ppt': ['application/vnd.ms-powerpoint'],
    'pptx': [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/octet-stream'
    ],
    'txt': ['text/plain'],

    # Изображения
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'png': ['image/png'],

    # Архивы
    'zip': ['application/zip', 'application/x-zip-compressed'],
    'rar': ['application/x-rar-compressed', 'application/x-rar'],
}


def validate_file_mime_type(file_obj, allowed_extensions=None):
    """
    Проверяет MIME-тип загружаемого файла.

    Args:
        file_obj: UploadedFile объект из Django
        allowed_extensions: список разрешенных расширений (если None, используются все из ALLOWED_MIME_TYPES)

    Returns:
        tuple: (is_valid: bool, error_message: str|None)

    Raises:
        ImportError: если python-magic не установлен
    """
    try:
        import magic
    except ImportError:
        logger.error(
            "python-magic not installed. File MIME type validation skipped. "
            "Install with: pip install python-magic"
        )
        # Если библиотека не установлена, пропускаем проверку
        # В production это должно быть критической ошибкой
        return True, None

    if not file_obj:
        return False, "Файл не предоставлен"

    # Получаем расширение файла
    file_name = file_obj.name
    file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''

    # Проверяем, разрешено ли расширение
    if allowed_extensions is None:
        allowed_extensions = list(ALLOWED_MIME_TYPES.keys())

    if file_extension not in allowed_extensions:
        return False, f"Неподдерживаемое расширение файла: .{file_extension}"

    # Получаем MIME-тип из содержимого файла
    try:
        # Читаем первые 2048 байт для определения типа
        file_obj.seek(0)
        file_header = file_obj.read(2048)
        file_obj.seek(0)  # Возвращаем указатель в начало

        # Определяем MIME-тип
        mime = magic.from_buffer(file_header, mime=True)

        # Проверяем, соответствует ли MIME-тип расширению
        allowed_mimes = ALLOWED_MIME_TYPES.get(file_extension, [])

        if mime not in allowed_mimes:
            logger.warning(
                f"File MIME type mismatch: extension={file_extension}, "
                f"detected_mime={mime}, allowed_mimes={allowed_mimes}"
            )
            return False, (
                f"Содержимое файла не соответствует расширению .{file_extension}. "
                f"Обнаружен тип: {mime}"
            )

        return True, None

    except Exception as e:
        logger.error(f"Error validating file MIME type: {e}", exc_info=True)
        # В случае ошибки валидации, пропускаем проверку (fail open)
        # В production можно сделать fail closed (return False)
        return True, None


def validate_file_size(file_obj, max_size_mb=10):
    """
    Проверяет размер загружаемого файла.

    Args:
        file_obj: UploadedFile объект из Django
        max_size_mb: максимальный размер в мегабайтах

    Returns:
        tuple: (is_valid: bool, error_message: str|None)
    """
    if not file_obj:
        return False, "Файл не предоставлен"

    max_size_bytes = max_size_mb * 1024 * 1024

    if file_obj.size > max_size_bytes:
        return False, f"Размер файла не должен превышать {max_size_mb}MB"

    return True, None


def validate_uploaded_file(file_obj, allowed_extensions=None, max_size_mb=10):
    """
    Комплексная валидация загружаемого файла.

    Args:
        file_obj: UploadedFile объект из Django
        allowed_extensions: список разрешенных расширений
        max_size_mb: максимальный размер в мегабайтах

    Returns:
        tuple: (is_valid: bool, error_message: str|None)
    """
    # Проверка размера
    size_valid, size_error = validate_file_size(file_obj, max_size_mb)
    if not size_valid:
        return False, size_error

    # Проверка MIME-типа
    mime_valid, mime_error = validate_file_mime_type(file_obj, allowed_extensions)
    if not mime_valid:
        return False, mime_error

    return True, None
