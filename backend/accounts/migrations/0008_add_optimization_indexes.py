# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields for better performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_telegram_id_to_profiles'),
    ]

    operations = [
        # Index on User.email for fast authentication lookups
        migrations.AddIndex(
            model_name='user',
            index=models.Index(
                fields=['email'],
                name='user_email_idx',
            ),
        ),

        # Index on StudentProfile.tutor_id for select_related optimization
        # Allows fast JOIN when retrieving students with tutors
        migrations.AddIndex(
            model_name='studentprofile',
            index=models.Index(
                fields=['tutor_id'],
                name='student_tutor_idx',
            ),
        ),

        # Index on StudentProfile.parent_id for parent-child relationships
        # Enables fast lookup of children for a parent
        migrations.AddIndex(
            model_name='studentprofile',
            index=models.Index(
                fields=['parent_id'],
                name='student_parent_idx',
            ),
        ),

        # Composite index on StudentProfile for common queries
        # student.objects.filter(tutor=x).order_by('-created_at')
        migrations.AddIndex(
            model_name='studentprofile',
            index=models.Index(
                fields=['user_id'],  # Links to User for joins
                name='student_user_idx',
            ),
        ),
    ]
