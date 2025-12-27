# Generated migration for NotificationUnsubscribe model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0010_broadcast_enhancements'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationUnsubscribe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_types', models.JSONField(blank=True, default=list, help_text='List of notification types unsubscribed from (e.g., [assignments, materials])', verbose_name='Notification types')),
                ('channel', models.CharField(choices=[('email', 'Email'), ('push', 'Push notifications'), ('sms', 'SMS'), ('all', 'All channels')], default='email', max_length=10, verbose_name='Channel')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP address')),
                ('user_agent', models.TextField(blank=True, verbose_name='User agent')),
                ('token_used', models.BooleanField(default=False, help_text='Whether unsubscribe was done via secure token link', verbose_name='Token-based unsubscribe')),
                ('reason', models.TextField(blank=True, help_text='User reason for unsubscribing (if provided)', verbose_name='Reason')),
                ('unsubscribed_at', models.DateTimeField(auto_now_add=True, verbose_name='Unsubscribed at')),
                ('resubscribed_at', models.DateTimeField(blank=True, help_text='When user re-enabled notifications (if applicable)', null=True, verbose_name='Resubscribed at')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_unsubscribes', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Notification unsubscribe',
                'verbose_name_plural': 'Notification unsubscribes',
                'ordering': ['-unsubscribed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notificationunsubscribe',
            index=models.Index(fields=['user', '-unsubscribed_at'], name='notifications_notif_user_id_unsubscr_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationunsubscribe',
            index=models.Index(fields=['channel', '-unsubscribed_at'], name='notifications_notif_channel_unsubsc_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationunsubscribe',
            index=models.Index(fields=['-unsubscribed_at'], name='notifications_notif_unsubscribed_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationunsubscribe',
            index=models.Index(fields=['user', 'resubscribed_at'], name='notifications_notif_user_id_resubsc_idx'),
        ),
    ]
