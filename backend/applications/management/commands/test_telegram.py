from django.core.management.base import BaseCommand
from django.utils import timezone
from applications.telegram_service import telegram_service
from applications.models import Application


class Command(BaseCommand):
    help = 'Тестирует интеграцию с Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-message',
            action='store_true',
            help='Отправить тестовое сообщение',
        )
        parser.add_argument(
            '--test-application',
            action='store_true',
            help='Отправить тестовое уведомление о заявке',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Запуск тестирования Telegram интеграции\n'))
        
        # Проверяем настройки
        from django.conf import settings
        
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write(
                self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не настроен в .env файле')
            )
            return
        
        if not settings.TELEGRAM_CHAT_ID:
            self.stdout.write(
                self.style.ERROR('❌ TELEGRAM_CHAT_ID не настроен в .env файле')
            )
            return
        
        self.stdout.write(f'🤖 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...')
        self.stdout.write(f'💬 Chat ID: {settings.TELEGRAM_CHAT_ID}\n')
        
        # Тест соединения
        self.stdout.write('🔍 Тестирование соединения с Telegram...')
        if telegram_service.test_connection():
            self.stdout.write(self.style.SUCCESS('✅ Соединение с Telegram успешно!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Не удалось подключиться к Telegram'))
            return
        
        # Тест отправки сообщения
        if options['test_message']:
            self.stdout.write('\n📤 Тестирование отправки сообщения...')
            
            test_message = f"""
🧪 <b>Тестовое сообщение</b>

Это тестовое сообщение для проверки работы Telegram интеграции.

⏰ <b>Время:</b> {timezone.now().strftime('%d.%m.%Y в %H:%M')}
🆔 <b>Тест ID:</b> #test-001
            """
            
            result = telegram_service.send_message(test_message)
            
            if result:
                self.stdout.write(self.style.SUCCESS('✅ Тестовое сообщение отправлено успешно!'))
                self.stdout.write(f'Message ID: {result["result"]["message_id"]}')
            else:
                self.stdout.write(self.style.ERROR('❌ Не удалось отправить тестовое сообщение'))
        
        # Тест уведомления о заявке
        if options['test_application']:
            self.stdout.write('\n📋 Тестирование уведомления о заявке...')
            
            # Создаем тестовую заявку
            test_application = Application(
                student_name="Тестовый Ученик",
                parent_name="Тестовый Родитель",
                phone="+7 (999) 123-45-67",
                email="test@example.com",
                grade=9,
                goal="Тестовая цель обучения",
                message="Это тестовое сообщение для проверки интеграции",
                created_at=timezone.now()
            )
            
            result = telegram_service.send_application_notification(test_application)
            
            if result:
                self.stdout.write(self.style.SUCCESS('✅ Уведомление о заявке отправлено успешно!'))
                self.stdout.write(f'Message ID: {result}')
            else:
                self.stdout.write(self.style.ERROR('❌ Не удалось отправить уведомление о заявке'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Тестирование завершено!'))
