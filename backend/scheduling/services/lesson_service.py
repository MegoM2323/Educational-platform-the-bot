"""
Lesson management service with business logic.

Handles lesson creation, retrieval, updates, and deletion with validation.
"""

from typing import List, Optional, Dict, Any
from datetime import timedelta, datetime, date, time
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from uuid import UUID

from scheduling.models import Lesson, LessonHistory
from materials.models import SubjectEnrollment

User = get_user_model()


class LessonService:
    """Service layer for lesson management with business logic."""

    @staticmethod
    def _check_time_conflicts(
        date: date,
        start_time: time,
        end_time: time,
        teacher: Optional[User] = None,
        student: Optional[User] = None,
        exclude_lesson_id: Optional[UUID] = None
    ) -> None:
        """
        Check for overlapping lessons for teacher or student.

        Args:
            date: lesson date
            start_time, end_time: lesson time range
            teacher: teacher to check for conflicts
            student: student to check for conflicts
            exclude_lesson_id: lesson to exclude from check (for updates)

        Raises:
            ValidationError if conflicts found
        """
        # Combine datetime для точной проверки пересечений
        dt_start = datetime.combine(date, start_time)
        dt_end = datetime.combine(date, end_time)

        # Base queryset - уроки в тот же день, не отменённые
        base_qs = Lesson.objects.filter(
            date=date,
            status__in=['pending', 'confirmed']
        )
        if exclude_lesson_id:
            base_qs = base_qs.exclude(id=exclude_lesson_id)

        # Проверка конфликтов для преподавателя
        if teacher:
            teacher_conflicts = base_qs.filter(teacher=teacher)
            for existing in teacher_conflicts:
                dt_existing_start = datetime.combine(existing.date, existing.start_time)
                dt_existing_end = datetime.combine(existing.date, existing.end_time)

                # Проверка пересечения: new.start < existing.end AND new.end > existing.start
                if dt_start < dt_existing_end and dt_end > dt_existing_start:
                    raise ValidationError(
                        f'Преподаватель {teacher.get_full_name()} уже занят с '
                        f'{existing.start_time.strftime("%H:%M")} до '
                        f'{existing.end_time.strftime("%H:%M")} в этот день.'
                    )

        # Проверка конфликтов для студента
        if student:
            student_conflicts = base_qs.filter(student=student)
            for existing in student_conflicts:
                dt_existing_start = datetime.combine(existing.date, existing.start_time)
                dt_existing_end = datetime.combine(existing.date, existing.end_time)

                if dt_start < dt_existing_end and dt_end > dt_existing_start:
                    raise ValidationError(
                        f'Ученик {student.get_full_name()} уже запланирован на '
                        f'{existing.start_time.strftime("%H:%M")}-'
                        f'{existing.end_time.strftime("%H:%M")} в этот день '
                        f'(предмет {existing.subject.name} с '
                        f'{existing.teacher.get_full_name()}).'
                    )

    @staticmethod
    @transaction.atomic
    def create_lesson(
        teacher: User,
        student: User,
        subject: 'Subject',
        date,
        start_time,
        end_time,
        description: str = '',
        telemost_link: str = '',
    ) -> Lesson:
        """
        Create a new lesson with validation.

        Args:
            teacher: Teacher user instance
            student: Student user instance
            subject: Subject instance
            date: Lesson date (DateField)
            start_time: Lesson start time (TimeField)
            end_time: Lesson end time (TimeField)
            description: Optional lesson description
            telemost_link: Optional Yandex Telemost link

        Returns:
            Created Lesson instance

        Raises:
            ValidationError: If validation fails
        """
        # Validate teacher role
        if teacher.role != 'teacher':
            raise ValidationError('Only users with teacher role can create lessons')

        # Validate student role
        if student.role != 'student':
            raise ValidationError('Only users with student role can be enrolled in lessons')

        # Validate time range
        if start_time >= end_time:
            raise ValidationError('Start time must be before end time')

        # Validate date not in past
        if date < timezone.now().date():
            raise ValidationError('Cannot create lesson in the past')

        # Validate teacher teaches subject to student (via SubjectEnrollment)
        try:
            SubjectEnrollment.objects.get(
                student=student,
                teacher=teacher,
                subject=subject,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            raise ValidationError(
                f'Teacher {teacher.get_full_name()} does not teach '
                f'{subject.name} to student {student.get_full_name()}'
            )

        # Check for time conflicts
        LessonService._check_time_conflicts(
            date=date,
            start_time=start_time,
            end_time=end_time,
            teacher=teacher,
            student=student
        )

        # Create lesson
        lesson = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=subject,
            date=date,
            start_time=start_time,
            end_time=end_time,
            description=description,
            telemost_link=telemost_link,
            status='pending'
        )

        # Record in history
        LessonHistory.objects.create(
            lesson=lesson,
            action='created',
            performed_by=teacher,
            new_values={
                'date': str(date),
                'start_time': str(start_time),
                'end_time': str(end_time),
                'student': student.get_full_name(),
                'subject': subject.name,
            }
        )

        return lesson

    @staticmethod
    def get_teacher_lessons(
        teacher: User,
        filters: Optional[Dict[str, Any]] = None
    ) -> 'QuerySet[Lesson]':
        """
        Get all lessons created by a teacher.

        Args:
            teacher: Teacher user instance
            filters: Optional dict with filters:
                - date_from: Start date
                - date_to: End date
                - subject_id: Filter by subject
                - status: Filter by status

        Returns:
            Optimized QuerySet of lessons
        """
        queryset = Lesson.objects.filter(teacher=teacher).select_related(
            'teacher', 'student', 'subject'
        ).order_by('date', 'start_time')

        if filters:
            if 'date_from' in filters and filters['date_from']:
                queryset = queryset.filter(date__gte=filters['date_from'])

            if 'date_to' in filters and filters['date_to']:
                queryset = queryset.filter(date__lte=filters['date_to'])

            if 'subject_id' in filters and filters['subject_id']:
                queryset = queryset.filter(subject_id=filters['subject_id'])

            if 'status' in filters and filters['status']:
                queryset = queryset.filter(status=filters['status'])

        return queryset

    @staticmethod
    def get_student_lessons(
        student: User,
        filters: Optional[Dict[str, Any]] = None
    ) -> 'QuerySet[Lesson]':
        """
        Get all lessons for a student.

        Args:
            student: Student user instance
            filters: Optional dict with filters:
                - date_from: Start date
                - date_to: End date
                - subject_id: Filter by subject
                - teacher_id: Filter by teacher
                - status: Filter by status

        Returns:
            Optimized QuerySet of lessons
        """
        queryset = Lesson.objects.filter(student=student).select_related(
            'teacher', 'student', 'subject'
        ).order_by('date', 'start_time')

        if filters:
            if 'date_from' in filters and filters['date_from']:
                queryset = queryset.filter(date__gte=filters['date_from'])

            if 'date_to' in filters and filters['date_to']:
                queryset = queryset.filter(date__lte=filters['date_to'])

            if 'subject_id' in filters and filters['subject_id']:
                queryset = queryset.filter(subject_id=filters['subject_id'])

            if 'teacher_id' in filters and filters['teacher_id']:
                queryset = queryset.filter(teacher_id=filters['teacher_id'])

            if 'status' in filters and filters['status']:
                queryset = queryset.filter(status=filters['status'])

        return queryset

    @staticmethod
    def get_tutor_student_lessons(tutor: User, student_id: int) -> 'QuerySet[Lesson]':
        """
        Get all lessons for a student (tutor view).

        Validates that tutor manages the student.

        Args:
            tutor: Tutor user instance
            student_id: Student user ID

        Returns:
            Optimized QuerySet of lessons

        Raises:
            ValidationError: If tutor doesn't manage the student
        """
        # Verify tutor manages student
        from accounts.models import StudentProfile

        try:
            StudentProfile.objects.get(user_id=student_id, tutor=tutor)
        except StudentProfile.DoesNotExist:
            raise ValidationError(f'You do not manage this student')

        return Lesson.objects.filter(student_id=student_id).select_related(
            'teacher', 'student', 'subject'
        ).order_by('date', 'start_time')

    @staticmethod
    @transaction.atomic
    def update_lesson(
        lesson: Lesson,
        updates: Dict[str, Any],
        user: User
    ) -> Lesson:
        """
        Update a lesson with validation.

        Can only edit lessons that haven't started yet.

        Args:
            lesson: Lesson instance to update
            updates: Dict with fields to update
            user: User making the update

        Returns:
            Updated Lesson instance

        Raises:
            ValidationError: If update is not allowed
        """
        # Verify user is the teacher who created the lesson
        if lesson.teacher != user:
            raise ValidationError('Only the teacher who created the lesson can update it')

        # Can't edit past or current lessons (before start time + some buffer)
        if lesson.date < timezone.now().date():
            raise ValidationError('Cannot update past lessons')

        if lesson.date == timezone.now().date():
            # If lesson is today, check time
            if lesson.datetime_start <= timezone.now():
                raise ValidationError('Cannot update lesson that has already started')

        # Save old values for history
        old_values = {}
        new_values = {}

        # Define allowed fields to update
        allowed_fields = ['date', 'start_time', 'end_time', 'description', 'telemost_link', 'status']

        # Check if date/time changed for conflict detection
        date_time_changed = any(field in updates for field in ['date', 'start_time', 'end_time'])

        for field, value in updates.items():
            if field not in allowed_fields:
                continue

            old_value = getattr(lesson, field)
            old_values[field] = str(old_value)
            new_values[field] = str(value)
            setattr(lesson, field, value)

        # If date/time changed, check for conflicts
        if date_time_changed:
            LessonService._check_time_conflicts(
                date=lesson.date,
                start_time=lesson.start_time,
                end_time=lesson.end_time,
                teacher=lesson.teacher,
                student=lesson.student,
                exclude_lesson_id=lesson.id
            )

        # Validate after setting values
        lesson.full_clean()

        lesson.save()

        # Record in history
        if old_values:
            LessonHistory.objects.create(
                lesson=lesson,
                action='updated',
                performed_by=user,
                old_values=old_values,
                new_values=new_values
            )

        return lesson

    @staticmethod
    @transaction.atomic
    def delete_lesson(lesson: Lesson, user: User) -> None:
        """
        Delete (cancel) a lesson.

        Only teacher can delete. Must be at least 2 hours before lesson.

        Args:
            lesson: Lesson instance to delete
            user: User making the deletion

        Raises:
            ValidationError: If deletion is not allowed
        """
        # Verify user is the teacher who created the lesson
        if lesson.teacher != user:
            raise ValidationError('Only the teacher who created the lesson can cancel it')

        # Check 2-hour rule
        if not lesson.can_cancel:
            raise ValidationError('Lessons cannot be cancelled less than 2 hours before start time')

        # Mark as cancelled and record history
        old_status = lesson.status
        lesson.status = 'cancelled'
        lesson.save()

        LessonHistory.objects.create(
            lesson=lesson,
            action='cancelled',
            performed_by=user,
            old_values={'status': old_status},
            new_values={'status': 'cancelled'}
        )

    @staticmethod
    def get_upcoming_lessons(user: User, limit: int = 3) -> 'QuerySet[Lesson]':
        """
        Get upcoming lessons for a user (role-aware).

        Args:
            user: User instance
            limit: Max number of lessons to return

        Returns:
            QuerySet of upcoming lessons
        """
        now = timezone.now()

        if user.role == 'teacher':
            queryset = Lesson.objects.filter(
                teacher=user,
                date__gte=now.date(),
                status__in=['pending', 'confirmed']
            )
        elif user.role == 'student':
            queryset = Lesson.objects.filter(
                student=user,
                date__gte=now.date(),
                status__in=['pending', 'confirmed']
            )
        elif user.role == 'tutor':
            # Get lessons for managed students
            from accounts.models import StudentProfile

            student_ids = StudentProfile.objects.filter(
                tutor=user
            ).values_list('user_id', flat=True)

            queryset = Lesson.objects.filter(
                student_id__in=student_ids,
                date__gte=now.date(),
                status__in=['pending', 'confirmed']
            )
        elif user.role == 'parent':
            # Get lessons for parent's children
            from accounts.models import StudentProfile

            children_ids = StudentProfile.objects.filter(
                parent=user
            ).values_list('user_id', flat=True)

            queryset = Lesson.objects.filter(
                student_id__in=children_ids,
                date__gte=now.date(),
                status__in=['pending', 'confirmed']
            )
        else:
            return Lesson.objects.none()

        return queryset.select_related(
            'teacher', 'student', 'subject'
        ).order_by('date', 'start_time')[:limit]
