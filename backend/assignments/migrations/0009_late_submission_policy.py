# Generated migration for T_ASSIGN_012

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0008_add_allow_late_submissions"),
    ]

    operations = [
        # Add late submission policy fields to Assignment
        migrations.AddField(
            model_name="assignment",
            name="late_submission_deadline",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Крайний срок для поздней сдачи",
                help_text="Если установлено, позволяет сдавать только до этого времени. Если не установлено, может сдаваться бесконечно если allow_late_submission=True",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="late_penalty_type",
            field=models.CharField(
                choices=[
                    ("percentage", "Процент от балла"),
                    ("fixed_points", "Фиксированное количество баллов"),
                ],
                default="percentage",
                max_length=20,
                verbose_name="Тип штрафа за позднюю сдачу",
                help_text="Как считается штраф за позднюю сдачу",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="late_penalty_value",
            field=models.DecimalField(
                default=0,
                decimal_places=2,
                max_digits=5,
                verbose_name="Значение штрафа за позднюю сдачу",
                help_text="Процент или количество баллов, на которые снижается оценка за каждую единицу времени",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="penalty_frequency",
            field=models.CharField(
                choices=[
                    ("per_day", "За каждый день"),
                    ("per_hour", "За каждый час"),
                ],
                default="per_day",
                max_length=20,
                verbose_name="Частота штрафа",
                help_text="Как часто применяется штраф (в день или в час)",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="max_penalty",
            field=models.DecimalField(
                default=50,
                decimal_places=2,
                max_digits=5,
                verbose_name="Максимальный штраф",
                help_text="Максимальный процент от балла, который можно потерять из-за позднего сдачи",
            ),
        ),
        # Add penalty tracking fields to AssignmentSubmission
        migrations.AddField(
            model_name="assignmentsubmission",
            name="days_late",
            field=models.DecimalField(
                default=0,
                decimal_places=2,
                max_digits=10,
                verbose_name="Дней с опозданием",
                help_text="Количество дней/часов просрочки для расчета штрафа",
            ),
        ),
        migrations.AddField(
            model_name="assignmentsubmission",
            name="penalty_applied",
            field=models.DecimalField(
                blank=True,
                null=True,
                decimal_places=2,
                max_digits=5,
                verbose_name="Примененный штраф",
                help_text="Размер штрафа, примененный к оценке",
            ),
        ),
        # Create SubmissionExemption model
        migrations.CreateModel(
            name="SubmissionExemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "exemption_type",
                    models.CharField(
                        choices=[
                            ("full", "Полное - без штрафа"),
                            ("custom_rate", "Пользовательская ставка"),
                        ],
                        default="full",
                        max_length=20,
                        verbose_name="Тип освобождения",
                    ),
                ),
                (
                    "custom_penalty_rate",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                        verbose_name="Пользовательская ставка штрафа",
                        help_text="Используется вместо стандартной ставки если exemption_type='custom_rate'",
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        verbose_name="Причина освобождения",
                        help_text="Объяснение причины освобождения от штрафа",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "exemption_created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_exemptions",
                        to="auth.user",
                        verbose_name="Создано",
                    ),
                ),
                (
                    "submission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exemption",
                        to="assignments.assignmentsubmission",
                        verbose_name="Ответ на задание",
                    ),
                ),
            ],
            options={
                "verbose_name": "Освобождение от штрафа",
                "verbose_name_plural": "Освобождения от штрафа",
                "ordering": ["-created_at"],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="submissionexemption",
            index=models.Index(
                fields=["submission", "exemption_type"],
                name="exemption_submission_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="submissionexemption",
            index=models.Index(
                fields=["exemption_created_by", "-created_at"],
                name="exemption_creator_date_idx",
            ),
        ),
    ]
