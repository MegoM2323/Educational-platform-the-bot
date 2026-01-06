from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0022_assignment_show_correct_answers'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS submission_student_idx ON assignments_assignmentsubmission(student_id);',
            'DROP INDEX IF EXISTS submission_student_idx;',
        ),
    ]
