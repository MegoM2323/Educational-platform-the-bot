from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile


class UserLoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа пользователя (поддерживает email и username)
    """
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')
        password = attrs.get('password')
        
        # Должен быть указан либо email, либо username
        if not email and not username:
            raise serializers.ValidationError('Необходимо указать email или имя пользователя')
        
        if not password:
            raise serializers.ValidationError('Необходимо указать пароль')
        
        # Если передан email, используем его; иначе используем username
        if email:
            attrs['email'] = email.strip() if email else None
            attrs['username'] = None
        elif username:
            attrs['username'] = username.strip() if username else None
            attrs['email'] = None
        
        attrs['password'] = password
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения пользователя
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'phone', 'avatar', 'is_verified', 'is_staff', 'date_joined', 'full_name'
        )
        read_only_fields = ('id', 'date_joined', 'is_verified', 'is_staff')
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля студента
    """
    user = UserSerializer(read_only=True)
    tutor_name = serializers.CharField(source='tutor.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user', 'grade', 'goal', 'tutor', 'tutor_name',
            'parent', 'parent_name', 'progress_percentage', 'streak_days',
            'total_points', 'accuracy_percentage'
        )


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля преподавателя
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TeacherProfile
        fields = (
            'id', 'user', 'subject', 'experience_years', 'bio'
        )


class TutorProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля тьютора
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TutorProfile
        fields = (
            'id', 'user', 'specialization', 'experience_years', 'bio'
        )


class ParentProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля родителя
    """
    user = UserSerializer(read_only=True)
    children = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = ParentProfile
        fields = (
            'id', 'user', 'children'
        )


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для смены пароля
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Новые пароли не совпадают")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value


