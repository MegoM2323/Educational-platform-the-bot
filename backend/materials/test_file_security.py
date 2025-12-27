"""
Security tests for Material file upload handling.

Tests:
- File size validation
- MIME type validation
- Path traversal prevention
- Malicious filename handling
- File permission setting
- Audit logging
"""

import os
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from materials.utils import FileAuditLogger, MaterialFileValidator, SecureFileStorage


class TestMaterialFileValidator:
    """Test MaterialFileValidator security features"""

    def test_validate_file_size_document(self):
        """Test document file size validation (50MB limit)"""
        # Create file just under limit - should pass
        content = b"x" * (49 * 1024 * 1024)
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        # Should not raise
        MaterialFileValidator.validate_file_size(file, file_type="document")

    def test_validate_file_size_exceeds_document_limit(self):
        """Test document file size exceeds limit"""
        # Create file over 50MB limit
        content = b"x" * (51 * 1024 * 1024)
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.validate_file_size(file, file_type="document")

        assert "exceeds maximum" in str(exc_info.value)
        assert "50MB" in str(exc_info.value)

    def test_validate_file_size_video(self):
        """Test video file size validation (500MB limit)"""
        # Create video file just under limit
        content = b"x" * (499 * 1024 * 1024)
        file = SimpleUploadedFile("test.mp4", content, content_type="video/mp4")

        # Should not raise
        MaterialFileValidator.validate_file_size(file, file_type="video")

    def test_validate_file_size_exceeds_video_limit(self):
        """Test video file exceeds size limit"""
        # Create video file over 500MB
        content = b"x" * (501 * 1024 * 1024)
        file = SimpleUploadedFile("test.mp4", content, content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.validate_file_size(file, file_type="video")

        assert "exceeds maximum" in str(exc_info.value)

    def test_validate_file_extension_allowed(self):
        """Test file extension validation - allowed type"""
        ext = MaterialFileValidator.validate_file_extension("document.pdf", file_type="document")
        assert ext == "pdf"

    def test_validate_file_extension_not_allowed(self):
        """Test file extension validation - not allowed type"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.validate_file_extension("script.exe", file_type="document")

        assert "not allowed" in str(exc_info.value)

    def test_validate_file_extension_no_extension(self):
        """Test file without extension"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.validate_file_extension("filewithoutext", file_type="document")

        assert "must have an extension" in str(exc_info.value)

    def test_validate_file_extension_case_insensitive(self):
        """Test file extension validation is case-insensitive"""
        ext = MaterialFileValidator.validate_file_extension("document.PDF", file_type="document")
        assert ext == "pdf"

        ext = MaterialFileValidator.validate_file_extension("image.PNG", file_type="image")
        assert ext == "png"

    def test_validate_mime_type_matching(self):
        """Test MIME type validation - correct type"""
        file = SimpleUploadedFile(
            "test.pdf", b"PDF content", content_type="application/pdf"
        )

        # Should not raise
        MaterialFileValidator.validate_mime_type(file, "pdf")

    def test_validate_mime_type_dangerous(self):
        """Test MIME type validation - dangerous type"""
        file = SimpleUploadedFile(
            "test.exe", b"EXECUTABLE", content_type="application/x-executable"
        )

        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.validate_mime_type(file, "exe")

        assert "not allowed" in str(exc_info.value)

    def test_sanitize_filename_removes_path(self):
        """Test filename sanitization removes directory paths"""
        result = MaterialFileValidator.sanitize_filename("../../etc/passwd.txt")
        assert ".." not in result
        assert "/" not in result
        assert "passwd" in result.lower()

    def test_sanitize_filename_removes_special_chars(self):
        """Test filename sanitization removes special characters"""
        result = MaterialFileValidator.sanitize_filename("file<>:|?.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result

    def test_sanitize_filename_removes_hidden_file(self):
        """Test filename sanitization rejects hidden files"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.sanitize_filename(".bashrc")

        assert "invalid" in str(exc_info.value)

    def test_sanitize_filename_windows_reserved(self):
        """Test filename sanitization rejects Windows reserved names"""
        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("CON.txt")

        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("PRN.pdf")

    def test_generate_safe_filename_contains_timestamp(self):
        """Test safe filename generation includes timestamp"""
        filename = MaterialFileValidator.generate_safe_filename("document.pdf")
        # Format: timestamp_uuid_name.ext
        assert "_" in filename
        assert ".pdf" in filename
        assert len(filename) > 10

    def test_generate_safe_filename_unique(self):
        """Test safe filename generation creates unique names"""
        filename1 = MaterialFileValidator.generate_safe_filename("document.pdf")
        filename2 = MaterialFileValidator.generate_safe_filename("document.pdf")

        # Should be different due to UUID
        assert filename1 != filename2

    def test_generate_safe_filename_length(self):
        """Test safe filename generation respects length limits"""
        long_name = "a" * 300 + ".pdf"
        filename = MaterialFileValidator.generate_safe_filename(long_name)

        # Should be under filesystem limit (usually 255)
        assert len(filename) <= 255

    def test_scan_file_signature_executable(self):
        """Test file signature scanning detects executables"""
        # MZ is executable signature
        content = b"MZ" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.scan_file_signature(file)

        assert "executable" in str(exc_info.value).lower()

    def test_scan_file_signature_shell_script(self):
        """Test file signature scanning detects shell scripts"""
        # Shell script signature
        content = b"#!/bin/bash" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        with pytest.raises(ValidationError) as exc_info:
            MaterialFileValidator.scan_file_signature(file)

        assert "executable or script" in str(exc_info.value).lower()

    def test_scan_file_signature_safe_file(self):
        """Test file signature scanning allows safe files"""
        # Regular PDF content
        content = b"%PDF-1.4" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        # Should not raise
        result = MaterialFileValidator.scan_file_signature(file)
        assert result is True

    def test_validate_comprehensive(self):
        """Test comprehensive validation flow"""
        content = b"%PDF-1.4" + b"x" * 1000
        file = SimpleUploadedFile("document.pdf", content, content_type="application/pdf")

        # Should pass all checks
        is_valid, message = MaterialFileValidator.validate(file, file_type="document")
        assert is_valid is True
        assert "passed" in message

    def test_validate_comprehensive_failure(self):
        """Test comprehensive validation flow with failure"""
        # File too large
        content = b"x" * (51 * 1024 * 1024)
        file = SimpleUploadedFile("document.pdf", content, content_type="application/pdf")

        with pytest.raises(ValidationError):
            MaterialFileValidator.validate(file, file_type="document")

    def test_validate_submission_file_type(self):
        """Test submission file type validation"""
        # Submit ZIP file which is allowed for submissions
        content = b"PK" + b"x" * 100  # ZIP signature
        file = SimpleUploadedFile("archive.zip", content, content_type="application/zip")

        # Should pass
        is_valid, message = MaterialFileValidator.validate(file, file_type="submission")
        assert is_valid is True


class TestSecureFileStorage:
    """Test SecureFileStorage secure path management"""

    def test_get_secure_upload_path(self):
        """Test secure upload path generation"""
        path = SecureFileStorage.get_secure_upload_path("materials", user_id=123)
        assert "secure" in path
        assert "materials" in path
        assert "123" in path
        assert path.startswith("secure/")

    def test_get_secure_upload_path_submissions(self):
        """Test secure upload path for submissions"""
        path = SecureFileStorage.get_secure_upload_path("submissions", user_id=456)
        assert "secure/submissions/456/" == path

    def test_get_full_storage_path(self):
        """Test full storage path calculation"""
        with patch("materials.utils.settings") as mock_settings:
            mock_settings.MEDIA_ROOT = "/media"
            full_path = SecureFileStorage.get_full_storage_path("secure/materials/123/file.pdf")

            assert isinstance(full_path, Path)
            assert "secure/materials/123/file.pdf" in str(full_path)

    def test_set_file_permissions(self):
        """Test file permission setting"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"test content")

        try:
            SecureFileStorage.set_file_permissions(tmp_path, mode=0o644)

            # Check permissions were set
            mode = tmp_path.stat().st_mode
            # Extract last 3 octal digits
            perms = mode & 0o777
            assert perms == 0o644

        finally:
            tmp_path.unlink()

    def test_set_directory_permissions(self):
        """Test directory permission setting"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)

            SecureFileStorage.set_directory_permissions(dir_path, mode=0o755)

            mode = dir_path.stat().st_mode
            perms = mode & 0o777
            assert perms == 0o755

    def test_ensure_secure_directory(self):
        """Test secure directory creation"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            new_dir = Path(tmp_dir) / "secure" / "materials"

            # Directory doesn't exist yet
            assert not new_dir.exists()

            SecureFileStorage.ensure_secure_directory(new_dir)

            # Directory should be created
            assert new_dir.exists()
            assert new_dir.is_dir()


class TestFileAuditLogger:
    """Test file audit logging functionality"""

    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        content = b"test file content"
        file = SimpleUploadedFile("test.txt", content)

        hash_value = FileAuditLogger.calculate_file_hash(file)

        # Should be SHA256 hex (64 chars)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_calculate_file_hash_consistent(self):
        """Test file hash is consistent"""
        content = b"test file content"
        file1 = SimpleUploadedFile("test.txt", content)
        file2 = SimpleUploadedFile("test.txt", content)

        hash1 = FileAuditLogger.calculate_file_hash(file1)
        hash2 = FileAuditLogger.calculate_file_hash(file2)

        assert hash1 == hash2

    def test_calculate_file_hash_different_content(self):
        """Test file hash differs for different content"""
        file1 = SimpleUploadedFile("test.txt", b"content1")
        file2 = SimpleUploadedFile("test.txt", b"content2")

        hash1 = FileAuditLogger.calculate_file_hash(file1)
        hash2 = FileAuditLogger.calculate_file_hash(file2)

        assert hash1 != hash2

    @patch("materials.utils.logger")
    def test_log_upload(self, mock_logger):
        """Test upload logging"""
        FileAuditLogger.log_upload(
            user_id=1,
            user_email="test@example.com",
            filename="test.pdf",
            file_size=10240,
            file_type="document",
            file_hash="abc123",
            storage_path="/secure/materials/1/test.pdf",
            validation_result=True,
        )

        # Should log the event
        mock_logger.info.assert_called_once()
        call_args = str(mock_logger.info.call_args)
        assert "file_upload" in call_args
        assert "test@example.com" in call_args

    @patch("materials.utils.logger")
    def test_log_upload_with_errors(self, mock_logger):
        """Test upload logging with validation errors"""
        errors = ["File too large", "Invalid MIME type"]

        FileAuditLogger.log_upload(
            user_id=2,
            user_email="user@example.com",
            filename="bad.exe",
            file_size=100,
            file_type="submission",
            file_hash="",
            storage_path="",
            validation_result=False,
            errors=errors,
        )

        mock_logger.info.assert_called_once()
        call_args = str(mock_logger.info.call_args)
        assert "File too large" in call_args

    @patch("materials.utils.logger")
    def test_log_download(self, mock_logger):
        """Test download logging"""
        FileAuditLogger.log_download(
            user_id=1,
            user_email="test@example.com",
            filename="test.pdf",
            file_type="material",
            storage_path="/secure/materials/1/test.pdf",
        )

        mock_logger.info.assert_called_once()
        call_args = str(mock_logger.info.call_args)
        assert "file_download" in call_args

    @patch("materials.utils.logger")
    def test_log_deletion(self, mock_logger):
        """Test deletion logging"""
        FileAuditLogger.log_deletion(
            user_id=1,
            user_email="test@example.com",
            filename="test.pdf",
            file_type="submission",
            storage_path="/secure/materials/1/test.pdf",
            reason="user_request",
        )

        mock_logger.info.assert_called_once()
        call_args = str(mock_logger.info.call_args)
        assert "file_deletion" in call_args
        assert "user_request" in call_args


class TestPathTraversalPrevention:
    """Test path traversal attack prevention"""

    def test_path_traversal_attack_double_dot(self):
        """Test prevention of ../ path traversal"""
        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("../../../etc/passwd.txt")

    def test_path_traversal_attack_backslash(self):
        """Test prevention of backslash traversal"""
        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("..\\..\\windows\\system32.txt")

    def test_path_traversal_attack_encoded(self):
        """Test prevention of encoded traversal attempts"""
        # URL encoded traversal
        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("%2e%2e/etc/passwd.txt")

    def test_absolute_path_attack(self):
        """Test prevention of absolute path attacks"""
        with pytest.raises(ValidationError):
            MaterialFileValidator.sanitize_filename("/etc/passwd.txt")


@pytest.mark.integration
class TestFileUploadIntegration:
    """Integration tests for file upload security"""

    def test_large_file_handling(self):
        """Test handling of large files (without actually uploading 50MB)"""
        # Create 10MB file for testing
        size = 10 * 1024 * 1024
        content = b"x" * size
        file = SimpleUploadedFile("largefile.pdf", content, content_type="application/pdf")

        # Should pass size validation
        MaterialFileValidator.validate_file_size(file, file_type="document")

    def test_batch_file_validation(self):
        """Test validating multiple files"""
        files = [
            SimpleUploadedFile("doc1.pdf", b"%PDF" + b"x" * 100),
            SimpleUploadedFile("doc2.docx", b"PK" + b"x" * 100),
            SimpleUploadedFile("img.png", b"\x89PNG" + b"x" * 100),
        ]

        validated_count = 0
        for file in files:
            try:
                MaterialFileValidator.validate(file, file_type="submission")
                validated_count += 1
            except ValidationError:
                pass

        # At least some should pass
        assert validated_count > 0
