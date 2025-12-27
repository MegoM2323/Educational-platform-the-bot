# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in reports app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0007_create_materialized_views'),
    ]

    operations = [
        # Index on student for student reports
        # Used for: StudentReport.objects.filter(student=s)
        migrations.AddIndex(
            model_name='studentreport',
            index=models.Index(
                fields=['student_id'],
                name='student_report_student_idx',
            ),
        ),

        # Index on created_at for report ordering
        # Used for: StudentReport.objects.order_by('-created_at')
        migrations.AddIndex(
            model_name='studentreport',
            index=models.Index(
                fields=['-created_at'],
                name='student_report_created_at_idx',
            ),
        ),

        # Index on tutor for tutor reports
        # Used for: TutorWeeklyReport.objects.filter(tutor=t)
        migrations.AddIndex(
            model_name='tutorweeklyreport',
            index=models.Index(
                fields=['tutor_id'],
                name='tutor_report_tutor_idx',
            ),
        ),

        # Index on week_start for report periods
        # Used for: TutorWeeklyReport.objects.filter(week_start__gte=date)
        migrations.AddIndex(
            model_name='tutorweeklyreport',
            index=models.Index(
                fields=['week_start'],
                name='tutor_report_week_start_idx',
            ),
        ),

        # Index on teacher for teacher reports
        # Used for: TeacherWeeklyReport.objects.filter(teacher=t)
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['teacher_id'],
                name='teacher_report_teacher_idx',
            ),
        ),

        # Index on week_start for report periods
        # Used for: TeacherWeeklyReport.objects.filter(week_start__gte=date)
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['week_start'],
                name='teacher_report_week_start_idx',
            ),
        ),
    ]
