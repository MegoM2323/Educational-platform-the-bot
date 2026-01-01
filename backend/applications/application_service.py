import secrets
import string
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Tuple, Optional
import logging

from .models import Application
from .notification_service import telegram_notification_service
from accounts.models import StudentProfile, TeacherProfile, ParentProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class ApplicationService:
    """
    Сервис для обработки жизненного цикла заявок
    Обрабатывает создание пользователей и отправку учетных данных
    """

    def __init__(self):
        self.notification_service = telegram_notification_service

    def approve_application(self, application: Application, admin_user) -> bool:
        """
        Одобряет заявку и создает пользовательские аккаунты

        Args:
            application: Объект заявки
            admin_user: Администратор, одобряющий заявку

        Returns:
            True если успешно, False в случае ошибки
        """
        if application.status != Application.Status.PENDING:
            logger.error(f"Заявка #{application.id} уже обработана")
            return False

        try:
            with transaction.atomic():
                username, password = self._generate_credentials(application)
                user = self._create_user(application, username, password)
                application.generated_username = username

                parent_user = None
                parent_password = ""
                if application.applicant_type == Application.ApplicantType.STUDENT:
                    parent_user, parent_password = self._create_parent_user(
                        application, user
                    )

                application.status = Application.Status.APPROVED
                application.processed_by = admin_user
                application.processed_at = timezone.now()
                application.save()

                self._send_credentials_via_telegram(
                    application, user, password, parent_user, parent_password
                )

                logger.info(
                    f"Заявка #{application.id} успешно одобрена и аккаунты созданы"
                )
                return True

        except Exception as e:
            logger.error(f"Ошибка при одобрении заявки #{application.id}: {e}")
            return False

    def reject_application(
        self, application: Application, admin_user, reason: str = None
    ) -> bool:
        """
        Отклоняет заявку

        Args:
            application: Объект заявки
            admin_user: Администратор, отклоняющий заявку
            reason: Причина отклонения

        Returns:
            True если успешно, False в случае ошибки
        """
        if application.status != Application.Status.PENDING:
            logger.error(f"Заявка #{application.id} уже обработана")
            return False

        try:
            with transaction.atomic():
                # Обновляем статус заявки
                application.status = Application.Status.REJECTED
                application.processed_by = admin_user
                application.processed_at = timezone.now()
                if reason:
                    application.notes = reason
                application.save()

                # Отправляем уведомление об отклонении
                if application.telegram_id:
                    self.notification_service.send_application_status(
                        application.telegram_id, Application.Status.REJECTED, reason
                    )

                logger.info(f"Заявка #{application.id} отклонена")
                return True

        except Exception as e:
            logger.error(f"Ошибка при отклонении заявки #{application.id}: {e}")
            return False

    def _generate_credentials(self, application: Application) -> Tuple[str, str]:
        """
        Генерирует имя пользователя и пароль

        Args:
            application: Объект заявки

        Returns:
            Кортеж (username, password)
        """
        # Генерируем имя пользователя на основе имени и фамилии
        base_username = (
            f"{application.first_name.lower()}.{application.last_name.lower()}"
        )
        # Убираем специальные символы и заменяем пробелы
        base_username = "".join(c for c in base_username if c.isalnum() or c == ".")

        # Проверяем уникальность и добавляем номер если нужно
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Генерируем безопасный пароль
        password = self._generate_password()

        return username, password

    def _generate_password(self, length: int = 12) -> str:
        """
        Генерирует безопасный пароль

        Args:
            length: Длина пароля

        Returns:
            Сгенерированный пароль
        """
        # Используем буквы, цифры и некоторые специальные символы
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(characters) for _ in range(length))

        # Убеждаемся, что пароль содержит хотя бы одну цифру и одну букву
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)
        if not any(c.isalpha() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_letters)

        return password

    def _create_user(
        self, application: Application, username: str, password: str
    ) -> User:
        """
        Создает пользователя на основе заявки

        Args:
            application: Объект заявки
            username: Имя пользователя
            password: Пароль

        Returns:
            Созданный пользователь
        """
        # Определяем роль пользователя
        role_mapping = {
            Application.ApplicantType.STUDENT: User.Role.STUDENT,
            Application.ApplicantType.TEACHER: User.Role.TEACHER,
            Application.ApplicantType.PARENT: User.Role.PARENT,
        }

        role = role_mapping.get(application.applicant_type, User.Role.STUDENT)

        # Создаем пользователя
        user = User.objects.create_user(
            username=username,
            email=application.email,
            password=password,
            first_name=application.first_name,
            last_name=application.last_name,
            phone=application.phone,
            role=role,
            is_verified=True,  # Автоматически подтверждаем пользователей из заявок
        )

        # Создаем профиль в зависимости от роли
        self._create_user_profile(user, application)

        logger.info(f"Создан пользователь {username} с ролью {role}")
        return user

    def _create_user_profile(self, user: User, application: Application):
        """
        Создает профиль пользователя в зависимости от роли

        Args:
            user: Пользователь
            application: Заявка
        """
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(
                user=user,
                grade=application.grade or "1",
                goal=application.motivation or "",
            )
        elif user.role == User.Role.TEACHER:
            TeacherProfile.objects.create(
                user=user,
                subject=application.subject or "",
                bio=application.experience or "",
            )
        elif user.role == User.Role.PARENT:
            ParentProfile.objects.create(user=user)

    def _create_parent_user(
        self, application: Application, student_user: User
    ) -> Tuple[Optional[User], str]:
        """
        Создает родительский аккаунт для студента

        Args:
            application: Заявка студента
            student_user: Пользователь-студент

        Returns:
            Кортеж (родительский пользователь или None, пароль)
        """
        if not all(
            [
                application.parent_first_name,
                application.parent_last_name,
                application.parent_email,
            ]
        ):
            logger.warning(
                f"Недостаточно данных для создания родительского аккаунта для заявки #{application.id}"
            )
            return None, ""

        try:
            parent_username, parent_password = self._generate_parent_credentials(
                application
            )

            parent_user = User.objects.create_user(
                username=parent_username,
                email=application.parent_email,
                password=parent_password,
                first_name=application.parent_first_name,
                last_name=application.parent_last_name,
                phone=application.parent_phone or "",
                role=User.Role.PARENT,
                is_verified=True,
            )

            parent_profile = ParentProfile.objects.create(user=parent_user)
            if hasattr(student_user, "student_profile"):
                student_user.student_profile.parent = parent_user
                student_user.student_profile.save()

            application.parent_username = parent_username

            logger.info(
                f"Создан родительский аккаунт {parent_username} для студента {student_user.username}"
            )
            return parent_user, parent_password

        except Exception as e:
            logger.error(f"Ошибка при создании родительского аккаунта: {e}")
            return None, ""

    def _generate_parent_credentials(self, application: Application) -> Tuple[str, str]:
        """
        Генерирует учетные данные для родителя

        Args:
            application: Заявка

        Returns:
            Кортеж (username, password)
        """
        # Генерируем имя пользователя для родителя
        base_username = f"{application.parent_first_name.lower()}.{application.parent_last_name.lower()}.parent"
        base_username = "".join(c for c in base_username if c.isalnum() or c == ".")

        # Проверяем уникальность
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Генерируем пароль
        password = self._generate_password()

        return username, password

    def _send_credentials_via_telegram(
        self,
        application: Application,
        user: User,
        password: str,
        parent_user: Optional[User] = None,
        parent_password: str = "",
    ):
        """
        Отправляет учетные данные через Telegram

        Args:
            application: Заявка
            user: Основной пользователь
            password: Пароль пользователя (не хранится в БД)
            parent_user: Родительский пользователь (если есть)
            parent_password: Пароль родителя (не хранится в БД)
        """
        try:
            if application.telegram_id:
                self.notification_service.send_credentials(
                    application.telegram_id,
                    application.generated_username,
                    password,
                    user.role,
                    child_name=f"{application.first_name} {application.last_name}"
                    if parent_user
                    else None,
                )
                logger.info(
                    f"Учетные данные отправлены пользователю {application.telegram_id}"
                )

            if parent_user and application.parent_telegram_id and parent_password:
                self.notification_service.send_parent_link(
                    application.parent_telegram_id,
                    application.parent_username,
                    parent_password,
                    f"{application.first_name} {application.last_name}",
                )
                logger.info(
                    f"Родительские учетные данные отправлены {application.parent_telegram_id}"
                )

        except Exception as e:
            logger.error(f"Ошибка при отправке учетных данных через Telegram: {e}")


# Создаем экземпляр сервиса
application_service = ApplicationService()
