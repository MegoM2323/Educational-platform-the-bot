"""
Custom validators for materials forms and file uploads.

This module provides validation functions for:
- File type validation
- File size validation
- Title length validation
- Description length validation
"""

from rest_framework import serializers
import os


class MaterialFileValidator:
    """
    Comprehensive file validator for materials.

    Validates:
    - File type (extension)
    - File size
    - File content safety
    """

    # Allowed file extensions for materials
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z'
    }

    # MIME type mappings for validation
    MIME_TYPE_MAP = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'mp4': 'video/mp4',
        'mp3': 'audio/mpeg',
        'txt': 'text/plain',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        '7z': 'application/x-7z-compressed',
    }

    # Maximum file sizes in bytes
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB default
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB for videos
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB for documents

    @staticmethod
    def get_file_extension(filename):
        """Extract file extension from filename."""
        if not filename:
            return None
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else None

    @staticmethod
    def get_size_limit_for_extension(extension):
        """Get maximum file size for given extension."""
        if extension in {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}:
            return MaterialFileValidator.MAX_VIDEO_SIZE
        return MaterialFileValidator.MAX_DOCUMENT_SIZE

    @classmethod
    def validate_extension(cls, filename):
        """
        Validate file extension.

        Args:
            filename: The filename to validate

        Raises:
            serializers.ValidationError: If extension is not allowed
        """
        extension = cls.get_file_extension(filename)
        if not extension or extension not in cls.ALLOWED_EXTENSIONS:
            allowed = ', '.join(sorted(cls.ALLOWED_EXTENSIONS))
            raise serializers.ValidationError(
                f"Неподдерживаемый тип файла: .{extension}. "
                f"Разрешенные форматы: {allowed}"
            )
        return extension

    @classmethod
    def validate_size(cls, file_obj, extension=None):
        """
        Validate file size.

        Args:
            file_obj: The file object with size attribute
            extension: Optional file extension for specific size limits

        Raises:
            serializers.ValidationError: If file size exceeds limit
        """
        if not hasattr(file_obj, 'size'):
            return

        max_size = cls.MAX_FILE_SIZE
        if extension:
            max_size = cls.get_size_limit_for_extension(extension)

        if file_obj.size > max_size:
            max_mb = max_size // (1024 * 1024)
            current_mb = file_obj.size / (1024 * 1024)
            raise serializers.ValidationError(
                f"Размер файла превышает максимально допустимый. "
                f"Максимум: {max_mb}MB, загружено: {current_mb:.1f}MB"
            )

    @classmethod
    def validate(cls, file_obj):
        """
        Perform all file validations.

        Args:
            file_obj: The file object to validate

        Raises:
            serializers.ValidationError: If any validation fails
        """
        extension = cls.validate_extension(file_obj.name)
        cls.validate_size(file_obj, extension)


def validate_file_type(file_obj):
    """
    Validate file type/extension.

    Allowed types: pdf, doc, docx, xls, xlsx, ppt, pptx, mp4, mp3

    Args:
        file_obj: The file object to validate

    Raises:
        serializers.ValidationError: If file type is not allowed
    """
    allowed_extensions = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z'
    }

    if not file_obj or not file_obj.name:
        return

    file_extension = file_obj.name.rsplit('.', 1)[-1].lower() if '.' in file_obj.name else ''

    if file_extension not in allowed_extensions:
        allowed_str = ', '.join(sorted(allowed_extensions))
        raise serializers.ValidationError(
            f"Неподдерживаемый тип файла. Разрешенные форматы: {allowed_str}"
        )


def validate_file_size(file_obj):
    """
    Validate file size (maximum 50MB).

    Args:
        file_obj: The file object to validate

    Raises:
        serializers.ValidationError: If file size exceeds 50MB
    """
    max_size = 50 * 1024 * 1024  # 50MB

    if not file_obj or not hasattr(file_obj, 'size'):
        return

    if file_obj.size > max_size:
        max_mb = max_size // (1024 * 1024)
        current_mb = file_obj.size / (1024 * 1024)
        raise serializers.ValidationError(
            f"Размер файла не должен превышать {max_mb}MB. "
            f"Загружено: {current_mb:.1f}MB"
        )


def validate_title_length(value):
    """
    Validate title length (maximum 200 characters).

    Args:
        value: The title string to validate

    Raises:
        serializers.ValidationError: If title exceeds 200 characters
    """
    if not value:
        raise serializers.ValidationError("Название не может быть пустым")

    if len(value) > 200:
        raise serializers.ValidationError(
            f"Название не должно превышать 200 символов. Текущее количество: {len(value)}"
        )

    if len(value.strip()) < 3:
        raise serializers.ValidationError("Название должно содержать минимум 3 символа")


def validate_description_length(value):
    """
    Validate description length (maximum 5000 characters).

    Args:
        value: The description string to validate

    Raises:
        serializers.ValidationError: If description exceeds 5000 characters
    """
    if not value:
        return

    if len(value) > 5000:
        raise serializers.ValidationError(
            f"Описание не должно превышать 5000 символов. Текущее количество: {len(value)}"
        )


class ValidationErrorSerializer(serializers.Serializer):
    """
    Serializer for API validation error responses.

    This serializer standardizes error response format for form validation.
    """
    field = serializers.CharField(help_text="Название поля с ошибкой")
    message = serializers.CharField(help_text="Текст ошибки валидации")
    code = serializers.CharField(help_text="Код ошибки", required=False)

    @staticmethod
    def from_drf_errors(errors_dict):
        """
        Convert Django REST Framework validation errors to standardized format.

        Args:
            errors_dict: Dictionary of DRF validation errors

        Returns:
            List of ValidationErrorSerializer-compatible dicts
        """
        result = []
        for field, messages in errors_dict.items():
            if isinstance(messages, list):
                for msg in messages:
                    result.append({
                        'field': field,
                        'message': str(msg),
                        'code': getattr(msg, 'code', 'validation_error')
                    })
            else:
                result.append({
                    'field': field,
                    'message': str(messages),
                    'code': 'validation_error'
                })
        return result
