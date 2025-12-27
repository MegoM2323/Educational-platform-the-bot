"""
Subject Enrollment Service - T_MAT_006

Comprehensive validation and business logic for subject enrollments:
1. Duplicate enrollment prevention
2. User role validation
3. Subject existence verification
4. Atomic enrollment operations
5. Enrollment lifecycle management
"""

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import SubjectEnrollment, Subject, TeacherSubject

User = get_user_model()


class EnrollmentValidationError(DRFValidationError):
    """Custom validation error for enrollment operations"""
    pass


class SubjectEnrollmentService:
    """Service for managing subject enrollments with comprehensive validation"""

    @staticmethod
    def validate_user_role(user):
        """
        Validate that user has valid role for enrollment.

        Args:
            user: User instance

        Raises:
            EnrollmentValidationError: If user role is invalid
        """
        valid_roles = ['student', 'teacher', 'tutor']
        if user.role not in valid_roles:
            raise EnrollmentValidationError(
                f"Пользователь с ролью '{user.role}' не может быть зачислен. "
                f"Допустимые роли: {', '.join(valid_roles)}"
            )
        return True

    @staticmethod
    def validate_subject_exists(subject_id):
        """
        Validate that subject exists.

        Args:
            subject_id: Subject ID

        Returns:
            Subject instance

        Raises:
            EnrollmentValidationError: If subject does not exist
        """
        try:
            return Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise EnrollmentValidationError(
                f"Предмет с ID {subject_id} не найден"
            )

    @staticmethod
    def validate_teacher_exists(teacher_id):
        """
        Validate that teacher exists and has valid role.

        Args:
            teacher_id: Teacher user ID

        Returns:
            User instance

        Raises:
            EnrollmentValidationError: If teacher does not exist or invalid role
        """
        try:
            teacher = User.objects.get(id=teacher_id)
            if teacher.role not in ['teacher', 'tutor']:
                raise EnrollmentValidationError(
                    f"Пользователь '{teacher.get_full_name()}' не является преподавателем"
                )
            return teacher
        except User.DoesNotExist:
            raise EnrollmentValidationError(
                f"Преподаватель с ID {teacher_id} не найден"
            )

    @staticmethod
    def validate_student_exists(student_id):
        """
        Validate that student exists and has valid role.

        Args:
            student_id: Student user ID

        Returns:
            User instance

        Raises:
            EnrollmentValidationError: If student does not exist or invalid role
        """
        try:
            student = User.objects.get(id=student_id)
            if student.role not in ['student', 'tutor', 'teacher']:
                raise EnrollmentValidationError(
                    f"Пользователь '{student.get_full_name()}' не может быть студентом"
                )
            return student
        except User.DoesNotExist:
            raise EnrollmentValidationError(
                f"Студент с ID {student_id} не найден"
            )

    @staticmethod
    def check_duplicate_enrollment(student, subject, teacher):
        """
        Check if enrollment already exists (unique constraint).

        Args:
            student: Student user instance
            subject: Subject instance
            teacher: Teacher user instance

        Returns:
            SubjectEnrollment if exists, None otherwise
        """
        return SubjectEnrollment.objects.filter(
            student=student,
            subject=subject,
            teacher=teacher
        ).first()

    @staticmethod
    def prevent_self_enrollment_as_teacher(student, teacher):
        """
        Prevent self-enrollment (same user cannot be both student and teacher).

        Args:
            student: Student user instance
            teacher: Teacher user instance

        Raises:
            EnrollmentValidationError: If student and teacher are the same
        """
        if student.id == teacher.id:
            raise EnrollmentValidationError(
                "Пользователь не может зачислить сам себя как студента"
            )

    @staticmethod
    @transaction.atomic
    def create_enrollment(student_id, subject_id, teacher_id, assigned_by=None,
                        custom_subject_name=None):
        """
        Create subject enrollment with comprehensive validation.

        Args:
            student_id: Student user ID
            subject_id: Subject ID
            teacher_id: Teacher user ID
            assigned_by: User who assigned the enrollment (optional)
            custom_subject_name: Custom subject name (optional)

        Returns:
            SubjectEnrollment instance

        Raises:
            EnrollmentValidationError: If validation fails
        """
        # Validate all inputs exist
        student = SubjectEnrollmentService.validate_student_exists(student_id)
        subject = SubjectEnrollmentService.validate_subject_exists(subject_id)
        teacher = SubjectEnrollmentService.validate_teacher_exists(teacher_id)

        # Prevent self-enrollment
        SubjectEnrollmentService.prevent_self_enrollment_as_teacher(student, teacher)

        # Check for duplicate enrollment
        existing = SubjectEnrollmentService.check_duplicate_enrollment(
            student, subject, teacher
        )
        if existing:
            raise EnrollmentValidationError(
                f"Студент уже зачислен на предмет '{subject.name}' к преподавателю "
                f"'{teacher.get_full_name()}' (ID: {existing.id})"
            )

        # Validate assigned_by if provided
        if assigned_by:
            if not isinstance(assigned_by, User):
                try:
                    assigned_by = User.objects.get(id=assigned_by)
                except User.DoesNotExist:
                    raise EnrollmentValidationError(
                        f"Пользователь, назначивший зачисление (ID: {assigned_by}), не найден"
                    )

        # Validate custom subject name
        if custom_subject_name:
            custom_subject_name = custom_subject_name.strip()
            if not custom_subject_name:
                custom_subject_name = None
            elif len(custom_subject_name) > 200:
                raise EnrollmentValidationError(
                    "Кастомное название предмета не должно превышать 200 символов"
                )

        # Create enrollment
        try:
            enrollment = SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher,
                assigned_by=assigned_by,
                custom_subject_name=custom_subject_name,
                is_active=True
            )
            return enrollment
        except Exception as e:
            raise EnrollmentValidationError(
                f"Ошибка при создании зачисления: {str(e)}"
            )

    @staticmethod
    @transaction.atomic
    def cancel_enrollment(enrollment_id):
        """
        Cancel enrollment (soft delete - mark as inactive).

        Args:
            enrollment_id: SubjectEnrollment ID

        Returns:
            SubjectEnrollment instance

        Raises:
            EnrollmentValidationError: If enrollment not found
        """
        try:
            enrollment = SubjectEnrollment.objects.get(id=enrollment_id)
        except SubjectEnrollment.DoesNotExist:
            raise EnrollmentValidationError(
                f"Зачисление с ID {enrollment_id} не найдено"
            )

        if not enrollment.is_active:
            raise EnrollmentValidationError(
                f"Зачисление уже неактивно"
            )

        enrollment.is_active = False
        enrollment.save(update_fields=['is_active'])
        return enrollment

    @staticmethod
    @transaction.atomic
    def reactivate_enrollment(enrollment_id):
        """
        Reactivate a previously cancelled enrollment.

        Args:
            enrollment_id: SubjectEnrollment ID

        Returns:
            SubjectEnrollment instance

        Raises:
            EnrollmentValidationError: If enrollment not found
        """
        try:
            enrollment = SubjectEnrollment.objects.get(id=enrollment_id)
        except SubjectEnrollment.DoesNotExist:
            raise EnrollmentValidationError(
                f"Зачисление с ID {enrollment_id} не найдено"
            )

        if enrollment.is_active:
            raise EnrollmentValidationError(
                f"Зачисление уже активно"
            )

        enrollment.is_active = True
        enrollment.save(update_fields=['is_active'])
        return enrollment

    @staticmethod
    def get_student_enrollments(student_id, include_inactive=False):
        """
        Get all enrollments for a student.

        Args:
            student_id: Student user ID
            include_inactive: Include inactive enrollments (default: False)

        Returns:
            QuerySet of SubjectEnrollment instances
        """
        queryset = SubjectEnrollment.objects.filter(student_id=student_id)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset.select_related('subject', 'teacher')

    @staticmethod
    def get_teacher_students(teacher_id, subject_id=None):
        """
        Get all students enrolled with a specific teacher.

        Args:
            teacher_id: Teacher user ID
            subject_id: Optional subject filter

        Returns:
            QuerySet of SubjectEnrollment instances
        """
        queryset = SubjectEnrollment.objects.filter(
            teacher_id=teacher_id,
            is_active=True
        )

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        return queryset.select_related('student', 'subject')
