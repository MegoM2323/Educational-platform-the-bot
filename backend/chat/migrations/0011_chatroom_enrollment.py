# Generated to add enrollment field via raw SQL

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0035_alter_subjectenrollment_unique_together_and_more"),
        ("chat", "0010_convert_enrollment_to_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_chatroom
                ADD COLUMN IF NOT EXISTS enrollment_id BIGINT NULL REFERENCES materials_subjectenrollment(id) ON DELETE CASCADE;
                CREATE INDEX IF NOT EXISTS idx_chat_type_enrollment ON chat_chatroom(type, enrollment_id);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_chat_type_enrollment;
                ALTER TABLE chat_chatroom DROP COLUMN IF EXISTS enrollment_id;
            """,
        ),
    ]
