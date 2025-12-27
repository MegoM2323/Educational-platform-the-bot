# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in payments app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_alter_payment_status'),
    ]

    operations = [
        # Index on status for payment queries
        # Used for: Payment.objects.filter(status='completed')
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['status'],
                name='payment_status_idx',
            ),
        ),

        # Index on created for payment ordering
        # Used for: Payment.objects.order_by('-created')
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['-created'],
                name='payment_created_idx',
            ),
        ),

        # Composite index for payment status with date
        # Used for: Payment.objects.filter(status='pending').order_by('created')
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['status', '-created'],
                name='payment_status_date_idx',
            ),
        ),
    ]
