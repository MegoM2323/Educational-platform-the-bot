from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .supabase_service import supabase_auth_service


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = (
            'email', 'password', 'password_confirm', 'first_name', 'last_name',
            'phone', 'role'
        )
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        # Добавляем username = email для совместимости с AbstractUser
        validated_data['username'] = validated_data['email']
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Создаем соответствующий профиль
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user)
        elif user.role == User.Role.TEACHER:
            TeacherProfile.objects.create(user=user)
        elif user.role == User.Role.TUTOR:
            TutorProfile.objects.create(user=user)
        elif user.role == User.Role.PARENT:
            ParentProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа пользователя
    """
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные')
            if not user.is_active:
                raise serializers.ValidationError('Аккаунт деактивирован')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Необходимо указать email и пароль')
        
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
            'phone', 'avatar', 'is_verified', 'date_joined', 'full_name'
        )
        read_only_fields = ('id', 'date_joined', 'is_verified')
    
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


# Сериализаторы для работы с Supabase
class SupabaseUserRegistrationSerializer(serializers.Serializer):
    """
    Сериализатор для регистрации пользователя через Supabase
    """
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=[
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('tutor', 'Тьютор'),
        ('parent', 'Родитель'),
    ])
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs
    
    def create(self, validated_data):
        password_confirm = validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Подготавливаем данные для Supabase
        user_data = {
            'full_name': f"{validated_data['first_name']} {validated_data['last_name']}",
            'role': validated_data['role']
        }
        
        # Регистрация через Supabase
        result = supabase_auth_service.sign_up(
            email=validated_data['email'],
            password=password,
            user_data=user_data
        )
        
        if result['success']:
            return result
        else:
            raise serializers.ValidationError(result.get('error', 'Ошибка регистрации'))


class SupabaseUserLoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа пользователя через Supabase
    """
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Вход через Supabase
        result = supabase_auth_service.sign_in(email=email, password=password)
        
        if result['success']:
            attrs['supabase_user'] = result['user']
            attrs['supabase_session'] = result['session']
        else:
            raise serializers.ValidationError(result.get('error', 'Ошибка входа'))
        
        return attrs


class SupabaseUserProfileSerializer(serializers.Serializer):
    """
    Сериализатор для профиля пользователя из Supabase
    """
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    avatar_url = serializers.URLField(read_only=True)
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        # Получаем профиль из Supabase
        profile = supabase_auth_service.get_user_profile(instance['id'])
        roles = supabase_auth_service.get_user_roles(instance['id'])
        
        if profile:
            return {
                'id': instance['id'],
                'email': instance['email'],
                'full_name': profile.get('full_name', ''),
                'phone': profile.get('phone', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'roles': roles,
                'created_at': profile.get('created_at'),
                'updated_at': profile.get('updated_at'),
            }
        return instance
