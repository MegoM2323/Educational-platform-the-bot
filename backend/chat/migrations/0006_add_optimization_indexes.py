# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in chat app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_add_unique_constraint_forum_enrollment'),
    ]

    operations = [
        # Index on created_by for user's chat rooms
        # Used for: ChatRoom.objects.select_related('created_by').filter(created_by=user)
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(
                fields=['created_by_id'],
                name='chatroom_created_by_idx',
            ),
        ),

        # Index on is_active for active rooms queries
        # Used for: ChatRoom.objects.filter(is_active=True)
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(
                fields=['is_active'],
                name='chatroom_is_active_idx',
            ),
        ),

        # Index on enrollment_id for forum rooms
        # Used for: ChatRoom.objects.filter(enrollment=e)
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(
                fields=['enrollment_id'],
                name='chatroom_enrollment_idx',
            ),
        ),

        # Composite index for message listing by room and date
        # Used for: Message.objects.filter(room=r).order_by('-created_at')
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['room_id', '-created_at'],
                name='message_room_date_idx',
            ),
        ),

        # Index on sender for messages by user
        # Used for: Message.objects.filter(sender=user)
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['sender_id'],
                name='message_sender_idx',
            ),
        ),

        # Index on created_at for message ordering
        # Used for: Message.objects.filter(created_at__gte=date)
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['-created_at'],
                name='message_created_at_idx',
            ),
        ),

        # Index on thread for message threading
        # Used for: Message.objects.filter(thread=t)
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['thread_id'],
                name='message_thread_idx',
            ),
        ),

        # Index on message_type for filtering by content type
        # Used for: Message.objects.filter(message_type='file')
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['message_type'],
                name='message_type_idx',
            ),
        ),

        # Composite index for pending messages
        # Used for: PendingMessage.objects.filter(delivered=False).order_by('created_at')
        migrations.AddIndex(
            model_name='pendingmessage',
            index=models.Index(
                fields=['delivered', 'created_at'],
                name='pending_msg_delivery_idx',
            ),
        ),

        # Index on user_id for user's pending messages
        # Used for: PendingMessage.objects.filter(user=u)
        migrations.AddIndex(
            model_name='pendingmessage',
            index=models.Index(
                fields=['user_id'],
                name='pending_msg_user_idx',
            ),
        ),
    ]
