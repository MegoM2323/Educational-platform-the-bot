# Generated migration for assignment scheduling (T_ASSIGN_006)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0009_late_submission_policy'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='publish_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text='Автоматически опубликует задание в указанное время',
                null=True,
                verbose_name='Опубликовать в'
            ),
        ),
        migrations.AddField(
            model_name='assignment',
            name='close_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text='Автоматически закроет задание в указанное время',
                null=True,
                verbose_name='Закрыть в'
            ),
        ),
    ]
