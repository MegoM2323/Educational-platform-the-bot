# Generated migration: Fix ChatRoom.enrollment to use CASCADE instead of SET_NULL
# This ensures data integrity when SubjectEnrollment is deleted

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0011_alter_chatroom_enrollment'),
        ('materials', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatroom',
            name='enrollment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='forum_chats',
                to='materials.subjectenrollment',
                verbose_name='Зачисление на предмет',
                help_text='Зачисление студента на предмет (для forum_tutor/forum_subject типов)',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='chatroom',
            unique_together=set(),
        ),
        migrations.RemoveConstraint(
            model_name='chatroom',
            name='unique_forum_per_enrollment',
        ),
        migrations.AddConstraint(
            model_name='chatroom',
            constraint=models.UniqueConstraint(
                fields=('type', 'enrollment'),
                name='unique_forum_per_enrollment',
            ),
        ),
    ]
