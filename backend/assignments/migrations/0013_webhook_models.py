# Generated migration for webhook models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0012_assignment_history_versioning'),
    ]

    operations = [
        migrations.CreateModel(
            name='FailedWebhookLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_id', models.IntegerField(db_index=True, verbose_name='Submission ID')),
                ('payload', models.JSONField(help_text='Complete webhook payload that failed', verbose_name='Webhook Payload')),
                ('error_message', models.TextField(help_text='Exception message from processing', verbose_name='Error Message')),
                ('remote_ip', models.GenericIPAddressField(help_text='IP address that sent the webhook', verbose_name='Remote IP')),
                ('status', models.CharField(choices=[('pending', 'Pending Retry'), ('processing', 'Being Retried'), ('failed', 'Failed (Max Retries)'), ('success', 'Succeeded on Retry')], default='pending', max_length=20, verbose_name='Retry Status')),
                ('retry_count', models.PositiveIntegerField(default=0, help_text='Number of retry attempts (max 3)', verbose_name='Retry Count')),
                ('last_retry_at', models.DateTimeField(blank=True, null=True, verbose_name='Last Retry Time')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Failed Webhook Log',
                'verbose_name_plural': 'Failed Webhook Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookSignatureLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_id', models.IntegerField(db_index=True, verbose_name='Submission ID')),
                ('signature', models.CharField(help_text='HMAC-SHA256 signature from header', max_length=64, verbose_name='Signature')),
                ('is_valid', models.BooleanField(db_index=True, verbose_name='Signature Valid')),
                ('remote_ip', models.GenericIPAddressField(verbose_name='Remote IP')),
                ('user_agent', models.CharField(blank=True, max_length=500, verbose_name='User Agent')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Webhook Signature Log',
                'verbose_name_plural': 'Webhook Signature Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookAuditTrail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_id', models.IntegerField(db_index=True, verbose_name='Submission ID')),
                ('event_type', models.CharField(choices=[('received', 'Webhook Received'), ('signature_verified', 'Signature Verified'), ('replay_check', 'Replay Attack Check'), ('submission_found', 'Submission Found'), ('grade_applied', 'Grade Applied'), ('notification_sent', 'Notification Sent'), ('error', 'Processing Error')], max_length=50, verbose_name='Event Type')),
                ('details', models.JSONField(help_text='Structured data about the event', verbose_name='Event Details')),
                ('created_by', models.CharField(help_text='Service or user that created the event', max_length=100, verbose_name='Created By')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Webhook Audit Trail',
                'verbose_name_plural': 'Webhook Audit Trails',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='webhookaudittrail',
            index=models.Index(fields=['submission_id', 'event_type'], name='audit_submission_event_idx'),
        ),
        migrations.AddIndex(
            model_name='webhookaudittrail',
            index=models.Index(fields=['event_type', '-created_at'], name='audit_event_date_idx'),
        ),
        migrations.AddIndex(
            model_name='webhooksignaturelog',
            index=models.Index(fields=['submission_id', '-created_at'], name='sig_submission_date_idx'),
        ),
        migrations.AddIndex(
            model_name='webhooksignaturelog',
            index=models.Index(fields=['is_valid', '-created_at'], name='sig_valid_date_idx'),
        ),
        migrations.AddIndex(
            model_name='webhooksignaturelog',
            index=models.Index(fields=['remote_ip', '-created_at'], name='sig_ip_date_idx'),
        ),
        migrations.AddIndex(
            model_name='failedwebhooklog',
            index=models.Index(fields=['submission_id', 'status'], name='webhook_submission_status_idx'),
        ),
        migrations.AddIndex(
            model_name='failedwebhooklog',
            index=models.Index(fields=['status', '-created_at'], name='webhook_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='failedwebhooklog',
            index=models.Index(fields=['retry_count'], name='webhook_retry_count_idx'),
        ),
    ]
