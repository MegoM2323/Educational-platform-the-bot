"""
Services for chat system.

Includes:
- pachca_service: Pachca API integration for forum message notifications
- file_validation: File validation for forum attachments
- chat_service: Main chat service with business logic
- chat_service_new: New chat service architecture
"""

from .pachca_service import PachcaService
from .file_validation import (
    validate_attachment,
    ForumAttachmentValidator,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)
from .chat_service import ChatService
from .chat_service_new import ChatServiceNew

__all__ = [
    "PachcaService",
    "validate_attachment",
    "ForumAttachmentValidator",
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE",
    "ChatService",
    "ChatServiceNew",
]
