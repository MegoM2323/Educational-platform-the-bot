# Generated migration for PushDeliveryLog model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0012b_add_device_token_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushDeliveryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'В ожидании'),
                        ('sent', 'Отправлено'),
                        ('delivered', 'Доставлено'),
                        ('failed', 'Ошибка'),
                        ('partial', 'Частичная доставка'),
                        ('skipped', 'Пропущено')
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                    verbose_name='Статус доставки'
                )),
                ('attempt_number', models.PositiveIntegerField(default=1, verbose_name='Номер попытки')),
                ('max_attempts', models.PositiveIntegerField(default=3, verbose_name='Максимум попыток')),
                ('success', models.BooleanField(db_index=True, default=False, verbose_name='Успешно отправлено')),
                ('error_message', models.TextField(blank=True, verbose_name='Сообщение об ошибке')),
                ('error_code', models.CharField(
                    blank=True,
                    help_text='Firebase error code (INVALID_ARGUMENT, NOT_FOUND, etc.)',
                    max_length=50,
                    verbose_name='Код ошибки'
                )),
                ('fcm_message_id', models.CharField(
                    blank=True,
                    help_text='ID сообщения от Firebase',
                    max_length=255,
                    verbose_name='FCM Message ID'
                )),
                ('device_type', models.CharField(
                    blank=True,
                    choices=[
                        ('ios', 'iOS'),
                        ('android', 'Android'),
                        ('web', 'Web')
                    ],
                    max_length=20,
                    verbose_name='Тип устройства'
                )),
                ('payload_size', models.PositiveIntegerField(default=0, verbose_name='Размер payload (bytes)')),
                ('sent_at', models.DateTimeField(auto_now_add=True, verbose_name='Отправлено')),
                ('delivered_at', models.DateTimeField(blank=True, null=True, verbose_name='Доставлено')),
                ('retry_at', models.DateTimeField(blank=True, null=True, verbose_name='Следующая попытка')),
                ('notification', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_delivery_logs',
                    to='notifications.notification',
                    verbose_name='Уведомление'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_delivery_logs',
                    to='accounts.user',
                    verbose_name='Получатель'
                )),
                ('device_token', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='delivery_logs',
                    to='notifications.devicetoken',
                    verbose_name='Токен устройства'
                )),
            ],
            options={
                'verbose_name': 'Лог доставки push',
                'verbose_name_plural': 'Логи доставки push',
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pushdeliverylog',
            index=models.Index(fields=['notification', 'user'], name='notificati_notifi_idx'),
        ),
        migrations.AddIndex(
            model_name='pushdeliverylog',
            index=models.Index(fields=['user', 'status'], name='notificati_user_i_idx'),
        ),
        migrations.AddIndex(
            model_name='pushdeliverylog',
            index=models.Index(fields=['notification', 'status'], name='notificati_notifi_6a4c_idx'),
        ),
        migrations.AddIndex(
            model_name='pushdeliverylog',
            index=models.Index(fields=['success', 'sent_at'], name='notificati_success_idx'),
        ),
        migrations.AddIndex(
            model_name='pushdeliverylog',
            index=models.Index(fields=['-sent_at'], name='notificati_sent_at_idx'),
        ),
    ]
