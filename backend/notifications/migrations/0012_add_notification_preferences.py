# Generated migration for notification preferences fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0010_broadcast_enhancements'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationsettings',
            name='in_app_notifications',
            field=models.BooleanField(
                default=True,
                verbose_name='Уведомления в приложении'
            ),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='quiet_hours_enabled',
            field=models.BooleanField(
                default=False,
                verbose_name='Включены тихие часы'
            ),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='timezone',
            field=models.CharField(
                choices=[
                    ('UTC', 'UTC'),
                    ('US/Eastern', 'US/Eastern (EST)'),
                    ('US/Central', 'US/Central (CST)'),
                    ('US/Mountain', 'US/Mountain (MST)'),
                    ('US/Pacific', 'US/Pacific (PST)'),
                    ('Europe/London', 'Europe/London (GMT)'),
                    ('Europe/Paris', 'Europe/Paris (CET)'),
                    ('Europe/Moscow', 'Europe/Moscow (MSK)'),
                    ('Asia/Tokyo', 'Asia/Tokyo (JST)'),
                    ('Asia/Shanghai', 'Asia/Shanghai (CST)'),
                    ('Asia/Hong_Kong', 'Asia/Hong_Kong (HKT)'),
                    ('Asia/Bangkok', 'Asia/Bangkok (ICT)'),
                    ('Australia/Sydney', 'Australia/Sydney (AEDT)'),
                    ('Pacific/Auckland', 'Pacific/Auckland (NZDT)'),
                ],
                default='UTC',
                max_length=50,
                verbose_name='Часовой пояс'
            ),
        ),
    ]
