# Generated migration for broadcast enhancements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0009_add_archive_and_scheduling_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='broadcast',
            name='error_log',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Список ошибок по получателям: [{"recipient_id": 123, "error": "Network error", "timestamp": "2024-01-01T00:00:00Z"}]',
                verbose_name='Лог ошибок при отправке'
            ),
        ),
        migrations.AlterField(
            model_name='broadcast',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Черновик'),
                    ('scheduled', 'Запланирована'),
                    ('sending', 'Отправляется'),
                    ('sent', 'Отправлена'),
                    ('completed', 'Завершена'),
                    ('failed', 'Ошибка'),
                    ('cancelled', 'Отменена')
                ],
                default='draft',
                max_length=20,
                verbose_name='Статус'
            ),
        ),
    ]
