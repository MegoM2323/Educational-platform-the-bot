# Generated migration for AssignmentAttempt model
# T_ASN_003: Assignment Attempt Tracking

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assignments', '0015_rubric_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Attempt Number')),
                ('score', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Score')),
                ('max_score', models.PositiveIntegerField(blank=True, null=True, verbose_name='Maximum Score')),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('in_review', 'In Review'), ('graded', 'Graded'), ('returned', 'Returned for Revision')], default='submitted', max_length=20, verbose_name='Status')),
                ('submitted_at', models.DateTimeField(auto_now_add=True, verbose_name='Submitted At')),
                ('graded_at', models.DateTimeField(blank=True, null=True, verbose_name='Graded At')),
                ('feedback', models.TextField(blank=True, verbose_name='Feedback')),
                ('content', models.TextField(verbose_name='Submission Content')),
                ('file', models.FileField(blank=True, null=True, upload_to='assignments/attempts/', verbose_name='File Attachment')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_attempts', to='assignments.assignment', verbose_name='Assignment')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_attempts', to=settings.AUTH_USER_MODEL, verbose_name='Student')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='assignments.assignmentsubmission', verbose_name='Assignment Submission')),
            ],
            options={
                'verbose_name': 'Assignment Attempt',
                'verbose_name_plural': 'Assignment Attempts',
                'ordering': ['attempt_number'],
            },
        ),
        migrations.AddIndex(
            model_name='assignmentattempt',
            index=models.Index(fields=['submission', 'attempt_number'], name='attempt_submission_number_idx'),
        ),
        migrations.AddIndex(
            model_name='assignmentattempt',
            index=models.Index(fields=['student', 'assignment', 'attempt_number'], name='attempt_student_assignment_idx'),
        ),
        migrations.AddIndex(
            model_name='assignmentattempt',
            index=models.Index(fields=['status', '-submitted_at'], name='attempt_status_date_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='assignmentattempt',
            unique_together={('submission', 'attempt_number')},
        ),
    ]
