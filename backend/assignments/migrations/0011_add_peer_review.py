# Generated migration for peer review functionality

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assignments', '0010_add_assignment_scheduling'),
    ]

    operations = [
        migrations.CreateModel(
            name='PeerReviewAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignment_type', models.CharField(choices=[('random', 'Random Assignment'), ('manual', 'Manual Assignment'), ('automatic', 'Automatic Assignment')], default='random', max_length=20, verbose_name='Assignment Type')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('skipped', 'Skipped')], default='pending', max_length=20, verbose_name='Status')),
                ('deadline', models.DateTimeField(help_text='When the review must be completed', verbose_name='Review Deadline')),
                ('is_anonymous', models.BooleanField(default=False, help_text='Hide reviewer identity from the student being reviewed', verbose_name='Anonymous Review')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peer_reviews_assigned', to=settings.AUTH_USER_MODEL, verbose_name='Reviewer')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peer_review_assignments', to='assignments.assignmentsubmission', verbose_name='Submission to review')),
            ],
            options={
                'verbose_name': 'Peer Review Assignment',
                'verbose_name_plural': 'Peer Review Assignments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PeerReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(help_text='Score given by the peer reviewer', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Score (0-100)')),
                ('feedback_text', models.TextField(help_text='Detailed feedback from the peer reviewer', verbose_name='Feedback')),
                ('rubric_scores', models.JSONField(blank=True, default=dict, help_text='Scores for each rubric criterion in JSON format', verbose_name='Rubric Scores')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('peer_assignment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review', to='assignments.peerreviewassignment', verbose_name='Peer Review Assignment')),
            ],
            options={
                'verbose_name': 'Peer Review',
                'verbose_name_plural': 'Peer Reviews',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='peerreviewassignment',
            index=models.Index(fields=['submission', 'status'], name='peer_review_submission_status_idx'),
        ),
        migrations.AddIndex(
            model_name='peerreviewassignment',
            index=models.Index(fields=['reviewer', 'status'], name='peer_review_reviewer_status_idx'),
        ),
        migrations.AddIndex(
            model_name='peerreviewassignment',
            index=models.Index(fields=['deadline'], name='peer_review_deadline_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='peerreviewassignment',
            unique_together={('submission', 'reviewer')},
        ),
    ]
