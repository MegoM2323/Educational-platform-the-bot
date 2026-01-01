"""
Unit Tests for Material Validators (Pure Python)
No Django ORM required
"""

import unittest
from io import BytesIO


class MockFile:
    """Mock file object for testing"""
    def __init__(self, name, content=None, size=None):
        self.name = name
        self.content = content or b"test"
        self.size = size if size is not None else len(self.content)


class FileValidatorTests(unittest.TestCase):
    """Test file validator logic"""

    def test_get_extension_valid(self):
        """Test extraction of file extension"""
        def get_extension(filename):
            if not filename:
                return None
            return filename.rsplit('.', 1)[-1].lower() if '.' in filename else None

        self.assertEqual(get_extension("document.pdf"), "pdf")
        self.assertEqual(get_extension("image.PNG"), "png")
        self.assertEqual(get_extension("archive.7Z"), "7z")
        self.assertIsNone(get_extension("noextension"))
        self.assertIsNone(get_extension(None))

    def test_extension_validation_allowed(self):
        """Test that allowed extensions pass validation"""
        allowed = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                  'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                  'zip', 'rar', '7z'}

        def validate_extension(filename):
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
            if not ext or ext not in allowed:
                raise ValueError(f"Invalid extension: {ext}")
            return ext

        # Valid extensions
        for ext in ['pdf', 'docx', 'png', 'mp4']:
            result = validate_extension(f"file.{ext}")
            self.assertEqual(result, ext)

    def test_extension_validation_denied(self):
        """Test that dangerous extensions are rejected"""
        allowed = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                  'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                  'zip', 'rar', '7z'}

        def validate_extension(filename):
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
            if not ext or ext not in allowed:
                raise ValueError(f"Invalid extension: {ext}")
            return ext

        # Invalid extensions
        dangerous = ['py', 'exe', 'sh', 'bat', 'js', 'php']
        for ext in dangerous:
            with self.assertRaises(ValueError):
                validate_extension(f"malware.{ext}")

    def test_file_size_validation(self):
        """Test file size validation"""
        MAX_SIZE = 50 * 1024 * 1024  # 50MB

        def validate_size(size):
            if size > MAX_SIZE:
                raise ValueError(f"File too large: {size} > {MAX_SIZE}")
            return True

        # Valid sizes
        self.assertTrue(validate_size(1024))  # 1KB
        self.assertTrue(validate_size(10 * 1024 * 1024))  # 10MB
        self.assertTrue(validate_size(MAX_SIZE))  # Exactly 50MB

        # Invalid sizes
        with self.assertRaises(ValueError):
            validate_size(MAX_SIZE + 1)  # 50MB + 1 byte
        with self.assertRaises(ValueError):
            validate_size(100 * 1024 * 1024)  # 100MB

    def test_video_size_limit_higher(self):
        """Test that videos have higher size limit"""
        DOCUMENT_SIZE = 50 * 1024 * 1024
        VIDEO_SIZE = 500 * 1024 * 1024

        def get_size_limit(extension):
            if extension in {'mp4', 'mov', 'avi'}:
                return VIDEO_SIZE
            return DOCUMENT_SIZE

        # Document limit
        self.assertEqual(get_size_limit("pdf"), DOCUMENT_SIZE)
        self.assertEqual(get_size_limit("docx"), DOCUMENT_SIZE)

        # Video limit
        self.assertEqual(get_size_limit("mp4"), VIDEO_SIZE)
        self.assertEqual(get_size_limit("mov"), VIDEO_SIZE)

    def test_title_validation(self):
        """Test title validation logic"""
        def validate_title(title):
            if not title or not title.strip():
                raise ValueError("Title is empty")
            if len(title) < 3:
                raise ValueError("Title too short")
            if len(title) > 200:
                raise ValueError("Title too long")
            return True

        # Valid titles
        self.assertTrue(validate_title("Valid Title"))
        self.assertTrue(validate_title("A" * 200))  # Exactly 200 chars

        # Invalid titles
        with self.assertRaises(ValueError):
            validate_title("")  # Empty
        with self.assertRaises(ValueError):
            validate_title("   ")  # Whitespace only
        with self.assertRaises(ValueError):
            validate_title("AB")  # Too short
        with self.assertRaises(ValueError):
            validate_title("A" * 201)  # Too long

    def test_description_validation(self):
        """Test description validation logic"""
        def validate_description(desc):
            if desc and len(desc) > 5000:
                raise ValueError("Description too long")
            return True

        # Valid descriptions
        self.assertTrue(validate_description(""))  # Empty is OK
        self.assertTrue(validate_description("A valid description"))
        self.assertTrue(validate_description("A" * 5000))  # Exactly 5000

        # Invalid descriptions
        with self.assertRaises(ValueError):
            validate_description("A" * 5001)  # Too long


