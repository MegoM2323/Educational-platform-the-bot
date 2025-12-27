"""
Команда Django для синхронизации данных с Supabase
"""
from django.core.management.base import BaseCommand, CommandError
from accounts.supabase_sync import supabase_sync_service
from accounts.supabase_service import supabase_auth_service


class Command(BaseCommand):
    help = 'Синхронизация пользователей Django с Supabase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['sync-all', 'test-connection', 'sync-user'],
            default='test-connection',
            help='Действие для выполнения'
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='ID пользователя для синхронизации (для действия sync-user)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'test-connection':
            self.test_connection()
        elif action == 'sync-all':
            self.sync_all_users()
        elif action == 'sync-user':
            user_id = options.get('user_id')
            if not user_id:
                raise CommandError('Для действия sync-user необходимо указать --user-id')
            self.sync_user(user_id)

    def test_connection(self):
        """Тест подключения к Supabase"""
        self.stdout.write('Проверка подключения к Supabase...')
        
        try:
            # Проверяем настройки
            if not supabase_auth_service.url or not supabase_auth_service.key:
                self.stdout.write(
                    self.style.ERROR('❌ SUPABASE_URL или SUPABASE_KEY не установлены')
                )
                self.stdout.write('Создайте файл .env в папке backend/ с необходимыми переменными')
                return
            
            self.stdout.write(
                self.style.SUCCESS('✅ Настройки Supabase корректны')
            )
            self.stdout.write(f'URL: {supabase_auth_service.url}')
            self.stdout.write(f'Key: {"*" * 20}...{supabase_auth_service.key[-4:]}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка подключения: {e}')
            )

    def sync_all_users(self):
        """Синхронизация всех пользователей"""
        self.stdout.write('Синхронизация всех пользователей с Supabase...')
        
        result = supabase_sync_service.sync_all_users()
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Синхронизация завершена: {result["synced_count"]}/{result["total_count"]} пользователей'
                )
            )
            
            if result['errors']:
                self.stdout.write('Ошибки:')
                for error in result['errors']:
                    self.stdout.write(self.style.WARNING(f'  - {error}'))
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка синхронизации: {result.get("error", "Неизвестная ошибка")}')
            )

    def sync_user(self, user_id):
        """Синхронизация конкретного пользователя"""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f'Синхронизация пользователя: {user.email}')
            
            result = supabase_sync_service.sync_user_to_supabase(user)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Пользователь {user.email} синхронизирован')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка синхронизации: {result.get("error", "Неизвестная ошибка")}')
                )
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Пользователь с ID {user_id} не найден')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {e}')
            )
