# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in assignments app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0013_webhook_models'),
    ]

    operations = [
        # Index on Assignment.due_date for date range queries
        # Used for: Assignment.objects.filter(due_date__lt=now, due_date__gte=past)
        migrations.AddIndex(
            model_name='assignment',
            index=models.Index(
                fields=['due_date'],
                name='assignment_due_date_idx',
            ),
        ),

        # Composite index for assignment submissions listing
        # Used for: AssignmentSubmission.objects.filter(assignment=a).order_by('-submitted_at')
        migrations.AddIndex(
            model_name='assignmentsubmission',
            index=models.Index(
                fields=['assignment_id', '-submitted_at'],
                name='submission_assignment_date_idx',
            ),
        ),

        # Index on student_id for student submissions
        # Used for: AssignmentSubmission.objects.filter(student=s)
        migrations.AddIndex(
            model_name='assignmentsubmission',
            index=models.Index(
                fields=['student_id'],
                name='submission_student_idx',
            ),
        ),

        # Index on status for filtering submissions by status
        # Used for: AssignmentSubmission.objects.filter(status='graded')
        migrations.AddIndex(
            model_name='assignmentsubmission',
            index=models.Index(
                fields=['status'],
                name='submission_status_idx',
            ),
        ),

        # Index on graded_at for date filtering
        # Used for: AssignmentSubmission.objects.filter(graded_at__gte=date)
        migrations.AddIndex(
            model_name='assignmentsubmission',
            index=models.Index(
                fields=['graded_at'],
                name='submission_graded_at_idx',
            ),
        ),

        # Composite index for assignment question lookup
        # Used for: AssignmentQuestion.objects.filter(assignment=a)
        migrations.AddIndex(
            model_name='assignmentquestion',
            index=models.Index(
                fields=['assignment_id', 'order'],
                name='question_assignment_order_idx',
            ),
        ),

        # Index on submission_id for answer lookups
        # Used for: AssignmentAnswer.objects.filter(submission=s)
        migrations.AddIndex(
            model_name='assignmentanswer',
            index=models.Index(
                fields=['submission_id'],
                name='answer_submission_idx',
            ),
        ),

        # Index on is_correct for analytics
        # Used for: AssignmentAnswer.objects.filter(is_correct=True)
        migrations.AddIndex(
            model_name='assignmentanswer',
            index=models.Index(
                fields=['is_correct'],
                name='answer_correct_idx',
            ),
        ),

        # Index on changed_by for audit trail
        # Used for: AssignmentHistory.objects.filter(changed_by=user)
        migrations.AddIndex(
            model_name='assignmenthistory',
            index=models.Index(
                fields=['changed_by_id', '-change_time'],
                name='history_changed_by_idx',
            ),
        ),

        # Index on status for peer review tracking
        # Used for: PeerReviewAssignment.objects.filter(status='pending')
        migrations.AddIndex(
            model_name='peerreviewassignment',
            index=models.Index(
                fields=['status'],
                name='peer_review_status_idx',
            ),
        ),
    ]
