from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0015_alter_teacherweeklyreport_unique_together_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS report_student_idx ON reports_teacherweeklyreport(student_id);',
            'DROP INDEX IF EXISTS report_student_idx;',
        ),
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS tutor_report_student_idx ON reports_tutorweeklyreport(student_id);',
            'DROP INDEX IF EXISTS tutor_report_student_idx;',
        ),
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS tutor_report_tutor_idx ON reports_tutorweeklyreport(tutor_id);',
            'DROP INDEX IF EXISTS tutor_report_tutor_idx;',
        ),
    ]
