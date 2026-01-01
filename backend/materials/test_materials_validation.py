"""
Unit Tests for Materials Upload Validation
Tests validators and file handling
"""

import pytest
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.test import TestCase

from materials.validators import (
    MaterialFileValidator,
    validate_file_type,
    validate_file_size,
    validate_title_length,
    validate_description_length
)
from materials.models import Material, Subject

User = get_user_model()


class MaterialFileValidatorTests(TestCase):
    """Test the MaterialFileValidator class"""

    def test_allowed_extensions(self):
        """Test that all expected extensions are allowed"""
        validator = MaterialFileValidator()
        expected = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                   'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                   'zip', 'rar', '7z'}
        self.assertEqual(validator.ALLOWED_EXTENSIONS, expected)

    def test_get_file_extension_valid(self):
        """Test extraction of file extension"""
        assert MaterialFileValidator.get_file_extension("document.pdf") == "pdf"
        assert MaterialFileValidator.get_file_extension("image.PNG") == "png"
        assert MaterialFileValidator.get_file_extension("archive.7Z") == "7z"

    def test_get_file_extension_no_extension(self):
        """Test handling of files without extension"""
        assert MaterialFileValidator.get_file_extension("noextension") is None
        assert MaterialFileValidator.get_file_extension("") is None
        assert MaterialFileValidator.get_file_extension(None) is None

    def test_validate_extension_valid(self):
        """Test validation of valid extensions"""
        # Should not raise
        MaterialFileValidator.validate_extension("test.pdf")
        MaterialFileValidator.validate_extension("document.docx")
        MaterialFileValidator.validate_extension("image.png")

    def test_validate_extension_invalid(self):
        """Test rejection of invalid extensions"""
        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_extension("script.py")

        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_extension("executable.exe")

        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_extension("batch.bat")

    def test_validate_extension_no_extension(self):
        """Test rejection of files without extension"""
        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_extension("noextension")

    def test_get_size_limit_for_video(self):
        """Test size limit for video files"""
        limit = MaterialFileValidator.get_size_limit_for_extension("mp4")
        assert limit == 500 * 1024 * 1024  # 500MB

    def test_get_size_limit_for_document(self):
        """Test size limit for document files"""
        limit = MaterialFileValidator.get_size_limit_for_extension("pdf")
        assert limit == 50 * 1024 * 1024  # 50MB

        limit = MaterialFileValidator.get_size_limit_for_extension("docx")
        assert limit == 50 * 1024 * 1024  # 50MB

    def test_validate_size_within_limit(self):
        """Test validation of file within size limit"""
        file_obj = BytesIO(b"x" * 1000)  # 1KB
        file_obj.size = 1000
        file_obj.name = "test.pdf"

        # Should not raise
        MaterialFileValidator.validate_size(file_obj, "pdf")

    def test_validate_size_exceeds_limit(self):
        """Test rejection of oversized files"""
        # Create 51MB file
        file_obj = BytesIO(b"x" * (51 * 1024 * 1024))
        file_obj.size = 51 * 1024 * 1024
        file_obj.name = "large.pdf"

        with self.assertRaises(serializers.ValidationError) as context:
            MaterialFileValidator.validate_size(file_obj, "pdf")

        self.assertIn("превышает", str(context.exception))

    def test_validate_size_video_limit(self):
        """Test video size limit is higher than document"""
        # Create 501MB file
        file_obj = BytesIO()
        file_obj.size = 501 * 1024 * 1024
        file_obj.name = "video.mp4"

        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_size(file_obj, "mp4")

    def test_full_validation_valid_pdf(self):
        """Test full validation of valid PDF"""
        file_obj = BytesIO(b"%PDF-1.4\ntest content")
        file_obj.size = 1024
        file_obj.name = "document.pdf"

        # Should not raise
        MaterialFileValidator.validate(file_obj)

    def test_full_validation_invalid_extension(self):
        """Test full validation rejects invalid extension"""
        file_obj = BytesIO(b"malicious code")
        file_obj.size = 1024
        file_obj.name = "script.py"

        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate(file_obj)

    def test_full_validation_oversized(self):
        """Test full validation rejects oversized file"""
        file_obj = BytesIO(b"x" * (51 * 1024 * 1024))
        file_obj.size = 51 * 1024 * 1024
        file_obj.name = "huge.pdf"

        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate(file_obj)


