"""
Management команда для обработки регулярных платежей по подпискам
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal
import logging

from materials.models import SubjectSubscription, SubjectPayment, SubjectEnrollment
from payments.models import Payment
from payments.views import create_yookassa_payment
from payments.telegram_service import TelegramNotificationService
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Обрабатывает регулярные платежи по активным подпискам'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано без фактического создания платежей'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Режим тестирования (dry-run)'))
        
        # Получаем активные подписки, у которых наступила дата следующего платежа
        now = timezone.now()
        subscriptions = SubjectSubscription.objects.filter(
            status=SubjectSubscription.Status.ACTIVE,
            next_payment_date__lte=now
        ).select_related('enrollment__student', 'enrollment__subject', 'enrollment__teacher')
        
        self.stdout.write(f'Найдено {subscriptions.count()} подписок для обработки')
        
        processed = 0
        errors = 0
        
        for subscription in subscriptions:
            try:
                with transaction.atomic():
                    enrollment = subscription.enrollment
                    student = enrollment.student
                    
                    # Получаем родителя студента
                    parent = None
                    if hasattr(student, 'student_profile') and student.student_profile:
                        parent = student.student_profile.parent
                    
                    if not parent:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Пропущена подписка {subscription.id}: у студента {student.get_full_name()} нет родителя'
                            )
                        )
                        continue

                    # Проверяем, нет ли уже pending/waiting_for_payment платежей для этой подписки
                    # Это предотвращает создание дублирующихся платежей если webhook еще не обработан
                    existing_pending = SubjectPayment.objects.filter(
                        enrollment=enrollment,
                        status__in=[SubjectPayment.Status.PENDING, SubjectPayment.Status.WAITING_FOR_PAYMENT]
                    ).exists()

                    if existing_pending:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Пропущена подписка {subscription.id}: уже есть необработанный платеж'
                            )
                        )
                        continue

                    subject_name = enrollment.get_subject_name()
                    if dry_run:
                        self.stdout.write(
                            f'[DRY-RUN] Создан платеж для подписки {subscription.id}: '
                            f'Студент: {student.get_full_name()}, '
                            f'Предмет: {subject_name}, '
                            f'Сумма: {subscription.amount} руб.'
                        )
                        processed += 1
                        continue
                    
                    # Создаем платеж в нашей системе
                    payment = Payment.objects.create(
                        amount=subscription.amount,
                        service_name=f"Регулярный платеж за предмет: {subject_name} (ученик: {student.get_full_name()})",
                        customer_fio=f"{parent.first_name} {parent.last_name}",
                        description=(
                            f"Регулярный платеж за предмет {subject_name} "
                            f"для ученика {student.get_full_name()} (преподаватель: {enrollment.teacher.get_full_name()})"
                        ),
                        metadata={
                            "payer_role": "parent",
                            "parent_id": parent.id,
                            "parent_email": parent.email,
                            "student_id": student.id,
                            "student_name": student.get_full_name(),
                            "subject_id": enrollment.subject.id,
                            "subject_name": subject_name,
                            "enrollment_id": enrollment.id,
                            "teacher_id": enrollment.teacher_id,
                            "subscription_id": subscription.id,
                            "is_recurring": True,
                            "create_subscription": False,  # Не создаем новую подписку, она уже есть
                        },
                    )
                    
                    # Создаем платеж в YooKassa
                    # Для команды создаем фиктивный request объект
                    # Важно: для команды используется FRONTEND_URL из настроек
                    from django.test import RequestFactory
                    from django.conf import settings as django_settings
                    factory = RequestFactory()
                    fake_request = factory.get('/')
                    # Устанавливаем HTTP_HOST для корректной работы build_absolute_uri
                    # Используем реальный домен из ALLOWED_HOSTS, если он не localhost
                    allowed_hosts = getattr(django_settings, 'ALLOWED_HOSTS', [])
                    if allowed_hosts and isinstance(allowed_hosts, (list, tuple)):
                        # Ищем первый не-localhost хост
                        real_host = None
                        for host in allowed_hosts:
                            if 'localhost' not in str(host) and '127.0.0.1' not in str(host):
                                real_host = host
                                break
                        fake_request.META['HTTP_HOST'] = real_host if real_host else allowed_hosts[0]
                        # Устанавливаем HTTPS если это продакшен домен
                        if real_host and ('the-bot.ru' in str(real_host) or 'www.the-bot.ru' in str(real_host)):
                            fake_request.META['wsgi.url_scheme'] = 'https'
                    else:
                        fake_request.META['HTTP_HOST'] = 'localhost'
                    
                    yookassa_payment = create_yookassa_payment(payment, fake_request)
                    
                    if not yookassa_payment:
                        logger.error(f"Не удалось создать платеж в YooKassa для подписки {subscription.id}")
                        payment.delete()  # Удаляем платеж, если не удалось создать в YooKassa
                        raise Exception("Не удалось создать платеж в YooKassa")
                    
                    # Обновляем платеж с данными от ЮКассы
                    payment.yookassa_payment_id = yookassa_payment.get('id')
                    payment.confirmation_url = yookassa_payment.get('confirmation', {}).get('confirmation_url')
                    payment.raw_response = yookassa_payment
                    
                    # Обновляем статус Payment на основе ответа от ЮКассы
                    yookassa_status = yookassa_payment.get('status')
                    if yookassa_status == 'pending':
                        payment.status = Payment.Status.PENDING
                    elif yookassa_status == 'waiting_for_capture':
                        payment.status = Payment.Status.WAITING_FOR_CAPTURE
                    elif yookassa_status == 'succeeded':
                        payment.status = Payment.Status.SUCCEEDED
                        payment.paid_at = timezone.now()
                    elif yookassa_status == 'canceled':
                        payment.status = Payment.Status.CANCELED
                    
                    payment.save(update_fields=['yookassa_payment_id', 'confirmation_url', 'raw_response', 'status', 'paid_at', 'updated'])
                    
                    # Создаем платеж по предмету
                    due_date = timezone.now() + timedelta(days=7)
                    # Определяем статус на основе наличия confirmation_url
                    payment_status = SubjectPayment.Status.WAITING_FOR_PAYMENT if payment.confirmation_url else SubjectPayment.Status.PENDING
                    
                    subject_payment = SubjectPayment.objects.create(
                        enrollment=enrollment,
                        payment=payment,
                        amount=subscription.amount,
                        status=payment_status,
                        due_date=due_date
                    )

                    # Отправляем Telegram уведомление родителю о новом счете
                    try:
                        telegram_service = TelegramNotificationService()
                        notification_sent = self._send_parent_notification(
                            telegram_service,
                            parent,
                            student,
                            enrollment,
                            payment,
                            subscription.amount,
                            due_date
                        )
                        if notification_sent:
                            logger.info(f"Telegram notification sent to parent {parent.id} for payment {payment.id}")
                        else:
                            logger.warning(f"Failed to send Telegram notification to parent {parent.id} for payment {payment.id}")
                    except Exception as notif_error:
                        # Не прерываем процесс создания платежа из-за ошибки уведомления
                        logger.error(f"Error sending Telegram notification for payment {payment.id}: {notif_error}", exc_info=True)

                    # КРИТИЧНО: Обновляем next_payment_date СРАЗУ после создания платежа
                    # Это предотвращает создание повторных платежей каждые 5 минут
                    # если webhook придет с задержкой или не придет вообще
                    if settings.PAYMENT_DEVELOPMENT_MODE:
                        next_payment_delta = timedelta(minutes=settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES)
                        subscription.payment_interval_weeks = 0  # Для режима разработки
                    else:
                        next_payment_delta = timedelta(weeks=settings.PRODUCTION_RECURRING_INTERVAL_WEEKS)
                        subscription.payment_interval_weeks = settings.PRODUCTION_RECURRING_INTERVAL_WEEKS

                    subscription.next_payment_date = timezone.now() + next_payment_delta
                    subscription.save(update_fields=['next_payment_date', 'payment_interval_weeks', 'updated_at'])

                    logger.info(
                        f"Subscription {subscription.id} next payment scheduled for {subscription.next_payment_date} "
                        f"(interval: {next_payment_delta})"
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Создан платеж {payment.id} для подписки {subscription.id}: '
                            f'Студент: {student.get_full_name()}, '
                            f'Предмет: {enrollment.get_subject_name()}, '
                            f'Сумма: {subscription.amount} руб., '
                            f'Статус: {payment.status}'
                        )
                    )
                    processed += 1
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке подписки {subscription.id}: {e}", exc_info=True)
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при обработке подписки {subscription.id}: {str(e)}')
                )
                errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nОбработка завершена: обработано {processed}, ошибок {errors}'
            )
        )

    def _send_parent_notification(self, telegram_service, parent, student, enrollment, payment, amount, due_date):
        """
        Отправляет Telegram уведомление родителю о новом счете.

        Args:
            telegram_service: Экземпляр TelegramNotificationService
            parent: Объект пользователя-родителя
            student: Объект пользователя-студента
            enrollment: Объект SubjectEnrollment
            payment: Объект Payment
            amount: Decimal сумма платежа
            due_date: datetime дата оплаты

        Returns:
            bool: True если уведомление отправлено успешно, False иначе
        """
        # Проверяем, что у родителя настроен Telegram
        parent_telegram_id = None

        # Пытаемся получить telegram_id из профиля родителя
        if hasattr(parent, 'parent_profile') and parent.parent_profile:
            parent_telegram_id = getattr(parent.parent_profile, 'telegram_id', None)

        if not parent_telegram_id:
            logger.info(f"Parent {parent.id} has no Telegram ID configured, skipping notification")
            return False

        # Формируем сообщение
        subject_name = enrollment.get_subject_name()
        student_name = student.get_full_name()
        payment_link = payment.confirmation_url if payment.confirmation_url else "Ссылка будет доступна после обработки"

        message = f"""
💳 *Новый счет на оплату*

👤 *Ученик:* {student_name}
📚 *Предмет:* {subject_name}
💰 *Сумма:* {amount} ₽
📅 *Срок оплаты:* {due_date.strftime('%d.%m.%Y')}

🔗 *Ссылка для оплаты:*
{payment_link}

_Это автоматическое уведомление о регулярном платеже по подписке._
        """.strip()

        try:
            # Отправляем сообщение напрямую родителю
            import requests
            bot_token = telegram_service.bot_token
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            data = {
                'chat_id': parent_telegram_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }

            response = requests.post(api_url, json=data, timeout=10)

            if response.status_code == 200:
                logger.info(f"Telegram notification sent to parent {parent.id} (chat_id: {parent_telegram_id})")
                return True
            else:
                from core.json_utils import safe_json_response
                error_data = safe_json_response(response, {})
                error_description = error_data.get('description', 'Unknown error') if error_data else response.text[:200]
                logger.warning(
                    f"Failed to send Telegram notification to parent {parent.id}: "
                    f"{response.status_code} - {error_description}"
                )
                return False

        except Exception as e:
            logger.error(f"Exception sending Telegram notification to parent {parent.id}: {e}", exc_info=True)
            return False

