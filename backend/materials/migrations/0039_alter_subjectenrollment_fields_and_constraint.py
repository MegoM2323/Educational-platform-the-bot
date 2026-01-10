"""
Migration 0039: Alter SubjectEnrollment fields on_delete and update constraint (C2, C5)

This migration:
1. Changes student, subject, teacher ForeignKey on_delete from CASCADE to PROTECT
2. Removes old constraint unique_student_subject_teacher
3. Adds new conditional constraint unique_active_student_subject_teacher
   that only applies when is_active=True
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0037_subjectenrollment_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subjectenrollment",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subject_enrollments",
                to="accounts.user",
                verbose_name="Студент",
            ),
        ),
        migrations.AlterField(
            model_name="subjectenrollment",
            name="subject",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="enrollments",
                to="materials.subject",
                verbose_name="Предмет",
            ),
        ),
        migrations.AlterField(
            model_name="subjectenrollment",
            name="teacher",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="taught_subjects",
                to="accounts.user",
                verbose_name="Преподаватель",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="subjectenrollment",
            name="unique_student_subject_teacher",
        ),
        migrations.AddConstraint(
            model_name="subjectenrollment",
            constraint=models.UniqueConstraint(
                fields=["student", "subject", "teacher"],
                condition=models.Q(is_active=True),
                name="unique_active_student_subject_teacher",
            ),
        ),
    ]
