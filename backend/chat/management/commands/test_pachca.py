from django.core.management.base import BaseCommand
from chat.services.pachca_service import PachcaService


class Command(BaseCommand):
    help = 'Test Pachca API connection'

    def handle(self, *args, **options):
        service = PachcaService()

        self.stdout.write(f'API Token: {"***" + service.api_token[-4:] if service.api_token else "NOT SET"}')
        self.stdout.write(f'Channel ID: {service.channel_id or "NOT SET"}')
        self.stdout.write(f'Base URL: {service.base_url}')

        if service.validate_token():
            self.stdout.write(self.style.SUCCESS('✅ Pachca token is valid!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Pachca token validation failed'))
