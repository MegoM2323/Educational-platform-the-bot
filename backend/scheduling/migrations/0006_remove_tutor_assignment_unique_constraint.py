# Migration: Remove unique_together from TutorAssignment

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0005_add_slot_type_and_optional_student"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="tutorassignment",
            unique_together=set(),
        ),
    ]
