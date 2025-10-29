from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction

from materials.models import Subject, SubjectEnrollment
from .models import StudentProfile, ParentProfile, TutorStudentCreation
from notifications.notification_service import NotificationService


User = get_user_model()


def _generate_unique_username(base: str) -> str:
    base = base.lower().replace(' ', '')[:20] or 'user'
    suffix = 1
    candidate = base
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@dataclass
class GeneratedCredentials:
    username: str
    password: str


class StudentCreationService:
    """
    Сервис создания ученика и родителя тьютором с генерацией учетных данных
    """

    @staticmethod
    @transaction.atomic
    def create_student_with_parent(
        *,
        tutor: User,
        student_first_name: str,
        student_last_name: str,
        grade: str,
        goal: str = "",
        parent_first_name: str,
        parent_last_name: str,
        parent_email: str = "",
        parent_phone: str = "",
    ) -> Tuple[User, User, GeneratedCredentials, GeneratedCredentials]:
        if tutor.role != User.Role.TUTOR:
            raise PermissionError("Только тьютор может создавать учеников")

        # Генерация учетных данных
        student_username = _generate_unique_username(
            f"{student_first_name}.{student_last_name}"
        )
        parent_username = _generate_unique_username(
            f"parent.{student_last_name}"
        )

        # Для простоты: генерируем пароли как безопасный случайный hash-несекьюрный видимой строкой
        # В реальном проде использовать генератор секретов
        import secrets
        import string
        student_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        parent_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Создаем пользователя ученика
        student_user = User.objects.create(
            username=student_username,
            first_name=student_first_name,
            last_name=student_last_name,
            email="",
            role=User.Role.STUDENT,
            password=make_password(student_password),
            created_by_tutor=tutor,
        )

        # Создаем пользователя родителя
        parent_user = User.objects.create(
            username=parent_username,
            first_name=parent_first_name,
            last_name=parent_last_name,
            email=parent_email or "",
            phone=parent_phone or "",
            role=User.Role.PARENT,
            password=make_password(parent_password),
            created_by_tutor=tutor,
        )

        # Профили
        StudentProfile.objects.create(
            user=student_user,
            grade=grade,
            goal=goal,
            tutor=tutor,
            parent=parent_user,
            generated_username=student_username,
            generated_password=student_password,
        )

        ParentProfile.objects.get_or_create(user=parent_user)
        parent_profile = parent_user.parent_profile
        parent_profile.children.add(student_user)

        # Запись о создании
        TutorStudentCreation.objects.create(
            tutor=tutor,
            student=student_user,
            parent=parent_user,
            student_credentials={"username": student_username, "password": student_password},
            parent_credentials={"username": parent_username, "password": parent_password},
        )

        # Уведомление тьютора о создании ученика
        try:
            NotificationService().notify_student_created(tutor=tutor, student=student_user)
        except Exception:
            pass

        return (
            student_user,
            parent_user,
            GeneratedCredentials(student_username, student_password),
            GeneratedCredentials(parent_username, parent_password),
        )


class SubjectAssignmentService:
    """
    Сервис управления назначениями предметов для ученика тьютором
    """

    @staticmethod
    def get_available_teachers(subject: Subject):
        """Возвращает список доступных преподавателей для предмета.
        Пока что возвращаем всех пользователей с ролью TEACHER.
        В будущем можно учитывать нагрузку/календарь/скилы.
        """
        return User.objects.filter(role=User.Role.TEACHER).order_by('id')

    @staticmethod
    def assign_subject(*, tutor: User, student: User, subject: Subject, teacher: User | None = None) -> SubjectEnrollment:
        if tutor.role != User.Role.TUTOR:
            raise PermissionError("Только тьютор может назначать предметы")
        # Валидация ролей
        if student.role != User.Role.STUDENT:
            raise ValueError("Указанный пользователь не является студентом")
        if teacher is not None and teacher.role != User.Role.TEACHER:
            raise ValueError("Указанный пользователь не является преподавателем")

        # Проверка, что данный студент привязан к этому тьютору
        try:
            if student.student_profile.tutor_id != tutor.id:
                raise PermissionError("Студент не принадлежит тьютору")
        except StudentProfile.DoesNotExist:
            raise ValueError("Профиль студента не найден")

        # Если преподаватель не указан — подберем автоматически первого доступного
        if teacher is None:
            teacher = SubjectAssignmentService.get_available_teachers(subject).first()
            if teacher is None:
                raise ValueError("Нет доступных преподавателей для назначения")

        enrollment, _ = SubjectEnrollment.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={"teacher": teacher, "assigned_by": tutor, "is_active": True},
        )

        # Если существовало и поменялся преподаватель — обновим
        if enrollment.teacher_id != teacher.id:
            enrollment.teacher = teacher
            enrollment.assigned_by = tutor
            enrollment.is_active = True
            enrollment.save()

        # Уведомления студенту и преподавателю о назначении предмета
        try:
            service = NotificationService()
            service.notify_subject_assigned(student=student, subject_id=subject.id, teacher=teacher)
            service.send(
                recipient=teacher,
                notif_type='subject_assigned',
                title='Назначен студент по предмету',
                message=f"Вам назначен студент {student.get_full_name() or student.username} по предмету {subject.name}.",
                data={'student_id': student.id, 'subject_id': subject.id},
            )
        except Exception:
            pass

        return enrollment

    @staticmethod
    def unassign_subject(*, tutor: User, student: User, subject: Subject) -> None:
        if tutor.role != User.Role.TUTOR:
            raise PermissionError("Только тьютор может отменять назначения")
        try:
            enrollment = SubjectEnrollment.objects.get(student=student, subject=subject)
        except SubjectEnrollment.DoesNotExist:
            return
        # Разрешаем только для своих студентов
        try:
            if enrollment.student.student_profile.tutor_id != tutor.id:
                raise PermissionError("Студент не принадлежит тьютору")
        except StudentProfile.DoesNotExist:
            raise ValueError("Профиль студента не найден")
        enrollment.is_active = False
        enrollment.save()


