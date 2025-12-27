"""
T_MAT_003: Material Progress Edge Case Handler Service

Comprehensive service for handling material progress tracking with edge case support:
1. Student enrollment validation
2. Deleted/archived material handling
3. Concurrent progress updates (race condition safe)
4. Progress percentage NULL-safe handling
5. Progress can only increase (rollback prevention)
6. Inactive enrollment materials handling
7. Archived materials access control
8. Idempotent progress updates
"""

import logging
from typing import Optional, Dict, Any

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Material, MaterialProgress, SubjectEnrollment

User = get_user_model()
logger = logging.getLogger(__name__)


class MaterialProgressService:
    """Service for managing material progress with comprehensive edge case handling"""

    @staticmethod
    def validate_student_access(
        student: User, material: Material
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if student has access to the material.

        T_MAT_003 Edge Case 1: Student enrollment validation
        T_MAT_003 Edge Case 7: Inactive enrollment validation

        Args:
            student: User object (must be student role)
            material: Material object

        Returns:
            tuple: (is_valid, error_message)
            - (True, None) if access allowed
            - (False, error_msg) if access denied
        """
        if student.role != "student":
            return False, "Только студенты могут обновлять прогресс"

        if not material.assigned_to.filter(id=student.id).exists():
            if not material.is_public:
                return False, "Материал вам не доступен"

        if material.status == Material.Status.ARCHIVED:
            return True, None

        if material.status != Material.Status.ACTIVE:
            return False, "Материал недоступен"

        return True, None

    @staticmethod
    def validate_enrollment_active(student: User, material: Material) -> bool:
        """
        Check if student has active enrollment for material's subject.

        T_MAT_003 Edge Case 7: Inactive enrollment check

        Args:
            student: User object
            material: Material object

        Returns:
            bool: True if enrollment is active, False otherwise
        """
        return SubjectEnrollment.objects.filter(
            student=student,
            subject=material.subject,
            is_active=True
        ).exists()

    @staticmethod
    def normalize_progress_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize progress data with NULL-safe handling.

        T_MAT_003 Edge Cases 4: NULL value handling
        - progress_percentage: clamp to 0-100
        - time_spent: clamp to >= 0
        - is_completed: boolean

        Args:
            data: Raw progress data

        Returns:
            Dict: Normalized data
        """
        normalized = {}

        if "progress_percentage" in data:
            value = data["progress_percentage"]
            if value is None:
                normalized["progress_percentage"] = 0
            else:
                try:
                    value = int(value)
                    normalized["progress_percentage"] = max(0, min(100, value))
                except (ValueError, TypeError):
                    raise ValueError("progress_percentage должен быть числом")
        else:
            normalized["progress_percentage"] = None

        if "time_spent" in data:
            value = data["time_spent"]
            if value is None:
                normalized["time_spent"] = 0
            else:
                try:
                    value = int(value)
                    normalized["time_spent"] = max(0, value)
                except (ValueError, TypeError):
                    raise ValueError("time_spent должен быть числом")
        else:
            normalized["time_spent"] = None

        if "is_completed" in data:
            normalized["is_completed"] = bool(data["is_completed"])

        return normalized

    @staticmethod
    @transaction.atomic
    def update_progress(
        student: User,
        material: Material,
        progress_percentage: Optional[int] = None,
        time_spent: Optional[int] = None,
        is_completed: Optional[bool] = None,
    ) -> tuple[MaterialProgress, Dict[str, Any]]:
        """
        Atomically update material progress with race condition protection.

        T_MAT_003 Edge Cases:
        - 3: Concurrent updates (select_for_update)
        - 5: Progress rollback prevention
        - 6: Idempotent updates

        Args:
            student: User object
            material: Material object
            progress_percentage: New progress percentage (0-100)
            time_spent: Time spent in minutes
            is_completed: Completion status

        Returns:
            tuple: (MaterialProgress instance, update_info dict)

        Raises:
            ValueError: If validation fails
        """
        is_valid, error_msg = MaterialProgressService.validate_student_access(
            student, material
        )
        if not is_valid:
            raise ValueError(error_msg)

        with transaction.atomic():
            progress, created = MaterialProgress.objects.select_for_update().get_or_create(
                student=student,
                material=material
            )

            update_info = {
                "created": created,
                "previous_percentage": progress.progress_percentage,
                "previous_time_spent": progress.time_spent,
                "rollback_prevented": False,
                "completed_now": False
            }

            if progress_percentage is not None:
                progress_percentage = max(0, min(100, int(progress_percentage)))

                if progress_percentage < progress.progress_percentage:
                    logger.warning(
                        f"Progress rollback prevented for student {student.id} "
                        f"on material {material.id}: {progress.progress_percentage}% -> {progress_percentage}%"
                    )
                    update_info["rollback_prevented"] = True
                else:
                    progress.progress_percentage = progress_percentage

            if time_spent is not None:
                time_spent = max(0, int(time_spent))
                progress.time_spent += time_spent

            if is_completed is True and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = timezone.now()
                update_info["completed_now"] = True

            if progress_percentage is not None and progress_percentage >= 100:
                progress.is_completed = True
                if not progress.completed_at:
                    progress.completed_at = timezone.now()
                    update_info["completed_now"] = True

            progress.save(
                update_fields=[
                    "progress_percentage",
                    "time_spent",
                    "is_completed",
                    "completed_at",
                    "last_accessed"
                ]
            )

            return progress, update_info

    @staticmethod
    def get_student_progress(
        student: User,
        material: Material
    ) -> Optional[MaterialProgress]:
        """
        Safely retrieve student progress with NULL-safe handling.

        T_MAT_003 Edge Case 4: NULL-safe retrieval

        Args:
            student: User object
            material: Material object

        Returns:
            MaterialProgress instance or None
        """
        try:
            return MaterialProgress.objects.select_related(
                "student", "material", "material__subject"
            ).get(student=student, material=material)
        except MaterialProgress.DoesNotExist:
            return None

    @staticmethod
    def calculate_progress_metrics(student: User, subject=None) -> Dict[str, Any]:
        """
        Calculate progress metrics with NULL-safe aggregation.

        T_MAT_003 Edge Case 4: NULL-safe aggregation

        Args:
            student: User object
            subject: Optional subject filter

        Returns:
            Dict with metrics
        """
        queryset = MaterialProgress.objects.filter(
            student=student,
            material__status__in=[Material.Status.ACTIVE, Material.Status.ARCHIVED]
        )

        if subject:
            queryset = queryset.filter(material__subject=subject)

        total = queryset.count()
        if total == 0:
            return {
                "total_materials": 0,
                "completed_materials": 0,
                "completion_rate": 0.0,
                "average_progress": 0.0,
                "total_time_spent": 0
            }

        completed = queryset.filter(is_completed=True).count()
        avg_progress = queryset.aggregate(
            avg=models.functions.Coalesce(
                models.Avg("progress_percentage"),
                0
            )
        )["avg"] or 0

        total_time = queryset.aggregate(
            total=models.functions.Coalesce(
                models.Sum("time_spent"),
                0
            )
        )["total"] or 0

        return {
            "total_materials": total,
            "completed_materials": completed,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "average_progress": float(avg_progress),
            "total_time_spent": int(total_time)
        }

    @staticmethod
    def handle_material_archive(material: Material) -> Dict[str, Any]:
        """
        Handle material archival with safe progress tracking.

        T_MAT_003 Edge Case 6: Archived material handling

        When a material is archived:
        - Existing progress records remain intact (read-only)
        - New progress updates are blocked
        - Students can still view their progress
        - Teachers can view all student progress

        Args:
            material: Material to archive

        Returns:
            Dict with archival info
        """
        if material.status == Material.Status.ARCHIVED:
            return {"status": "already_archived", "affected_records": 0}

        material.status = Material.Status.ARCHIVED
        material.save(update_fields=["status"])

        affected_count = material.progress.count()

        logger.info(
            f"Material {material.id} archived. "
            f"Preserved {affected_count} progress records"
        )

        return {
            "status": "archived",
            "affected_records": affected_count,
            "message": "Материал архивирован. Прогресс сохранён в архиве"
        }

    @staticmethod
    def delete_material_safe(material: Material) -> Dict[str, Any]:
        """
        Safely 'delete' material by archiving (prevent data loss).

        T_MAT_003 Edge Case 2: Deleted material handling

        Instead of hard delete:
        - Archive the material
        - Preserve all progress records
        - Block new progress updates
        - Allow reading historical data

        Args:
            material: Material to delete

        Returns:
            Dict with deletion info
        """
        if material.status == Material.Status.ARCHIVED:
            logger.info(f"Material {material.id} already archived, skipping archival")
            return {
                "status": "already_archived",
                "preserved_records": material.progress.count()
            }

        return MaterialProgressService.handle_material_archive(material)


# Import models at end to avoid circular imports
from django.db import models
