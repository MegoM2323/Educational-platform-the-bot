"""
Recreate chat models with simplified architecture.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0011_rename_forum_chats"),
    ]

    operations = [
        # Delete old tables
        migrations.DeleteModel(
            name='ChatRoom',
        ),
        migrations.DeleteModel(
            name='ChatParticipant',
        ),
        migrations.DeleteModel(
            name='Message',
        ),
        # Create new ChatRoom
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
            ],
            options={
                'verbose_name': 'Чат-комната',
                'verbose_name_plural': 'Чат-комнаты',
                'ordering': ['-updated_at'],
            },
        ),
        # Create ChatParticipant
        migrations.CreateModel(
            name='ChatParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('last_read_at', models.DateTimeField(blank=True, null=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='chat.chatroom')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Участник чата',
                'verbose_name_plural': 'Участники чата',
            },
        ),
        # Create Message
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_edited', models.BooleanField(default=False)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatroom')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Сообщение',
                'verbose_name_plural': 'Сообщения',
                'ordering': ['created_at'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(fields=['-updated_at'], name='idx_chat_room_updated'),
        ),
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(fields=['is_active'], name='idx_chat_room_active'),
        ),
        migrations.AddIndex(
            model_name='chatparticipant',
            index=models.Index(fields=['user', 'room'], name='idx_chat_participant_user_room'),
        ),
        migrations.AddIndex(
            model_name='chatparticipant',
            index=models.Index(fields=['room'], name='idx_chat_participant_room'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', 'created_at'], name='idx_message_room_created'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', 'is_deleted'], name='idx_message_room_deleted'),
        ),
        # Add unique constraint
        migrations.AlterUniqueTogether(
            name='chatparticipant',
            unique_together={('room', 'user')},
        ),
    ]
