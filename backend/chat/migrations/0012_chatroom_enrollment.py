from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0035_alter_subjectenrollment_unique_together_and_more"),
        ("chat", "0011_remove_chatroom_chat_type_enrollment_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_chatroom
                ADD COLUMN IF NOT EXISTS enrollment_id BIGINT NULL REFERENCES materials_subjectenrollment(id) ON DELETE CASCADE;
                CREATE INDEX IF NOT EXISTS chat_type_enrollment_idx_v2 ON chat_chatroom(type, enrollment_id);
                ALTER TABLE chat_chatroom ADD CONSTRAINT unique_forum_per_enrollment UNIQUE(type, enrollment_id);
            """,
            reverse_sql="""
                ALTER TABLE chat_chatroom DROP CONSTRAINT IF EXISTS unique_forum_per_enrollment;
                DROP INDEX IF EXISTS chat_type_enrollment_idx_v2;
                ALTER TABLE chat_chatroom DROP COLUMN IF EXISTS enrollment_id;
            """,
        ),
    ]
