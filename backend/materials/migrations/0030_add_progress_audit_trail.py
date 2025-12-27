# Generated migration for MaterialProgressAuditTrail model
# T_MAT_003: Material Progress Edge Cases - Audit Trail Implementation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("materials", "0029_add_optimization_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialProgressAuditTrail",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "previous_percentage",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Progress percentage before update",
                        verbose_name="Предыдущий процент прогресса",
                    ),
                ),
                (
                    "previous_time_spent",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Time spent before update",
                        verbose_name="Предыдущее время (мин)",
                    ),
                ),
                (
                    "previous_is_completed",
                    models.BooleanField(
                        default=False,
                        help_text="Completion status before update",
                        verbose_name="Было ли завершено (до)",
                    ),
                ),
                (
                    "new_percentage",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Progress percentage after update",
                        verbose_name="Новый процент прогресса",
                    ),
                ),
                (
                    "new_time_spent",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Time spent after update",
                        verbose_name="Новое время (мин)",
                    ),
                ),
                (
                    "new_is_completed",
                    models.BooleanField(
                        default=False,
                        help_text="Completion status after update",
                        verbose_name="Новое состояние завершено",
                    ),
                ),
                (
                    "change_reason",
                    models.CharField(
                        choices=[
                            ("manual_update", "Manual Update"),
                            ("auto_completion", "Auto-completion at 100%"),
                            ("rollback_prevented", "Rollback Prevention"),
                            ("time_accumulation", "Time Spent Added"),
                            ("material_archived", "Material Archived"),
                        ],
                        default="manual_update",
                        help_text="Why the progress was updated",
                        max_length=50,
                        verbose_name="Причина изменения",
                    ),
                ),
                (
                    "change_details",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional context (e.g., rollback info, time delta)",
                        verbose_name="Детали изменения",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the change occurred",
                        verbose_name="Время изменения",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        help_text="User IP address during update",
                        null=True,
                        verbose_name="IP-адрес",
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(
                        blank=True,
                        help_text="Browser/client information",
                        verbose_name="User-Agent",
                    ),
                ),
                (
                    "progress",
                    models.ForeignKey(
                        help_text="MaterialProgress record being tracked",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_trail",
                        to="materials.materialprogress",
                        verbose_name="Прогресс",
                    ),
                ),
            ],
            options={
                "verbose_name": "Аудит прогресса материала",
                "verbose_name_plural": "Аудиты прогресса материалов",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="materialprogressaudittrail",
            index=models.Index(
                fields=["progress", "timestamp"],
                name="mat_prog_audit_idx_1"
            ),
        ),
        migrations.AddIndex(
            model_name="materialprogressaudittrail",
            index=models.Index(
                fields=["timestamp"],
                name="mat_prog_audit_idx_3"
            ),
        ),
        migrations.AddIndex(
            model_name="materialprogressaudittrail",
            index=models.Index(
                fields=["change_reason"],
                name="mat_prog_audit_idx_4"
            ),
        ),
    ]
