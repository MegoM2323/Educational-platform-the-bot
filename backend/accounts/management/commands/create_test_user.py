from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import User

class Command(BaseCommand):
    help = 'Создает тестового пользователя для входа'

    def handle(self, *args, **options):
        # Создаем тестового пользователя
        email = 'test@example.com'
        password = 'testpassword123'
        
        # Проверяем, существует ли пользователь
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Пользователь с email {email} уже существует')
            )
            return
        
        # Создаем пользователя
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name='Тест',
            last_name='Пользователь',
            role=User.Role.STUDENT,
            is_active=True,
            is_verified=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Тестовый пользователь создан: {email} / {password}')
        )
