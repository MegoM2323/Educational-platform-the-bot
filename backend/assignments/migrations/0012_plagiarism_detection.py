# Generated migration for plagiarism detection
# T_ASSIGN_014: Plagiarism detection integration

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0011_add_peer_review'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlagiarismReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('similarity_score', models.DecimalField(
                    decimal_places=2, default=0, max_digits=5,
                    validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                    verbose_name='Similarity Score (%)'
                )),
                ('detection_status', models.CharField(
                    choices=[
                        ('pending', 'Pending - Not yet submitted'),
                        ('processing', 'Processing - Awaiting results'),
                        ('completed', 'Completed - Results available'),
                        ('failed', 'Failed - Check could not complete')
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Detection Status'
                )),
                ('sources', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='List of sources with matched content',
                    verbose_name='Detected Sources'
                )),
                ('service', models.CharField(
                    choices=[
                        ('turnitin', 'Turnitin'),
                        ('copyscape', 'Copyscape'),
                        ('custom', 'Custom/Internal')
                    ],
                    default='custom',
                    max_length=20,
                    verbose_name='Detection Service'
                )),
                ('service_report_id', models.CharField(
                    blank=True,
                    help_text='ID from external plagiarism service for reference',
                    max_length=255,
                    null=True,
                    verbose_name='External Service Report ID'
                )),
                ('error_message', models.TextField(
                    blank=True,
                    help_text='Error details if detection failed',
                    verbose_name='Error Message'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Queued at')),
                ('checked_at', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='Checked at'
                )),
                ('submission', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='plagiarism_report',
                    to='assignments.assignmentsubmission',
                    verbose_name='Assignment Submission'
                )),
            ],
            options={
                'verbose_name': 'Plagiarism Report',
                'verbose_name_plural': 'Plagiarism Reports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='plagiarismreport',
            index=models.Index(
                fields=['submission', 'detection_status'],
                name='plag_submission_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='plagiarismreport',
            index=models.Index(
                fields=['detection_status', '-created_at'],
                name='plag_status_date_idx'
            ),
        ),
    ]
