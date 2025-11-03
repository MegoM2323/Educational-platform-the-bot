from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import SubjectEnrollment, SubjectPayment, MaterialProgress, Material, Subject
from notifications.notification_service import NotificationService
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
                    'id': e.teacher_id,
                    'name': e.teacher.get_full_name(),
                    'email': e.teacher.email,
                    'subjects': set()
                }
            teachers[e.teacher_id]['subjects'].add(e.subject.name)
        
        result = []
        for t in teachers.values():
            t['subjects'] = sorted(list(t['subjects']))
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
        
        # Создаем основной платеж (плательщик — родитель)
        parent = self.parent_user
        payment = Payment.objects.create(
            amount=amount,
            service_name=f"Оплата за предмет: {enrollment.subject.name} (ученик: {child.get_full_name()})",
            customer_fio=f"{parent.first_name} {parent.last_name}",
            description=(
                description
                or f"Оплата за предмет {enrollment.subject.name} для ученика {child.get_full_name()}"
            ),
            metadata={
                "payer_role": "parent",
                "parent_id": parent.id,
                "parent_email": parent.email,
                "student_id": child.id,
                "student_name": child.get_full_name(),
                "subject_id": enrollment.subject.id,
                "subject_name": enrollment.subject.name,
                "enrollment_id": enrollment.id,
                "teacher_id": enrollment.teacher_id,
            },
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
            'amount': amount,
            'subject': enrollment.subject.name,
            'due_date': due_date.isoformat(),
            'confirmation_url': payment.confirmation_url,
            'return_url': payment.return_url,
            'payment_url': payment.confirmation_url  # Для фронтенда
        }
    
    def get_parent_payments(self):
        """
        История платежей родителя по всем детям
        """
        children = self.get_children()
        payments = SubjectPayment.objects.select_related(
            'enrollment__student', 'enrollment__subject', 'payment'
        ).filter(enrollment__student__in=children).order_by('-created_at')
        
        data = []
        for sp in payments:
            data.append({
                'subject': sp.enrollment.subject.name,
                'student': sp.enrollment.student.get_full_name(),
                'status': sp.status,
                'amount': sp.amount,
                'due_date': sp.due_date,
                'paid_at': sp.paid_at,
                'payment_id': str(sp.payment_id),
                'gateway_status': sp.payment.status if sp.payment_id else None,
            })
        return data
    
    def get_parent_pending_payments(self):
        """
        Ожидающие платежи родителя (включая просроченные)
        """
        children = self.get_children()
        now = timezone.now()
        payments = SubjectPayment.objects.select_related(
            'enrollment__student', 'enrollment__subject', 'payment'
        ).filter(
            enrollment__student__in=children,
            status__in=[SubjectPayment.Status.PENDING]
        ).order_by('due_date')
        
        data = []
        for sp in payments:
            state = 'overdue' if sp.due_date < now else 'pending'
            data.append({
                'subject': sp.enrollment.subject.name,
                'student': sp.enrollment.student.get_full_name(),
                'status': state,
                'amount': sp.amount,
                'due_date': sp.due_date,
                'payment_id': str(sp.payment_id),
            })
        return data

    def mark_payment_processed(self, *, enrollment: SubjectEnrollment, status: str, amount) -> None:
        """Уведомить родителя об изменении статуса платежа по зачислению."""
        parent = getattr(enrollment.student.student_profile, 'parent', None) if hasattr(enrollment.student, 'student_profile') else None
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
        children_qs = self.get_children()
        children_data = []
        
        total_progress_list = []
        completed_payments = 0
        pending_payments = 0
        overdue_payments = 0
        
        for child in children_qs:
            # Профиль ученика
            student_profile = getattr(child, 'student_profile', None)
            grade = getattr(student_profile, 'grade', '') if student_profile else ''
            goal = getattr(student_profile, 'goal', '') if student_profile else ''
            tutor = getattr(student_profile, 'tutor', None) if student_profile else None
            tutor_name = tutor.get_full_name() if tutor else ''
            progress_percentage = getattr(student_profile, 'progress_percentage', 0) if student_profile else 0
            avatar = getattr(child, 'avatar', None)
            
            # Предметы и платежи
            subjects = []
            payments_info = self.get_payment_status(child)
            # Индекс платежей по предмету
            payments_by_subject = {}
            for p in payments_info:
                payments_by_subject[p['subject']] = p
                if p['status'] == 'paid':
                    completed_payments += 1
                elif p['status'] == 'pending':
                    pending_payments += 1
                elif p['status'] == 'overdue':
                    overdue_payments += 1
            
            for enrollment in self.get_child_subjects(child):
                subj_name = enrollment.subject.name
                payment = payments_by_subject.get(subj_name, None)
                subjects.append({
                    'id': enrollment.subject.id,
                    'name': subj_name,
                    'teacher_name': enrollment.teacher.get_full_name(),
                    'payment_status': payment['status'] if payment else 'no_payment',
                    'next_payment_date': payment['due_date'] if payment else None,
                })
            
            # Копим для средней статистики
            total_progress_list.append(progress_percentage or 0)
            
            children_data.append({
                'id': child.id,
                'name': child.get_full_name(),
                'grade': str(grade) if grade is not None else '',
                'goal': goal or '',
                'tutor_name': tutor_name,
                'progress_percentage': progress_percentage or 0,
                'progress': progress_percentage or 0,
                # Безопасно формируем URL аватара только если файл реально существует
                'avatar': (avatar.url if (avatar and getattr(avatar, 'name', None)) else None),
                'subjects': subjects,
                'payments': payments_info,
            })
        
        avg_progress = 0
        if total_progress_list:
            avg_progress = round(sum(total_progress_list) / max(len(total_progress_list), 1), 1)
        
        return {
            'parent': {
                'id': self.parent_user.id,
                'name': self.parent_user.get_full_name(),
                'email': self.parent_user.email,
            },
            'children': children_data,
            'reports': [],  # пока нет реальных отчётов
            'statistics': {
                'total_children': children_qs.count(),
                'average_progress': avg_progress,
                'completed_payments': completed_payments,
                'pending_payments': pending_payments,
                'overdue_payments': overdue_payments,
            },
            # Дублируем ключ для совместимости с ожиданиями тестов
            'total_children': children_qs.count(),
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
