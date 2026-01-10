from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0019_fix_chatroom_schema"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["sender"], name="idx_message_sender"),
        ),
    ]
