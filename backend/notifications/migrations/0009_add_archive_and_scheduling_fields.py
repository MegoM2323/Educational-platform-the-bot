# Generated migration for archive and scheduling fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0008_add_feedback_notification_settings"),
    ]

    operations = [
        # Archive fields
        migrations.AddField(
            model_name='notification',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='Архивировано', db_index=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата архивирования'),
        ),
        
        # Scheduling fields
        migrations.AddField(
            model_name='notification',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Запланировано на'),
        ),
        migrations.AddField(
            model_name='notification',
            name='scheduled_status',
            field=models.CharField(
                choices=[('pending', 'Ожидает отправки'), ('sent', 'Отправлено'), ('cancelled', 'Отменено')],
                default='pending',
                max_length=20,
                verbose_name='Статус расписания'
            ),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_archived', '-created_at'], name='notif_archive_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_archived'], name='notif_archive_simple_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['scheduled_at', 'scheduled_status'], name='notif_schedule_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'scheduled_status'], name='notif_user_schedule_idx'),
        ),
    ]
