from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction

from .models import StudentProfile, ParentProfile, TutorStudentCreation
from notifications.notification_service import NotificationService


logger = logging.getLogger(__name__)
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
        # Разрешаем создание учеников тьюторам или администраторам
        if tutor.role != User.Role.TUTOR and not (tutor.is_staff or tutor.is_superuser):
            raise PermissionError("Только тьютор или администратор может создавать учеников")

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
            role=User.Role.STUDENT,  # Явно устанавливаем роль STUDENT
            password=make_password(student_password),
            created_by_tutor=tutor,
            is_active=True,
        )
        logger.info(f"Student user created: {student_user.username}, role: {student_user.role}, id: {student_user.id}")

        # Создаем пользователя родителя
        parent_user = User.objects.create(
            username=parent_username,
            first_name=parent_first_name,
            last_name=parent_last_name,
            email=parent_email or "",
            phone=parent_phone or "",
            role=User.Role.PARENT,  # Явно устанавливаем роль PARENT
            password=make_password(parent_password),
            created_by_tutor=tutor,
            is_active=True,
        )
        logger.info(f"Parent user created: {parent_user.username}, role: {parent_user.role}, id: {parent_user.id}")

        # Профили
        # Всегда устанавливаем tutor в профиле, если ученика создает пользователь через функционал тьютора
        # Это обеспечивает правильную связь между тьютором и учеником
        student_profile = StudentProfile.objects.create(
            user=student_user,
            grade=grade,
            goal=goal,
            tutor=tutor,  # Всегда устанавливаем создателя как тьютора
            parent=parent_user,
            generated_username=student_username,
            generated_password=student_password,
        )
        logger.info(f"StudentProfile created: id={student_profile.id}, student={student_user.username}, tutor={tutor.username}")

        # КРИТИЧНО: Проверяем, что parent установлен
        if student_profile.parent is None:
            error_msg = (
                f"CRITICAL: StudentProfile.parent must be set for proper dashboard visibility. "
                f"StudentProfile.id={student_profile.id}, student={student_user.username}, "
                f"parent_user.id={parent_user.id if parent_user else None}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Логируем успешное установление связи
        logger.info(
            f"StudentProfile.parent validated: parent_id={student_profile.parent_id}, "
            f"parent_username={student_profile.parent.username}"
        )

        # Создаем ParentProfile
        parent_profile, created = ParentProfile.objects.get_or_create(user=parent_user)
        logger.info(f"ParentProfile {'created' if created else 'retrieved'}: id={parent_profile.id}, user={parent_user.username}")

        # КРИТИЧНО: Проверяем, что ParentProfile создан успешно
        if not parent_profile:
            error_msg = (
                f"CRITICAL: ParentProfile creation failed. "
                f"parent_user.id={parent_user.id}, parent_user.username={parent_user.username}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверяем связь после создания
        children_count = User.objects.filter(student_profile__parent=parent_user, role=User.Role.STUDENT).count()
        logger.info(f"Parent-student relationship verified: parent={parent_user.username} has {children_count} child(ren)")

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
    def get_available_teachers(subject: 'materials.Subject'):
        """Возвращает список доступных преподавателей для предмета.
        Сначала проверяем связь через TeacherSubject, если нет - возвращаем всех преподавателей.
        """
        from materials.models import TeacherSubject, Subject
        
        # Ищем преподавателей, которые ведут этот предмет
        teacher_ids_list = list(TeacherSubject.objects.filter(
            subject=subject,
            is_active=True
        ).values_list('teacher_id', flat=True))
        
        if teacher_ids_list:
            # Если есть преподаватели, которые ведут предмет, возвращаем их
            return User.objects.filter(id__in=teacher_ids_list, role=User.Role.TEACHER, is_active=True).order_by('id')
        else:
            # Если предмет новый или нет связи, возвращаем всех активных преподавателей
            return User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by('id')
    
    @staticmethod
    def get_or_create_subject(subject_name: str) -> 'materials.Subject':
        """Получает существующий предмет по названию или создает новый.

        Args:
            subject_name: Название предмета (должно быть уже валидировано и обрезано)

        Returns:
            Существующий или созданный предмет
        """
        from materials.models import Subject

        if not subject_name or not subject_name.strip():
            raise ValueError("Название предмета не может быть пустым")

        subject_name = subject_name.strip()

        # Ищем предмет по названию (без учета регистра)
        subject = Subject.objects.filter(name__iexact=subject_name).first()
        
        if not subject:
            # Создаем новый предмет с дефолтным цветом
            subject = Subject.objects.create(
                name=subject_name,
                description=f"Предмет '{subject_name}' создан тьютором",
                color='#3B82F6'  # Дефолтный синий цвет
            )
        
        return subject

    @staticmethod
    def assign_subject(*, tutor: User, student: User, subject: 'materials.Subject', teacher: User | None = None) -> 'materials.SubjectEnrollment':
        from materials.models import SubjectEnrollment

        # Разрешаем назначение предметов тьюторам или администраторам
        if tutor.role != User.Role.TUTOR and not (tutor.is_staff or tutor.is_superuser):
            raise PermissionError("Только тьютор или администратор может назначать предметы")
        # Валидация ролей
        if student.role != User.Role.STUDENT:
            raise ValueError("Указанный пользователь не является студентом")
        
        # Проверка, что данный студент привязан к этому тьютору
        # Проверяем через tutor в профиле студента ИЛИ через created_by_tutor в User
        # Используем OR логику: если студент назначен в профиле ИЛИ создан тьютором, разрешаем

        # Проверка через StudentProfile.tutor
        is_assigned_via_profile = False
        try:
            profile = student.student_profile
            is_assigned_via_profile = profile.tutor_id == tutor.id
        except StudentProfile.DoesNotExist:
            # Профиль может не существовать, это нормально, проверим created_by_tutor
            is_assigned_via_profile = False

        # Проверка через User.created_by_tutor
        is_created_by_tutor = student.created_by_tutor_id == tutor.id

        # Студент принадлежит тьютору, если выполнено ИЛИ условие
        if not (is_assigned_via_profile or is_created_by_tutor):
            raise PermissionError("Студент не принадлежит тьютору")

        # Если преподаватель указан, проверяем его
        if teacher is not None:
            if teacher.role != User.Role.TEACHER:
                raise ValueError("Указанный пользователь не является преподавателем")
            if not teacher.is_active:
                raise ValueError("Указанный преподаватель неактивен")
            
            # Примечание: мы не проверяем связь TeacherSubject здесь, так как тьютор
            # может назначить любого активного преподавателя любому студенту.
            # Если требуется проверка, что преподаватель ведет предмет, это можно
            # добавить в будущем, но пока оставляем гибкость для тьютора.
        
        # Преподаватель обязателен
        if teacher is None:
            raise ValueError("Необходимо указать преподавателя")
        
        # Проверяем, не существует ли уже такое зачисление (включая неактивные)
        # unique_together гарантирует, что может быть только одно зачисление для student+subject+teacher
        # Используем get_or_create для атомарности операции с обработкой race condition
        from django.db import IntegrityError
        
        try:
            enrollment, created = SubjectEnrollment.objects.get_or_create(
                student=student,
                subject=subject,
                teacher=teacher,
                defaults={
                    'assigned_by': tutor,
                    'is_active': True,
                }
            )

            # Если зачисление уже существовало, обновляем его
            if not created:
                enrollment.assigned_by = tutor
                enrollment.is_active = True  # Активируем, если было деактивировано
                enrollment.save(update_fields=['assigned_by', 'is_active'])

            logger.info(
                f"Enrollment {'created' if created else 'updated'}: id={enrollment.id}, "
                f"student_id={student.id}, subject_id={subject.id}, teacher_id={teacher.id}, "
                f"is_active={enrollment.is_active}"
            )

            # Принудительно перезагружаем enrollment из базы для гарантии актуальных данных
            enrollment.refresh_from_db()

        except IntegrityError:
            # В случае race condition, пытаемся получить существующее зачисление и обновить
            try:
                enrollment = SubjectEnrollment.objects.get(
                    student=student,
                    subject=subject,
                    teacher=teacher
                )
                enrollment.assigned_by = tutor
                enrollment.is_active = True
                enrollment.save(update_fields=['assigned_by', 'is_active'])
                enrollment.refresh_from_db()
                logger.info(f"Enrollment updated after IntegrityError: id={enrollment.id}")
            except SubjectEnrollment.DoesNotExist:
                # Если даже после IntegrityError объект не найден, это странно, но обрабатываем
                raise ValueError("Не удалось создать или обновить зачисление из-за конфликта данных")

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
    def unassign_subject(*, tutor: User, student: User, subject: 'materials.Subject') -> None:
        from materials.models import SubjectEnrollment
        # Разрешаем отмену назначений тьюторам или администраторам
        if tutor.role != User.Role.TUTOR and not (tutor.is_staff or tutor.is_superuser):
            raise PermissionError("Только тьютор или администратор может отменять назначения")
        try:
            enrollment = SubjectEnrollment.objects.get(student=student, subject=subject)
        except SubjectEnrollment.DoesNotExist:
            return
        # Разрешаем только для своих студентов
        # Проверяем через tutor в профиле студента ИЛИ через created_by_tutor в User
        # Используем OR логику: если студент назначен в профиле ИЛИ создан тьютором, разрешаем

        # Проверка через StudentProfile.tutor
        is_assigned_via_profile = False
        try:
            profile = enrollment.student.student_profile
            is_assigned_via_profile = profile.tutor_id == tutor.id
        except StudentProfile.DoesNotExist:
            # Профиль может не существовать, это нормально, проверим created_by_tutor
            is_assigned_via_profile = False

        # Проверка через User.created_by_tutor
        is_created_by_tutor = enrollment.student.created_by_tutor_id == tutor.id

        # Студент принадлежит тьютору, если выполнено ИЛИ условие
        if not (is_assigned_via_profile or is_created_by_tutor):
            raise PermissionError("Студент не принадлежит тьютору")
        enrollment.is_active = False
        enrollment.save()


