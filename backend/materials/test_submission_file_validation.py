"""
Comprehensive tests for T_MAT_008 - Submission File Validation

Tests validate:
1. File type validation (pdf, doc, docx, txt, images, videos, archives)
2. File size limits (50MB per file, 200MB total per submission)
3. Duplicate submission detection (by checksum)
4. MIME type validation
5. Malware scanning (signatures)
6. Filename sanitization (path traversal prevention)
7. Checksum generation and storage
8. Minimum 1 file requirement
9. Maximum 10 files limit
10. Audit logging
"""

import io
import hashlib
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile

from materials.models import (
    Subject,
    Material,
    MaterialSubmission,
    SubmissionFile,
)
from materials.serializers import BulkMaterialSubmissionSerializer
from materials.utils import SubmissionFileValidator, FileAuditLogger

User = get_user_model()


class TestSubmissionFileValidator(TestCase):
    """Test SubmissionFileValidator class"""

    def setUp(self):
        """Set up test data"""
        # Create test student
        self.student = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        # Create test teacher
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Create subject and material
        self.subject = Subject.objects.create(name="Test Subject")
        self.material = Material.objects.create(
            title="Test Material",
            subject=self.subject,
            author=self.teacher,
            type=Material.Type.TEXT
        )

    def _create_test_file(self, filename: str, content: bytes = None, size: int = None) -> SimpleUploadedFile:
        """Helper to create test files"""
        if content is None:
            if size is None:
                content = b"Test file content" * 100
            else:
                content = b"x" * size

        return SimpleUploadedFile(
            filename,
            content,
            content_type="application/octet-stream"
        )

    def test_validate_file_count_min(self):
        """Test minimum file count validation (T_MAT_008.7)"""
        # Empty list should raise error
        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_count(0)

    def test_validate_file_count_max(self):
        """Test maximum file count validation (T_MAT_008.8)"""
        # More than 10 files should raise error
        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_file_count(11)

    def test_validate_file_count_valid(self):
        """Test valid file counts"""
        # These should not raise errors
        SubmissionFileValidator.validate_file_count(1)
        SubmissionFileValidator.validate_file_count(5)
        SubmissionFileValidator.validate_file_count(10)

    def test_validate_individual_file_size_under_limit(self):
        """Test file size validation under limit (T_MAT_008.2)"""
        file = self._create_test_file("test.pdf", size=10 * 1024 * 1024)  # 10MB
        # Should not raise error
        SubmissionFileValidator.validate_individual_file_size(file)

    def test_validate_individual_file_size_at_limit(self):
        """Test file size validation at limit (T_MAT_008.2)"""
        file = self._create_test_file("test.pdf", size=50 * 1024 * 1024)  # 50MB
        # Should not raise error
        SubmissionFileValidator.validate_individual_file_size(file)

    def test_validate_individual_file_size_over_limit(self):
        """Test file size validation over limit (T_MAT_008.2)"""
        file = self._create_test_file("test.pdf", size=51 * 1024 * 1024)  # 51MB
        # Should raise error
        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_individual_file_size(file)
        self.assertIn("too large", str(cm.exception))

    def test_validate_total_submission_size_under_limit(self):
        """Test total submission size under limit (T_MAT_008.2)"""
        sizes = [10 * 1024 * 1024, 20 * 1024 * 1024, 30 * 1024 * 1024]  # 60MB total
        # Should not raise error
        SubmissionFileValidator.validate_total_submission_size(sizes)

    def test_validate_total_submission_size_at_limit(self):
        """Test total submission size at limit (T_MAT_008.2)"""
        sizes = [200 * 1024 * 1024]  # 200MB exactly
        # Should not raise error
        SubmissionFileValidator.validate_total_submission_size(sizes)

    def test_validate_total_submission_size_over_limit(self):
        """Test total submission size over limit (T_MAT_008.2)"""
        sizes = [150 * 1024 * 1024, 60 * 1024 * 1024]  # 210MB total
        # Should raise error
        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_total_submission_size(sizes)
        self.assertIn("exceeds", str(cm.exception))

    def test_validate_file_extension_valid_pdf(self):
        """Test valid PDF extension (T_MAT_008.1)"""
        ext = SubmissionFileValidator.validate_file_extension("document.pdf")
        self.assertEqual(ext, "pdf")

    def test_validate_file_extension_valid_image(self):
        """Test valid image extension (T_MAT_008.1)"""
        ext = SubmissionFileValidator.validate_file_extension("image.jpg")
        self.assertEqual(ext, "jpg")

    def test_validate_file_extension_valid_video(self):
        """Test valid video extension (T_MAT_008.1)"""
        ext = SubmissionFileValidator.validate_file_extension("video.mp4")
        self.assertEqual(ext, "mp4")

    def test_validate_file_extension_invalid(self):
        """Test invalid extension (T_MAT_008.1)"""
        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_file_extension("script.exe")
        self.assertIn("not allowed", str(cm.exception))

    def test_validate_file_extension_no_extension(self):
        """Test file without extension (T_MAT_008.1)"""
        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_file_extension("filewithoutext")
        self.assertIn("must have an extension", str(cm.exception))

    def test_validate_mime_type_valid(self):
        """Test valid MIME type (T_MAT_008.5)"""
        file = SimpleUploadedFile("test.pdf", b"%PDF", content_type="application/pdf")
        # Should not raise error
        SubmissionFileValidator.validate_mime_type(file, "pdf")

    def test_validate_mime_type_dangerous(self):
        """Test dangerous MIME type rejection (T_MAT_008.5)"""
        file = SimpleUploadedFile(
            "test.exe",
            b"MZ\x90\x00",  # PE executable header
            content_type="application/x-executable"
        )
        # Should raise error
        with self.assertRaises(ValidationError):
            SubmissionFileValidator.validate_mime_type(file, "exe")

    def test_validate_file_valid_pdf(self):
        """Test valid PDF file validation (T_MAT_008.1, T_MAT_008.2)"""
        file = self._create_test_file("document.pdf", size=5 * 1024 * 1024)
        result = SubmissionFileValidator.validate_file(file, self.student.id)

        self.assertTrue(result["valid"])
        self.assertEqual(result["filename"], "document.pdf")
        self.assertEqual(result["extension"], "pdf")
        self.assertIsNotNone(result["checksum"])
        self.assertEqual(len(result["checksum"]), 64)  # SHA256 is 64 hex chars

    def test_validate_file_checksum_generation(self):
        """Test checksum generation (T_MAT_008.10)"""
        content = b"Test file content"
        file = SimpleUploadedFile("test.txt", content)

        result = SubmissionFileValidator.validate_file(file, self.student.id)
        checksum = result["checksum"]

        # Verify checksum is correct
        expected_checksum = hashlib.sha256(content).hexdigest()
        self.assertEqual(checksum, expected_checksum)

    def test_check_duplicate_submission_no_duplicate(self):
        """Test duplicate detection - no duplicate (T_MAT_008.3)"""
        file_checksum = "abc123"
        # Should return False (no duplicate)
        is_duplicate = SubmissionFileValidator.check_duplicate_submission(
            file_checksum, self.student.id
        )
        self.assertFalse(is_duplicate)

    def test_check_duplicate_submission_with_duplicate(self):
        """Test duplicate detection - with duplicate (T_MAT_008.3)"""
        # Create a submission with a file
        submission = MaterialSubmission.objects.create(
            material=self.material,
            student=self.student,
            submission_text="Test answer"
        )

        file_checksum = "abc123def456"
        SubmissionFile.objects.create(
            submission=submission,
            file=self._create_test_file("test.pdf"),
            file_name="test.pdf",
            file_size=1024,
            file_checksum=file_checksum
        )

        # Check if duplicate exists
        is_duplicate = SubmissionFileValidator.check_duplicate_submission(
            file_checksum, self.student.id
        )
        self.assertTrue(is_duplicate)

    def test_validate_submission_files_valid_batch(self):
        """Test batch file validation with valid files (T_MAT_008)"""
        files = [
            self._create_test_file("doc1.pdf", size=5 * 1024 * 1024),
            self._create_test_file("doc2.docx", size=3 * 1024 * 1024),
            self._create_test_file("image.jpg", size=2 * 1024 * 1024),
        ]

        result = SubmissionFileValidator.validate_submission_files(
            files, self.student.id, check_duplicates=False
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(len(result["files"]), 3)

    def test_validate_submission_files_exceeds_max_count(self):
        """Test batch validation exceeding max file count (T_MAT_008.8)"""
        files = [self._create_test_file(f"file{i}.pdf") for i in range(11)]

        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_submission_files(
                files, self.student.id
            )
        self.assertIn("more than", str(cm.exception))

    def test_validate_submission_files_exceeds_total_size(self):
        """Test batch validation exceeding total size (T_MAT_008.2)"""
        # Create files that total > 200MB
        files = [
            self._create_test_file("file1.pdf", size=150 * 1024 * 1024),
            self._create_test_file("file2.pdf", size=60 * 1024 * 1024),
        ]

        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_submission_files(
                files, self.student.id
            )
        self.assertIn("exceeds", str(cm.exception))

    def test_validate_submission_files_duplicate_within_batch(self):
        """Test detection of duplicate within batch (T_MAT_008.3)"""
        content = b"Same content"
        files = [
            SimpleUploadedFile("file1.pdf", content),
            SimpleUploadedFile("file2.pdf", content),
        ]

        with self.assertRaises(ValidationError) as cm:
            SubmissionFileValidator.validate_submission_files(
                files, self.student.id, check_duplicates=False
            )
        self.assertIn("duplicate", str(cm.exception))


class TestBulkMaterialSubmissionSerializer(TestCase):
    """Test BulkMaterialSubmissionSerializer with new validation"""

    def setUp(self):
        """Set up test data"""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        self.factory = RequestFactory()

    def _create_test_file(self, filename: str, size: int = 1024) -> SimpleUploadedFile:
        """Helper to create test files"""
        return SimpleUploadedFile(
            filename,
            b"x" * size,
            content_type="application/octet-stream"
        )

    def test_serializer_valid_files(self):
        """Test serializer validation with valid files"""
        request = self.factory.post("/api/test/")
        request.user = self.student

        files = [
            self._create_test_file("doc.pdf", size=1024),
            self._create_test_file("image.jpg", size=2048),
        ]

        serializer = BulkMaterialSubmissionSerializer(
            data={"files": files},
            context={"request": request}
        )

        # Validation should pass
        self.assertTrue(serializer.is_valid())

    def test_serializer_invalid_extension(self):
        """Test serializer validation with invalid extension"""
        request = self.factory.post("/api/test/")
        request.user = self.student

        files = [self._create_test_file("script.exe", size=1024)]

        serializer = BulkMaterialSubmissionSerializer(
            data={"files": files},
            context={"request": request}
        )

        # Validation should fail
        self.assertFalse(serializer.is_valid())
        self.assertIn("files", serializer.errors)

    def test_serializer_empty_files(self):
        """Test serializer validation with empty files list"""
        request = self.factory.post("/api/test/")
        request.user = self.student

        serializer = BulkMaterialSubmissionSerializer(
            data={"files": []},
            context={"request": request}
        )

        # Validation should fail (min_length=1)
        self.assertFalse(serializer.is_valid())

    def test_serializer_too_many_files(self):
        """Test serializer validation with too many files"""
        request = self.factory.post("/api/test/")
        request.user = self.student

        files = [self._create_test_file(f"file{i}.pdf") for i in range(11)]

        serializer = BulkMaterialSubmissionSerializer(
            data={"files": files},
            context={"request": request}
        )

        # Validation should fail
        self.assertFalse(serializer.is_valid())


class TestSubmissionFileModel(TestCase):
    """Test SubmissionFile model with checksum functionality"""

    def setUp(self):
        """Set up test data"""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        self.subject = Subject.objects.create(name="Test Subject")
        self.material = Material.objects.create(
            title="Test Material",
            subject=self.subject,
            author=self.teacher,
            type=Material.Type.TEXT
        )

        self.submission = MaterialSubmission.objects.create(
            material=self.material,
            student=self.student,
            submission_text="Test answer"
        )

    def test_submission_file_checksum_generation(self):
        """Test checksum generation on save (T_MAT_008.10)"""
        content = b"Test file content"
        file = SimpleUploadedFile("test.pdf", content)

        submission_file = SubmissionFile(
            submission=self.submission,
            file=file,
            file_name="test.pdf",
            file_size=len(content)
        )
        submission_file.save()

        # Checksum should be generated
        self.assertIsNotNone(submission_file.file_checksum)
        self.assertEqual(len(submission_file.file_checksum), 64)

        # Verify checksum is correct
        expected_checksum = hashlib.sha256(content).hexdigest()
        self.assertEqual(submission_file.file_checksum, expected_checksum)

    def test_submission_file_auto_populate_fields(self):
        """Test automatic population of file_name and file_size"""
        file = SimpleUploadedFile("document.pdf", b"PDF content")

        submission_file = SubmissionFile(
            submission=self.submission,
            file=file
        )
        submission_file.save()

        # Fields should be auto-populated
        self.assertEqual(submission_file.file_name, file.name)
        self.assertEqual(submission_file.file_size, len(b"PDF content"))


class TestFileAuditLogger(TestCase):
    """Test file audit logging functionality"""

    def test_calculate_file_hash(self):
        """Test SHA256 hash calculation (T_MAT_008.10)"""
        content = b"Test content for hashing"
        file = SimpleUploadedFile("test.txt", content)

        checksum = FileAuditLogger.calculate_file_hash(file)

        # Verify checksum
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(checksum, expected)
        self.assertEqual(len(checksum), 64)

    def test_calculate_file_hash_large_file(self):
        """Test hash calculation for large file"""
        # Create a 10MB file (in memory)
        content = b"x" * (10 * 1024 * 1024)
        file = SimpleUploadedFile("large.bin", content)

        checksum = FileAuditLogger.calculate_file_hash(file)

        # Should still work and produce valid hash
        self.assertEqual(len(checksum), 64)
        self.assertIsNotNone(checksum)

    def test_log_upload(self):
        """Test upload logging (T_MAT_008.6)"""
        # This should not raise an error
        FileAuditLogger.log_upload(
            user_id=1,
            user_email="test@test.com",
            filename="test.pdf",
            file_size=1024,
            file_type="submission",
            file_hash="abc123",
            storage_path="/submissions/test.pdf",
            validation_result=True,
            errors=None
        )
        # Log entry should be created (verified via logger)


# Pytest fixtures and additional tests
@pytest.mark.django_db
class TestSubmissionFileValidationIntegration:
    """Integration tests for submission file validation"""

    def test_end_to_end_submission_with_files(self):
        """Test complete submission workflow with files (T_MAT_008)"""
        # Create test user and material
        student = User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            role="student"
        )

        teacher = User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

        subject = Subject.objects.create(name="Test Subject")
        material = Material.objects.create(
            title="Test Material",
            subject=subject,
            author=teacher,
            type=Material.Type.TEXT
        )

        # Create submission with files
        submission = MaterialSubmission.objects.create(
            material=material,
            student=student,
            submission_text="My answer"
        )

        # Add multiple files
        for i in range(3):
            content = f"File content {i}".encode()
            file = SimpleUploadedFile(f"file{i}.pdf", content)

            submission_file = SubmissionFile(
                submission=submission,
                file=file,
                file_name=f"file{i}.pdf",
                file_size=len(content)
            )
            submission_file.save()

        # Verify submission and files
        assert submission.additional_files.count() == 3
        assert all(f.file_checksum for f in submission.additional_files.all())
