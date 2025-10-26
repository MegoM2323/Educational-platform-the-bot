"""
Management команда для создания резервных копий
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.backup_utils import backup_manager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Создает резервную копию базы данных и/или медиафайлов'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['database', 'media', 'full'],
            default='full',
            help='Тип резервной копии (database, media, full)'
        )
        parser.add_argument(
            '--description',
            type=str,
            help='Описание резервной копии'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Показать список существующих резервных копий'
        )
    
    def handle(self, *args, **options):
        if options['list']:
            self.list_backups()
            return
        
        backup_type = options['type']
        description = options['description'] or f"Manual {backup_type} backup"
        
        try:
            if backup_type == 'database':
                backup_info = backup_manager.create_database_backup(description)
            elif backup_type == 'media':
                backup_info = backup_manager.create_media_backup(description)
            elif backup_type == 'full':
                backup_info = backup_manager.create_full_backup(description)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Резервная копия создана успешно:\n'
                    f'ID: {backup_info["id"]}\n'
                    f'Тип: {backup_info["type"]}\n'
                    f'Размер: {backup_info["size"]} байт\n'
                    f'Путь: {backup_info["path"]}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Ошибка создания резервной копии: {e}')
    
    def list_backups(self):
        """Показывает список существующих резервных копий"""
        try:
            backups = backup_manager.list_backups()
            
            if not backups:
                self.stdout.write('Резервные копии не найдены')
                return
            
            self.stdout.write(f'Найдено резервных копий: {len(backups)}\n')
            
            for backup in backups:
                self.stdout.write(
                    f'ID: {backup["id"]}\n'
                    f'Тип: {backup["type"]}\n'
                    f'Описание: {backup["description"]}\n'
                    f'Создана: {backup["created_at"]}\n'
                    f'Размер: {backup["size"]} байт\n'
                    f'Файл: {backup["filename"]}\n'
                    f'---'
                )
                
        except Exception as e:
            raise CommandError(f'Ошибка получения списка резервных копий: {e}')
