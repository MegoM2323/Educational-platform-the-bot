# Generated data migration
# Переименование forum_subject и forum_tutor чатов по новым правилам

from django.db import migrations
import json


def rename_forum_chats(apps, schema_editor):
    """
    Переименовывает forum_subject и forum_tutor чаты по новым правилам:
    - forum_subject: "{subject.name}: {teacher.get_full_name() или email или Unknown}"
    - forum_tutor: "{student.get_full_name() или email или Unknown}"

    Сохраняет информацию о переименованиях в поле description для отката.
    """
    ChatRoom = apps.get_model("chat", "ChatRoom")

    renamed_chats = []

    for chat in ChatRoom.objects.select_related(
        "enrollment__subject", "enrollment__teacher", "enrollment__student"
    ).filter(type__in=["forum_subject", "forum_tutor"]):
        old_name = chat.name
        new_name = None

        if chat.type == "forum_subject":
            if chat.enrollment:
                subject_name = chat.enrollment.subject.name
                teacher = chat.enrollment.teacher
                teacher_name = (
                    f"{teacher.first_name} {teacher.last_name}".strip()
                    or teacher.email
                    or "Unknown"
                )
                new_name = f"{subject_name}: {teacher_name}"

        elif chat.type == "forum_tutor":
            if chat.enrollment:
                student = chat.enrollment.student
                student_name = (
                    f"{student.first_name} {student.last_name}".strip()
                    or student.email
                    or "Unknown"
                )
                new_name = student_name

        if new_name and new_name != old_name:
            chat.name = new_name
            if not chat.description:
                chat.description = json.dumps(
                    {"__migration_0011__": {"original_name": old_name}},
                    ensure_ascii=False,
                )
            else:
                try:
                    desc_data = json.loads(chat.description)
                    if "__migration_0011__" not in desc_data:
                        desc_data["__migration_0011__"] = {"original_name": old_name}
                        chat.description = json.dumps(desc_data, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    chat.description = json.dumps(
                        {"__migration_0011__": {"original_name": old_name}},
                        ensure_ascii=False,
                    )

            chat.save(update_fields=["name", "description"])
            renamed_chats.append(
                {
                    "id": chat.id,
                    "type": chat.type,
                    "old_name": old_name,
                    "new_name": new_name,
                }
            )

    if renamed_chats:
        print(f"\n{'=' * 70}")
        print(f"Переименовано чатов: {len(renamed_chats)}")
        print(f"{'=' * 70}")
        for item in renamed_chats:
            print(f"  [{item['id']:4d}] {item['type']:15s}: '{item['old_name'][:40]}'")
            print(f"        {'':15s}  -> '{item['new_name'][:40]}'")
        print(f"{'=' * 70}\n")


def reverse_rename_forum_chats(apps, schema_editor):
    """
    Откатывает переименования forum_subject и forum_tutor чатов.
    Использует сохраненные оригинальные имена из поля description.
    """
    ChatRoom = apps.get_model("chat", "ChatRoom")

    reverted_count = 0

    for chat in ChatRoom.objects.filter(type__in=["forum_subject", "forum_tutor"]):
        if not chat.description:
            continue

        try:
            desc_data = json.loads(chat.description)
            if "__migration_0011__" in desc_data:
                original_name = desc_data["__migration_0011__"].get("original_name")
                if original_name:
                    chat.name = original_name

                    del desc_data["__migration_0011__"]
                    if desc_data:
                        chat.description = json.dumps(desc_data, ensure_ascii=False)
                    else:
                        chat.description = ""

                    chat.save(update_fields=["name", "description"])
                    reverted_count += 1
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    if reverted_count > 0:
        print(f"\n{'=' * 70}")
        print(f"Откачено переименований: {reverted_count} чатов")
        print(f"{'=' * 70}\n")


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0037_subjectenrollment_status"),
        (
            "chat",
            "0010_rename_chat_type_enrollment_idx_chat_type_enrollment_idx_v2_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(rename_forum_chats, reverse_rename_forum_chats),
    ]
