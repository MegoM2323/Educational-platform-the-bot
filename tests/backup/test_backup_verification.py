"""
Tests for backup verification system
"""
import os
import json
import gzip
import hashlib
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, override_settings
from django.core.management import call_command
from django.db import connection
from io import StringIO

# Import the backup verifier
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))

from core.management.commands.verify_backup import BackupVerifier


class TestBackupVerifier(TestCase):
    """Tests for BackupVerifier class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = Path(self.temp_dir) / 'backups'
        self.backup_dir.mkdir(parents=True)
        self.verifier = BackupVerifier()
        self.verifier.backup_dir = self.backup_dir

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_backup_file(self, filename='backup_test.gz', size=1024):
        """Helper to create a test backup file"""
        backup_file = self.backup_dir / filename
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        # Create test data
        test_data = b'X' * size

        # Compress it
        with gzip.open(backup_file, 'wb') as f:
            f.write(test_data)

        return backup_file

    def create_test_metadata(self, backup_file):
        """Helper to create metadata for backup file"""
        sha256_hash = hashlib.sha256()
        with open(backup_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)

        metadata = {
            'backup_file': backup_file.name,
            'backup_path': str(backup_file),
            'backup_type': 'postgresql',
            'backup_category': 'daily',
            'backup_date': datetime.now().isoformat(),
            'backup_size': '1KB',
            'backup_duration_seconds': 10,
            'backup_checksum_sha256': sha256_hash.hexdigest(),
            'compression': 'gzip',
            'timestamp': int(datetime.now().timestamp()),
            'hostname': 'test-host',
            'database_type': 'postgresql'
        }

        metadata_file = Path(str(backup_file) + '.metadata')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return metadata_file

    def test_verify_gzip_integrity_valid(self):
        """Test gzip integrity check with valid file"""
        backup_file = self.create_test_backup_file()

        success, message = self.verifier.verify_gzip_integrity(backup_file)

        assert success is True
        assert 'OK' in message

    def test_verify_gzip_integrity_corrupted(self):
        """Test gzip integrity check with corrupted file"""
        backup_file = self.create_test_backup_file()

        # Corrupt the file
        with open(backup_file, 'ab') as f:
            f.write(b'corrupted data')

        success, message = self.verifier.verify_gzip_integrity(backup_file)

        assert success is False
        assert 'failed' in message.lower()

    def test_verify_sha256_checksum_valid(self):
        """Test SHA256 checksum verification with valid checksum"""
        backup_file = self.create_test_backup_file()
        metadata_file = self.create_test_metadata(backup_file)

        success, message = self.verifier.verify_sha256_checksum(backup_file, metadata_file)

        assert success is True
        assert 'verified' in message.lower()

    def test_verify_sha256_checksum_missing_metadata(self):
        """Test SHA256 checksum verification with missing metadata"""
        backup_file = self.create_test_backup_file()

        success, message = self.verifier.verify_sha256_checksum(
            backup_file,
            Path(str(backup_file) + '.metadata.nonexistent')
        )

        assert success is False
        assert 'not found' in message.lower()

    def test_verify_sha256_checksum_mismatch(self):
        """Test SHA256 checksum verification with mismatched checksum"""
        backup_file = self.create_test_backup_file()
        metadata_file = self.create_test_metadata(backup_file)

        # Corrupt the file after metadata creation
        with open(backup_file, 'ab') as f:
            f.write(b'extra data')

        success, message = self.verifier.verify_sha256_checksum(backup_file, metadata_file)

        assert success is False
        assert 'mismatch' in message.lower()

    def test_verify_file_size_valid(self):
        """Test file size verification with valid size"""
        backup_file = self.create_test_backup_file(size=10 * 1024)

        success, message = self.verifier.verify_file_size(backup_file)

        assert success is True
        assert 'OK' in message

    def test_verify_file_size_too_small(self):
        """Test file size verification with file too small"""
        # Create a file with only 50 bytes
        backup_file = self.backup_dir / 'backup_small.gz'
        backup_file.write_bytes(b'X' * 50)

        success, message = self.verifier.verify_file_size(backup_file)

        assert success is False
        assert 'small' in message.lower()

    def test_verify_file_size_too_large(self):
        """Test file size verification with file too large"""
        # Create metadata for a hypothetical large file
        backup_file = self.backup_dir / 'backup_large.gz'

        # Mock the stat method to return a large size
        with patch.object(backup_file, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 200 * 1024 * 1024 * 1024  # 200GB

            success, message = self.verifier.verify_file_size(backup_file)

            assert success is False
            assert 'large' in message.lower()

    def test_verify_backup_extractable_valid(self):
        """Test backup extractability with valid file"""
        backup_file = self.create_test_backup_file()

        success, message = self.verifier.verify_backup_extractable(backup_file)

        assert success is True
        assert 'extractable' in message.lower()

    def test_verify_backup_extractable_corrupted(self):
        """Test backup extractability with corrupted file"""
        backup_file = self.create_test_backup_file()

        # Corrupt the file
        with open(backup_file, 'w') as f:
            f.write('not valid gzip data')

        success, message = self.verifier.verify_backup_extractable(backup_file)

        assert success is False
        assert 'failed' in message.lower()

    def test_verify_metadata_valid(self):
        """Test metadata verification with valid metadata"""
        backup_file = self.create_test_backup_file()
        self.create_test_metadata(backup_file)

        success, message = self.verifier.verify_metadata(backup_file)

        assert success is True
        assert 'valid' in message.lower()

    def test_verify_metadata_missing(self):
        """Test metadata verification with missing metadata"""
        backup_file = self.create_test_backup_file()

        success, message = self.verifier.verify_metadata(backup_file)

        assert success is False
        assert 'not found' in message.lower()

    def test_verify_metadata_corrupted(self):
        """Test metadata verification with corrupted metadata"""
        backup_file = self.create_test_backup_file()
        metadata_file = Path(str(backup_file) + '.metadata')

        # Write invalid JSON
        with open(metadata_file, 'w') as f:
            f.write('{ invalid json }')

        success, message = self.verifier.verify_metadata(backup_file)

        assert success is False
        assert 'invalid' in message.lower()

    def test_verify_metadata_missing_fields(self):
        """Test metadata verification with missing required fields"""
        backup_file = self.create_test_backup_file()
        metadata_file = Path(str(backup_file) + '.metadata')

        # Write metadata with missing fields
        metadata = {
            'backup_file': 'test.gz',
            # Missing other required fields
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        success, message = self.verifier.verify_metadata(backup_file)

        assert success is False
        assert 'missing' in message.lower()

    def test_verify_backup_file_complete(self):
        """Test complete backup file verification"""
        backup_file = self.create_test_backup_file()
        self.create_test_metadata(backup_file)

        result = self.verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'PASSED'
        assert result['backup_file'] == 'backup_test.gz'

        # Check all sub-checks
        checks = result['checks']
        assert checks['gzip_integrity']['status'] == 'PASSED'
        assert checks['file_size']['status'] == 'PASSED'
        assert checks['metadata']['status'] == 'PASSED'
        assert checks['sha256_checksum']['status'] == 'PASSED'
        assert checks['extractable']['status'] == 'PASSED'

    def test_verify_backup_file_not_found(self):
        """Test backup file verification with non-existent file"""
        backup_file = self.backup_dir / 'nonexistent.gz'

        result = self.verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'FAILED'
        assert 'error' in result

    def test_verify_backup_file_multiple_failures(self):
        """Test backup file with multiple verification failures"""
        backup_file = self.create_test_backup_file(size=50)  # Too small
        # Don't create metadata

        result = self.verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'FAILED'

        # Should have failures
        failed_checks = [
            check for check in result['checks'].values()
            if check['status'] == 'FAILED'
        ]
        assert len(failed_checks) > 0

    def test_verify_all_backups_empty_directory(self):
        """Test verification with no backup files"""
        results = self.verifier.verify_all_backups()

        assert self.verifier.verification_results['total_backups'] == 0
        assert self.verifier.verification_results['verified_backups'] == 0
        assert self.verifier.verification_results['failed_backups'] == 0

    def test_verify_all_backups_multiple(self):
        """Test verification of multiple backup files"""
        # Create multiple backup files
        backup_files = []
        for i in range(3):
            backup_file = self.backup_dir / f'backup_test_{i}.gz'
            backup_file = self.create_test_backup_file(f'daily/backup_test_{i}.gz')
            self.create_test_metadata(backup_file)
            backup_files.append(backup_file)

        results = self.verifier.verify_all_backups()

        assert self.verifier.verification_results['total_backups'] == 3
        assert self.verifier.verification_results['verified_backups'] == 3
        assert self.verifier.verification_results['failed_backups'] == 0

    def test_check_database_integrity(self):
        """Test database integrity check"""
        checks = self.verifier.check_database_integrity()

        assert 'checks' in checks
        assert 'overall_status' in checks
        assert checks['overall_status'] in ['HEALTHY', 'ISSUES_FOUND', 'ERROR']

    def test_generate_verification_report(self):
        """Test report generation"""
        backup_file = self.create_test_backup_file()
        self.create_test_metadata(backup_file)
        self.verifier.verify_backup_file(backup_file)

        report = self.verifier.generate_verification_report()

        assert 'BACKUP VERIFICATION REPORT' in report
        assert 'SUMMARY' in report
        assert 'CHECKS PERFORMED' in report
        assert 'RECOMMENDATIONS' in report


class TestVerifyBackupCommand(TestCase):
    """Tests for verify_backup management command"""

    def test_command_runs_successfully(self):
        """Test that command runs without errors"""
        out = StringIO()
        call_command('verify_backup', stdout=out)

        output = out.getvalue()
        assert 'verify_backup' in output.lower() or 'резервн' in output.lower()

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_command_with_all_flag(self):
        """Test command with --all flag"""
        out = StringIO()
        call_command('verify_backup', '--all', stdout=out)

        output = out.getvalue()
        # Should complete without error


class TestBackupVerificationIntegration(TestCase):
    """Integration tests for backup verification system"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = Path(self.temp_dir) / 'backups'
        self.backup_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backup_verification_workflow(self):
        """Test complete backup verification workflow"""
        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create test backup
        backup_file = self.backup_dir / 'daily' / 'backup_20251227_120000.gz'
        backup_file.parent.mkdir(parents=True)

        with gzip.open(backup_file, 'wb') as f:
            f.write(b'backup data' * 1000)

        # Create metadata
        sha256_hash = hashlib.sha256()
        with open(backup_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)

        metadata = {
            'backup_file': backup_file.name,
            'backup_path': str(backup_file),
            'backup_type': 'postgresql',
            'backup_category': 'daily',
            'backup_date': datetime.now().isoformat(),
            'backup_size': '11KB',
            'backup_duration_seconds': 10,
            'backup_checksum_sha256': sha256_hash.hexdigest(),
            'compression': 'gzip',
            'timestamp': int(datetime.now().timestamp()),
            'hostname': 'test-host',
            'database_type': 'postgresql'
        }

        metadata_file = Path(str(backup_file) + '.metadata')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # Run verification
        result = verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'PASSED'
        assert result['checks']['gzip_integrity']['status'] == 'PASSED'
        assert result['checks']['sha256_checksum']['status'] == 'PASSED'

        # Generate report
        report = verifier.generate_verification_report()
        assert 'PASSED' in report


# Pytest-style tests for backup verification
@pytest.mark.django_db
class TestBackupVerificationPytest:
    """Pytest-style tests for backup verification"""

    def test_verifier_initialization(self):
        """Test BackupVerifier initialization"""
        verifier = BackupVerifier()

        assert verifier.backup_dir is not None
        assert verifier.verification_log_dir is not None

    def test_create_valid_backup_file(self, tmp_path):
        """Test creating and verifying a valid backup file"""
        backup_file = tmp_path / 'backup_test.gz'

        with gzip.open(backup_file, 'wb') as f:
            f.write(b'test data' * 1000)

        # Verify it can be read
        with gzip.open(backup_file, 'rb') as f:
            data = f.read()

        assert len(data) > 0
        assert data.startswith(b'test data')

    def test_checksum_calculation(self, tmp_path):
        """Test SHA256 checksum calculation"""
        backup_file = tmp_path / 'backup_test.gz'
        test_data = b'test data for checksum'

        with gzip.open(backup_file, 'wb') as f:
            f.write(test_data)

        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(backup_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)

        checksum = sha256_hash.hexdigest()

        assert len(checksum) == 64  # SHA256 is 64 hex characters
        assert checksum.isalnum()
