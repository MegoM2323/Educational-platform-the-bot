# Generated migration for DeviceToken and UserPhoneNumber models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0012_add_notification_preferences'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.TextField(help_text='Firebase Cloud Messaging device token', unique=True, verbose_name='Device Token')),
                ('device_type', models.CharField(choices=[('ios', 'iOS Device'), ('android', 'Android Device'), ('web', 'Web Browser')], max_length=10, verbose_name='Device Type')),
                ('device_name', models.CharField(blank=True, help_text='User-friendly name (e.g., "iPhone 12", "Chrome on MacBook")', max_length=255, verbose_name='Device Name')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this token is currently active for receiving notifications', verbose_name='Active')),
                ('last_used_at', models.DateTimeField(blank=True, help_text='Last time a notification was successfully sent to this device', null=True, verbose_name='Last Used')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_tokens', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Device Token',
                'verbose_name_plural': 'Device Tokens',
                'ordering': ['-last_used_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserPhoneNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(help_text='Phone number in international format (e.g., +79876543210)', max_length=20, verbose_name='Phone Number')),
                ('status', models.CharField(choices=[('pending', 'Pending Verification'), ('verified', 'Verified'), ('invalid', 'Invalid')], default='pending', max_length=20, verbose_name='Verification Status')),
                ('verification_code', models.CharField(blank=True, max_length=6, verbose_name='Verification Code')),
                ('verification_attempts', models.PositiveIntegerField(default=0, verbose_name='Verification Attempts')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='Verified At')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='phone_number_record', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'User Phone Number',
                'verbose_name_plural': 'User Phone Numbers',
            },
        ),
        migrations.AddIndex(
            model_name='devicetoken',
            index=models.Index(fields=['user', 'is_active'], name='notificati_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='devicetoken',
            index=models.Index(fields=['token'], name='notificati_token_idx'),
        ),
    ]
