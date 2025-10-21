from django.core.management.base import BaseCommand
from payments.telegram_service import TelegramNotificationService

class Command(BaseCommand):
    help = 'Тестирует подключение к Telegram Bot API'

    def handle(self, *args, **options):
        self.stdout.write('Тестирование подключения к Telegram...')
        
        telegram_service = TelegramNotificationService()
        success, message = telegram_service.test_connection()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('✅ Уведомление в Telegram отправлено успешно!')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {message}')
            )
            self.stdout.write(
                self.style.WARNING('Проверьте настройки TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env файле')
            )
