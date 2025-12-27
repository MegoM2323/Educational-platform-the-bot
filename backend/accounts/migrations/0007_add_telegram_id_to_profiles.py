# Generated migration for adding telegram_id field to profiles
# Telegram ID (numeric chat_id) required for sending Telegram bot messages

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_studentprofile_grade_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='parentprofile',
            name='telegram_id',
            field=models.CharField(
                max_length=50,
                blank=True,
                verbose_name='Telegram Chat ID',
                help_text='Числовой ID чата Telegram для отправки уведомлений (например: 123456789)'
            ),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='telegram_id',
            field=models.CharField(
                max_length=50,
                blank=True,
                verbose_name='Telegram Chat ID',
                help_text='Числовой ID чата Telegram для отправки уведомлений (например: 123456789)'
            ),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='telegram_id',
            field=models.CharField(
                max_length=50,
                blank=True,
                verbose_name='Telegram Chat ID',
                help_text='Числовой ID чата Telegram для отправки уведомлений (например: 123456789)'
            ),
        ),
        migrations.AddField(
            model_name='tutorprofile',
            name='telegram_id',
            field=models.CharField(
                max_length=50,
                blank=True,
                verbose_name='Telegram Chat ID',
                help_text='Числовой ID чата Telegram для отправки уведомлений (например: 123456789)'
            ),
        ),
    ]
