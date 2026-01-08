"""
Сервис валидации файлов для вложений форума.

Валидирует:
- Размер файла (максимум 10MB)
- Расширение файла
- MIME тип файла
"""

from django.core.exceptions import ValidationError
import os
import mimetypes


# Разрешенные расширения по категориям
ALLOWED_EXTENSIONS = {
    "image": ["jpg", "jpeg", "png", "gif", "webp"],
    "document": ["pdf", "doc", "docx", "xls", "xlsx", "txt"],
    "archive": ["zip", "rar", "7z"],
}

# Плоский список всех разрешенных расширений
ALL_ALLOWED_EXTENSIONS = set()
for extensions in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(extensions)

# Максимальный размер файла: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Соответствие расширений MIME типам
MIME_TYPE_MAP = {
    # Изображения
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "png": ["image/png"],
    "gif": ["image/gif"],
    "webp": ["image/webp"],
    # Документы
    "pdf": ["application/pdf"],
    "doc": ["application/msword"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    "xls": ["application/vnd.ms-excel"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    "txt": ["text/plain"],
    # Архивы
    "zip": ["application/zip", "application/x-zip-compressed"],
    "rar": ["application/x-rar-compressed", "application/vnd.rar"],
    "7z": ["application/x-7z-compressed"],
}


def get_file_extension(filename: str) -> str | None:
    """
    Извлекает расширение файла из имени.

    Args:
        filename: Имя файла

    Returns:
        Расширение файла в нижнем регистре или None
    """
    if not filename:
        return None
    if "." not in filename:
        return None
    return filename.rsplit(".", 1)[-1].lower()


def get_file_type(extension: str) -> str | None:
    """
    Определяет тип файла по расширению.

    Args:
        extension: Расширение файла

    Returns:
        Тип файла ('image', 'document', 'archive') или None
    """
    if not extension:
        return None

    extension = extension.lower()
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            return file_type
    return None


def validate_file_extension(filename: str) -> str:
    """
    Валидирует расширение файла.

    Args:
        filename: Имя файла

    Returns:
        Расширение файла в нижнем регистре

    Raises:
        ValidationError: Если расширение не разрешено
    """
    extension = get_file_extension(filename)

    if not extension:
        raise ValidationError(
            "Невозможно определить тип файла. Убедитесь, что файл имеет расширение."
        )

    if extension not in ALL_ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALL_ALLOWED_EXTENSIONS))
        raise ValidationError(
            f"Неподдерживаемый тип файла: .{extension}. "
            f"Разрешенные форматы: {allowed_str}"
        )

    return extension


def validate_file_size(file_obj) -> None:
    """
    Валидирует размер файла.

    Args:
        file_obj: Объект файла с атрибутом size

    Raises:
        ValidationError: Если размер превышает лимит
    """
    if not hasattr(file_obj, "size"):
        return

    if file_obj.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        current_mb = file_obj.size / (1024 * 1024)
        raise ValidationError(
            f"Размер файла превышает максимально допустимый. "
            f"Максимум: {max_mb}MB, загружено: {current_mb:.1f}MB"
        )


def validate_mime_type(file_obj, extension: str) -> None:
    """
    Валидирует MIME тип файла.

    Args:
        file_obj: Объект файла с атрибутом content_type
        extension: Расширение файла

    Raises:
        ValidationError: Если MIME тип не соответствует расширению
    """
    if not hasattr(file_obj, "content_type") or not file_obj.content_type:
        return

    if extension not in MIME_TYPE_MAP:
        return

    allowed_mimes = MIME_TYPE_MAP[extension]
    content_type = file_obj.content_type.lower()

    # Проверяем точное соответствие или начало (для типов с параметрами)
    mime_matches = any(
        content_type == mime or content_type.startswith(mime + ";")
        for mime in allowed_mimes
    )

    if not mime_matches:
        raise ValidationError(
            f"Тип содержимого файла ({content_type}) не соответствует расширению .{extension}. "
            f"Ожидаемые типы: {', '.join(allowed_mimes)}"
        )


def validate_attachment(file_obj) -> str:
    """
    Полная валидация вложения форума.

    Проверяет:
    - Размер файла (максимум 10MB)
    - Расширение файла
    - MIME тип файла

    Args:
        file_obj: Объект файла для валидации (с атрибутами name, size, content_type)

    Returns:
        Тип файла ('image', 'document', 'archive')

    Raises:
        ValidationError: Если файл не прошел валидацию
    """
    if not file_obj:
        raise ValidationError("Файл не предоставлен")

    if not hasattr(file_obj, "name") or not file_obj.name:
        raise ValidationError("Имя файла не определено")

    # Валидация размера
    validate_file_size(file_obj)

    # Валидация расширения
    extension = validate_file_extension(file_obj.name)

    # Валидация MIME типа
    validate_mime_type(file_obj, extension)

    # Определение типа файла
    file_type = get_file_type(extension)

    if not file_type:
        raise ValidationError(
            f"Не удалось определить тип файла для расширения .{extension}"
        )

    return file_type


class ForumAttachmentValidator:
    """
    Класс-валидатор для вложений форума.

    Предоставляет статические методы для валидации и получения информации о файлах.
    """

    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    ALL_ALLOWED_EXTENSIONS = ALL_ALLOWED_EXTENSIONS
    MAX_FILE_SIZE = MAX_FILE_SIZE
    MIME_TYPE_MAP = MIME_TYPE_MAP

    @classmethod
    def validate(cls, file_obj) -> str:
        """
        Валидирует файл вложения.

        Args:
            file_obj: Объект файла для валидации

        Returns:
            Тип файла ('image', 'document', 'archive')

        Raises:
            ValidationError: Если файл не прошел валидацию
        """
        return validate_attachment(file_obj)

    @classmethod
    def get_file_type(cls, filename: str) -> str | None:
        """
        Определяет тип файла по имени.

        Args:
            filename: Имя файла

        Returns:
            Тип файла или None
        """
        extension = get_file_extension(filename)
        return get_file_type(extension)

    @classmethod
    def is_allowed(cls, filename: str) -> bool:
        """
        Проверяет, разрешен ли файл.

        Args:
            filename: Имя файла

        Returns:
            True если файл разрешен, False иначе
        """
        extension = get_file_extension(filename)
        return extension in cls.ALL_ALLOWED_EXTENSIONS if extension else False

    @classmethod
    def get_max_size_mb(cls) -> int:
        """
        Возвращает максимальный размер файла в мегабайтах.

        Returns:
            Максимальный размер в MB
        """
        return cls.MAX_FILE_SIZE // (1024 * 1024)

    @classmethod
    def get_allowed_extensions_string(cls) -> str:
        """
        Возвращает строку со всеми разрешенными расширениями.

        Returns:
            Строка с расширениями через запятую
        """
        return ", ".join(sorted(cls.ALL_ALLOWED_EXTENSIONS))
