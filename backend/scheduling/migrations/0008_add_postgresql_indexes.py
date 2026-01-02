# Generated migration for PostgreSQL optimization indexes
# Adds indexes on frequently queried fields in scheduling app for improved query performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0007_add_optimization_indexes"),
    ]

    operations = [
        # Lesson model indexes
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(fields=["teacher"], name="scheduling_lesson_teacher_idx"),
        ),
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(fields=["student"], name="scheduling_lesson_student_idx"),
        ),
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(fields=["date", "status"], name="scheduling_lesson_date_status_idx"),
        ),
    ]
