"""
Fix ChatRoom schema mismatch - drop old columns not in models.py
This migration removes all columns not defined in the current models using raw SQL.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0013_remove_messagethread_created_by_and_more"),
    ]

    operations = [
        # Drop columns using raw SQL (safer for schema sync issues)
        migrations.RunSQL(
            sql="""
            ALTER TABLE chat_chatroom
            DROP COLUMN IF EXISTS enrollment_id,
            DROP COLUMN IF EXISTS auto_delete_days,
            DROP COLUMN IF EXISTS created_by_id,
            DROP COLUMN IF EXISTS type,
            DROP COLUMN IF EXISTS description,
            DROP COLUMN IF EXISTS name;
            """,
            reverse_sql="-- Cannot reverse schema changes"
        ),
    ]
