# Generated migration for PostgreSQL optimization indexes
# Adds indexes on frequently queried fields for improved query performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_remove_plaintext_passwords"),
    ]

    operations = [
        # User model indexes
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["username"], name="accounts_user_username_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["email"], name="accounts_user_email_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["telegram_id"], name="accounts_user_telegram_id_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["role", "is_active"], name="accounts_user_role_active_idx"),
        ),

        # StudentProfile model indexes
        migrations.AddIndex(
            model_name="studentprofile",
            index=models.Index(fields=["tutor"], name="accounts_student_tutor_idx"),
        ),
        migrations.AddIndex(
            model_name="studentprofile",
            index=models.Index(fields=["parent"], name="accounts_student_parent_idx"),
        ),
        migrations.AddIndex(
            model_name="studentprofile",
            index=models.Index(fields=["grade"], name="accounts_student_grade_idx"),
        ),

        # TutorStudentCreation model indexes
        migrations.AddIndex(
            model_name="tutorstudentcreation",
            index=models.Index(fields=["tutor"], name="accounts_tutorcreation_tutor_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorstudentcreation",
            index=models.Index(fields=["student"], name="accounts_tutorcreation_student_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorstudentcreation",
            index=models.Index(fields=["parent"], name="accounts_tutorcreation_parent_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorstudentcreation",
            index=models.Index(fields=["created_at"], name="accounts_tutorcreation_created_idx"),
        ),
    ]
