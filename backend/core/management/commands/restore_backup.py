"""
Management команда для восстановления из резервных копий
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.backup_utils import backup_manager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Восстанавливает базу данных из резервной копии'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_id',
            type=str,
            help='ID резервной копии для восстановления'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить восстановление (обязательно для выполнения)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Показать список доступных резервных копий'
        )
    
    def handle(self, *args, **options):
        if options['list']:
            self.list_backups()
            return
        
        backup_id = options['backup_id']
        confirm = options['confirm']
        
        if not confirm:
            self.stdout.write(
                self.style.WARNING(
                    'ВНИМАНИЕ: Восстановление из резервной копии заменит текущие данные!\n'
                    'Используйте --confirm для подтверждения операции.'
                )
            )
            return
        
        try:
            # Показываем информацию о резервной копии
            backup_info = self.get_backup_info(backup_id)
            if not backup_info:
                raise CommandError(f'Резервная копия с ID {backup_id} не найдена')
            
            self.stdout.write(
                f'Восстановление из резервной копии:\n'
                f'ID: {backup_info["id"]}\n'
                f'Тип: {backup_info["type"]}\n'
                f'Описание: {backup_info["description"]}\n'
                f'Создана: {backup_info["created_at"]}\n'
                f'Размер: {backup_info["size"]} байт\n'
            )
            
            # Выполняем восстановление
            success = backup_manager.restore_database_backup(backup_id)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('База данных успешно восстановлена!')
                )
            else:
                raise CommandError('Ошибка восстановления базы данных')
                
        except Exception as e:
            raise CommandError(f'Ошибка восстановления: {e}')
    
    def get_backup_info(self, backup_id):
        """Получает информацию о резервной копии"""
        try:
            backups = backup_manager.list_backups()
            for backup in backups:
                if backup['id'] == backup_id:
                    return backup
            return None
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return None
    
    def list_backups(self):
        """Показывает список доступных резервных копий"""
        try:
            backups = backup_manager.list_backups()
            
            if not backups:
                self.stdout.write('Резервные копии не найдены')
                return
            
            self.stdout.write(f'Доступные резервные копии ({len(backups)}):\n')
            
            for backup in backups:
                self.stdout.write(
                    f'ID: {backup["id"]}\n'
                    f'Тип: {backup["type"]}\n'
                    f'Описание: {backup["description"]}\n'
                    f'Создана: {backup["created_at"]}\n'
                    f'Размер: {backup["size"]} байт\n'
                    f'---'
                )
                
        except Exception as e:
            raise CommandError(f'Ошибка получения списка резервных копий: {e}')
