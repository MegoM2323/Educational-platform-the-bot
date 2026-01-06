from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
import logging
from .models import (
    SubjectEnrollment,
    SubjectPayment,
    SubjectSubscription,
    MaterialProgress,
    Material,
    Subject,
)
from notifications.notification_service import NotificationService
from payments.models import Payment
from .cache_utils import cache_dashboard_data, DashboardCacheManager

logger = logging.getLogger(__name__)

User = get_user_model()


class ParentDashboardService:
    """
    Сервис для работы с дашбордом родителя
    """

    def __init__(self, parent_user, request=None):
        """
        Инициализация сервиса для конкретного родителя

        Args:
            parent_user: Пользователь с ролью PARENT
            request: HTTP request для формирования абсолютных URL (опционально)
        """
        self.request = request

        if not parent_user:
            logger.error("[ParentDashboardService] parent_user is None")
            raise ValueError("Пользователь должен иметь роль PARENT")

        # Логируем информацию о пользователе для отладки
        logger.info(
            f"[ParentDashboardService] Initializing for user: {parent_user.username}"
        )
        logger.info(
            f"[ParentDashboardService] User role: {parent_user.role}, type: {type(parent_user.role)}"
        )
        logger.info(
            f"[ParentDashboardService] User.Role.PARENT: {User.Role.PARENT}, type: {type(User.Role.PARENT)}"
        )
        logger.info(
            f"[ParentDashboardService] Role comparison: {parent_user.role == User.Role.PARENT}"
        )

        # Проверяем роль (поддерживаем как строку, так и enum)
        # User.Role.PARENT возвращает 'parent' (строка), а parent_user.role тоже строка
        # Нормализуем роль для сравнения
        user_role = parent_user.role
        if hasattr(user_role, "value"):
            user_role_str = user_role.value
        else:
            user_role_str = str(user_role).lower()

        parent_role_str = (
            User.Role.PARENT.value
            if hasattr(User.Role.PARENT, "value")
            else str(User.Role.PARENT).lower()
        )

        # Разрешаем доступ родителям или администраторам, которые создали детей
        is_parent = user_role_str == parent_role_str

        # Для администраторов проверяем, создали ли они детей (через created_by_tutor) или являются родителями
        is_admin_with_children = (
            parent_user.is_staff or parent_user.is_superuser
        ) and (
            User.objects.filter(
                student_profile__parent=parent_user, role=User.Role.STUDENT
            ).exists()
            or User.objects.filter(
                created_by_tutor=parent_user, role=User.Role.STUDENT
            ).exists()
        )

        if not is_parent and not is_admin_with_children:
            logger.error(
                f"[ParentDashboardService] User {parent_user.username} has role '{parent_user.role}' (type: {type(parent_user.role)}), expected '{User.Role.PARENT}' (type: {type(User.Role.PARENT)})"
            )
            logger.error(
                f"[ParentDashboardService] Normalized: user_role_str='{user_role_str}', parent_role_str='{parent_role_str}', is_parent={is_parent}, is_admin_with_children={is_admin_with_children}"
            )
            raise ValueError(
                f"Пользователь должен иметь роль PARENT или быть администратором с созданными детьми. Текущая роль: {parent_user.role}"
            )

        self.parent_user = parent_user
        # Создаем ParentProfile, если его нет
        from accounts.models import ParentProfile

        self.parent_profile, created = ParentProfile.objects.get_or_create(
            user=parent_user
        )
        if created:
            logger.info(f"Создан ParentProfile для пользователя {parent_user.username}")

    def _build_file_url(self, file_field):
        """Формирует абсолютный URL для файла"""
        if not file_field:
            return None
        if self.request:
            return self.request.build_absolute_uri(file_field.url)
        return file_field.url

    def _has_active_subscription(self, enrollment):
        """Проверяет, есть ли у зачисления активная подписка"""
        try:
            # Используем getattr для безопасного доступа к related объекту
            subscription = getattr(enrollment, "subscription", None)
            if subscription:
                return (
                    subscription.status == SubjectSubscription.Status.ACTIVE
                    and subscription.expires_at >= timezone.now()
                )
        except Exception:
            # Если произошла любая ошибка (например, DoesNotExist), возвращаем False
            pass
        return False

    def get_children(self):
        """
        Получить список детей родителя

        Returns:
            QuerySet: Список детей пользователя
        """
        logger.info(
            f"[get_children] Getting children for parent: {self.parent_user.username} (id: {self.parent_user.id}, role: {self.parent_user.role})"
        )

        # Если пользователь - родитель, используем ParentProfile.children
        # Если пользователь - администратор, ищем детей через StudentProfile.parent или created_by_tutor
        if self.parent_user.role == User.Role.PARENT:
            # Свойство children уже фильтрует по роли STUDENT, но для надежности оставляем фильтр
            logger.debug(f"[get_children] User is PARENT, using ParentProfile.children")
            children = self.parent_profile.children.filter(role=User.Role.STUDENT)

            # Проверяем есть ли ParentProfile
            if (
                not hasattr(self.parent_user, "parent_profile")
                or self.parent_profile is None
            ):
                logger.warning(
                    f"[get_children] ParentProfile not found for parent {self.parent_user.id}"
                )
        else:
            # Для администраторов ищем детей, у которых parent = этому пользователю или created_by_tutor = этому пользователю
            logger.debug(
                f"[get_children] User is not PARENT, searching through StudentProfile.parent or created_by_tutor"
            )
            children = User.objects.filter(
                Q(student_profile__parent=self.parent_user)
                | Q(created_by_tutor=self.parent_user),
                role=User.Role.STUDENT,
            ).distinct()

        child_count = children.count()
        logger.info(
            f"[get_children] Found {child_count} children for parent {self.parent_user.username}"
        )

        if child_count == 0:
            logger.warning(
                f"[get_children] WARNING: No children found for parent {self.parent_user.username}. This might indicate:"
            )
            logger.warning(f"  - ParentProfile not linked to StudentProfile.parent")
            logger.warning(f"  - StudentProfile.parent is None or incorrect")
            logger.warning(f"  - Children don't exist in database")
        else:
            logger.debug(
                f"[get_children] Children: {[(c.id, c.username) for c in children]}"
            )

        return children

    def get_child_subjects(self, child):
        """
        Получить предметы конкретного ребенка

        Args:
            child: Пользователь-студент

        Returns:
            QuerySet: Предметы ребенка с информацией о зачислениях
        """
        # Проверяем, что ребенок принадлежит родителю
        # Для родителей проверяем через StudentProfile.parent
        # Для администраторов проверяем через created_by_tutor или parent
        if self.parent_user.role == User.Role.PARENT:
            # Для родителей проверяем, что child.student_profile.parent == self.parent_user
            try:
                if (
                    not hasattr(child, "student_profile")
                    or child.student_profile.parent != self.parent_user
                ):
                    logger.warning(
                        f"[get_child_subjects] Child {child.username} does not belong to parent {self.parent_user.username}"
                    )
                    return SubjectEnrollment.objects.none()
            except Exception as e:
                logger.error(
                    f"[get_child_subjects] Error checking child ownership: {e}"
                )
                return SubjectEnrollment.objects.none()
        else:
            # Для администраторов проверяем через created_by_tutor или parent
            from django.db.models import Q

            is_created_by_admin = child.created_by_tutor == self.parent_user
            is_parent_of_child = (
                hasattr(child, "student_profile")
                and child.student_profile.parent == self.parent_user
            )
            if not (is_created_by_admin or is_parent_of_child):
                logger.warning(
                    f"[get_child_subjects] Child {child.username} does not belong to admin {self.parent_user.username}"
                )
                return SubjectEnrollment.objects.none()

        enrollments = (
            SubjectEnrollment.objects.filter(student=child, is_active=True)
            .select_related("subject", "teacher", "assigned_by")
            .prefetch_related("subscription")
        )

        logger.info(
            f"get_child_subjects for child {child.id}: "
            f"found {enrollments.count()} active enrollments"
        )

        # Детали каждого enrollment
        for enr in enrollments:
            logger.debug(
                f"  - Enrollment {enr.id}: subject={enr.subject.name}, "
                f"is_active={enr.is_active}, teacher={enr.teacher.get_full_name()}"
            )

        return enrollments

    def get_child_teachers(self, child):
        """
        Получить список преподавателей ребенка (уникальный список по зачислениям)

        Args:
            child: Пользователь-студент

        Returns:
            list[dict]: Список преподавателей с базовой информацией
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")

        enrollments = self.get_child_subjects(child)
        teachers = {}
        for e in enrollments:
            if e.teacher_id not in teachers:
                teachers[e.teacher_id] = {
                    "id": e.teacher_id,
                    "name": e.teacher.get_full_name(),
                    "email": e.teacher.email,
                    "subjects": set(),
                }
            teachers[e.teacher_id]["subjects"].add(e.get_subject_name())

        result = []
        for t in teachers.values():
            t["subjects"] = sorted(list(t["subjects"]))
            result.append(t)

        return result

    def get_child_progress(self, child):
        """
        Получить прогресс ребенка по всем предметам

        Args:
            child: Пользователь-студент

        Returns:
            dict: Статистика прогресса ребенка
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")

        # Оптимизированная общая статистика прогресса одним запросом
        progress_stats = (
            MaterialProgress.objects.filter(student=child)
            .select_related("material__subject")
            .aggregate(
                total_materials=Count("id"),
                completed_materials=Count("id", filter=Q(is_completed=True)),
                avg_progress=Avg("progress_percentage"),
                total_time=Sum("time_spent"),
            )
        )

        total_materials = progress_stats["total_materials"] or 0
        completed_materials = progress_stats["completed_materials"] or 0
        avg_progress = progress_stats["avg_progress"] or 0
        total_time = progress_stats["total_time"] or 0

        # Оптимизированный прогресс по предметам через аннотации
        enrollments = self.get_child_subjects(child).select_related(
            "subject", "teacher"
        )

        # Получаем статистику по предметам одним запросом
        subject_progress_data = (
            MaterialProgress.objects.filter(
                student=child,
                material__subject__in=[
                    enrollment.subject for enrollment in enrollments
                ],
            )
            .values("material__subject__name", "material__subject__id")
            .annotate(
                total_materials=Count("id"),
                completed_materials=Count("id", filter=Q(is_completed=True)),
                avg_progress=Avg("progress_percentage"),
            )
            .order_by("material__subject__name")
        )

        # Создаем словарь для быстрого поиска
        subject_progress_dict = {
            item["material__subject__name"]: item for item in subject_progress_data
        }

        subject_progress = []
        for enrollment in enrollments:
            subject_name = enrollment.get_subject_name()
            # Используем стандартное название для поиска в progress_data, так как материалы привязаны к стандартному предмету
            standard_subject_name = enrollment.subject.name
            progress_data = subject_progress_dict.get(
                standard_subject_name,
                {"total_materials": 0, "completed_materials": 0, "avg_progress": 0},
            )

            subject_progress.append(
                {
                    "subject": subject_name,
                    "teacher": enrollment.teacher.get_full_name(),
                    "completed_materials": progress_data["completed_materials"],
                    "total_materials": progress_data["total_materials"],
                    "average_progress": round(progress_data["avg_progress"], 1),
                    "enrollment_date": enrollment.enrolled_at,
                }
            )

        return {
            "total_materials": total_materials,
            "completed_materials": completed_materials,
            "completion_percentage": round(
                (completed_materials / total_materials * 100)
                if total_materials > 0
                else 0,
                1,
            ),
            "average_progress": round(avg_progress, 1),
            "total_study_time": total_time,
            "subject_progress": subject_progress,
        }

    def get_payment_status(self, child):
        """
        Получить статус платежей для ребенка

        Args:
            child: Пользователь-студент

        Returns:
            dict: Информация о платежах
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")

        enrollments = self.get_child_subjects(child)

        # Оптимизация: загружаем все платежи одним запросом с использованием Prefetch
        from django.db.models import Prefetch

        enrollment_ids = [e.id for e in enrollments]
        if not enrollment_ids:
            return []

        # Получаем последние платежи для каждого enrollment одним запросом через subquery
        # Используем аннотацию для получения ID последнего платежа, затем загружаем их
        from django.db.models import Max, OuterRef, Subquery

        latest_payment_subquery = (
            SubjectPayment.objects.filter(enrollment=OuterRef("pk"))
            .order_by("-created_at")
            .values("id")[:1]
        )

        enrollments_with_payments = (
            SubjectEnrollment.objects.filter(id__in=enrollment_ids)
            .select_related("subject", "teacher", "subscription")
            .annotate(latest_payment_id=Subquery(latest_payment_subquery))
            .prefetch_related(
                Prefetch(
                    "payments",
                    queryset=SubjectPayment.objects.select_related("payment").order_by(
                        "-created_at"
                    ),
                    to_attr="all_payments",
                )
            )
        )

        # Создаем словарь для быстрого доступа
        enrollments_dict = {e.id: e for e in enrollments_with_payments}

        payment_info = []
        current_time = timezone.now()

        for enrollment_id in enrollment_ids:
            enrollment = enrollments_dict.get(enrollment_id)
            if not enrollment:
                continue

            # Получаем последний платеж из prefetched данных
            last_payment = (
                enrollment.all_payments[0] if enrollment.all_payments else None
            )

            # Проверяем статус платежа
            payment_status = "no_payment"
            next_payment_date = None
            if last_payment:
                if last_payment.status == SubjectPayment.Status.PAID:
                    payment_status = "paid"
                elif last_payment.status == SubjectPayment.Status.WAITING_FOR_PAYMENT:
                    payment_status = "waiting_for_payment"
                elif last_payment.status == SubjectPayment.Status.PENDING:
                    if last_payment.due_date < current_time:
                        payment_status = "overdue"
                    else:
                        payment_status = "pending"
                elif last_payment.status == SubjectPayment.Status.EXPIRED:
                    payment_status = "expired"

            # Получаем информацию о подписке (уже загружена через select_related)
            has_subscription = False
            try:
                subscription = enrollment.subscription
                if (
                    subscription
                    and subscription.status == SubjectSubscription.Status.ACTIVE
                    and subscription.expires_at >= current_time
                ):
                    has_subscription = True
                    next_payment_date = subscription.next_payment_date
            except SubjectSubscription.DoesNotExist:
                pass

            payment_info.append(
                {
                    "enrollment_id": enrollment.id,
                    "subject": enrollment.get_subject_name(),
                    "subject_id": enrollment.subject.id,
                    "teacher": enrollment.teacher.get_full_name(),
                    "teacher_id": enrollment.teacher.id,
                    "status": payment_status,
                    "amount": str(last_payment.amount) if last_payment else "0.00",
                    "due_date": last_payment.due_date.isoformat()
                    if last_payment and last_payment.due_date
                    else None,
                    "paid_at": last_payment.paid_at.isoformat()
                    if last_payment and last_payment.paid_at
                    else None,
                    "has_subscription": has_subscription,
                    "next_payment_date": next_payment_date.isoformat()
                    if next_payment_date
                    else None,
                }
            )

        return payment_info

    def initiate_payment(
        self,
        child,
        enrollment,
        amount=None,
        description="",
        create_subscription=False,
        request=None,
    ):
        """
        Инициировать платеж за предмет с конкретным преподавателем

        Args:
            child: Пользователь-студент
            enrollment: SubjectEnrollment объект (зачисление на предмет с преподавателем)
            amount: Сумма платежа (если не указана, используется из настроек)
            description: Описание платежа
            create_subscription: Создать регулярную подписку (еженедельное списание)
            request: Django request object для создания платежа через ЮКассу

        Returns:
            dict: Информация о созданном платеже
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")

        if enrollment.student != child:
            raise ValueError("Зачисление не принадлежит данному ребенку")

        if not enrollment.is_active:
            raise ValueError("Зачисление неактивно")

        # Если сумма не указана, используем настройки из settings
        if amount is None:
            if settings.PAYMENT_DEVELOPMENT_MODE:
                amount = settings.DEVELOPMENT_PAYMENT_AMOUNT
            else:
                amount = settings.PRODUCTION_PAYMENT_AMOUNT

        # Создаем основной платеж (плательщик — родитель)
        parent = self.parent_user
        subject_name = enrollment.get_subject_name()

        # КРИТИЧНО: Оборачиваем всё создание в атомарную транзакцию
        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            logger.info(
                f"[initiate_payment] Creating payment for enrollment {enrollment.id}"
            )

            payment = Payment.objects.create(
                amount=amount,
                service_name=f"Оплата за предмет: {subject_name} (ученик: {child.get_full_name()})",
                customer_fio=f"{parent.first_name} {parent.last_name}",
                description=(
                    description
                    or f"Оплата за предмет {subject_name} для ученика {child.get_full_name()}"
                ),
                metadata={
                    "payer_role": "parent",
                    "parent_id": parent.id,
                    "parent_email": parent.email,
                    "student_id": child.id,
                    "student_name": child.get_full_name(),
                    "subject_id": enrollment.subject.id,
                    "subject_name": subject_name,
                    "enrollment_id": enrollment.id,
                    "teacher_id": enrollment.teacher_id,
                    "create_subscription": create_subscription,  # Сохраняем флаг для создания подписки после успешной оплаты
                },
            )
            logger.info(f"[initiate_payment] Payment {payment.id} created")

            # ✅ FIX: Создаем SubjectPayment СРАЗУ ПОСЛЕ Payment, но ДО вызова YooKassa API
            # Это предотвращает race condition когда webhook приходит раньше создания SubjectPayment
            due_date = timezone.now() + timedelta(days=7)  # 7 дней на оплату

            subject_payment = SubjectPayment.objects.create(
                enrollment=enrollment,
                payment=payment,
                amount=amount,
                status=SubjectPayment.Status.PENDING,  # Начальный статус - PENDING
                due_date=due_date,
            )
            logger.info(
                f"[initiate_payment] SubjectPayment {subject_payment.id} created BEFORE YooKassa call "
                f"(enrollment={enrollment.id}, payment={payment.id}, status=PENDING)"
            )

            # Если передан request, создаем платеж в ЮКассу
            if request:
                from payments.views import create_yookassa_payment

                # Проверяем наличие ключей перед созданием платежа
                if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
                    logger.error(
                        "YOOKASSA_SHOP_ID or YOOKASSA_SECRET_KEY not configured"
                    )
                    raise ValueError(
                        "Настройки ЮКассы не сконфигурированы. Обратитесь к администратору."
                    )

                logger.info(
                    f"[initiate_payment] Calling YooKassa API for payment {payment.id}"
                )
                yookassa_payment = create_yookassa_payment(payment, request)

                if yookassa_payment:
                    # Сохраняем ID платежа ЮКассы и URL подтверждения
                    payment.yookassa_payment_id = yookassa_payment.get("id")
                    confirmation = yookassa_payment.get("confirmation", {})
                    payment.confirmation_url = confirmation.get("confirmation_url")
                    # Получаем return_url из ответа ЮКассы (он уже содержит URL фронтенда)
                    payment.return_url = confirmation.get("return_url")
                    payment.raw_response = yookassa_payment

                    # Обновляем статус Payment на основе ответа от ЮКассы
                    yookassa_status = yookassa_payment.get("status")
                    if yookassa_status == "pending":
                        payment.status = Payment.Status.PENDING
                    elif yookassa_status == "waiting_for_capture":
                        payment.status = Payment.Status.WAITING_FOR_CAPTURE
                    elif yookassa_status == "succeeded":
                        payment.status = Payment.Status.SUCCEEDED
                        payment.paid_at = timezone.now()
                    elif yookassa_status == "canceled":
                        payment.status = Payment.Status.CANCELED

                    payment.save()
                    logger.info(
                        f"[initiate_payment] Payment {payment.id} updated with YooKassa ID: "
                        f"{payment.yookassa_payment_id}, status: {payment.status}"
                    )

                    # Обновляем статус SubjectPayment на WAITING_FOR_PAYMENT если получили confirmation_url
                    if payment.confirmation_url:
                        subject_payment.status = (
                            SubjectPayment.Status.WAITING_FOR_PAYMENT
                        )
                        subject_payment.save(update_fields=["status", "updated_at"])
                        logger.info(
                            f"[initiate_payment] SubjectPayment {subject_payment.id} status updated to "
                            f"WAITING_FOR_PAYMENT after YooKassa response"
                        )
                else:
                    # Если платеж не создан, логируем ошибку
                    # Транзакция откатится автоматически при raise
                    logger.error(
                        f"Failed to create YooKassa payment for payment {payment.id}"
                    )
                    raise ValueError(
                        "Не удалось создать платеж в ЮКассу. Проверьте настройки "
                        "YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY, а также логи сервера для деталей."
                    )

            logger.info(
                f"[initiate_payment] Transaction complete. Payment={payment.id}, "
                f"SubjectPayment={subject_payment.id}, Status={subject_payment.status}"
            )

        # Подписка будет создана только после успешной оплаты (в webhook обработке)
        # Флаг create_subscription сохранен в metadata платежа

        result = {
            "payment_id": str(payment.id),
            "amount": amount,
            "subject": enrollment.get_subject_name(),
            "teacher_name": enrollment.teacher.get_full_name(),
            "due_date": due_date.isoformat(),
            "confirmation_url": payment.confirmation_url,
            "return_url": payment.return_url,
            "payment_url": payment.confirmation_url
            or payment.return_url,  # Для фронтенда
            "subscription_created": False,  # Подписка будет создана после успешной оплаты
        }

        # Если нет confirmation_url, но есть return_url, используем его
        if not result["confirmation_url"] and result["return_url"]:
            result["confirmation_url"] = result["return_url"]
            result["payment_url"] = result["return_url"]

        DashboardCacheManager.clear(self.parent_user.id)

        return result

    def get_parent_payments(self):
        """
        История платежей родителя по всем детям
        """
        children = self.get_children()
        payments = (
            SubjectPayment.objects.select_related(
                "enrollment__student",
                "enrollment__subject",
                "enrollment__teacher",
                "payment",
            )
            .filter(enrollment__student__in=children)
            .order_by("-created_at")
        )

        data = []
        for sp in payments:
            data.append(
                {
                    "id": sp.id,
                    "enrollment_id": sp.enrollment.id,
                    "subject": sp.enrollment.get_subject_name(),
                    "subject_id": sp.enrollment.subject.id,
                    "teacher": sp.enrollment.teacher.get_full_name(),
                    "teacher_id": sp.enrollment.teacher.id,
                    "student": sp.enrollment.student.get_full_name(),
                    "student_id": sp.enrollment.student.id,
                    "status": sp.status,
                    "amount": str(sp.amount),
                    "due_date": sp.due_date.isoformat() if sp.due_date else None,
                    "paid_at": sp.paid_at.isoformat() if sp.paid_at else None,
                    "created_at": sp.created_at.isoformat(),
                    "payment_id": str(sp.payment_id),
                    "gateway_status": sp.payment.status if sp.payment_id else None,
                    "is_recurring": sp.payment.metadata.get("is_recurring", False)
                    if sp.payment_id and sp.payment.metadata
                    else False,
                }
            )
        return data

    def get_parent_pending_payments(self):
        """
        Ожидающие платежи родителя (включая просроченные)
        """
        children = self.get_children()
        now = timezone.now()
        payments = (
            SubjectPayment.objects.select_related(
                "enrollment__student", "enrollment__subject", "payment"
            )
            .filter(
                enrollment__student__in=children,
                status__in=[
                    SubjectPayment.Status.PENDING,
                    SubjectPayment.Status.WAITING_FOR_PAYMENT,
                ],
            )
            .order_by("due_date")
        )

        data = []
        for sp in payments:
            if sp.status == SubjectPayment.Status.WAITING_FOR_PAYMENT:
                state = "waiting_for_payment"
            elif sp.due_date < now:
                state = "overdue"
            else:
                state = "pending"
            data.append(
                {
                    "subject": sp.enrollment.get_subject_name(),
                    "student": sp.enrollment.student.get_full_name(),
                    "status": state,
                    "amount": sp.amount,
                    "due_date": sp.due_date.isoformat() if sp.due_date else None,
                    "payment_id": str(sp.payment_id),
                }
            )
        return data

    def mark_payment_processed(
        self, *, enrollment: SubjectEnrollment, status: str, amount
    ) -> None:
        """Уведомить родителя об изменении статуса платежа по зачислению."""
        parent = (
            getattr(enrollment.student.student_profile, "parent", None)
            if hasattr(enrollment.student, "student_profile")
            else None
        )
        if not parent:
            return
        try:
            NotificationService().notify_payment_processed(
                parent=parent,
                status=status,
                amount=str(amount),
                enrollment_id=enrollment.id,
            )
        except Exception:
            pass

    def get_dashboard_data(self):
        """
        Сформировать данные дашборда в формате, ожидаемом фронтендом.

        Структура:
        {
          children: [
            {
              id, name, grade, goal, tutor_name, progress_percentage, avatar,
              subjects: [ { id, name, teacher_name, payment_status, next_payment_date } ]
            }
          ],
          reports: [],
          statistics: { total_children, average_progress, completed_payments, pending_payments, overdue_payments }
        }
        """
        logger.info(f"get_dashboard_data called for parent {self.parent_user.id}")
        logger.info(
            f"[get_dashboard_data] Getting dashboard data for parent: {self.parent_user.username}"
        )

        # ОПТИМИЗАЦИЯ P_CACHE_003: Загружаем все связанные данные за один раз через prefetch_related
        from django.db.models import Prefetch

        children_qs = self.get_children().prefetch_related(
            "student_profile",
            "student_profile__parent",
            "student_profile__tutor",
            Prefetch(
                "subject_enrollments",
                queryset=SubjectEnrollment.objects.filter(is_active=True)
                .select_related("subject", "teacher", "assigned_by")
                .prefetch_related("subscription"),
            ),
        )

        # Преобразуем QuerySet в список, чтобы избежать повторных запросов
        children_list = list(children_qs)
        logger.info(f"[get_dashboard_data] Found {len(children_list)} children")
        logger.info(
            f"[get_dashboard_data] Children usernames: {[c.username for c in children_list]}"
        )

        # ОПТИМИЗАЦИЯ P_CACHE_003: Загружаем все платежи для всех детей одним запросом
        children_ids = [c.id for c in children_list]
        payments_by_enrollment = {}
        current_time = timezone.now()

        if children_ids:
            payments_list = (
                SubjectPayment.objects.select_related(
                    "enrollment__student",
                    "enrollment__subject",
                    "enrollment__teacher",
                    "payment",
                )
                .filter(enrollment__student_id__in=children_ids)
                .order_by("enrollment_id", "-created_at")
            )

            # Группируем платежи по enrollment_id (берем последний платеж)
            seen_enrollments = set()
            for payment in payments_list:
                if payment.enrollment_id not in seen_enrollments:
                    # Определяем статус платежа
                    payment_status = "no_payment"
                    if payment.status == SubjectPayment.Status.PAID:
                        payment_status = "paid"
                    elif payment.status == SubjectPayment.Status.WAITING_FOR_PAYMENT:
                        payment_status = "waiting_for_payment"
                    elif payment.status == SubjectPayment.Status.PENDING:
                        if payment.due_date and payment.due_date < current_time:
                            payment_status = "overdue"
                        else:
                            payment_status = "pending"
                    elif payment.status == SubjectPayment.Status.EXPIRED:
                        payment_status = "expired"

                    payments_by_enrollment[payment.enrollment_id] = {
                        "status": payment_status,
                        "amount": str(payment.amount),
                        "due_date": payment.due_date.isoformat()
                        if payment.due_date
                        else None,
                        "paid_at": payment.paid_at.isoformat()
                        if payment.paid_at
                        else None,
                        "next_payment_date": None,
                        "enrollment_id": payment.enrollment_id,
                    }
                    seen_enrollments.add(payment.enrollment_id)

        children_data = []

        total_progress_list = []
        completed_payments = 0
        pending_payments = 0
        overdue_payments = 0

        for child in children_list:
            try:
                logger.info(
                    f"[get_dashboard_data] Processing child: {child.username} (id: {child.id})"
                )
                # Профиль ученика (уже загружен через prefetch_related)
                student_profile = getattr(child, "student_profile", None)
                grade = getattr(student_profile, "grade", "") if student_profile else ""
                goal = getattr(student_profile, "goal", "") if student_profile else ""
                tutor = (
                    getattr(student_profile, "tutor", None) if student_profile else None
                )
                tutor_name = tutor.get_full_name() if tutor else ""
                progress_percentage = (
                    getattr(student_profile, "progress_percentage", 0)
                    if student_profile
                    else 0
                )
                avatar = getattr(child, "avatar", None)

                # Предметы и платежи (уже загружены через prefetch_related)
                subjects = []
                payments_info = []

                try:
                    # Получаем enrollments из prefetch_related
                    child_enrollments = getattr(child, "subjectenrollment_set", [])
                    if hasattr(child_enrollments, "all"):
                        child_enrollments = child_enrollments.all()
                    else:
                        child_enrollments = list(child_enrollments)

                    logger.info(
                        f"[get_dashboard_data] Child subjects for {child.username}: {len(child_enrollments)} subjects"
                    )

                    for enrollment in child_enrollments:
                        payment = payments_by_enrollment.get(enrollment.id, None)

                        # Получаем next_payment_date из подписки (уже загружена через prefetch_related)
                        next_payment_date = None
                        has_subscription = False

                        try:
                            subscription = getattr(enrollment, "subscription", None)
                            if (
                                subscription
                                and subscription.status
                                == SubjectSubscription.Status.ACTIVE
                                and subscription.expires_at >= current_time
                            ):
                                has_subscription = True
                                if subscription.next_payment_date:
                                    next_payment_date = (
                                        subscription.next_payment_date.isoformat()
                                    )
                        except Exception:
                            pass

                        payment_status = payment["status"] if payment else "no_payment"
                        payment_amount = payment["amount"] if payment else None

                        subjects.append(
                            {
                                "id": enrollment.subject.id,
                                "enrollment_id": enrollment.id,
                                "name": enrollment.get_subject_name(),
                                "teacher_name": enrollment.teacher.get_full_name(),
                                "teacher_id": enrollment.teacher.id,
                                "payment_status": payment_status,
                                "next_payment_date": next_payment_date,
                                "has_subscription": has_subscription,
                                "amount": payment_amount,
                            }
                        )

                        # Сразу подсчитываем статистику по платежам
                        if payment:
                            if payment_status == "paid":
                                completed_payments += 1
                            elif payment_status in ["pending", "waiting_for_payment"]:
                                pending_payments += 1
                            elif payment_status == "overdue":
                                overdue_payments += 1

                            # Добавляем в общий список платежей
                            payments_info.append(
                                {
                                    "enrollment_id": enrollment.id,
                                    "subject": enrollment.get_subject_name(),
                                    "subject_id": enrollment.subject.id,
                                    "teacher": enrollment.teacher.get_full_name(),
                                    "teacher_id": enrollment.teacher.id,
                                    "status": payment_status,
                                    "amount": payment_amount,
                                    "due_date": payment["due_date"],
                                    "paid_at": payment["paid_at"],
                                    "has_subscription": has_subscription,
                                    "next_payment_date": next_payment_date,
                                }
                            )

                except Exception as e:
                    logger.error(
                        f"[get_dashboard_data] Error processing subjects for {child.username}: {e}",
                        exc_info=True,
                    )
                    subjects = []
                    payments_info = []

                # Копим для средней статистики
                total_progress_list.append(progress_percentage or 0)

                child_data = {
                    "id": child.id,
                    "name": child.get_full_name(),
                    "grade": str(grade) if grade is not None else "",
                    "goal": goal or "",
                    "tutor_name": tutor_name,
                    "progress_percentage": progress_percentage or 0,
                    "progress": progress_percentage or 0,
                    # Безопасно формируем URL аватара только если файл реально существует
                    "avatar": (
                        self._build_file_url(avatar)
                        if (avatar and getattr(avatar, "name", None))
                        else None
                    ),
                    "subjects": subjects,
                    "payments": payments_info,
                }
                logger.info(
                    f"[get_dashboard_data] Adding child data: {child_data['name']} (id: {child_data['id']}), subjects: {len(subjects)}"
                )
                children_data.append(child_data)
            except Exception as e:
                logger.error(
                    f"[get_dashboard_data] Error processing child {child.username}: {e}",
                    exc_info=True,
                )
                # Продолжаем обработку других детей даже если один не удался
                continue

        avg_progress = 0
        if total_progress_list:
            avg_progress = round(
                sum(total_progress_list) / max(len(total_progress_list), 1), 1
            )

        result = {
            "parent": {
                "id": self.parent_user.id,
                "name": self.parent_user.get_full_name(),
                "email": self.parent_user.email,
            },
            "children": children_data,
            "reports": [],  # пока нет реальных отчётов
            "statistics": {
                "total_children": len(children_list),
                "average_progress": avg_progress,
                "completed_payments": completed_payments,
                "pending_payments": pending_payments,
                "overdue_payments": overdue_payments,
            },
            # Дублируем ключ для совместимости с ожиданиями тестов
            "total_children": len(children_list),
        }
        logger.info(
            f"[get_dashboard_data] Returning dashboard data with {len(children_data)} children"
        )
        logger.info(
            f"get_dashboard_data for parent {self.parent_user.id}: "
            f"returning {len(children_data)} children"
        )
        return result

    def get_reports(self, child=None):
        """
        Получить отчеты о прогрессе ребенка от тьютора

        Args:
            child: Конкретный ребенок (опционально)

        Returns:
            QuerySet: Отчеты о прогрессе
        """
        from reports.models import TutorWeeklyReport
        from django.db.models import Q

        # Получаем детей родителя
        children_ids = list(
            User.objects.filter(
                student_profile__parent_id=self.parent_user.id, role=User.Role.STUDENT
            ).values_list("id", flat=True)
        )

        # Базовый запрос - только отправленные отчеты (не черновики)
        queryset = TutorWeeklyReport.objects.select_related(
            "tutor", "student", "parent", "student__student_profile"
        ).exclude(status=TutorWeeklyReport.Status.DRAFT)

        if child:
            # Отчеты о конкретном ребенке
            return queryset.filter(student=child)
        elif children_ids:
            # Отчеты обо всех детях родителя
            return queryset.filter(
                Q(parent_id=self.parent_user.id) | Q(student_id__in=children_ids)
            )
        else:
            # Если нет детей в профилях, фильтруем только по parent
            return queryset.filter(parent_id=self.parent_user.id)
