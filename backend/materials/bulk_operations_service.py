"""
Service for handling bulk material assignment operations.
Provides pre-flight validation, transaction-safe bulk operations,
and comprehensive audit logging.
"""
import logging
import time
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from notifications.notification_service import NotificationService

from .models import (
    BulkAssignmentAuditLog,
    Material,
    MaterialProgress,
    Subject,
    SubjectEnrollment,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class BulkAssignmentService:
    """
    Service for efficient bulk material assignment operations.

    Handles:
    - Bulk assign single material to multiple students
    - Bulk assign multiple materials to single student
    - Bulk assignment to entire class
    - Bulk remove assignments
    - Pre-flight validation
    - Transaction safety
    - Audit logging
    - Error recovery with partial success

    Rate limit: Max 1000 items per operation
    """

    MAX_ITEMS_PER_OPERATION = 1000

    def __init__(self, user: User):
        """Initialize service with performing user"""
        self.user = user
        self.notifier = NotificationService()

    def preflight_check(
        self,
        material_id: int = None,
        student_ids: List[int] = None,
        material_ids: List[int] = None,
        student_id: int = None,
        class_id: int = None,
    ) -> Dict[str, Any]:
        """
        Pre-flight validation before executing bulk operation.
        Checks all conditions without making changes.

        Returns:
            {
                'valid': bool,
                'errors': [list of error messages],
                'warnings': [list of warnings],
                'total_items': estimated number of assignments,
                'affected_students': list of student IDs that will be affected,
                'affected_materials': list of material IDs that will be affected,
            }
        """
        errors = []
        warnings = []
        affected_students = set()
        affected_materials = set()

        try:
            # Scenario 1: Bulk assign single material to multiple students
            if material_id and student_ids:
                if len(student_ids) > self.MAX_ITEMS_PER_OPERATION:
                    errors.append(
                        f"Too many students. Maximum {self.MAX_ITEMS_PER_OPERATION} per operation"
                    )
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check material exists
                if not Material.objects.filter(id=material_id).exists():
                    errors.append(f"Material {material_id} not found")
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check all students exist
                students = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)
                if len(students) != len(student_ids):
                    missing_ids = set(student_ids) - set(
                        students.values_list("id", flat=True)
                    )
                    errors.append(f"Students not found: {missing_ids}")

                affected_students = set(students.values_list("id", flat=True))
                affected_materials = {material_id}
                total_items = len(affected_students)

            # Scenario 2: Bulk assign multiple materials to single student
            elif material_ids and student_id:
                if len(material_ids) > self.MAX_ITEMS_PER_OPERATION:
                    errors.append(
                        f"Too many materials. Maximum {self.MAX_ITEMS_PER_OPERATION} per operation"
                    )
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check student exists
                if not User.objects.filter(id=student_id, role=User.Role.STUDENT).exists():
                    errors.append(f"Student {student_id} not found")
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check all materials exist
                materials = Material.objects.filter(id__in=material_ids)
                if len(materials) != len(material_ids):
                    missing_ids = set(material_ids) - set(
                        materials.values_list("id", flat=True)
                    )
                    errors.append(f"Materials not found: {missing_ids}")

                affected_materials = set(materials.values_list("id", flat=True))
                affected_students = {student_id}
                total_items = len(affected_materials)

            # Scenario 3: Bulk assign materials to entire class
            elif material_ids and class_id:
                if len(material_ids) > self.MAX_ITEMS_PER_OPERATION:
                    errors.append(
                        f"Too many materials. Maximum {self.MAX_ITEMS_PER_OPERATION} per operation"
                    )
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check subject (class) exists
                if not Subject.objects.filter(id=class_id).exists():
                    errors.append(f"Class/Subject {class_id} not found")
                    return {
                        "valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "total_items": 0,
                    }

                # Check all materials exist
                materials = Material.objects.filter(id__in=material_ids)
                if len(materials) != len(material_ids):
                    missing_ids = set(material_ids) - set(
                        materials.values_list("id", flat=True)
                    )
                    errors.append(f"Materials not found: {missing_ids}")

                # Get all students enrolled in this subject
                students = User.objects.filter(
                    subject_enrollments__subject_id=class_id,
                    subject_enrollments__is_active=True,
                    role=User.Role.STUDENT,
                ).distinct()

                if not students.exists():
                    warnings.append(
                        f"No active students enrolled in class {class_id}"
                    )

                affected_materials = set(materials.values_list("id", flat=True))
                affected_students = set(students.values_list("id", flat=True))
                total_items = len(affected_students) * len(affected_materials)

                if total_items > self.MAX_ITEMS_PER_OPERATION:
                    errors.append(
                        f"Operation would create {total_items} assignments, "
                        f"exceeds limit of {self.MAX_ITEMS_PER_OPERATION}"
                    )

            else:
                errors.append("Invalid operation parameters")

        except Exception as e:
            logger.error(f"Preflight check failed: {str(e)}")
            errors.append(f"Preflight check error: {str(e)}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_items": total_items if 'total_items' in locals() else 0,
            "affected_students": list(affected_students),
            "affected_materials": list(affected_materials),
        }

    @transaction.atomic
    def bulk_assign_students(
        self,
        material_id: int,
        student_ids: List[int],
        skip_existing: bool = True,
        notify: bool = True,
    ) -> Dict[str, Any]:
        """
        Assign single material to multiple students.

        Args:
            material_id: Material ID
            student_ids: List of student IDs
            skip_existing: If True, skip students already assigned
            notify: If True, send notifications to students

        Returns:
            {
                'created': count of new assignments,
                'skipped': count of existing assignments,
                'failed': count of failed assignments,
                'failed_items': list of failed items with errors,
            }
        """
        audit_log = BulkAssignmentAuditLog.objects.create(
            performed_by=self.user,
            operation_type=BulkAssignmentAuditLog.OperationType.BULK_ASSIGN_TO_STUDENTS,
            status=BulkAssignmentAuditLog.Status.PROCESSING,
            metadata={
                "material_id": material_id,
                "student_ids": student_ids,
                "skip_existing": skip_existing,
            },
            total_items=len(student_ids),
        )

        start_time = time.time()
        created_count = 0
        skipped_count = 0
        failed_count = 0
        failed_items = []

        try:
            material = Material.objects.select_related("subject").get(id=material_id)
            students = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)

            for student in students:
                try:
                    # Check if already assigned
                    if skip_existing and material.assigned_to.filter(id=student.id).exists():
                        skipped_count += 1
                        continue

                    # Add assignment
                    material.assigned_to.add(student)

                    # Create progress record
                    MaterialProgress.objects.get_or_create(
                        student=student, material=material
                    )

                    created_count += 1

                    # Send notification
                    if notify:
                        try:
                            self.notifier.notify_material_published(
                                student=student,
                                material_id=material.id,
                                subject_id=material.subject_id,
                            )
                        except Exception as e:
                            logger.warning(f"Notification failed for {student.id}: {str(e)}")

                except Exception as e:
                    failed_count += 1
                    failed_items.append({
                        "student_id": student.id,
                        "error": str(e),
                    })
                    logger.error(f"Failed to assign material to student {student.id}: {str(e)}")

            # Update audit log
            duration = time.time() - start_time
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.skipped_count = skipped_count
            audit_log.failed_count = failed_count
            audit_log.failed_items = failed_items
            audit_log.status = (
                BulkAssignmentAuditLog.Status.COMPLETED
                if failed_count == 0
                else BulkAssignmentAuditLog.Status.PARTIAL_FAILURE
            )
            audit_log.save()

            return {
                "created": created_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "failed_items": failed_items,
            }

        except Exception as e:
            logger.error(f"Bulk assign operation failed: {str(e)}")
            duration = time.time() - start_time
            audit_log.status = BulkAssignmentAuditLog.Status.FAILED
            audit_log.error_message = str(e)
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.failed_count = failed_count + 1
            audit_log.failed_items = failed_items
            audit_log.save()
            raise

    @transaction.atomic
    def bulk_assign_materials(
        self,
        material_ids: List[int],
        student_id: int,
        skip_existing: bool = True,
        notify: bool = True,
    ) -> Dict[str, Any]:
        """
        Assign multiple materials to single student.

        Args:
            material_ids: List of material IDs
            student_id: Student ID
            skip_existing: If True, skip already assigned materials
            notify: If True, send notifications

        Returns:
            {
                'created': count of new assignments,
                'skipped': count of existing assignments,
                'failed': count of failed assignments,
                'failed_items': list of failed items with errors,
            }
        """
        audit_log = BulkAssignmentAuditLog.objects.create(
            performed_by=self.user,
            operation_type=BulkAssignmentAuditLog.OperationType.BULK_ASSIGN_MATERIALS,
            status=BulkAssignmentAuditLog.Status.PROCESSING,
            metadata={
                "student_id": student_id,
                "material_ids": material_ids,
                "skip_existing": skip_existing,
            },
            total_items=len(material_ids),
        )

        start_time = time.time()
        created_count = 0
        skipped_count = 0
        failed_count = 0
        failed_items = []

        try:
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
            materials = Material.objects.select_related("subject").filter(
                id__in=material_ids
            )

            for material in materials:
                try:
                    # Check if already assigned
                    if skip_existing and material.assigned_to.filter(id=student.id).exists():
                        skipped_count += 1
                        continue

                    # Add assignment
                    material.assigned_to.add(student)

                    # Create progress record
                    MaterialProgress.objects.get_or_create(
                        student=student, material=material
                    )

                    created_count += 1

                    # Send notification
                    if notify:
                        try:
                            self.notifier.notify_material_published(
                                student=student,
                                material_id=material.id,
                                subject_id=material.subject_id,
                            )
                        except Exception as e:
                            logger.warning(f"Notification failed for material {material.id}: {str(e)}")

                except Exception as e:
                    failed_count += 1
                    failed_items.append({
                        "material_id": material.id,
                        "error": str(e),
                    })
                    logger.error(f"Failed to assign material {material.id} to student: {str(e)}")

            # Update audit log
            duration = time.time() - start_time
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.skipped_count = skipped_count
            audit_log.failed_count = failed_count
            audit_log.failed_items = failed_items
            audit_log.status = (
                BulkAssignmentAuditLog.Status.COMPLETED
                if failed_count == 0
                else BulkAssignmentAuditLog.Status.PARTIAL_FAILURE
            )
            audit_log.save()

            return {
                "created": created_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "failed_items": failed_items,
            }

        except Exception as e:
            logger.error(f"Bulk assign materials operation failed: {str(e)}")
            duration = time.time() - start_time
            audit_log.status = BulkAssignmentAuditLog.Status.FAILED
            audit_log.error_message = str(e)
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.failed_count = failed_count + 1
            audit_log.failed_items = failed_items
            audit_log.save()
            raise

    @transaction.atomic
    def bulk_assign_class(
        self,
        material_ids: List[int],
        class_id: int,
        skip_existing: bool = True,
        notify: bool = True,
    ) -> Dict[str, Any]:
        """
        Assign materials to all students in a class.

        Args:
            material_ids: List of material IDs
            class_id: Subject/Class ID
            skip_existing: If True, skip already assigned materials
            notify: If True, send notifications

        Returns:
            {
                'created': count of new assignments,
                'skipped': count of existing assignments,
                'failed': count of failed assignments,
                'failed_items': list of failed items with errors,
            }
        """
        audit_log = BulkAssignmentAuditLog.objects.create(
            performed_by=self.user,
            operation_type=BulkAssignmentAuditLog.OperationType.BULK_ASSIGN_TO_CLASS,
            status=BulkAssignmentAuditLog.Status.PROCESSING,
            metadata={
                "class_id": class_id,
                "material_ids": material_ids,
                "skip_existing": skip_existing,
            },
            total_items=0,
        )

        start_time = time.time()
        created_count = 0
        skipped_count = 0
        failed_count = 0
        failed_items = []

        try:
            # Get all students in class
            students = User.objects.filter(
                subject_enrollments__subject_id=class_id,
                subject_enrollments__is_active=True,
                role=User.Role.STUDENT,
            ).distinct()

            materials = Material.objects.select_related("subject").filter(
                id__in=material_ids
            )

            total_operations = len(students) * len(materials)
            audit_log.total_items = total_operations
            audit_log.save()

            for material in materials:
                for student in students:
                    try:
                        # Check if already assigned
                        if skip_existing and material.assigned_to.filter(id=student.id).exists():
                            skipped_count += 1
                            continue

                        # Add assignment
                        material.assigned_to.add(student)

                        # Create progress record
                        MaterialProgress.objects.get_or_create(
                            student=student, material=material
                        )

                        created_count += 1

                        # Send notification (batch them for efficiency)
                        if notify:
                            try:
                                self.notifier.notify_material_published(
                                    student=student,
                                    material_id=material.id,
                                    subject_id=material.subject_id,
                                )
                            except Exception as e:
                                logger.warning(f"Notification failed: {str(e)}")

                    except Exception as e:
                        failed_count += 1
                        failed_items.append({
                            "student_id": student.id,
                            "material_id": material.id,
                            "error": str(e),
                        })
                        logger.error(f"Failed to assign: {str(e)}")

            # Update audit log
            duration = time.time() - start_time
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.skipped_count = skipped_count
            audit_log.failed_count = failed_count
            audit_log.failed_items = failed_items
            audit_log.status = (
                BulkAssignmentAuditLog.Status.COMPLETED
                if failed_count == 0
                else BulkAssignmentAuditLog.Status.PARTIAL_FAILURE
            )
            audit_log.save()

            return {
                "created": created_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "failed_items": failed_items,
            }

        except Exception as e:
            logger.error(f"Bulk assign class operation failed: {str(e)}")
            duration = time.time() - start_time
            audit_log.status = BulkAssignmentAuditLog.Status.FAILED
            audit_log.error_message = str(e)
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = created_count
            audit_log.failed_count = failed_count + 1
            audit_log.failed_items = failed_items
            audit_log.save()
            raise

    @transaction.atomic
    def bulk_remove(
        self,
        material_ids: List[int] = None,
        student_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Remove material assignments.

        Args:
            material_ids: Optional - Remove from these materials
            student_ids: Optional - Remove from these students

        Returns:
            {
                'removed': count of removed assignments,
                'not_found': count of non-existent assignments,
                'failed': count of failed removals,
            }
        """
        audit_log = BulkAssignmentAuditLog.objects.create(
            performed_by=self.user,
            operation_type=BulkAssignmentAuditLog.OperationType.BULK_REMOVE,
            status=BulkAssignmentAuditLog.Status.PROCESSING,
            metadata={
                "material_ids": material_ids,
                "student_ids": student_ids,
            },
            total_items=(len(material_ids) if material_ids else 0)
            + (len(student_ids) if student_ids else 0),
        )

        start_time = time.time()
        removed_count = 0
        not_found_count = 0
        failed_count = 0

        try:
            if material_ids:
                materials = Material.objects.filter(id__in=material_ids)
                for material in materials:
                    try:
                        count = material.assigned_to.count()
                        material.assigned_to.clear()
                        removed_count += count
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to remove assignments from material {material.id}: {str(e)}")

                not_found_count += max(0, len(material_ids) - len(materials))

            if student_ids:
                students = User.objects.filter(id__in=student_ids)
                for student in students:
                    try:
                        count = student.assigned_materials.count()
                        student.assigned_materials.clear()
                        removed_count += count
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to remove assignments from student {student.id}: {str(e)}")

                not_found_count += max(0, len(student_ids) - len(students))

            # Update audit log
            duration = time.time() - start_time
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.created_count = removed_count
            audit_log.skipped_count = not_found_count
            audit_log.failed_count = failed_count
            audit_log.status = (
                BulkAssignmentAuditLog.Status.COMPLETED
                if failed_count == 0
                else BulkAssignmentAuditLog.Status.PARTIAL_FAILURE
            )
            audit_log.save()

            return {
                "removed": removed_count,
                "not_found": not_found_count,
                "failed": failed_count,
            }

        except Exception as e:
            logger.error(f"Bulk remove operation failed: {str(e)}")
            duration = time.time() - start_time
            audit_log.status = BulkAssignmentAuditLog.Status.FAILED
            audit_log.error_message = str(e)
            audit_log.completed_at = timezone.now()
            audit_log.duration_seconds = duration
            audit_log.failed_count = failed_count + 1
            audit_log.save()
            raise
