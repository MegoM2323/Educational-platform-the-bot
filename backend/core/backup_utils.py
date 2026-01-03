"""
Утилиты для создания резервных копий и восстановления данных
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db import connection
from django.utils import timezone
import subprocess

logger = logging.getLogger(__name__)


class BackupManager:
    """Менеджер для управления резервными копиями"""
    
    def __init__(self):
        self.backup_dir = getattr(settings, 'BACKUP_DIR', '/tmp/backups')
        self.max_backups = getattr(settings, 'MAX_BACKUPS', 30)
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Создает директорию для бэкапов если она не существует"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, mode=0o755)
            logger.info(f"Created backup directory: {self.backup_dir}")
    
    def create_database_backup(self, description: str = None) -> Dict[str, Any]:
        """
        Создает резервную копию PostgreSQL базы данных
        
        Args:
            description: Описание бэкапа
            
        Returns:
            Словарь с информацией о бэкапе
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"db_backup_{timestamp}.sql"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Получаем настройки базы данных
            db_settings = settings.DATABASES['default']
            
            if db_settings['ENGINE'] == 'django.db.backends.postgresql':
                self._create_postgresql_backup(db_settings, backup_path)
            else:
                raise Exception(f"Unsupported database engine: {db_settings['ENGINE']}. Only PostgreSQL is supported.")
            
            # Создаем метаданные бэкапа
            backup_info = {
                'id': f"backup_{timestamp}",
                'filename': backup_filename,
                'path': backup_path,
                'created_at': timezone.now().isoformat(),
                'description': description or f"Database backup {timestamp}",
                'size': os.path.getsize(backup_path),
                'type': 'database'
            }
            
            # Сохраняем метаданные
            metadata_path = os.path.join(self.backup_dir, f"{backup_filename}.meta")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Database backup created: {backup_path}")
            self._cleanup_old_backups()
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            raise
    
    def _create_postgresql_backup(self, db_settings: Dict, backup_path: str):
        """Создает бэкап PostgreSQL базы данных"""
        cmd = [
            'pg_dump',
            '-h', db_settings.get('HOST', 'localhost'),
            '-p', str(db_settings.get('PORT', 5432)),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', backup_path
        ]
        
        # Устанавливаем пароль через переменную окружения
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PostgreSQL backup failed: {result.stderr}")
            
    def create_media_backup(self, description: str = None) -> Dict[str, Any]:
        """
        Создает резервную копию медиафайлов
        
        Args:
            description: Описание бэкапа
            
        Returns:
            Словарь с информацией о бэкапе
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"media_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            media_root = settings.MEDIA_ROOT
            
            if not os.path.exists(media_root):
                logger.warning(f"Media directory does not exist: {media_root}")
                return None
            
            # Создаем архив медиафайлов
            cmd = ['tar', '-czf', backup_path, '-C', os.path.dirname(media_root), os.path.basename(media_root)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Media backup failed: {result.stderr}")
            
            # Создаем метаданные бэкапа
            backup_info = {
                'id': f"media_backup_{timestamp}",
                'filename': backup_filename,
                'path': backup_path,
                'created_at': timezone.now().isoformat(),
                'description': description or f"Media backup {timestamp}",
                'size': os.path.getsize(backup_path),
                'type': 'media'
            }
            
            # Сохраняем метаданные
            metadata_path = os.path.join(self.backup_dir, f"{backup_filename}.meta")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Media backup created: {backup_path}")
            self._cleanup_old_backups()
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Error creating media backup: {e}")
            raise
    
    def create_full_backup(self, description: str = None) -> Dict[str, Any]:
        """
        Создает полную резервную копию (база данных + медиафайлы)
        
        Args:
            description: Описание бэкапа
            
        Returns:
            Словарь с информацией о бэкапе
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = f"full_backup_{timestamp}"
        
        try:
            # Создаем бэкап базы данных
            db_backup = self.create_database_backup(f"Full backup DB - {description or timestamp}")
            
            # Создаем бэкап медиафайлов
            media_backup = self.create_media_backup(f"Full backup Media - {description or timestamp}")
            
            # Создаем общие метаданные
            full_backup_info = {
                'id': backup_id,
                'created_at': timezone.now().isoformat(),
                'description': description or f"Full backup {timestamp}",
                'type': 'full',
                'components': {
                    'database': db_backup,
                    'media': media_backup
                }
            }
            
            # Сохраняем общие метаданные
            metadata_path = os.path.join(self.backup_dir, f"{backup_id}.meta")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(full_backup_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Full backup created: {backup_id}")
            
            return full_backup_info
            
        except Exception as e:
            logger.error(f"Error creating full backup: {e}")
            raise
    
    def list_backups(self, backup_type: str = None) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных бэкапов
        
        Args:
            backup_type: Тип бэкапа для фильтрации (database, media, full)
            
        Returns:
            Список информации о бэкапах
        """
        backups = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.meta'):
                metadata_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    if backup_type is None or backup_info.get('type') == backup_type:
                        backups.append(backup_info)
                        
                except Exception as e:
                    logger.warning(f"Error reading backup metadata {filename}: {e}")
        
        # Сортируем по дате создания (новые сначала)
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return backups
    
    def restore_database_backup(self, backup_id: str) -> bool:
        """
        Восстанавливает PostgreSQL базу данных из бэкапа
        
        Args:
            backup_id: ID бэкапа для восстановления
            
        Returns:
            True если восстановление успешно
        """
        try:
            # Находим файл бэкапа
            backup_info = self._find_backup(backup_id)
            if not backup_info:
                raise Exception(f"Backup not found: {backup_id}")
            
            backup_path = backup_info['path']
            if not os.path.exists(backup_path):
                raise Exception(f"Backup file not found: {backup_path}")
            
            # Получаем настройки базы данных
            db_settings = settings.DATABASES['default']
            
            if db_settings['ENGINE'] == 'django.db.backends.postgresql':
                self._restore_postgresql_backup(db_settings, backup_path)
            else:
                raise Exception(f"Unsupported database engine: {db_settings['ENGINE']}. Only PostgreSQL is supported.")
            
            logger.info(f"Database restored from backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database backup: {e}")
            return False
    
    def _restore_postgresql_backup(self, db_settings: Dict, backup_path: str):
        """Восстанавливает PostgreSQL базу данных"""
        cmd = [
            'psql',
            '-h', db_settings.get('HOST', 'localhost'),
            '-p', str(db_settings.get('PORT', 5432)),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', backup_path
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PostgreSQL restore failed: {result.stderr}")
            
    def _find_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Находит информацию о бэкапе по ID"""
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.meta'):
                metadata_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    if backup_info.get('id') == backup_id:
                        return backup_info
                        
                except Exception as e:
                    logger.warning(f"Error reading backup metadata {filename}: {e}")
        
        return None
    
    def _cleanup_old_backups(self):
        """Удаляет старые бэкапы, оставляя только последние MAX_BACKUPS"""
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            # Удаляем старые бэкапы
            backups_to_delete = backups[self.max_backups:]
            
            for backup in backups_to_delete:
                try:
                    # Удаляем файл бэкапа
                    if os.path.exists(backup['path']):
                        os.remove(backup['path'])
                    
                    # Удаляем метаданные
                    metadata_path = os.path.join(self.backup_dir, f"{backup['filename']}.meta")
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    
                    logger.info(f"Deleted old backup: {backup['id']}")
                    
                except Exception as e:
                    logger.warning(f"Error deleting old backup {backup['id']}: {e}")


# Глобальный экземпляр менеджера бэкапов
backup_manager = BackupManager()


def create_automatic_backup():
    """Создает автоматический бэкап (вызывается по расписанию)"""
    try:
        backup_info = backup_manager.create_full_backup("Automatic backup")
        logger.info(f"Automatic backup created: {backup_info['id']}")
        return backup_info
    except Exception as e:
        logger.error(f"Error creating automatic backup: {e}")
        return None


def verify_data_integrity() -> Dict[str, Any]:
    """
    Проверяет целостность данных в системе
    
    Returns:
        Словарь с результатами проверки
    """
    integrity_checks = {
        'orphaned_records': [],
        'missing_relations': [],
        'data_consistency': [],
        'overall_status': 'healthy'
    }
    
    try:
        with connection.cursor() as cursor:
            # Проверяем пользователей без профилей
            cursor.execute("""
                SELECT u.id, u.username, u.role 
                FROM accounts_user u 
                LEFT JOIN accounts_studentprofile sp ON u.id = sp.user_id
                LEFT JOIN accounts_teacherprofile tp ON u.id = tp.user_id
                LEFT JOIN accounts_tutorprofile tup ON u.id = tup.user_id
                LEFT JOIN accounts_parentprofile pp ON u.id = pp.user_id
                WHERE sp.user_id IS NULL 
                AND tp.user_id IS NULL 
                AND tup.user_id IS NULL 
                AND pp.user_id IS NULL
            """)
            
            orphaned_users = cursor.fetchall()
            if orphaned_users:
                integrity_checks['orphaned_records'].append({
                    'type': 'users_without_profiles',
                    'count': len(orphaned_users),
                    'details': orphaned_users
                })
            
            # Проверяем студентов без родителей (если должны быть)
            cursor.execute("""
                SELECT s.id, s.user_id, u.username
                FROM accounts_studentprofile s
                JOIN accounts_user u ON s.user_id = u.id
                WHERE s.parent_id IS NULL
            """)
            
            students_without_parents = cursor.fetchall()
            if students_without_parents:
                integrity_checks['data_consistency'].append({
                    'type': 'students_without_parents',
                    'count': len(students_without_parents),
                    'details': students_without_parents
                })
        
        # Определяем общий статус
        total_issues = (len(integrity_checks['orphaned_records']) + 
                       len(integrity_checks['missing_relations']) + 
                       len(integrity_checks['data_consistency']))
        
        if total_issues > 0:
            integrity_checks['overall_status'] = 'issues_found'
        else:
            integrity_checks['overall_status'] = 'healthy'
        
        logger.info(f"Data integrity check completed. Status: {integrity_checks['overall_status']}")
        
        return integrity_checks
        
    except Exception as e:
        logger.error(f"Error during data integrity check: {e}")
        integrity_checks['overall_status'] = 'error'
        integrity_checks['error'] = str(e)
        return integrity_checks
