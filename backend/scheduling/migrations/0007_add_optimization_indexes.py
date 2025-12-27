# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in scheduling app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0006_remove_tutor_assignment_unique_constraint'),
    ]

    operations = [
        # Index on start_time for lesson queries
        # Used for: Lesson.objects.filter(start_time__gte=now)
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(
                fields=['start_time'],
                name='lesson_start_time_idx',
            ),
        ),

        # Index on created_by for user's lessons
        # Used for: Lesson.objects.filter(created_by=user)
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(
                fields=['created_by_id'],
                name='lesson_created_by_idx',
            ),
        ),

        # Index on tutor for tutor lessons
        # Used for: Lesson.objects.filter(tutor=t)
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(
                fields=['tutor_id'],
                name='lesson_tutor_idx',
            ),
        ),

        # Composite index for user lesson schedule
        # Used for: Lesson.objects.filter(created_by=u).order_by('start_time')
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(
                fields=['created_by_id', 'start_time'],
                name='lesson_created_by_start_time_idx',
            ),
        ),

        # Index on status for active lesson queries
        # Used for: Lesson.objects.filter(status='scheduled')
        migrations.AddIndex(
            model_name='lesson',
            index=models.Index(
                fields=['status'],
                name='lesson_status_idx',
            ),
        ),

        # Index on student for tutor assignments
        # Used for: TutorAssignment.objects.filter(student=s)
        migrations.AddIndex(
            model_name='tutorassignment',
            index=models.Index(
                fields=['student_id'],
                name='tutor_assignment_student_idx',
            ),
        ),

        # Index on tutor for assignments
        # Used for: TutorAssignment.objects.filter(tutor=t)
        migrations.AddIndex(
            model_name='tutorassignment',
            index=models.Index(
                fields=['tutor_id'],
                name='tutor_assignment_tutor_idx',
            ),
        ),

        # Composite index for tutor student relationship
        # Used for: TutorAssignment.objects.filter(student=s, tutor=t)
        migrations.AddIndex(
            model_name='tutorassignment',
            index=models.Index(
                fields=['student_id', 'tutor_id'],
                name='tutor_assignment_student_tutor_idx',
            ),
        ),

        # Index on assigned_to for tutor slot assignments
        # Used for: TutorAssignment.objects.filter(assigned_to=user)
        migrations.AddIndex(
            model_name='tutorassignment',
            index=models.Index(
                fields=['assigned_to_id'],
                name='tutor_assignment_assigned_to_idx',
            ),
        ),
    ]