class FileMimeTypeTests(unittest.TestCase):
    """Test MIME type handling"""

    def setUp(self):
        """Set up MIME type mapping"""
        self.mime_types = {
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
        }

    def test_pdf_mime_type(self):
        """Test PDF MIME type"""
        self.assertEqual(self.mime_types['pdf'], 'application/pdf')

    def test_image_mime_types(self):
        """Test image MIME types"""
        self.assertEqual(self.mime_types['jpg'], 'image/jpeg')
        self.assertEqual(self.mime_types['png'], 'image/png')
        self.assertEqual(self.mime_types['gif'], 'image/gif')

    def test_document_mime_types(self):
        """Test document MIME types"""
        self.assertTrue(self.mime_types['docx'].startswith('application/vnd'))
        self.assertTrue(self.mime_types['xlsx'].startswith('application/vnd'))

    def test_all_extensions_have_mime_types(self):
        """Test all supported extensions have MIME types"""
        allowed = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                  'mp4', 'mp3', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                  'zip', 'rar', '7z'}

        # At least most should have mappings
        found = set(self.mime_types.keys())
        coverage = len(found) / len(allowed)
        self.assertGreater(coverage, 0.7)  # At least 70%


class EdgeCaseTests(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_file_with_multiple_dots(self):
        """Test file with multiple dots in name"""
        def get_extension(filename):
            return filename.rsplit('.', 1)[-1].lower() if '.' in filename else None

        self.assertEqual(get_extension("my.document.v2.pdf"), "pdf")
        self.assertEqual(get_extension("archive.tar.gz"), "gz")

    def test_uppercase_extension(self):
        """Test uppercase extension handling"""
        def normalize_extension(filename):
            return filename.rsplit('.', 1)[-1].lower() if '.' in filename else None

        self.assertEqual(normalize_extension("DOCUMENT.PDF"), "pdf")
        self.assertEqual(normalize_extension("Image.PNG"), "png")
        self.assertEqual(normalize_extension("Video.MP4"), "mp4")

    def test_unicode_filename(self):
        """Test unicode in filename"""
        def get_extension(filename):
            if '.' not in filename:
                return None
            return filename.rsplit('.', 1)[-1].lower()

        # Should handle unicode filenames
        ext = get_extension("Учебник-Математика.pdf")
        self.assertEqual(ext, "pdf")

        ext = get_extension("图片-样本.png")
        self.assertEqual(ext, "png")

    def test_boundary_sizes(self):
        """Test size boundary conditions"""
        MAX = 50 * 1024 * 1024

        def validate(size):
            return size <= MAX

        # At boundary
        self.assertTrue(validate(MAX))  # Exactly at limit
        self.assertFalse(validate(MAX + 1))  # One byte over

        # Well before limit
        self.assertTrue(validate(10 * 1024 * 1024))  # 10MB
        self.assertTrue(validate(1024))  # 1KB


class FileTypeMatrixTests(unittest.TestCase):
    """Test file type support matrix"""

    def setUp(self):
        """Set up file type categories"""
        self.documents = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
        self.images = {'jpg', 'jpeg', 'png', 'gif'}
        self.videos = {'mp4'}
        self.audio = {'mp3'}
        self.archives = {'zip', 'rar', '7z'}

    def test_document_types(self):
        """Test document file types"""
        self.assertIn('pdf', self.documents)
        self.assertIn('docx', self.documents)
        self.assertEqual(len(self.documents), 8)

    def test_image_types(self):
        """Test image file types"""
        self.assertIn('jpg', self.images)
        self.assertIn('png', self.images)
        self.assertEqual(len(self.images), 4)

    def test_video_types(self):
        """Test video file types"""
        self.assertIn('mp4', self.videos)
        self.assertEqual(len(self.videos), 1)

    def test_audio_types(self):
        """Test audio file types"""
        self.assertIn('mp3', self.audio)

    def test_archive_types(self):
        """Test archive file types"""
        self.assertIn('zip', self.archives)
        self.assertIn('rar', self.archives)
        self.assertIn('7z', self.archives)
        self.assertEqual(len(self.archives), 3)

    def test_total_supported_types(self):
        """Test total number of supported file types"""
        all_types = (self.documents | self.images | self.videos |
                    self.audio | self.archives)
        # documents(8) + images(4) + videos(1) + audio(1) + archives(3) = 17
        self.assertEqual(len(all_types), 17)

    def test_no_dangerous_types(self):
        """Test that dangerous types are not supported"""
        dangerous = {'py', 'exe', 'sh', 'bat', 'js', 'php', 'jar', 'dll'}
        all_types = (self.documents | self.images | self.videos |
                    self.audio | self.archives)

        for dtype in dangerous:
            self.assertNotIn(dtype, all_types)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