class FileTypeValidationTests(TestCase):
    """Test the validate_file_type function"""

    def test_valid_pdf(self):
        """Test PDF is accepted"""
        file_obj = SimpleUploadedFile("test.pdf", b"PDF content")
        # Should not raise
        validate_file_type(file_obj)

    def test_valid_image(self):
        """Test image types are accepted"""
        for ext in ["jpg", "jpeg", "png", "gif"]:
            file_obj = SimpleUploadedFile(f"image.{ext}", b"image data")
            validate_file_type(file_obj)

    def test_valid_document(self):
        """Test document types are accepted"""
        for ext in ["doc", "docx", "xls", "xlsx", "ppt", "pptx"]:
            file_obj = SimpleUploadedFile(f"doc.{ext}", b"doc data")
            validate_file_type(file_obj)

    def test_invalid_executable(self):
        """Test executables are rejected"""
        file_obj = SimpleUploadedFile("malware.exe", b"malicious")
        with self.assertRaises(serializers.ValidationError):
            validate_file_type(file_obj)

    def test_invalid_script(self):
        """Test scripts are rejected"""
        for ext in ["py", "js", "sh", "bat"]:
            file_obj = SimpleUploadedFile(f"script.{ext}", b"code")
            with self.assertRaises(serializers.ValidationError):
                validate_file_type(file_obj)

    def test_none_file(self):
        """Test None file is handled gracefully"""
        # Should not raise
        validate_file_type(None)


class FileSizeValidationTests(TestCase):
    """Test the validate_file_size function"""

    def test_small_file(self):
        """Test small file is accepted"""
        file_obj = SimpleUploadedFile("test.pdf", b"small content")
        file_obj.size = 1024  # 1KB
        # Should not raise
        validate_file_size(file_obj)

    def test_max_size_file(self):
        """Test file at max size is accepted"""
        file_obj = SimpleUploadedFile("test.pdf", b"x")
        file_obj.size = 50 * 1024 * 1024  # Exactly 50MB
        # Should not raise
        validate_file_size(file_obj)

    def test_oversized_file(self):
        """Test file over max size is rejected"""
        file_obj = SimpleUploadedFile("test.pdf", b"x")
        file_obj.size = 51 * 1024 * 1024  # 51MB
        with self.assertRaises(serializers.ValidationError) as context:
            validate_file_size(file_obj)
        self.assertIn("не должен превышать", str(context.exception))

    def test_none_file(self):
        """Test None file is handled gracefully"""
        # Should not raise
        validate_file_size(None)

    def test_file_without_size(self):
        """Test file object without size attribute"""
        file_obj = SimpleUploadedFile("test.pdf", b"content")
        # Manually remove size attribute
        if hasattr(file_obj, 'size'):
            # Should handle gracefully
            validate_file_size(file_obj)


class TitleValidationTests(TestCase):
    """Test the validate_title_length function"""

    def test_valid_title(self):
        """Test valid title is accepted"""
        validate_title_length("Учебник Математика - Глава 3")
        validate_title_length("Test")
        validate_title_length("A" * 200)  # Max length

    def test_empty_title(self):
        """Test empty title is rejected"""
        with self.assertRaises(serializers.ValidationError):
            validate_title_length("")

    def test_too_long_title(self):
        """Test title exceeding 200 chars is rejected"""
        long_title = "A" * 201
        with self.assertRaises(serializers.ValidationError) as context:
            validate_title_length(long_title)
        self.assertIn("200", str(context.exception))

    def test_too_short_title(self):
        """Test title under 3 chars is rejected"""
        with self.assertRaises(serializers.ValidationError):
            validate_title_length("AB")

    def test_whitespace_only(self):
        """Test whitespace-only title is rejected"""
        with self.assertRaises(serializers.ValidationError):
            validate_title_length("   ")


