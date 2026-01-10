"""
Migration 0016: Alter Lesson.subject on_delete to PROTECT (C1)

This migration changes the on_delete behavior of Lesson.subject from CASCADE to PROTECT
to prevent accidental deletion of Subject when lessons exist.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0037_subjectenrollment_status'),
        ('scheduling', '0015_optimize_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='subject',
            field=models.ForeignKey(on_delete=models.PROTECT, related_name='lessons', to='materials.subject', verbose_name='Subject'),
        ),
    ]
