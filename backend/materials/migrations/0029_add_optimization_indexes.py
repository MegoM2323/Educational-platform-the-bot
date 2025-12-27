# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in materials app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0027_add_material_download_log_model'),
    ]

    operations = [
        # Index on subject for material listing
        # Used for: Material.objects.filter(subject=s)
        migrations.AddIndex(
            model_name='material',
            index=models.Index(
                fields=['subject_id'],
                name='material_subject_idx',
            ),
        ),

        # Index on author for author's materials
        # Used for: Material.objects.filter(author=user)
        migrations.AddIndex(
            model_name='material',
            index=models.Index(
                fields=['author_id'],
                name='material_author_idx',
            ),
        ),

        # Index on status for published materials
        # Used for: Material.objects.filter(status='published')
        migrations.AddIndex(
            model_name='material',
            index=models.Index(
                fields=['status'],
                name='material_status_idx',
            ),
        ),

        # Index on created_at for material ordering
        # Used for: Material.objects.order_by('-created_at')
        migrations.AddIndex(
            model_name='material',
            index=models.Index(
                fields=['-created_at'],
                name='material_created_at_idx',
            ),
        ),

        # Composite index for subject materials with status
        # Used for: Material.objects.filter(subject=s, status='published')
        migrations.AddIndex(
            model_name='material',
            index=models.Index(
                fields=['subject_id', 'status'],
                name='material_subject_status_idx',
            ),
        ),

        # Index on student for progress tracking
        # Used for: MaterialProgress.objects.filter(student=s)
        migrations.AddIndex(
            model_name='materialprogress',
            index=models.Index(
                fields=['student_id'],
                name='material_progress_student_idx',
            ),
        ),

        # Composite index for student material progress
        # Used for: MaterialProgress.objects.filter(student=s, material=m)
        migrations.AddIndex(
            model_name='materialprogress',
            index=models.Index(
                fields=['student_id', 'material_id'],
                name='material_progress_student_material_idx',
            ),
        ),

        # Index on material for submissions
        # Used for: MaterialSubmission.objects.filter(material=m)
        migrations.AddIndex(
            model_name='materialsubmission',
            index=models.Index(
                fields=['material_id'],
                name='material_submission_material_idx',
            ),
        ),

        # Composite index for submission tracking
        # Used for: MaterialSubmission.objects.filter(student=s, material=m)
        migrations.AddIndex(
            model_name='materialsubmission',
            index=models.Index(
                fields=['student_id', 'material_id'],
                name='material_submission_student_material_idx',
            ),
        ),

        # Index on submitted_at for submission ordering
        # Used for: MaterialSubmission.objects.order_by('-submitted_at')
        migrations.AddIndex(
            model_name='materialsubmission',
            index=models.Index(
                fields=['-submitted_at'],
                name='material_submission_submitted_at_idx',
            ),
        ),

        # Index on enrollment for subject enrollment tracking
        # Used for: SubjectEnrollment.objects.filter(student=s)
        migrations.AddIndex(
            model_name='subjectenrollment',
            index=models.Index(
                fields=['student_id'],
                name='subject_enrollment_student_idx',
            ),
        ),

        # Composite index for subject enrollment queries
        # Used for: SubjectEnrollment.objects.filter(subject=s, student=st)
        migrations.AddIndex(
            model_name='subjectenrollment',
            index=models.Index(
                fields=['subject_id', 'student_id'],
                name='subject_enrollment_subject_student_idx',
            ),
        ),

        # Index on teacher for subject enrollment
        # Used for: SubjectEnrollment.objects.filter(teacher=t)
        migrations.AddIndex(
            model_name='subjectenrollment',
            index=models.Index(
                fields=['teacher_id'],
                name='subject_enrollment_teacher_idx',
            ),
        ),

        # Index on timestamp for analytics
        # Used for: MaterialDownloadLog.objects.filter(timestamp__gte=date)
        migrations.AddIndex(
            model_name='materialdownloadlog',
            index=models.Index(
                fields=['-timestamp'],
                name='download_log_timestamp_idx',
            ),
        ),

        # Index on user for download tracking
        # Used for: MaterialDownloadLog.objects.filter(user=u)
        migrations.AddIndex(
            model_name='materialdownloadlog',
            index=models.Index(
                fields=['user_id'],
                name='download_log_user_idx',
            ),
        ),
    ]
