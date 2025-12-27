from django.core.management.base import BaseCommand
from django.conf import settings
from payments.telegram_service import TelegramNotificationService

class Command(BaseCommand):
    help = 'Тестирует подключение к Telegram Bot API'

    def handle(self, *args, **options):
        self.stdout.write('🤖 Тестирование подключения к Telegram...')
        self.stdout.write('')
        
        # Проверяем настройки
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        
        if not bot_token:
            self.stdout.write(self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не настроен'))
            return
        
        if not chat_id:
            self.stdout.write(self.style.ERROR('❌ TELEGRAM_CHAT_ID не настроен'))
            return
            
        self.stdout.write(f'📝 Bot Token: {bot_token[:10]}...{bot_token[-5:]}')
        self.stdout.write(f'💬 Chat ID: {chat_id}')
        self.stdout.write('')
        
        telegram_service = TelegramNotificationService()
        
        # Получаем информацию о боте
        self.stdout.write('🔍 Получение информации о боте...')
        bot_ok, bot_info = telegram_service.get_bot_info()
        
        if bot_ok:
            bot_data = bot_info['result']
            self.stdout.write(self.style.SUCCESS(f'✅ Бот найден: @{bot_data["username"]} ({bot_data["first_name"]})'))
            self.stdout.write(f'📋 Описание: {bot_data.get("description", "Не указано")}')
        else:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка получения информации о боте: {bot_info}'))
            return
        
        self.stdout.write('')
        
        # Тестируем отправку сообщения
        self.stdout.write('📤 Отправка тестового сообщения...')
        success, message = telegram_service.test_connection()
        
        if success:
            self.stdout.write(self.style.SUCCESS('✅ Тестовое сообщение отправлено успешно!'))
            self.stdout.write(self.style.SUCCESS(f'✅ {message}'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('🎉 Все готово! Бот может отправлять уведомления о платежах.'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка отправки: {message}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('🔧 Возможные решения:'))
            self.stdout.write('   1. Убедитесь, что написали боту /start')
            self.stdout.write('   2. Проверьте правильность TELEGRAM_CHAT_ID')
            self.stdout.write('   3. Убедитесь, что бот не заблокирован')
            self.stdout.write('   4. Проверьте интернет-соединение')
