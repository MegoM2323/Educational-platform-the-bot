from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import SubjectEnrollment, SubjectPayment, MaterialProgress, Material, Subject
from payments.models import Payment
from .cache_utils import cache_dashboard_data, DashboardCacheManager

User = get_user_model()


class ParentDashboardService:
    """
    Сервис для работы с дашбордом родителя
    """
    
    def __init__(self, parent_user):
        """
        Инициализация сервиса для конкретного родителя
        
        Args:
            parent_user: Пользователь с ролью PARENT
        """
        if not parent_user or parent_user.role != User.Role.PARENT:
            raise ValueError("Пользователь должен иметь роль PARENT")
        
        self.parent_user = parent_user
        self.parent_profile = parent_user.parent_profile
    
    def get_children(self):
        """
        Получить список детей родителя
        
        Returns:
            QuerySet: Список детей пользователя
        """
        return self.parent_profile.children.filter(role=User.Role.STUDENT)
    
    def get_child_subjects(self, child):
        """
        Получить предметы конкретного ребенка
        
        Args:
            child: Пользователь-студент
            
        Returns:
            QuerySet: Предметы ребенка с информацией о зачислениях
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")
        
        return SubjectEnrollment.objects.filter(
            student=child,
            is_active=True
        ).select_related('subject', 'teacher').prefetch_related(
            'subject__materials__progress'
        )
    
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
        progress_stats = MaterialProgress.objects.filter(
            student=child
        ).select_related('material__subject').aggregate(
            total_materials=Count('id'),
            completed_materials=Count('id', filter=Q(is_completed=True)),
            avg_progress=Avg('progress_percentage'),
            total_time=Sum('time_spent')
        )
        
        total_materials = progress_stats['total_materials'] or 0
        completed_materials = progress_stats['completed_materials'] or 0
        avg_progress = progress_stats['avg_progress'] or 0
        total_time = progress_stats['total_time'] or 0
        
        # Оптимизированный прогресс по предметам через аннотации
        enrollments = self.get_child_subjects(child).select_related('subject', 'teacher')
        
        # Получаем статистику по предметам одним запросом
        subject_progress_data = MaterialProgress.objects.filter(
            student=child,
            material__subject__in=[enrollment.subject for enrollment in enrollments]
        ).values('material__subject__name', 'material__subject__id').annotate(
            total_materials=Count('id'),
            completed_materials=Count('id', filter=Q(is_completed=True)),
            avg_progress=Avg('progress_percentage')
        ).order_by('material__subject__name')
        
        # Создаем словарь для быстрого поиска
        subject_progress_dict = {
            item['material__subject__name']: item 
            for item in subject_progress_data
        }
        
        subject_progress = []
        for enrollment in enrollments:
            subject_name = enrollment.subject.name
            progress_data = subject_progress_dict.get(subject_name, {
                'total_materials': 0,
                'completed_materials': 0,
                'avg_progress': 0
            })
            
            subject_progress.append({
                'subject': subject_name,
                'teacher': enrollment.teacher.get_full_name(),
                'completed_materials': progress_data['completed_materials'],
                'total_materials': progress_data['total_materials'],
                'average_progress': round(progress_data['avg_progress'], 1),
                'enrollment_date': enrollment.enrolled_at
            })
        
        return {
            'total_materials': total_materials,
            'completed_materials': completed_materials,
            'completion_percentage': round((completed_materials / total_materials * 100) if total_materials > 0 else 0, 1),
            'average_progress': round(avg_progress, 1),
            'total_study_time': total_time,
            'subject_progress': subject_progress
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
        payment_info = []
        
        for enrollment in enrollments:
            # Получаем последний платеж по предмету
            last_payment = SubjectPayment.objects.filter(
                enrollment=enrollment
            ).order_by('-created_at').first()
            
            # Проверяем статус платежа
            payment_status = 'no_payment'
            if last_payment:
                if last_payment.status == SubjectPayment.Status.PAID:
                    payment_status = 'paid'
                elif last_payment.status == SubjectPayment.Status.PENDING:
                    if last_payment.due_date < timezone.now():
                        payment_status = 'overdue'
                    else:
                        payment_status = 'pending'
                elif last_payment.status == SubjectPayment.Status.EXPIRED:
                    payment_status = 'expired'
            
            payment_info.append({
                'subject': enrollment.subject.name,
                'teacher': enrollment.teacher.get_full_name(),
                'status': payment_status,
                'amount': last_payment.amount if last_payment else Decimal('0.00'),
                'due_date': last_payment.due_date if last_payment else None,
                'paid_at': last_payment.paid_at if last_payment else None
            })
        
        return payment_info
    
    def initiate_payment(self, child, subject_id, amount, description="", request=None):
        """
        Инициировать платеж за предмет
        
        Args:
            child: Пользователь-студент
            subject_id: ID предмета
            amount: Сумма платежа
            description: Описание платежа
            request: Django request object для создания платежа через ЮКассу
            
        Returns:
            dict: Информация о созданном платеже
        """
        if child not in self.get_children():
            raise ValueError("Ребенок не принадлежит данному родителю")
        
        try:
            enrollment = SubjectEnrollment.objects.get(
                student=child,
                subject_id=subject_id,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            raise ValueError("Ребенок не зачислен на данный предмет")
        
        # Создаем основной платеж
        payment = Payment.objects.create(
            amount=amount,
            service_name=f"Оплата за предмет: {enrollment.subject.name}",
            customer_fio=f"{child.first_name} {child.last_name}",
            description=description or f"Оплата за предмет {enrollment.subject.name} для {child.get_full_name()}"
        )
        
        # Если передан request, создаем платеж в ЮКассу
        if request:
            from payments.views import create_yookassa_payment
            yookassa_payment = create_yookassa_payment(payment, request)
            
            if yookassa_payment:
                # Сохраняем ID платежа ЮКассы и URL подтверждения
                payment.yookassa_payment_id = yookassa_payment.get('id')
                payment.confirmation_url = yookassa_payment.get('confirmation', {}).get('confirmation_url')
                payment.return_url = f"{request.build_absolute_uri('/payments/success/')}?payment_id={payment.id}"
                payment.raw_response = yookassa_payment
                payment.save()
        
        # Создаем платеж по предмету
        due_date = timezone.now() + timedelta(days=7)  # 7 дней на оплату
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=amount,
            due_date=due_date
        )
        
        return {
            'payment_id': str(payment.id),
            'amount': float(amount),
            'subject': enrollment.subject.name,
            'due_date': due_date.isoformat(),
            'confirmation_url': payment.confirmation_url,
            'return_url': payment.return_url,
            'payment_url': payment.confirmation_url  # Для фронтенда
        }
    
    def get_dashboard_data(self):
        """
        Получить все данные для дашборда родителя
        
        Returns:
            dict: Полные данные дашборда
        """
        children = self.get_children()
        children_data = []
        
        for child in children:
            child_data = {
                'id': child.id,
                'name': child.get_full_name(),
                'email': child.email,
                'subjects': list(self.get_child_subjects(child).values(
                    'id', 'subject__name', 'subject__color', 'teacher__first_name', 'teacher__last_name'
                )),
                'progress': self.get_child_progress(child),
                'payments': self.get_payment_status(child)
            }
            children_data.append(child_data)
        
        return {
            'parent': {
                'id': self.parent_user.id,
                'name': self.parent_user.get_full_name(),
                'email': self.parent_user.email
            },
            'children': children_data,
            'total_children': children.count()
        }
    
    def get_reports(self, child=None):
        """
        Получить отчеты о прогрессе ребенка
        
        Args:
            child: Конкретный ребенок (опционально)
            
        Returns:
            QuerySet: Отчеты о прогрессе
        """
        # Пока заглушка, так как модель отчетов еще не создана
        # TODO: Реализовать после создания модели отчетов
        return []
