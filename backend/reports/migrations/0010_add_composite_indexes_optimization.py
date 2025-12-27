# Migration for T_RPT_001: Query optimization with composite indexes
# Adds composite indexes for common report query patterns

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_add_optimization_indexes'),
    ]

    operations = [
        # Composite index for StudentReport filtering and sorting
        # Used by: StudentReport.objects.filter(teacher=t).order_by('-created_at')
        migrations.AddIndex(
            model_name='studentreport',
            index=models.Index(
                fields=['teacher_id', '-created_at'],
                name='student_report_teacher_date_idx',
            ),
        ),

        # Composite index for StudentReport student and period
        # Used by: StudentReport.objects.filter(student=s, period_start__gte=date)
        migrations.AddIndex(
            model_name='studentreport',
            index=models.Index(
                fields=['student_id', 'period_start'],
                name='student_report_student_period_idx',
            ),
        ),

        # Composite index for TutorWeeklyReport by tutor and student
        # Used by: TutorWeeklyReport.objects.filter(tutor=t, student=s)
        migrations.AddIndex(
            model_name='tutorweeklyreport',
            index=models.Index(
                fields=['tutor_id', 'student_id'],
                name='tutor_report_tutor_student_idx',
            ),
        ),

        # Composite index for TutorWeeklyReport by tutor and week
        # Used by: TutorWeeklyReport.objects.filter(tutor=t).filter(week_start__gte=date)
        migrations.AddIndex(
            model_name='tutorweeklyreport',
            index=models.Index(
                fields=['tutor_id', 'week_start'],
                name='tutor_report_tutor_week_idx',
            ),
        ),

        # Composite index for TutorWeeklyReport by student and week
        # Used by: TutorWeeklyReport.objects.filter(student=s, week_start__gte=date)
        migrations.AddIndex(
            model_name='tutorweeklyreport',
            index=models.Index(
                fields=['student_id', 'week_start'],
                name='tutor_report_student_week_idx',
            ),
        ),

        # Composite index for TeacherWeeklyReport by teacher and student
        # Used by: TeacherWeeklyReport.objects.filter(teacher=t, student=s)
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['teacher_id', 'student_id'],
                name='teacher_report_teacher_student_idx',
            ),
        ),

        # Composite index for TeacherWeeklyReport by teacher and subject
        # Used by: TeacherWeeklyReport.objects.filter(teacher=t, subject_id=s)
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['teacher_id', 'subject_id'],
                name='teacher_report_teacher_subject_idx',
            ),
        ),

        # Composite index for TeacherWeeklyReport by tutor and student
        # Used by: TeacherWeeklyReport.objects.filter(tutor=t, student=s)
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['tutor_id', 'student_id'],
                name='teacher_report_tutor_student_idx',
            ),
        ),

        # Composite index for TeacherWeeklyReport by teacher and week
        # Used by: TeacherWeeklyReport.objects.filter(teacher=t).order_by('-week_start')
        migrations.AddIndex(
            model_name='teacherweeklyreport',
            index=models.Index(
                fields=['teacher_id', '-week_start'],
                name='teacher_report_teacher_week_idx',
            ),
        ),

        # Index on AnalyticsData for student and metric type
        # Used by: AnalyticsData.objects.filter(student=s, metric_type=m)
        migrations.AddIndex(
            model_name='analyticsdata',
            index=models.Index(
                fields=['student_id', 'metric_type'],
                name='analytics_data_student_metric_idx',
            ),
        ),

        # Index on AnalyticsData for student and date range
        # Used by: AnalyticsData.objects.filter(student=s, date__gte=date)
        migrations.AddIndex(
            model_name='analyticsdata',
            index=models.Index(
                fields=['student_id', 'date'],
                name='analytics_data_student_date_idx',
            ),
        ),

    ]
