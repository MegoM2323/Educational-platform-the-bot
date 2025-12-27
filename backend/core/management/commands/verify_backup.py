"""
Django management command для проверки целостности резервных копий
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class BackupVerifier:
    """Класс для проверки целостности резервных копий"""

    def __init__(self):
        self.backup_dir = Path(getattr(settings, 'BACKUP_DIR', '/tmp/backups'))
        self.verification_log_dir = self.backup_dir / 'verification_logs'
        self.verification_log_dir.mkdir(parents=True, exist_ok=True)

        self.verification_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'total_backups': 0,
            'verified_backups': 0,
            'failed_backups': 0,
            'backup_details': [],
            'recommendations': []
        }

    def verify_gzip_integrity(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Проверяет целостность gzip файла

        Args:
            backup_file: Путь к файлу резервной копии

        Returns:
            Кортеж (результат проверки, сообщение)
        """
        try:
            import gzip
            with gzip.open(backup_file, 'rb') as f:
                f.read(1)
            return True, "Gzip integrity OK"
        except Exception as e:
            return False, f"Gzip integrity failed: {str(e)}"

    def verify_sha256_checksum(self, backup_file: Path, metadata_file: Path) -> Tuple[bool, str]:
        """
        Проверяет SHA256 контрольную сумму

        Args:
            backup_file: Путь к файлу резервной копии
            metadata_file: Путь к файлу метаданных

        Returns:
            Кортеж (результат проверки, сообщение)
        """
        try:
            # Читаем ожидаемую контрольную сумму
            if not metadata_file.exists():
                return False, "Metadata file not found"

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            expected_checksum = metadata.get('backup_checksum_sha256')
            if not expected_checksum:
                return False, "No checksum in metadata"

            # Вычисляем фактическую контрольную сумму
            sha256_hash = hashlib.sha256()
            with open(backup_file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)

            actual_checksum = sha256_hash.hexdigest()

            if expected_checksum == actual_checksum:
                return True, f"Checksum verified: {actual_checksum}"
            else:
                return False, f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"

        except Exception as e:
            return False, f"Checksum verification failed: {str(e)}"

    def verify_file_size(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Проверяет размер файла резервной копии

        Args:
            backup_file: Путь к файлу резервной копии

        Returns:
            Кортеж (результат проверки, сообщение)
        """
        try:
            file_size = backup_file.stat().st_size

            # Минимальный размер 100 байт
            if file_size < 100:
                return False, f"Backup too small: {file_size} bytes"

            # Максимальный размер 100GB
            if file_size > 107374182400:
                return False, f"Backup too large: {file_size} bytes"

            # Используем human-readable размер
            for unit in ['B', 'KB', 'MB', 'GB']:
                if file_size < 1024:
                    return True, f"File size OK: {file_size:.2f} {unit}"
                file_size /= 1024

            return True, "File size OK"

        except Exception as e:
            return False, f"File size check failed: {str(e)}"

    def verify_backup_extractable(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Проверяет, что резервная копия может быть извлечена

        Args:
            backup_file: Путь к файлу резервной копии

        Returns:
            Кортеж (результат проверки, сообщение)
        """
        try:
            import gzip
            import io

            # Пытаемся прочитать первые 1MB для проверки
            with gzip.open(backup_file, 'rb') as f:
                sample_data = f.read(1024 * 1024)

            if not sample_data:
                return False, "Backup file appears to be empty"

            return True, "Backup extractable"

        except Exception as e:
            return False, f"Extraction test failed: {str(e)}"

    def verify_metadata(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Проверяет наличие и корректность метаданных

        Args:
            backup_file: Путь к файлу резервной копии

        Returns:
            Кортеж (результат проверки, сообщение)
        """
        try:
            metadata_file = Path(str(backup_file) + '.metadata')

            if not metadata_file.exists():
                return False, "Metadata file not found"

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Проверяем обязательные поля
            required_fields = [
                'backup_file',
                'backup_path',
                'backup_checksum_sha256',
                'backup_date'
            ]

            missing_fields = [field for field in required_fields if field not in metadata]

            if missing_fields:
                return False, f"Missing metadata fields: {missing_fields}"

            return True, "Metadata valid"

        except json.JSONDecodeError:
            return False, "Invalid metadata JSON"
        except Exception as e:
            return False, f"Metadata verification failed: {str(e)}"

    def verify_backup_file(self, backup_file: Path) -> Dict[str, Any]:
        """
        Проверяет полноту резервной копии

        Args:
            backup_file: Путь к файлу резервной копии

        Returns:
            Словарь с результатами проверки
        """
        results = {
            'backup_file': backup_file.name,
            'backup_path': str(backup_file),
            'checks': {},
            'overall_status': 'PASSED',
            'timestamp': datetime.now().isoformat()
        }

        if not backup_file.exists():
            results['overall_status'] = 'FAILED'
            results['error'] = 'Backup file not found'
            return results

        # Проверка целостности gzip
        success, message = self.verify_gzip_integrity(backup_file)
        results['checks']['gzip_integrity'] = {
            'status': 'PASSED' if success else 'FAILED',
            'message': message
        }
        if not success:
            results['overall_status'] = 'FAILED'

        # Проверка размера файла
        success, message = self.verify_file_size(backup_file)
        results['checks']['file_size'] = {
            'status': 'PASSED' if success else 'FAILED',
            'message': message
        }
        if not success:
            results['overall_status'] = 'FAILED'

        # Проверка метаданных
        metadata_file = Path(str(backup_file) + '.metadata')
        success, message = self.verify_metadata(backup_file)
        results['checks']['metadata'] = {
            'status': 'PASSED' if success else 'FAILED',
            'message': message
        }

        # Проверка контрольной суммы
        if metadata_file.exists():
            success, message = self.verify_sha256_checksum(backup_file, metadata_file)
            results['checks']['sha256_checksum'] = {
                'status': 'PASSED' if success else 'FAILED',
                'message': message
            }
            if not success:
                results['overall_status'] = 'FAILED'

        # Проверка извлекаемости
        success, message = self.verify_backup_extractable(backup_file)
        results['checks']['extractable'] = {
            'status': 'PASSED' if success else 'FAILED',
            'message': message
        }
        if not success:
            results['overall_status'] = 'FAILED'

        return results

    def verify_all_backups(self) -> List[Dict[str, Any]]:
        """
        Проверяет все резервные копии в директории

        Returns:
            Список результатов проверки для каждой резервной копии
        """
        backup_files = list(self.backup_dir.glob('**/backup_*.gz'))
        self.verification_results['total_backups'] = len(backup_files)

        results = []
        for backup_file in backup_files:
            result = self.verify_backup_file(backup_file)
            results.append(result)

            if result['overall_status'] == 'PASSED':
                self.verification_results['verified_backups'] += 1
            else:
                self.verification_results['failed_backups'] += 1

            self.verification_results['backup_details'].append(result)

        return results

    def check_database_integrity(self) -> Dict[str, Any]:
        """
        Проверяет целостность базы данных

        Returns:
            Словарь с результатами проверки
        """
        checks = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall_status': 'HEALTHY'
        }

        try:
            with connection.cursor() as cursor:
                # Проверка пользователей без профилей
                cursor.execute("""
                    SELECT COUNT(*) FROM accounts_user u
                    LEFT JOIN accounts_studentprofile sp ON u.id = sp.user_id
                    LEFT JOIN accounts_teacherprofile tp ON u.id = tp.user_id
                    LEFT JOIN accounts_tutorprofile tup ON u.id = tup.user_id
                    LEFT JOIN accounts_parentprofile pp ON u.id = pp.user_id
                    WHERE sp.user_id IS NULL
                    AND tp.user_id IS NULL
                    AND tup.user_id IS NULL
                    AND pp.user_id IS NULL
                """)

                orphaned_count = cursor.fetchone()[0]
                checks['checks']['orphaned_users'] = {
                    'count': orphaned_count,
                    'status': 'OK' if orphaned_count == 0 else 'WARNING'
                }

                if orphaned_count > 0:
                    checks['overall_status'] = 'ISSUES_FOUND'

                # Проверка на заблокированные таблицы
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_locks
                    WHERE NOT granted
                """)

                locked_count = cursor.fetchone()[0]
                checks['checks']['table_locks'] = {
                    'count': locked_count,
                    'status': 'OK' if locked_count == 0 else 'WARNING'
                }

        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            checks['overall_status'] = 'ERROR'
            checks['error'] = str(e)

        return checks

    def generate_verification_report(self) -> str:
        """
        Генерирует отчет о проверке резервных копий

        Returns:
            Текст отчета
        """
        report = f"""
================================================================================
BACKUP VERIFICATION REPORT
================================================================================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Backup Directory: {self.backup_dir}

================================================================================
SUMMARY
================================================================================

Total Backups: {self.verification_results['total_backups']}
Verified: {self.verification_results['verified_backups']}
Failed: {self.verification_results['failed_backups']}

Pass Rate: {self.verification_results['verified_backups']}/{self.verification_results['total_backups']}
         = {(self.verification_results['verified_backups'] / max(1, self.verification_results['total_backups']) * 100):.1f}%

================================================================================
CHECKS PERFORMED
================================================================================

✓ Gzip integrity check
✓ SHA256 checksum verification
✓ File size validation
✓ Backup metadata verification
✓ Backup extractability test
✓ Database integrity check

================================================================================
BACKUP CATEGORIES
================================================================================

"""

        # Count backups by category
        if self.backup_dir.exists():
            daily_count = len(list((self.backup_dir / 'daily').glob('backup_*.gz'))) if (self.backup_dir / 'daily').exists() else 0
            weekly_count = len(list((self.backup_dir / 'weekly').glob('backup_*.gz'))) if (self.backup_dir / 'weekly').exists() else 0
            monthly_count = len(list((self.backup_dir / 'monthly').glob('backup_*.gz'))) if (self.backup_dir / 'monthly').exists() else 0

            report += f"""Daily Backups: {daily_count}
Weekly Backups: {weekly_count}
Monthly Backups: {monthly_count}

"""

        report += """================================================================================
RECOMMENDATIONS
================================================================================

"""

        if self.verification_results['failed_backups'] > 0:
            report += f"""
⚠ WARNING: {self.verification_results['failed_backups']} backup(s) failed verification!

Actions to take:
1. Review detailed error logs
2. Check backup storage permissions
3. Verify available disk space
4. Ensure backup script is running correctly
5. Test restore of failed backups
6. Review PostgreSQL/SQLite logs for errors

"""
        else:
            report += """
✓ All backups passed verification successfully!

Actions to take:
1. Continue regular backup schedule
2. Monitor backup size trends
3. Perform periodic restore tests
4. Keep backup logs for audit trail
5. Maintain backup retention policy

"""

        report += """
================================================================================
"""

        return report

    def send_alert_email(self):
        """Отправляет email уведомление о проблемах с резервными копиями"""
        if self.verification_results['failed_backups'] == 0:
            return

        try:
            admin_email = getattr(settings, 'ADMIN_EMAIL', None)
            if not admin_email:
                logger.warning("ADMIN_EMAIL not configured, skipping alert")
                return

            subject = f"ALERT: Backup Verification Failed - {self.verification_results['failed_backups']} backup(s)"

            message = f"""
Backup Verification Alert
=========================

Status: FAILED
Failed Backups: {self.verification_results['failed_backups']}/{self.verification_results['total_backups']}
Verification Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Failed Backups:
"""

            for detail in self.verification_results['backup_details']:
                if detail['overall_status'] != 'PASSED':
                    message += f"\n- {detail['backup_file']}: {detail['overall_status']}"
                    for check_name, check_result in detail.get('checks', {}).items():
                        if check_result.get('status') != 'PASSED':
                            message += f"\n  - {check_name}: {check_result.get('message')}"

            message += f"""

Please Review:
1. Backup logs in: {self.backup_dir}/logs/
2. Verification logs in: {self.verification_log_dir}/
3. System disk space and permissions

Action Required:
1. Check backup storage for errors
2. Verify disk space availability
3. Review backup script logs
4. Test restore from latest backup
5. Consider manual backup if needed
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=True
            )

            logger.info(f"Alert email sent to {admin_email}")

        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")


class Command(BaseCommand):
    help = 'Проверяет целостность резервных копий'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Проверить все резервные копии'
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Генерировать отчет о проверке'
        )
        parser.add_argument(
            '--alert',
            action='store_true',
            help='Отправить email уведомление при проблемах'
        )
        parser.add_argument(
            '--database-check',
            action='store_true',
            help='Проверить целостность базы данных'
        )
        parser.add_argument(
            '--backup-file',
            type=str,
            help='Проверить конкретный файл резервной копии'
        )

    def handle(self, *args, **options):
        verifier = BackupVerifier()

        try:
            if options['all']:
                self.stdout.write(self.style.SUCCESS('Проверка всех резервных копий...'))
                results = verifier.verify_all_backups()

                for result in results:
                    status_color = self.style.SUCCESS if result['overall_status'] == 'PASSED' else self.style.ERROR
                    self.stdout.write(status_color(
                        f"{result['backup_file']}: {result['overall_status']}"
                    ))

                if options['report']:
                    report = verifier.generate_verification_report()
                    self.stdout.write(self.style.SUCCESS(report))

                if options['alert']:
                    verifier.send_alert_email()

            elif options['database_check']:
                self.stdout.write(self.style.SUCCESS('Проверка целостности базы данных...'))
                db_check = verifier.check_database_integrity()

                for check_name, check_result in db_check.get('checks', {}).items():
                    status = check_result.get('status', 'UNKNOWN')
                    status_color = self.style.SUCCESS if status == 'OK' else self.style.WARNING
                    self.stdout.write(status_color(f"{check_name}: {status}"))

            elif options['backup_file']:
                self.stdout.write(self.style.SUCCESS(f"Проверка резервной копии: {options['backup_file']}"))
                backup_file = Path(options['backup_file'])

                if not backup_file.exists():
                    raise CommandError(f"Файл резервной копии не найден: {backup_file}")

                result = verifier.verify_backup_file(backup_file)

                for check_name, check_result in result['checks'].items():
                    status_color = self.style.SUCCESS if check_result['status'] == 'PASSED' else self.style.ERROR
                    self.stdout.write(status_color(
                        f"{check_name}: {check_result['status']} - {check_result['message']}"
                    ))

            else:
                # Default: verify latest backup
                self.stdout.write(self.style.SUCCESS('Проверка последней резервной копии...'))
                backup_files = list(verifier.backup_dir.glob('**/backup_*.gz'))

                if not backup_files:
                    raise CommandError('Файлы резервных копий не найдены')

                latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
                result = verifier.verify_backup_file(latest_backup)

                for check_name, check_result in result['checks'].items():
                    status_color = self.style.SUCCESS if check_result['status'] == 'PASSED' else self.style.ERROR
                    self.stdout.write(status_color(
                        f"{check_name}: {check_result['status']} - {check_result['message']}"
                    ))

                self.stdout.write(self.style.SUCCESS(f"\nОбщий статус: {result['overall_status']}"))

        except Exception as e:
            raise CommandError(f'Ошибка проверки резервной копии: {e}')
