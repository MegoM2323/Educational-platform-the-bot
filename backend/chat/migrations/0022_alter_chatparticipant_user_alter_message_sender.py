"""
Migration 0022: Alter ChatParticipant.user and Message.sender on_delete (C3)

This migration:
1. Changes ChatParticipant.user on_delete from CASCADE to PROTECT
2. Changes Message.sender on_delete from CASCADE to SET_NULL with null=True, blank=True
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0021_remove_message_idx_message_sender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatparticipant',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='message',
            name='sender',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]
