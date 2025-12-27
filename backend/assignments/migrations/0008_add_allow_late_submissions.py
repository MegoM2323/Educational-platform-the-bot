# Generated migration for T_ASSIGN_002

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0007_add_search_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="allow_late_submissions",
            field=models.BooleanField(
                default=True,
                help_text="Если включено, студенты могут сдать задание после срока (помечается как поздняя сдача). Если отключено, сдача после срока будет заблокирована.",
                verbose_name="Разрешить поздние сдачи",
            ),
        ),
    ]
