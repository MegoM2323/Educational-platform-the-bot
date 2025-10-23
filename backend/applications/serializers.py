from rest_framework import serializers
from rest_framework import serializers
from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заявок
    """
    class Meta:
        model = Application
        fields = [
            'id', 'student_name', 'parent_name', 'phone', 'email',
            'grade', 'goal', 'message', 'status', 'created_at',
            'updated_at', 'processed_at', 'notes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заявок
    """
    class Meta:
        model = Application
        fields = [
            'student_name', 'parent_name', 'phone', 'email',
            'grade', 'goal', 'message'
        ]
    
    def validate_phone(self, value):
        """
        Валидация номера телефона
        """
        if not value:
            raise serializers.ValidationError("Телефон обязателен")
        
        # Простая валидация формата телефона
        import re
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        if not re.match(phone_pattern, value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
            raise serializers.ValidationError("Неверный формат номера телефона")
        
        return value
    
    def validate_grade(self, value):
        """
        Валидация класса
        """
        if value < 1 or value > 11:
            raise serializers.ValidationError("Класс должен быть от 1 до 11")
        return value


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления статуса заявки
    """
    class Meta:
        model = Application
        fields = ['status', 'notes']
    
    def validate_status(self, value):
        """
        Валидация статуса
        """
        valid_statuses = [choice[0] for choice in Application.Status.choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Недопустимый статус. Доступные: {', '.join(valid_statuses)}")
        return value
