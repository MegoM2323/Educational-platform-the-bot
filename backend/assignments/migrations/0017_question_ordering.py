# Generated migration for T_ASN_002: Assignment Question Order

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0016_add_assignment_attempt_model'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='assignmentquestion',
            name='randomize_options',
            field=models.BooleanField(default=False, help_text='If enabled, answer options will be randomized per student', verbose_name='Randomize answer options'),
        ),
        migrations.AddField(
            model_name='assignmentquestion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='assignmentquestion',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Update order field with validators
        migrations.AlterField(
            model_name='assignmentquestion',
            name='order',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='Порядок',
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(1000),
                ]
            ),
        ),
        # Add unique constraint for order per assignment
        migrations.AlterUniqueTogether(
            name='assignmentquestion',
            unique_together={('assignment', 'order')},
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='assignmentquestion',
            index=models.Index(fields=['assignment', 'order'], name='question_assignment_order_idx'),
        ),
        migrations.AddIndex(
            model_name='assignmentquestion',
            index=models.Index(fields=['assignment', 'randomize_options'], name='question_randomize_idx'),
        ),
    ]
