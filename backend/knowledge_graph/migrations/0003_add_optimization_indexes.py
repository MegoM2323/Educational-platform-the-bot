# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in knowledge_graph app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge_graph', '0002_elementfile'),
    ]

    operations = [
        # Index on created_by for elements by author
        # Used for: Element.objects.filter(created_by=user)
        # Note: Already indexed in model Meta.indexes, but adding for migrations
        migrations.AddIndex(
            model_name='element',
            index=models.Index(
                fields=['created_by_id'],
                name='element_created_by_idx',
            ),
        ),

        # Index on is_public for public element discovery
        # Used for: Element.objects.filter(is_public=True)
        migrations.AddIndex(
            model_name='element',
            index=models.Index(
                fields=['is_public'],
                name='element_is_public_idx',
            ),
        ),

        # Index on element_type for filtering by type
        # Used for: Element.objects.filter(element_type='video')
        # Note: Already indexed in model Meta.indexes
        migrations.AddIndex(
            model_name='element',
            index=models.Index(
                fields=['element_type'],
                name='element_type_idx',
            ),
        ),

        # Index on difficulty for difficulty-based queries
        # Used for: Element.objects.filter(difficulty__gte=5)
        # Note: Already indexed in model Meta.indexes
        migrations.AddIndex(
            model_name='element',
            index=models.Index(
                fields=['difficulty'],
                name='element_difficulty_idx',
            ),
        ),

        # Index on uploaded_by for file tracking
        # Used for: ElementFile.objects.filter(uploaded_by=user)
        migrations.AddIndex(
            model_name='elementfile',
            index=models.Index(
                fields=['uploaded_by_id'],
                name='elementfile_uploaded_by_idx',
            ),
        ),

        # Composite index for element files listing
        # Used for: ElementFile.objects.filter(element=e).order_by('-uploaded_at')
        migrations.AddIndex(
            model_name='elementfile',
            index=models.Index(
                fields=['element_id', '-uploaded_at'],
                name='elementfile_element_date_idx',
            ),
        ),

        # Index on graph for lessons
        # Used for: GraphLesson.objects.filter(graph=kg)
        migrations.AddIndex(
            model_name='graphlesson',
            index=models.Index(
                fields=['graph_id'],
                name='graphlesson_graph_idx',
            ),
        ),

        # Index on is_completed for progress tracking
        # Used for: ElementProgress.objects.filter(is_completed=True)
        migrations.AddIndex(
            model_name='elementprogress',
            index=models.Index(
                fields=['is_completed'],
                name='elementprogress_completed_idx',
            ),
        ),

        # Composite index for student progress
        # Used for: ElementProgress.objects.filter(student=s, element=e)
        migrations.AddIndex(
            model_name='elementprogress',
            index=models.Index(
                fields=['student_id', 'element_id'],
                name='elementprogress_student_element_idx',
            ),
        ),

        # Index on created_at for progress tracking by date
        # Used for: ElementProgress.objects.filter(created_at__gte=date)
        migrations.AddIndex(
            model_name='elementprogress',
            index=models.Index(
                fields=['-created_at'],
                name='elementprogress_created_at_idx',
            ),
        ),

        # Index on lesson for dependency tracking
        # Used for: Dependency.objects.filter(lesson=l)
        migrations.AddIndex(
            model_name='dependency',
            index=models.Index(
                fields=['lesson_id'],
                name='dependency_lesson_idx',
            ),
        ),

        # Index on required_lesson for reverse dependencies
        # Used for: Dependency.objects.filter(required_lesson=l)
        migrations.AddIndex(
            model_name='dependency',
            index=models.Index(
                fields=['required_lesson_id'],
                name='dependency_required_idx',
            ),
        ),

        # Composite index for student lesson unlock
        # Used for: StudentLessonUnlock.objects.filter(student=s, lesson=l)
        migrations.AddIndex(
            model_name='studentlessonunlock',
            index=models.Index(
                fields=['student_id', 'lesson_id'],
                name='unlock_student_lesson_idx',
            ),
        ),

        # Index on is_unlocked for unlock status queries
        # Used for: StudentLessonUnlock.objects.filter(is_unlocked=True)
        migrations.AddIndex(
            model_name='studentlessonunlock',
            index=models.Index(
                fields=['is_unlocked'],
                name='unlock_is_unlocked_idx',
            ),
        ),
    ]
