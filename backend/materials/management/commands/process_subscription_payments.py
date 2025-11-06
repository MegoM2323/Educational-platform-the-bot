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
from django.contrib.auth import get_user_model

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
                    
                    if dry_run:
                        self.stdout.write(
                            f'[DRY-RUN] Создан платеж для подписки {subscription.id}: '
                            f'Студент: {student.get_full_name()}, '
                            f'Предмет: {enrollment.subject.name}, '
                            f'Сумма: {subscription.amount} руб.'
                        )
                        processed += 1
                        continue
                    
                    # Создаем платеж в нашей системе
                    payment = Payment.objects.create(
                        amount=subscription.amount,
                        service_name=f"Регулярный платеж за предмет: {enrollment.subject.name} (ученик: {student.get_full_name()})",
                        customer_fio=f"{parent.first_name} {parent.last_name}",
                        description=(
                            f"Регулярный платеж за предмет {enrollment.subject.name} "
                            f"для ученика {student.get_full_name()} (преподаватель: {enrollment.teacher.get_full_name()})"
                        ),
                        metadata={
                            "payer_role": "parent",
                            "parent_id": parent.id,
                            "parent_email": parent.email,
                            "student_id": student.id,
                            "student_name": student.get_full_name(),
                            "subject_id": enrollment.subject.id,
                            "subject_name": enrollment.subject.name,
                            "enrollment_id": enrollment.id,
                            "teacher_id": enrollment.teacher_id,
                            "subscription_id": subscription.id,
                            "is_recurring": True,
                        },
                    )
                    
                    # Создаем платеж по предмету
                    due_date = timezone.now() + timedelta(days=7)
                    subject_payment = SubjectPayment.objects.create(
                        enrollment=enrollment,
                        payment=payment,
                        amount=subscription.amount,
                        due_date=due_date
                    )
                    
                    # Планируем следующий платеж
                    subscription.schedule_next_payment()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Создан платеж {payment.id} для подписки {subscription.id}: '
                            f'Студент: {student.get_full_name()}, '
                            f'Предмет: {enrollment.subject.name}, '
                            f'Сумма: {subscription.amount} руб., '
                            f'Следующий платеж: {subscription.next_payment_date.strftime("%Y-%m-%d %H:%M")}'
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