class DescriptionValidationTests(TestCase):
    """Test the validate_description_length function"""

    def test_valid_description(self):
        """Test valid description is accepted"""
        validate_description_length("This is a valid description")
        validate_description_length("A" * 5000)  # Max length
        validate_description_length("")  # Empty is allowed

    def test_too_long_description(self):
        """Test description exceeding 5000 chars is rejected"""
        long_desc = "A" * 5001
        with self.assertRaises(serializers.ValidationError) as context:
            validate_description_length(long_desc)
        self.assertIn("5000", str(context.exception))

    def test_none_description(self):
        """Test None description is handled"""
        # Should not raise
        validate_description_length(None)


class MaterialModelFileTests(TestCase):
    """Test Material model file handling"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='password123',
            role='teacher'
        )
        self.subject = Subject.objects.create(
            name='Математика',
            description='Math subject'
        )

    def test_material_with_file(self):
        """Test material with file field"""
        file_content = b"%PDF-1.4\ntest"
        file_obj = SimpleUploadedFile("test.pdf", file_content)

        material = Material.objects.create(
            title="Test Material",
            description="Test",
            content="Content",
            author=self.teacher,
            subject=self.subject,
            type='document',
            status='active',
            file=file_obj
        )

        self.assertIsNotNone(material.file)
        self.assertTrue(material.file.name.endswith('.pdf'))

    def test_material_without_file(self):
        """Test material without file (video only)"""
        material = Material.objects.create(
            title="Video Material",
            description="Video lesson",
            content="Content",
            author=self.teacher,
            subject=self.subject,
            type='video',
            status='active',
            video_url='https://youtube.com/watch?v=example'
        )

        self.assertFalse(material.file)
        self.assertIsNotNone(material.video_url)


class FileTypeMatrixTests(TestCase):
    """Test file type MIME type mappings"""

    def test_pdf_mime_type(self):
        """Test PDF MIME type"""
        mime = MaterialFileValidator.MIME_TYPE_MAP['pdf']
        self.assertEqual(mime, 'application/pdf')

    def test_image_mime_types(self):
        """Test image MIME types"""
        self.assertEqual(
            MaterialFileValidator.MIME_TYPE_MAP['jpg'],
            'image/jpeg'
        )
        self.assertEqual(
            MaterialFileValidator.MIME_TYPE_MAP['png'],
            'image/png'
        )

    def test_document_mime_types(self):
        """Test document MIME types"""
        self.assertEqual(
            MaterialFileValidator.MIME_TYPE_MAP['docx'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertEqual(
            MaterialFileValidator.MIME_TYPE_MAP['xlsx'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions"""

    def test_file_with_multiple_dots(self):
        """Test file with multiple dots in name"""
        ext = MaterialFileValidator.get_file_extension("my.document.v2.pdf")
        self.assertEqual(ext, "pdf")

    def test_file_with_uppercase_extension(self):
        """Test case-insensitive extension handling"""
        ext = MaterialFileValidator.get_file_extension("document.PDF")
        self.assertEqual(ext, "pdf")

    def test_size_boundary_exactly_at_limit(self):
        """Test file size exactly at limit"""
        file_obj = BytesIO(b"x")
        file_obj.size = 50 * 1024 * 1024  # Exactly 50MB
        # Should not raise
        MaterialFileValidator.validate_size(file_obj, "pdf")

    def test_size_boundary_one_byte_over(self):
        """Test file size one byte over limit"""
        file_obj = BytesIO(b"x")
        file_obj.size = (50 * 1024 * 1024) + 1
        with self.assertRaises(serializers.ValidationError):
            MaterialFileValidator.validate_size(file_obj, "pdf")

    def test_unicode_filename(self):
        """Test handling of unicode in filename"""
        ext = MaterialFileValidator.get_file_extension("Учебник-Математика.pdf")
        self.assertEqual(ext, "pdf")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
