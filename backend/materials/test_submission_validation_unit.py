"""
Unit tests for T_MAT_008 - Submission File Validation

These tests verify the validation logic without requiring full Django setup.
Tests validate:
1. File type validation
2. File size limits
3. MIME type checking
4. Checksum generation
"""

import unittest
import hashlib
from io import BytesIO
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


class TestSubmissionFileValidationLogic(unittest.TestCase):
    """Test validation logic without Django models"""

    def test_file_extension_validation_pdf(self):
        """Test PDF extension validation"""
        from materials.utils import SubmissionFileValidator

        ext = SubmissionFileValidator.validate_file_extension("document.pdf")
        self.assertEqual(ext, "pdf")

    def test_file_extension_validation_docx(self):
        """Test DOCX extension validation"""
        from materials.utils import SubmissionFileValidator

        ext = SubmissionFileValidator.validate_file_extension("report.docx")
        self.assertEqual(ext, "docx")

    def test_file_extension_invalid(self):
        """Test invalid extension rejection"""
        from materials.utils import SubmissionFileValidator

        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_extension("script.exe")

    def test_file_extension_no_extension(self):
        """Test file without extension"""
        from materials.utils import SubmissionFileValidator

        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_extension("filename")

    def test_file_count_validation_min(self):
        """Test minimum file count"""
        from materials.utils import SubmissionFileValidator

        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_count(0)

    def test_file_count_validation_max(self):
        """Test maximum file count"""
        from materials.utils import SubmissionFileValidator

        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_count(11)

    def test_file_count_validation_valid(self):
        """Test valid file counts"""
        from materials.utils import SubmissionFileValidator

        # Should not raise
        SubmissionFileValidator.validate_file_count(1)
        SubmissionFileValidator.validate_file_count(5)
        SubmissionFileValidator.validate_file_count(10)

    def test_file_size_validation_under_limit(self):
        """Test file size under limit"""
        from materials.utils import SubmissionFileValidator

        file = SimpleUploadedFile("test.pdf", b"x" * (10 * 1024 * 1024))
        # Should not raise
        SubmissionFileValidator.validate_individual_file_size(file)

    def test_file_size_validation_at_limit(self):
        """Test file size at limit"""
        from materials.utils import SubmissionFileValidator

        file = SimpleUploadedFile("test.pdf", b"x" * (50 * 1024 * 1024))
        # Should not raise
        SubmissionFileValidator.validate_individual_file_size(file)

    def test_file_size_validation_over_limit(self):
        """Test file size over limit"""
        from materials.utils import SubmissionFileValidator

        file = SimpleUploadedFile("test.pdf", b"x" * (51 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_individual_file_size(file)

    def test_total_size_validation_under_limit(self):
        """Test total submission size under limit"""
        from materials.utils import SubmissionFileValidator

        sizes = [10 * 1024 * 1024, 20 * 1024 * 1024, 30 * 1024 * 1024]
        # Should not raise
        SubmissionFileValidator.validate_total_submission_size(sizes)

    def test_total_size_validation_at_limit(self):
        """Test total submission size at limit"""
        from materials.utils import SubmissionFileValidator

        sizes = [200 * 1024 * 1024]
        # Should not raise
        SubmissionFileValidator.validate_total_submission_size(sizes)

    def test_total_size_validation_over_limit(self):
        """Test total submission size over limit"""
        from materials.utils import SubmissionFileValidator

        sizes = [150 * 1024 * 1024, 60 * 1024 * 1024]
        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_total_submission_size(sizes)

    def test_checksum_calculation(self):
        """Test SHA256 checksum calculation"""
        from materials.utils import FileAuditLogger

        content = b"Test content for hashing"
        file = SimpleUploadedFile("test.txt", content)

        checksum = FileAuditLogger.calculate_file_hash(file)

        # Verify it's correct
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(checksum, expected)
        self.assertEqual(len(checksum), 64)

    def test_checksum_different_content(self):
        """Test different content produces different checksums"""
        from materials.utils import FileAuditLogger

        file1 = SimpleUploadedFile("test1.txt", b"Content A")
        file2 = SimpleUploadedFile("test2.txt", b"Content B")

        checksum1 = FileAuditLogger.calculate_file_hash(file1)
        checksum2 = FileAuditLogger.calculate_file_hash(file2)

        self.assertNotEqual(checksum1, checksum2)

    def test_dangerous_mime_type_rejection(self):
        """Test dangerous MIME types are rejected"""
        from materials.utils import SubmissionFileValidator

        file = SimpleUploadedFile(
            "test.exe",
            b"MZ\x90\x00",
            content_type="application/x-executable"
        )

        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_mime_type(file, "exe")

    def test_safe_mime_type_acceptance(self):
        """Test safe MIME types are accepted"""
        from materials.utils import SubmissionFileValidator

        file = SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4",
            content_type="application/pdf"
        )

        # Should not raise
        SubmissionFileValidator.validate_mime_type(file, "pdf")

    def test_allowed_extensions_list(self):
        """Test allowed extensions include all required types"""
        from materials.utils import SubmissionFileValidator

        allowed = SubmissionFileValidator.ALLOWED_SUBMISSION_EXTENSIONS

        # Check all required types are present
        required = {
            # Documents
            "pdf", "doc", "docx", "txt",
            # Images
            "jpg", "jpeg", "png",
            # Videos
            "mp4", "webm",
            # Archives
            "zip", "rar", "7z",
        }

        for ext in required:
            self.assertIn(ext, allowed, f"Extension '{ext}' should be allowed")

    def test_file_size_constants(self):
        """Test file size constants are correctly defined"""
        from materials.utils import SubmissionFileValidator

        # 50MB per file
        self.assertEqual(
            SubmissionFileValidator.MAX_SUBMISSION_FILE_SIZE,
            50 * 1024 * 1024
        )

        # 200MB total
        self.assertEqual(
            SubmissionFileValidator.MAX_SUBMISSION_TOTAL_SIZE,
            200 * 1024 * 1024
        )

        # Max 10 files
        self.assertEqual(
            SubmissionFileValidator.MAX_FILES_PER_SUBMISSION,
            10
        )

        # Min 1 file
        self.assertEqual(
            SubmissionFileValidator.MIN_FILES_PER_SUBMISSION,
            1
        )


class TestSubmissionFileValidatorIntegration(TestCase):
    """Integration tests that require Django TestCase"""

    def test_validate_file_all_supported_extensions(self):
        """Test that all supported extensions validate"""
        from materials.utils import SubmissionFileValidator

        test_files = [
            "document.pdf",
            "letter.doc",
            "report.docx",
            "notes.txt",
            "image.jpg",
            "photo.jpeg",
            "picture.png",
            "archive.zip",
            "compressed.rar",
            "video.mp4",
            "presentation.pptx",
            "spreadsheet.xlsx",
        ]

        for filename in test_files:
            ext = SubmissionFileValidator.validate_file_extension(filename)
            self.assertIsNotNone(ext, f"Failed to validate {filename}")

    def test_validate_file_with_uppercase_extension(self):
        """Test that uppercase extensions are normalized"""
        from materials.utils import SubmissionFileValidator

        ext = SubmissionFileValidator.validate_file_extension("document.PDF")
        self.assertEqual(ext, "pdf")

    def test_validate_file_with_multiple_dots(self):
        """Test files with multiple dots in name"""
        from materials.utils import SubmissionFileValidator

        ext = SubmissionFileValidator.validate_file_extension("my.document.final.pdf")
        self.assertEqual(ext, "pdf")

    def test_submission_file_validator_max_values(self):
        """Test that max values are correct per requirements"""
        from materials.utils import SubmissionFileValidator

        # Per requirement: max 50MB per file
        self.assertEqual(
            SubmissionFileValidator.MAX_SUBMISSION_FILE_SIZE,
            50 * 1024 * 1024
        )

        # Per requirement: max 200MB total
        self.assertEqual(
            SubmissionFileValidator.MAX_SUBMISSION_TOTAL_SIZE,
            200 * 1024 * 1024
        )

        # Per requirement: max 10 files
        self.assertEqual(
            SubmissionFileValidator.MAX_FILES_PER_SUBMISSION,
            10
        )

        # Per requirement: min 1 file
        self.assertEqual(
            SubmissionFileValidator.MIN_FILES_PER_SUBMISSION,
            1
        )


if __name__ == "__main__":
    unittest.main()
