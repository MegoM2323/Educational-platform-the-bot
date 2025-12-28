"""
Services for chat system.

Includes:
- pachca_service: Pachca API integration for forum message notifications
- file_validation: File validation for forum attachments
"""

from .pachca_service import PachcaService
from .file_validation import (
    validate_attachment,
    ForumAttachmentValidator,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)

__all__ = [
    'PachcaService',
    'validate_attachment',
    'ForumAttachmentValidator',
    'ALLOWED_EXTENSIONS',
    'MAX_FILE_SIZE',
]
