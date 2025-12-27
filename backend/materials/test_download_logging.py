"""
Tests for Material Download Logging functionality.

Covers:
- Download logging with metadata capture
- Deduplication (same user/material within 1 hour)
- Download counting across time
- Rate limiting (100/hour per IP)
- Statistics queries
- Cleanup command
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from materials.models import Material, MaterialDownloadLog, Subject
from materials.services.download_logger import DownloadLogger
from materials.views import MaterialViewSet

User = get_user_model()


@pytest.mark.django_db
class TestDownloadLogging(TestCase):
    """Test download logging functionality."""

    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student"
        )
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher"
        )

        self.subject = Subject.objects.create(
            name="Test Subject",
            description="Test"
        )

        self.material_file = SimpleUploadedFile(
            "test.pdf",
            b"pdf content",
            content_type="application/pdf"
        )
        self.material = Material.objects.create(
            title="Test Material",
            description="Test",
            content="Test content",
            author=self.teacher,
            subject=self.subject,
            file=self.material_file,
            is_public=True,
            status=Material.Status.ACTIVE
        )

        self.factory = RequestFactory()

    def test_log_download_creates_entry(self):
        """Test that logging a download creates an entry."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        log_entry = DownloadLogger.log_download(
            material=self.material,
            user=self.student,
            request=request,
            file_size=1024
        )

        self.assertIsNotNone(log_entry.id)
        self.assertEqual(log_entry.material, self.material)
        self.assertEqual(log_entry.user, self.student)
        self.assertEqual(log_entry.ip_address, '192.168.1.1')
        self.assertEqual(log_entry.file_size, 1024)
        self.assertIsNotNone(log_entry.timestamp)

    def test_deduplication_within_hour(self):
        """Test duplicate detection within 1 hour."""
        self.assertTrue(
            DownloadLogger.should_log_download(
                self.material.id,
                self.student.id
            )
        )

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        DownloadLogger.log_download(
            material=self.material,
            user=self.student,
            request=request
        )

        self.assertFalse(
            DownloadLogger.should_log_download(
                self.material.id,
                self.student.id
            )
        )

    def test_deduplication_after_hour(self):
        """Test that downloads are logged after deduplication window expires."""
        log1 = MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=1024
        )

        self.assertFalse(
            DownloadLogger.should_log_download(
                self.material.id,
                self.student.id
            )
        )

        log1.timestamp = timezone.now() - timedelta(minutes=61)
        log1.save()

        self.assertTrue(
            DownloadLogger.should_log_download(
                self.material.id,
                self.student.id
            )
        )

    def test_download_counting_multiple_downloads(self):
        """Test counting downloads across time."""
        for i in range(3):
            log = MaterialDownloadLog.objects.create(
                material=self.material,
                user=self.student,
                ip_address='192.168.1.1',
                file_size=1024
            )
            if i > 0:
                log.timestamp = timezone.now() - timedelta(hours=i)
                log.save()

        stats = DownloadLogger.get_material_download_stats(self.material.id)
        self.assertEqual(stats['total_downloads'], 3)
        self.assertEqual(stats['unique_users'], 1)

    def test_download_counting_multiple_users(self):
        """Test counting downloads from multiple users."""
        another_student = User.objects.create_user(
            email="student2@test.com",
            password="testpass123",
            role="student"
        )

        MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=1024
        )
        MaterialDownloadLog.objects.create(
            material=self.material,
            user=another_student,
            ip_address='192.168.1.2',
            file_size=1024
        )

        stats = DownloadLogger.get_material_download_stats(self.material.id)
        self.assertEqual(stats['total_downloads'], 2)
        self.assertEqual(stats['unique_users'], 2)

    def test_rate_limiting_same_ip(self):
        """Test rate limiting for same IP."""
        ip = '192.168.1.1'

        for i in range(100):
            self.assertTrue(
                DownloadLogger.check_rate_limit(ip),
                f"Failed at iteration {i}"
            )

        self.assertFalse(DownloadLogger.check_rate_limit(ip))

    def test_get_material_download_stats(self):
        """Test getting download statistics for a material."""
        MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=1000
        )
        MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=2000
        )

        stats = DownloadLogger.get_material_download_stats(self.material.id)

        self.assertEqual(stats['total_downloads'], 2)
        self.assertEqual(stats['unique_users'], 1)
        self.assertEqual(stats['total_data_transferred'], 3000)
        self.assertIsNotNone(stats['latest_download'])

    def test_get_user_download_stats(self):
        """Test getting download statistics for a user."""
        material2 = Material.objects.create(
            title="Another Material",
            description="Test",
            content="Test",
            author=self.teacher,
            subject=self.subject,
            is_public=True,
            status=Material.Status.ACTIVE
        )

        MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=1000
        )
        MaterialDownloadLog.objects.create(
            material=material2,
            user=self.student,
            ip_address='192.168.1.1',
            file_size=2000
        )

        stats = DownloadLogger.get_user_download_stats(self.student.id)

        self.assertEqual(stats['total_downloads'], 2)
        self.assertEqual(stats['materials_downloaded'], 2)
        self.assertEqual(stats['total_data_transferred'], 3000)

    def test_material_download_count_property(self):
        """Test Material.download_count property."""
        for i in range(3):
            MaterialDownloadLog.objects.create(
                material=self.material,
                user=self.student,
                ip_address='192.168.1.1'
            )

        self.assertEqual(self.material.download_count, 3)

    def test_cleanup_old_logs(self):
        """Test cleanup command for old logs."""
        now = timezone.now()

        old_log = MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1',
            timestamp=now - timedelta(days=181)
        )

        recent_log = MaterialDownloadLog.objects.create(
            material=self.material,
            user=self.student,
            ip_address='192.168.1.1'
        )

        deleted_count, details = DownloadLogger.cleanup_old_logs(days=180)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(MaterialDownloadLog.objects.filter(id=old_log.id).exists())
        self.assertTrue(MaterialDownloadLog.objects.filter(id=recent_log.id).exists())
