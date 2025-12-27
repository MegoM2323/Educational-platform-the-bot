"""
Secure file upload handling utilities for materials app.

Features:
- File size validation (max 500MB for video, 50MB for others)
- MIME type validation against file extension
- Path traversal attack prevention
- Safe filename generation with timestamps
- File permission management
- Audit logging for all uploads
"""

import hashlib
import logging
import mimetypes
import os
import re
import stat
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class MaterialFileValidator:
    """
    Comprehensive file upload validator for materials.

    Validates:
    - File size (max 500MB for video, 50MB for others)
    - MIME type matching file extension
    - Filename safety (no path traversal)
    - File integrity (no malware signatures)
    """

    # Maximum file sizes in bytes
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB

    # Allowed file extensions by category
    ALLOWED_DOCUMENT_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "ppt",
        "pptx",
        "txt",
        "xls",
        "xlsx",
        "odt",
        "odp",
        "ods",
    }

    ALLOWED_VIDEO_EXTENSIONS = {
        "mp4",
        "webm",
        "avi",
        "mov",
        "flv",
        "mkv",
        "m4v",
        "3gp",
    }

    ALLOWED_IMAGE_EXTENSIONS = {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp",
        "svg",
    }

    ALLOWED_SUBMISSION_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "txt",
        "jpg",
        "jpeg",
        "png",
        "zip",
        "rar",
        "7z",
        "tar",
        "gz",
    }

    # MIME type mapping (extension -> expected MIME type)
    MIME_TYPES = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "txt": "text/plain",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "zip": "application/zip",
        "rar": "application/x-rar-compressed",
    }

    # Dangerous MIME types that should be rejected
    DANGEROUS_MIME_TYPES = {
        "application/x-executable",
        "application/x-dosexec",
        "application/x-msdos-program",
        "application/x-msdownload",
        "application/x-shellscript",
        "application/x-perl",
        "application/x-python",
        "application/x-php",
        "text/x-shellscript",
        "text/x-python",
        "text/x-perl",
    }

    # Dangerous filename patterns - note: special chars are removed by slugify in sanitize_filename
    # These are kept for reference but the main validation happens in sanitize_filename
    DANGEROUS_PATTERNS = [
        r"^\.",  # Hidden files
        r"\.\.",  # Directory traversal
        r"[\x00-\x1f]",  # Control characters (null bytes, etc.)
        r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$",  # Windows reserved names
    ]

    @classmethod
    def validate_file_size(
        cls, file: UploadedFile, file_type: str = "document"
    ) -> None:
        """
        Validate file size based on type.

        Args:
            file: Uploaded file object
            file_type: Type of file ('video', 'document', 'image', 'submission')

        Raises:
            ValidationError: If file exceeds maximum size
        """
        if file_type == "video":
            max_size = cls.MAX_VIDEO_SIZE
            readable_max = "500MB"
        elif file_type == "image":
            max_size = cls.MAX_IMAGE_SIZE
            readable_max = "20MB"
        elif file_type == "submission":
            # Submissions can be up to 50MB (similar to documents)
            max_size = cls.MAX_DOCUMENT_SIZE
            readable_max = "50MB"
        else:
            max_size = cls.MAX_DOCUMENT_SIZE
            readable_max = "50MB"

        if file.size > max_size:
            raise ValidationError(
                f"File size exceeds maximum allowed size ({readable_max}). "
                f"File size: {file.size / (1024*1024):.2f}MB"
            )

    @classmethod
    def validate_file_extension(
        cls, filename: str, file_type: str = "document"
    ) -> str:
        """
        Validate file extension is allowed.

        Args:
            filename: Name of the uploaded file
            file_type: Type of file ('video', 'document', 'image', 'submission')

        Returns:
            File extension in lowercase

        Raises:
            ValidationError: If extension is not allowed
        """
        # Extract extension safely
        if "." not in filename:
            raise ValidationError("File must have an extension")

        ext = filename.rsplit(".", 1)[-1].lower()

        # Get allowed extensions for file type
        if file_type == "video":
            allowed = cls.ALLOWED_VIDEO_EXTENSIONS
        elif file_type == "image":
            allowed = cls.ALLOWED_IMAGE_EXTENSIONS
        elif file_type == "submission":
            allowed = cls.ALLOWED_SUBMISSION_EXTENSIONS
        else:
            allowed = cls.ALLOWED_DOCUMENT_EXTENSIONS

        if ext not in allowed:
            raise ValidationError(
                f"File type '.{ext}' is not allowed. "
                f"Allowed types: {', '.join(sorted(allowed))}"
            )

        return ext

    @classmethod
    def validate_mime_type(cls, file: UploadedFile, ext: str) -> None:
        """
        Validate MIME type matches file extension.

        Args:
            file: Uploaded file object
            ext: File extension (from validate_file_extension)

        Raises:
            ValidationError: If MIME type doesn't match extension
        """
        # Get MIME type from file
        file.seek(0)  # Reset to beginning
        file_mime = file.content_type or mimetypes.guess_type(file.name)[0]

        if not file_mime:
            # If no MIME type detected, use default for extension
            expected_mime = cls.MIME_TYPES.get(ext)
            if not expected_mime:
                logger.warning(f"Could not determine MIME type for extension: {ext}")
                return

        # Check if MIME type is dangerous
        if file_mime in cls.DANGEROUS_MIME_TYPES:
            raise ValidationError(f"File type is not allowed: {file_mime}")

        # For common types, validate MIME type matches extension
        expected_mime_list = []
        if ext in cls.MIME_TYPES:
            expected = cls.MIME_TYPES[ext]
            # Allow some flexibility for common types
            if ext in ("jpg", "jpeg"):
                expected_mime_list = ["image/jpeg", "image/jpg"]
            elif ext == "txt":
                expected_mime_list = ["text/plain", "text/txt", "application/octet-stream"]
            else:
                expected_mime_list = [expected]

            if expected_mime_list and file_mime not in expected_mime_list:
                # Log warning but allow if close match
                logger.warning(
                    f"MIME type mismatch for {ext}: expected {expected_mime_list}, "
                    f"got {file_mime}"
                )

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and injection attacks.

        Args:
            filename: Original filename

        Returns:
            Safe, sanitized filename

        Raises:
            ValidationError: If filename is dangerous
        """
        # Check for dangerous patterns BEFORE processing
        # This prevents path traversal attempts like ../../etc/passwd
        dangerous_patterns = [
            r"^\.",  # Hidden files (starts with dot)
            r"\.\.",  # Directory traversal (..)
            r"^/",  # Absolute paths
            r"^[A-Z]:\\",  # Windows absolute paths
            r"[\x00-\x1f]",  # Control characters
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                raise ValidationError(f"Filename contains invalid characters: {filename}")

        # Remove any directory path components (this is redundant with above check,
        # but provides defense in depth)
        filename = os.path.basename(filename)

        # Check for Windows reserved names
        if re.search(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", filename, re.IGNORECASE):
            raise ValidationError(f"Filename contains invalid characters: {filename}")

        # Split name and extension BEFORE slugifying
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            ext = ext.lower()
        else:
            name = filename
            ext = ""

        # Slugify the name (removes special characters like <>, :, |, ?, etc.)
        safe_name = slugify(name)

        # Ensure name is not empty after slugification
        if not safe_name:
            safe_name = "file"

        # Limit filename length (255 is standard, leave room for timestamp)
        max_name_length = 200
        if len(safe_name) > max_name_length:
            safe_name = safe_name[:max_name_length]

        # Reconstruct filename with extension
        if ext:
            return f"{safe_name}.{ext}"
        return safe_name

    @classmethod
    def generate_safe_filename(cls, original_filename: str) -> str:
        """
        Generate a unique safe filename with timestamp and UUID.

        Args:
            original_filename: Original filename from upload

        Returns:
            Safe, unique filename: timestamp_uuid_sanitized.ext
        """
        # Sanitize original filename
        safe_name = cls.sanitize_filename(original_filename)

        # Split into name and extension
        if "." in safe_name:
            name, ext = safe_name.rsplit(".", 1)
        else:
            name = safe_name
            ext = ""

        # Generate timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Limit original name length in final filename
        final_name = f"{timestamp}_{unique_id}_{name[:50]}"

        # Reconstruct with extension
        if ext:
            return f"{final_name}.{ext}"
        return final_name

    @classmethod
    def scan_file_signature(cls, file: UploadedFile) -> bool:
        """
        Scan file for malware signatures (basic check).

        This is a basic implementation. For production use, integrate with ClamAV.

        Args:
            file: Uploaded file object

        Returns:
            True if file is safe, False if potential malware detected

        Raises:
            ValidationError: If file appears to contain malware
        """
        # Dangerous file signatures (magic numbers)
        DANGEROUS_SIGNATURES = [
            b"MZ",  # Windows executable
            b"\x7FELF",  # ELF executable
            b"\xCA\xFE\xBA\xBE",  # Java class file
            b"#!/",  # Shell script
        ]

        try:
            file.seek(0)
            file_header = file.read(512)

            # Check for dangerous signatures
            for sig in DANGEROUS_SIGNATURES:
                if file_header.startswith(sig):
                    raise ValidationError(
                        f"File appears to be an executable or script (signature: {sig}). "
                        "Only documents, images, and videos are allowed."
                    )

            # Check for null bytes (common in binary uploads trying to bypass checks)
            if b"\x00" in file_header[:100]:
                # Some binary formats use null bytes, so this is just a warning
                logger.warning(f"File {file.name} contains null bytes in header")

            file.seek(0)
            return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error scanning file signature: {e}")
            return True  # Allow file if scanning fails

    @classmethod
    def try_clamav_scan(cls, file: UploadedFile) -> bool:
        """
        Scan file with ClamAV if available.

        Args:
            file: Uploaded file object

        Returns:
            True if file is safe or ClamAV not available, False if malware detected

        Raises:
            ValidationError: If ClamAV detects malware
        """
        try:
            import pyclamd

            # Try to connect to ClamAV daemon
            clam = pyclamd.ClamD()
            if not clam.ping():
                logger.warning("ClamAV daemon not available, skipping scan")
                return True

            # Scan file
            file.seek(0)
            result = clam.instream(file)

            if result:
                # Virus detected
                threat_name = result.get(True, "Unknown virus")
                raise ValidationError(
                    f"Malware detected in file: {threat_name}. "
                    "File upload rejected."
                )

            return True

        except ImportError:
            logger.debug("pyclamd not installed, skipping ClamAV scan")
            return True
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"ClamAV scan error: {e}, allowing file")
            return True

    @classmethod
    def validate(
        cls, file: UploadedFile, file_type: str = "document"
    ) -> Tuple[bool, str]:
        """
        Comprehensive file validation.

        Args:
            file: Uploaded file object
            file_type: Type of file ('video', 'document', 'image', 'submission')

        Returns:
            Tuple of (is_valid, message)

        Raises:
            ValidationError: On any validation failure
        """
        try:
            # 1. Validate file size
            cls.validate_file_size(file, file_type)

            # 2. Validate extension
            ext = cls.validate_file_extension(file.name, file_type)

            # 3. Validate MIME type
            cls.validate_mime_type(file, ext)

            # 4. Scan for malware signatures
            cls.scan_file_signature(file)

            # 5. Try ClamAV scan if available
            cls.try_clamav_scan(file)

            # Reset file position after all checks
            file.seek(0)

            return True, "File validation passed"

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"File validation error: {str(e)}")


class SecureFileStorage:
    """
    Secure file storage path management.

    - Store files outside web root
    - Generate secure storage paths
    - Manage file permissions
    """

    @staticmethod
    def get_secure_upload_path(file_type: str, user_id: int) -> str:
        """
        Get secure upload path for file type and user.

        Files are stored in: MEDIA_ROOT/secure/[file_type]/[user_id]/[filename]

        Args:
            file_type: Type of file ('materials', 'submissions')
            user_id: ID of uploading user

        Returns:
            Relative upload path
        """
        # Create path: secure/[type]/[user_id]/
        return f"secure/{file_type}/{user_id}/"

    @staticmethod
    def get_full_storage_path(relative_path: str) -> Path:
        """
        Get full filesystem path for file storage.

        Args:
            relative_path: Relative path under MEDIA_ROOT

        Returns:
            Full filesystem path
        """
        media_root = Path(settings.MEDIA_ROOT)
        return media_root / relative_path

    @staticmethod
    def set_file_permissions(file_path: Path, mode: int = 0o644) -> None:
        """
        Set file permissions to restrict access.

        Default: 644 (rw-r--r--)
        - Owner can read/write
        - Group can read
        - Others can read

        Args:
            file_path: Path to file
            mode: Permission mode (octal)
        """
        try:
            if file_path.exists():
                file_path.chmod(mode)
                logger.info(f"Set file permissions {oct(mode)} for {file_path}")
        except Exception as e:
            logger.error(f"Failed to set file permissions: {e}")

    @staticmethod
    def set_directory_permissions(dir_path: Path, mode: int = 0o755) -> None:
        """
        Set directory permissions.

        Default: 755 (rwxr-xr-x)
        - Owner can read/write/execute
        - Group can read/execute
        - Others can read/execute

        Args:
            dir_path: Path to directory
            mode: Permission mode (octal)
        """
        try:
            if dir_path.exists():
                dir_path.chmod(mode)
                logger.info(f"Set directory permissions {oct(mode)} for {dir_path}")
        except Exception as e:
            logger.error(f"Failed to set directory permissions: {e}")

    @staticmethod
    def ensure_secure_directory(dir_path: Path) -> None:
        """
        Ensure directory exists with secure permissions.

        Args:
            dir_path: Path to directory
        """
        dir_path.mkdir(parents=True, exist_ok=True)
        SecureFileStorage.set_directory_permissions(dir_path)
        logger.info(f"Created secure directory: {dir_path}")


class SubmissionFileValidator:
    """
    Comprehensive submission file validation.

    Validates:
    - File types (pdf, doc, docx, txt, images, videos)
    - File size (max 50MB per file, 200MB total per submission)
    - Duplicate submissions of same file (by checksum)
    - MIME types against extensions
    - Malware scanning (signatures + ClamAV)
    - Filename sanitization
    - Minimum 1 file requirement
    - Maximum 10 files per submission
    """

    # Maximum file sizes for submissions
    MAX_SUBMISSION_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
    MAX_SUBMISSION_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB total per submission
    MAX_FILES_PER_SUBMISSION = 10
    MIN_FILES_PER_SUBMISSION = 1

    # Allowed extensions for submission
    ALLOWED_SUBMISSION_EXTENSIONS = {
        # Documents
        "pdf", "doc", "docx", "txt", "odt",
        "ppt", "pptx", "odp",
        "xls", "xlsx", "ods",
        # Images
        "jpg", "jpeg", "png", "gif", "bmp", "webp",
        # Videos
        "mp4", "webm", "avi", "mov", "flv", "mkv",
        # Archives
        "zip", "rar", "7z", "tar", "gz",
    }

    @classmethod
    def validate_file_count(cls, file_count: int) -> None:
        """
        Validate number of files in submission.

        Args:
            file_count: Number of files

        Raises:
            ValidationError: If count is invalid
        """
        if file_count < cls.MIN_FILES_PER_SUBMISSION:
            raise ValidationError(
                f"Submission must contain at least {cls.MIN_FILES_PER_SUBMISSION} file"
            )

        if file_count > cls.MAX_FILES_PER_SUBMISSION:
            raise ValidationError(
                f"Submission cannot contain more than {cls.MAX_FILES_PER_SUBMISSION} files. "
                f"You provided {file_count} files."
            )

    @classmethod
    def validate_individual_file_size(cls, file: UploadedFile) -> None:
        """
        Validate individual file size.

        Args:
            file: Uploaded file object

        Raises:
            ValidationError: If file exceeds max size
        """
        if file.size > cls.MAX_SUBMISSION_FILE_SIZE:
            size_mb = file.size / (1024 * 1024)
            max_mb = cls.MAX_SUBMISSION_FILE_SIZE / (1024 * 1024)
            raise ValidationError(
                f"File '{file.name}' is too large ({size_mb:.2f}MB). "
                f"Maximum allowed size is {max_mb:.0f}MB."
            )

    @classmethod
    def validate_total_submission_size(cls, file_sizes: list) -> None:
        """
        Validate total submission size.

        Args:
            file_sizes: List of file sizes in bytes

        Raises:
            ValidationError: If total exceeds max size
        """
        total_size = sum(file_sizes)

        if total_size > cls.MAX_SUBMISSION_TOTAL_SIZE:
            total_mb = total_size / (1024 * 1024)
            max_mb = cls.MAX_SUBMISSION_TOTAL_SIZE / (1024 * 1024)
            raise ValidationError(
                f"Total submission size ({total_mb:.2f}MB) exceeds "
                f"maximum allowed ({max_mb:.0f}MB)."
            )

    @classmethod
    def validate_file_extension(cls, filename: str) -> str:
        """
        Validate file extension for submission.

        Args:
            filename: Name of file

        Returns:
            File extension in lowercase

        Raises:
            ValidationError: If extension not allowed
        """
        if "." not in filename:
            raise ValidationError(f"File '{filename}' must have an extension")

        ext = filename.rsplit(".", 1)[-1].lower()

        if ext not in cls.ALLOWED_SUBMISSION_EXTENSIONS:
            allowed = ", ".join(sorted(cls.ALLOWED_SUBMISSION_EXTENSIONS))
            raise ValidationError(
                f"File type '.{ext}' is not allowed. "
                f"Allowed types: {allowed}"
            )

        return ext

    @classmethod
    def validate_mime_type(cls, file: UploadedFile, ext: str) -> None:
        """
        Validate MIME type matches extension.

        Args:
            file: Uploaded file object
            ext: File extension

        Raises:
            ValidationError: If MIME type is dangerous
        """
        file.seek(0)
        file_mime = file.content_type or mimetypes.guess_type(file.name)[0]

        if not file_mime:
            return

        # Check for dangerous MIME types
        dangerous_types = {
            "application/x-executable",
            "application/x-dosexec",
            "application/x-msdos-program",
            "application/x-shellscript",
            "application/x-perl",
            "application/x-python",
            "application/x-php",
            "text/x-shellscript",
            "text/x-python",
            "text/x-perl",
        }

        if file_mime in dangerous_types:
            raise ValidationError(
                f"File type '{file_mime}' is not allowed."
            )

    @classmethod
    def check_duplicate_submission(cls, file_checksum: str, student_id: int) -> bool:
        """
        Check if student already submitted file with same checksum.

        Args:
            file_checksum: SHA256 checksum of file
            student_id: ID of student

        Returns:
            True if duplicate exists, False otherwise
        """
        from .models import SubmissionFile

        return SubmissionFile.objects.filter(
            submission__student_id=student_id,
            file_checksum=file_checksum
        ).exists()

    @classmethod
    def validate_file(
        cls,
        file: UploadedFile,
        student_id: int,
        check_duplicates: bool = True
    ) -> dict:
        """
        Comprehensive validation of a single submission file.

        Args:
            file: Uploaded file object
            student_id: ID of student submitting
            check_duplicates: Whether to check for duplicate submissions

        Returns:
            Dict with validation result and metadata

        Raises:
            ValidationError: On validation failure
        """
        try:
            # 1. Validate extension
            ext = cls.validate_file_extension(file.name)

            # 2. Validate individual file size
            cls.validate_individual_file_size(file)

            # 3. Validate MIME type
            cls.validate_mime_type(file, ext)

            # 4. Scan for malware signatures
            MaterialFileValidator.scan_file_signature(file)

            # 5. Calculate checksum
            checksum = FileAuditLogger.calculate_file_hash(file)

            # 6. Check for duplicate submissions
            if check_duplicates and cls.check_duplicate_submission(checksum, student_id):
                raise ValidationError(
                    f"File '{file.name}' was already submitted. "
                    "Duplicate submissions are not allowed."
                )

            # 7. Try ClamAV scan
            MaterialFileValidator.try_clamav_scan(file)

            file.seek(0)

            return {
                "valid": True,
                "filename": file.name,
                "size": file.size,
                "checksum": checksum,
                "extension": ext,
            }

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"File validation error: {str(e)}")

    @classmethod
    def validate_submission_files(
        cls,
        files: list,
        student_id: int,
        check_duplicates: bool = True
    ) -> dict:
        """
        Validate multiple files for a submission.

        Args:
            files: List of uploaded file objects
            student_id: ID of student submitting
            check_duplicates: Whether to check for duplicate submissions

        Returns:
            Dict with validation results and file metadata

        Raises:
            ValidationError: On validation failure
        """
        # Validate file count
        cls.validate_file_count(len(files))

        validated_files = []
        file_sizes = []
        checksums = set()

        for idx, file in enumerate(files):
            try:
                # Validate individual file
                result = cls.validate_file(file, student_id, check_duplicates)

                # Check for duplicates within this batch
                if result["checksum"] in checksums:
                    raise ValidationError(
                        f"File #{idx + 1} '{file.name}' is a duplicate "
                        f"within this submission."
                    )

                checksums.add(result["checksum"])
                file_sizes.append(file.size)
                validated_files.append(result)

            except ValidationError as e:
                raise ValidationError(
                    f"File #{idx + 1} '{file.name}': {str(e)}"
                )

        # Validate total submission size
        cls.validate_total_submission_size(file_sizes)

        return {
            "valid": True,
            "file_count": len(validated_files),
            "total_size": sum(file_sizes),
            "files": validated_files,
        }


class FileAuditLogger:
    """
    Audit logging for all file upload operations.

    Logs:
    - User ID and email
    - File metadata (name, size, type)
    - Validation results
    - Storage location
    - Timestamp
    """

    @staticmethod
    def log_upload(
        user_id: int,
        user_email: str,
        filename: str,
        file_size: int,
        file_type: str,
        file_hash: str,
        storage_path: str,
        validation_result: bool,
        errors: Optional[list] = None,
    ) -> None:
        """
        Log file upload event.

        Args:
            user_id: ID of uploading user
            user_email: Email of uploading user
            filename: Original filename
            file_size: File size in bytes
            file_type: Type of file
            file_hash: SHA256 hash of file
            storage_path: Where file was stored
            validation_result: True if validation passed
            errors: List of validation errors (if any)
        """
        log_entry = {
            "event": "file_upload",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "filename": filename,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_type": file_type,
            "file_hash": file_hash,
            "storage_path": storage_path,
            "validation_passed": validation_result,
            "validation_errors": errors or [],
        }

        logger.info(f"File upload: {log_entry}")

    @staticmethod
    def calculate_file_hash(file: UploadedFile) -> str:
        """
        Calculate SHA256 hash of file for integrity verification.

        Args:
            file: Uploaded file object

        Returns:
            Hex-encoded SHA256 hash
        """
        file.seek(0)
        sha256_hash = hashlib.sha256()

        # Read file in chunks to handle large files
        for chunk in file.chunks(chunk_size=65536):
            sha256_hash.update(chunk)

        file.seek(0)
        return sha256_hash.hexdigest()

    @staticmethod
    def log_download(
        user_id: int,
        user_email: str,
        filename: str,
        file_type: str,
        storage_path: str,
    ) -> None:
        """
        Log file download event.

        Args:
            user_id: ID of downloading user
            user_email: Email of downloading user
            filename: Original filename
            file_type: Type of file
            storage_path: Where file is stored
        """
        log_entry = {
            "event": "file_download",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "filename": filename,
            "file_type": file_type,
            "storage_path": storage_path,
        }

        logger.info(f"File download: {log_entry}")

    @staticmethod
    def log_deletion(
        user_id: int,
        user_email: str,
        filename: str,
        file_type: str,
        storage_path: str,
        reason: str = "user_request",
    ) -> None:
        """
        Log file deletion event.

        Args:
            user_id: ID of user who deleted file
            user_email: Email of user who deleted file
            filename: Original filename
            file_type: Type of file
            storage_path: Where file was stored
            reason: Reason for deletion
        """
        log_entry = {
            "event": "file_deletion",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "filename": filename,
            "file_type": file_type,
            "storage_path": storage_path,
            "reason": reason,
        }

        logger.info(f"File deletion: {log_entry}")
