"""
Integration tests for backup verification system
"""
import os
import json
import gzip
import hashlib
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

import pytest
from django.test import TestCase, override_settings


class TestBackupVerificationIntegration(TestCase):
    """Integration tests for entire backup verification workflow"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for all tests"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.backup_dir = Path(cls.temp_dir) / 'backups'
        cls.backup_dir.mkdir(parents=True)

        # Create subdirectories
        for subdir in ['daily', 'weekly', 'monthly', 'verification_logs']:
            (cls.backup_dir / subdir).mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def create_test_backup(self, name='backup_test.gz', size_kb=100):
        """Create a test backup file"""
        backup_file = self.backup_dir / 'daily' / name
        test_data = b'backup data' * (size_kb * 102)  # Approximately size_kb kilobytes

        with gzip.open(backup_file, 'wb') as f:
            f.write(test_data)

        return backup_file

    def create_backup_metadata(self, backup_file):
        """Create metadata file for backup"""
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
            'backup_size': f'{backup_file.stat().st_size / 1024:.0f}KB',
            'backup_duration_seconds': 30,
            'backup_checksum_sha256': sha256_hash.hexdigest(),
            'compression': 'gzip',
            'timestamp': int(datetime.now().timestamp()),
            'hostname': 'test-host',
            'database_type': 'postgresql'
        }

        metadata_file = Path(str(backup_file) + '.metadata')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        return metadata_file

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_backup_verification_command_exists(self):
        """Test that verify_backup management command exists"""
        from django.core.management import get_commands

        commands = get_commands()
        assert 'verify_backup' in commands

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_verify_single_backup(self):
        """Test verification of single backup file"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create test backup
        backup_file = self.create_test_backup('backup_20251227_120000.gz')
        self.create_backup_metadata(backup_file)

        # Verify
        result = verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'PASSED'
        assert result['checks']['gzip_integrity']['status'] == 'PASSED'
        assert result['checks']['sha256_checksum']['status'] == 'PASSED'
        assert result['checks']['file_size']['status'] == 'PASSED'

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_verify_multiple_backups(self):
        """Test verification of multiple backup files"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create multiple backups
        for i in range(3):
            backup_file = self.create_test_backup(f'backup_{i:03d}.gz')
            self.create_backup_metadata(backup_file)

        # Verify all
        results = verifier.verify_all_backups()

        assert len(results) >= 3
        assert verifier.verification_results['total_backups'] >= 3
        assert verifier.verification_results['verified_backups'] >= 3
        assert verifier.verification_results['failed_backups'] == 0

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_corrupted_backup_detection(self):
        """Test detection of corrupted backup"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create backup and corrupt it
        backup_file = self.create_test_backup('backup_corrupted.gz')
        self.create_backup_metadata(backup_file)

        # Corrupt the file
        with open(backup_file, 'ab') as f:
            f.write(b'corrupted extra data')

        # Verify - should fail checksum check
        result = verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'FAILED'
        assert result['checks']['sha256_checksum']['status'] == 'FAILED'

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_missing_metadata_detection(self):
        """Test detection of missing metadata"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create backup without metadata
        backup_file = self.create_test_backup('backup_no_metadata.gz')

        # Verify - should fail metadata check
        result = verifier.verify_backup_file(backup_file)

        assert result['overall_status'] == 'FAILED'
        assert result['checks']['metadata']['status'] == 'FAILED'

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_report_generation(self):
        """Test report generation"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()
        verifier.backup_dir = self.backup_dir

        # Create backup
        backup_file = self.create_test_backup('backup_report_test.gz')
        self.create_backup_metadata(backup_file)

        # Verify and generate report
        verifier.verify_backup_file(backup_file)
        report = verifier.generate_verification_report()

        assert 'BACKUP VERIFICATION REPORT' in report
        assert 'SUMMARY' in report
        assert 'CHECKS PERFORMED' in report
        assert 'RECOMMENDATIONS' in report

    @override_settings(BACKUP_DIR='/tmp/test_backups')
    def test_database_integrity_check(self):
        """Test database integrity check"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        # Run integrity check
        checks = verifier.check_database_integrity()

        assert 'checks' in checks
        assert 'overall_status' in checks
        assert checks['overall_status'] in ['HEALTHY', 'ISSUES_FOUND', 'ERROR']

    def test_verify_backup_script_exists(self):
        """Test that verify-backup.sh script exists"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/verify-backup.sh')

        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_restore_test_script_exists(self):
        """Test that restore-test.sh script exists"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/restore-test.sh')

        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_setup_cron_script_exists(self):
        """Test that setup-cron.sh script exists"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/setup-cron.sh')

        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_documentation_exists(self):
        """Test that documentation file exists"""
        doc = Path('/home/mego/Python Projects/THE_BOT_platform/docs/BACKUP_VERIFICATION.md')

        assert doc.exists()
        with open(doc, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Backup Verification' in content
            assert 'Usage' in content
            assert 'Installation' in content


class TestBackupVerificationBashScripts(TestCase):
    """Tests for bash verification scripts"""

    def test_verify_backup_script_syntax(self):
        """Test bash script syntax"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/verify-backup.sh')

        result = subprocess.run(
            ['bash', '-n', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error in verify-backup.sh: {result.stderr}"

    def test_restore_test_script_syntax(self):
        """Test bash script syntax"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/restore-test.sh')

        result = subprocess.run(
            ['bash', '-n', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error in restore-test.sh: {result.stderr}"

    def test_setup_cron_script_syntax(self):
        """Test bash script syntax"""
        script = Path('/home/mego/Python Projects/THE_BOT_platform/scripts/backup/setup-cron.sh')

        result = subprocess.run(
            ['bash', '-n', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error in setup-cron.sh: {result.stderr}"


# Pytest-style tests
@pytest.mark.django_db
class TestBackupVerificationPytest:
    """Pytest-style integration tests"""

    def test_backup_verification_module_imports(self):
        """Test that backup verification module imports correctly"""
        from core.management.commands.verify_backup import BackupVerifier

        assert BackupVerifier is not None

    def test_create_verifier_instance(self):
        """Test creating BackupVerifier instance"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert verifier.backup_dir is not None
        assert verifier.verification_log_dir is not None
        assert verifier.verification_timestamp is not None

    def test_verify_gzip_integrity_method_exists(self):
        """Test that verify_gzip_integrity method exists"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert hasattr(verifier, 'verify_gzip_integrity')
        assert callable(verifier.verify_gzip_integrity)

    def test_verify_sha256_checksum_method_exists(self):
        """Test that verify_sha256_checksum method exists"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert hasattr(verifier, 'verify_sha256_checksum')
        assert callable(verifier.verify_sha256_checksum)

    def test_verify_file_size_method_exists(self):
        """Test that verify_file_size method exists"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert hasattr(verifier, 'verify_file_size')
        assert callable(verifier.verify_file_size)

    def test_check_database_integrity_method_exists(self):
        """Test that check_database_integrity method exists"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert hasattr(verifier, 'check_database_integrity')
        assert callable(verifier.check_database_integrity)

    def test_generate_verification_report_method_exists(self):
        """Test that generate_verification_report method exists"""
        from core.management.commands.verify_backup import BackupVerifier

        verifier = BackupVerifier()

        assert hasattr(verifier, 'generate_verification_report')
        assert callable(verifier.generate_verification_report)
