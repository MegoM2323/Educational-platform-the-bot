"""
Сериализаторы для Invoice API endpoints.

Типы сериализаторов:
- InvoiceSerializer: полная детальная информация
- InvoiceListSerializer: краткая информация для списков
- CreateInvoiceSerializer: создание нового счета с валидацией
- SendInvoiceSerializer: отправка счета родителю
- ViewInvoiceSerializer: пометка просмотренным
"""

from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Invoice, InvoiceStatusHistory
from .exceptions import DuplicateInvoiceError, InvalidStudentEnrollment

User = get_user_model()


class UserBriefSerializer(serializers.Serializer):
    """Краткая информация о пользователе для вложенных объектов"""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.CharField()

    def to_representation(self, instance):
        """Кастомное представление"""
        return {
            'id': instance.id,
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'full_name': instance.get_full_name(),
            'role': instance.role
        }


class PaymentBriefSerializer(serializers.Serializer):
    """Краткая информация о платеже"""
    id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    yookassa_payment_id = serializers.CharField()
    paid_at = serializers.DateTimeField()


class InvoiceStatusHistorySerializer(serializers.ModelSerializer):
    """История изменений статуса счета"""
    changed_by = UserBriefSerializer()

    class Meta:
        model = InvoiceStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'changed_by',
            'changed_at', 'reason'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Полная детальная информация о счете.
    Используется для retrieve endpoint.
    """
    tutor = UserBriefSerializer()
    student = UserBriefSerializer()
    parent = UserBriefSerializer()
    payment = PaymentBriefSerializer(allow_null=True)
    status_history = InvoiceStatusHistorySerializer(many=True, read_only=True)

    # Дополнительные вычисляемые поля
    is_overdue = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'tutor', 'student', 'parent',
            'amount', 'description', 'status', 'status_display',
            'due_date', 'sent_at', 'viewed_at', 'paid_at',
            'payment', 'enrollment', 'telegram_message_id',
            'created_at', 'updated_at', 'is_overdue', 'status_history'
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Краткая информация о счете для списков.
    Используется для list endpoint (оптимизация производительности).
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)
    tutor_name = serializers.CharField(source='tutor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'student_name', 'parent_name', 'tutor_name',
            'amount', 'status', 'status_display', 'due_date',
            'created_at', 'is_overdue'
        ]


class CreateInvoiceSerializer(serializers.Serializer):
    """
    Сериализатор для создания нового счета.
    Валидирует входные данные перед передачей в сервис.
    """
    student_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        required=True,
        max_length=2000,
        allow_blank=False
    )
    due_date = serializers.DateField(required=True)
    enrollment_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_student_id(self, value):
        """Проверка существования студента"""
        try:
            student = User.objects.get(id=value, role='student')
        except User.DoesNotExist:
            raise serializers.ValidationError(f'Студент с ID {value} не найден')

        # Проверка что у студента есть профиль и родитель
        if not hasattr(student, 'student_profile'):
            raise serializers.ValidationError('У студента нет профиля')

        if not student.student_profile.parent:
            raise serializers.ValidationError('У студента не указан родитель')

        return value

    def validate_due_date(self, value):
        """Проверка что срок оплаты не в прошлом"""
        if value < timezone.now().date():
            raise serializers.ValidationError('Срок оплаты не может быть в прошлом')
        return value

    def validate_description(self, value):
        """Проверка описания"""
        if not value.strip():
            raise serializers.ValidationError('Описание не может быть пустым')
        return value.strip()

    def validate(self, attrs):
        """Комплексная валидация"""
        # Проверка enrollment_id если указан
        enrollment_id = attrs.get('enrollment_id')
        if enrollment_id:
            from materials.models import SubjectEnrollment
            try:
                enrollment = SubjectEnrollment.objects.select_related(
                    'student', 'subject', 'teacher'
                ).get(id=enrollment_id)

                # Проверяем что enrollment относится к указанному студенту
                student_id = attrs.get('student_id')
                if enrollment.student_id != student_id:
                    raise serializers.ValidationError({
                        'enrollment_id': 'Зачисление не относится к указанному студенту'
                    })

            except SubjectEnrollment.DoesNotExist:
                raise serializers.ValidationError({
                    'enrollment_id': f'Зачисление с ID {enrollment_id} не найдено'
                })

        return attrs


class SendInvoiceSerializer(serializers.Serializer):
    """
    Пустой сериализатор для action endpoint send.
    Не требует входных данных, только ID счета из URL.
    """
    pass


class ViewInvoiceSerializer(serializers.Serializer):
    """
    Пустой сериализатор для action endpoint mark_viewed.
    Не требует входных данных, только ID счета из URL.
    """
    pass


class TutorStatisticsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики тьютора
    """
    period = serializers.CharField()
    statistics = serializers.DictField(child=serializers.Field())


class PaymentHistoryItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для элемента истории платежей
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    tutor_name = serializers.CharField(source='tutor.get_full_name', read_only=True)
    subject_name = serializers.CharField(
        source='enrollment.subject.name',
        read_only=True,
        allow_null=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'student_name', 'tutor_name', 'subject_name',
            'amount', 'status', 'status_display',
            'paid_at', 'description', 'due_date', 'created_at'
        ]


class RevenueReportSerializer(serializers.Serializer):
    """
    Сериализатор для отчета по выручке
    """
    period = serializers.DictField()
    summary = serializers.DictField()
    breakdown = serializers.ListField(child=serializers.DictField())


class OutstandingInvoiceSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просроченных счетов
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'student_name', 'parent_name',
            'amount', 'status', 'status_display',
            'due_date', 'days_overdue', 'created_at', 'description'
        ]

    def get_days_overdue(self, obj) -> int:
        """
        Вычисление количества дней просрочки
        """
        from django.utils import timezone
        today = timezone.now().date()
        if obj.due_date < today and obj.status in [
            Invoice.Status.SENT,
            Invoice.Status.VIEWED,
            Invoice.Status.OVERDUE
        ]:
            delta = today - obj.due_date
            return delta.days
        return 0
