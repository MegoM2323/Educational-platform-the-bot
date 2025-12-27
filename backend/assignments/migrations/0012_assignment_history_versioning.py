"""
T_ASSIGN_010: Migration for assignment history and versioning models.

Creates:
- AssignmentHistory: Track all assignment changes
- SubmissionVersion: Track submission versions
- SubmissionVersionDiff: Store diffs between versions
- SubmissionVersionRestore: Audit trail for version restores
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0011_add_peer_review'),
    ]

    operations = [
        # AssignmentHistory model
        migrations.CreateModel(
            name='AssignmentHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_time', models.DateTimeField(auto_now_add=True, verbose_name='Change Time')),
                ('changes_dict', models.JSONField(blank=True, default=dict, help_text='JSON object with field diffs: {field_name: {old: value, new: value}}', verbose_name='Changes Dictionary')),
                ('change_summary', models.TextField(blank=True, help_text='Human-readable description of what changed', verbose_name='Change Summary')),
                ('fields_changed', models.JSONField(blank=True, default=list, help_text='List of field names that were modified', verbose_name='Fields Changed')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='assignments.assignment', verbose_name='Assignment')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignment_changes', to='accounts.user', verbose_name='Changed By')),
            ],
            options={
                'verbose_name': 'Assignment History',
                'verbose_name_plural': 'Assignment Histories',
                'ordering': ['-change_time'],
            },
        ),

        # SubmissionVersion model
        migrations.CreateModel(
            name='SubmissionVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.PositiveIntegerField(help_text='Sequential version number (1, 2, 3, ...)', verbose_name='Version Number')),
                ('file', models.FileField(blank=True, null=True, upload_to='assignments/submissions/versions/', verbose_name='File')),
                ('content', models.TextField(blank=True, verbose_name='Content')),
                ('submitted_at', models.DateTimeField(auto_now_add=True, verbose_name='Submitted At')),
                ('is_final', models.BooleanField(default=False, help_text='This is the submission used for grading', verbose_name='Is Final')),
                ('previous_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_version', to='assignments.submissionversion', verbose_name='Previous Version')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='assignments.assignmentsubmission', verbose_name='Submission')),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submission_versions', to='accounts.user', verbose_name='Submitted By')),
            ],
            options={
                'verbose_name': 'Submission Version',
                'verbose_name_plural': 'Submission Versions',
                'ordering': ['version_number'],
                'unique_together': {('submission', 'version_number')},
            },
        ),

        # SubmissionVersionDiff model
        migrations.CreateModel(
            name='SubmissionVersionDiff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('diff_content', models.JSONField(blank=True, default=dict, verbose_name='Diff Content')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('version_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diffs_as_a', to='assignments.submissionversion', verbose_name='Version A')),
                ('version_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diffs_as_b', to='assignments.submissionversion', verbose_name='Version B')),
            ],
            options={
                'verbose_name': 'Submission Version Diff',
                'verbose_name_plural': 'Submission Version Diffs',
                'unique_together': {('version_a', 'version_b')},
            },
        ),

        # SubmissionVersionRestore model
        migrations.CreateModel(
            name='SubmissionVersionRestore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('restored_at', models.DateTimeField(auto_now_add=True, verbose_name='Restored At')),
                ('reason', models.TextField(blank=True, help_text='Reason for restoring a previous version', verbose_name='Reason')),
                ('restored_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restored_submissions', to='accounts.user', verbose_name='Restored By')),
                ('restored_from_version', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restored_as_source', to='assignments.submissionversion', verbose_name='Restored From Version')),
                ('restored_to_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restored_as_target', to='assignments.submissionversion', verbose_name='Restored To Version')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='version_restores', to='assignments.assignmentsubmission', verbose_name='Submission')),
            ],
            options={
                'verbose_name': 'Submission Version Restore',
                'verbose_name_plural': 'Submission Version Restores',
                'ordering': ['-restored_at'],
            },
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='assignmenthistory',
            index=models.Index(fields=['assignment', '-change_time'], name='assignments_assignmenthistory_assignment_change_time_idx'),
        ),
        migrations.AddIndex(
            model_name='assignmenthistory',
            index=models.Index(fields=['changed_by', '-change_time'], name='assignments_assignmenthistory_changed_by_change_time_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionversion',
            index=models.Index(fields=['submission', 'version_number'], name='assignments_submissionversion_submission_version_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionversion',
            index=models.Index(fields=['is_final'], name='assignments_submissionversion_is_final_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionversiondiff',
            index=models.Index(fields=['version_a', 'version_b'], name='assignments_submissionversiondiff_version_a_b_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionversionrestore',
            index=models.Index(fields=['submission', '-restored_at'], name='assignments_submissionversionrestore_submission_date_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionversionrestore',
            index=models.Index(fields=['restored_by', '-restored_at'], name='assignments_submissionversionrestore_restored_by_date_idx'),
        ),
    ]
