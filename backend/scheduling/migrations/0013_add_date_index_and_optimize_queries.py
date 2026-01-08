# Generated manually on 2026-01-09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0012_alter_lesson_student"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(fields=["date"], name="scheduling_lesson_date_idx"),
        ),
    ]
