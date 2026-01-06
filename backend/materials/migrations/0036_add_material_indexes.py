from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0035_alter_subjectenrollment_unique_together_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS enrollment_student_idx ON materials_subjectenrollment(student_id);',
            'DROP INDEX IF EXISTS enrollment_student_idx;',
        ),
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS progress_student_idx ON materials_materialprogress(student_id);',
            'DROP INDEX IF EXISTS progress_student_idx;',
        ),
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS teacher_subject_teacher_idx ON materials_teachersubject(teacher_id);',
            'DROP INDEX IF EXISTS teacher_subject_teacher_idx;',
        ),
    ]
