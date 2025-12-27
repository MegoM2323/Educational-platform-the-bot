# Generated migration for NotificationClick model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0013_add_push_delivery_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationClick',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(
                    choices=[
                        ('link_click', 'Клик по ссылке'),
                        ('in_app_click', 'Клик в приложении'),
                        ('email_click', 'Клик в email'),
                        ('button_click', 'Клик по кнопке'),
                    ],
                    default='link_click',
                    max_length=50,
                    verbose_name='Тип действия'
                )),
                ('action_url', models.URLField(
                    blank=True,
                    null=True,
                    verbose_name='URL действия'
                )),
                ('action_data', models.JSONField(
                    blank=True,
                    default=dict,
                    verbose_name='Дополнительные данные действия'
                )),
                ('user_agent', models.TextField(
                    blank=True,
                    verbose_name='User Agent'
                )),
                ('ip_address', models.GenericIPAddressField(
                    blank=True,
                    null=True,
                    verbose_name='IP адрес'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='Дата клика'
                )),
                ('notification', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='clicks',
                    to='notifications.notification',
                    verbose_name='Уведомление'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notification_clicks',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Пользователь'
                )),
            ],
            options={
                'verbose_name': 'Клик по уведомлению',
                'verbose_name_plural': 'Клики по уведомлениям',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notificationclick',
            index=models.Index(
                fields=['notification', 'created_at'],
                name='notifications_notificationclick_notification_created_at_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationclick',
            index=models.Index(
                fields=['user', 'created_at'],
                name='notifications_notificationclick_user_created_at_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationclick',
            index=models.Index(
                fields=['notification', 'user'],
                name='notifications_notificationclick_notification_user_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationclick',
            index=models.Index(
                fields=['created_at'],
                name='notifications_notificationclick_created_at_idx',
            ),
        ),
    ]
