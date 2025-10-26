from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .serializers import (
    UserLoginSerializer, UserSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, TutorProfileSerializer,
    ParentProfileSerializer, ChangePasswordSerializer
)
from .supabase_service import SupabaseAuthService


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Вход пользователя через Supabase
    """
    try:
        # Валидируем данные
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # Проверяем аутентификацию через Supabase
        supabase_service = SupabaseAuthService()
        result = supabase_service.sign_in(email, password)
        
        if result['success']:
            # Находим или создаем пользователя в Django
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Если пользователь не найден в Django, создаем его
                user = User.objects.create(
                    email=email,
                    username=email,  # username = email для совместимости
                    first_name=result.get('user', {}).get('user_metadata', {}).get('full_name', '').split(' ')[0] if result.get('user', {}).get('user_metadata', {}).get('full_name') else '',
                    last_name=' '.join(result.get('user', {}).get('user_metadata', {}).get('full_name', '').split(' ')[1:]) if result.get('user', {}).get('user_metadata', {}).get('full_name') else '',
                    phone=result.get('user', {}).get('user_metadata', {}).get('phone', ''),
                    role=result.get('user', {}).get('user_metadata', {}).get('role', 'student'),
                    is_active=True,
                    is_verified=True
                )
            
            # Создаем токен для Django API
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Вход выполнен успешно',
                'supabase_session': result.get('session')
            })
        else:
            return Response({
                'error': result.get('error', 'Неверные учетные данные')
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        return Response({
            'error': f'Ошибка сервера: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Выход пользователя
    """
    try:
        request.user.auth_token.delete()
    except:
        pass
    logout(request)
    return Response({'message': 'Выход выполнен успешно'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Получение профиля текущего пользователя
    """
    user = request.user
    user_data = UserSerializer(user).data
    
    # Добавляем данные профиля в зависимости от роли
    if user.role == User.Role.STUDENT:
        try:
            student_profile = user.student_profile
            profile_data = StudentProfileSerializer(student_profile).data
        except StudentProfile.DoesNotExist:
            profile_data = None
    elif user.role == User.Role.TEACHER:
        try:
            teacher_profile = user.teacher_profile
            profile_data = TeacherProfileSerializer(teacher_profile).data
        except TeacherProfile.DoesNotExist:
            profile_data = None
    elif user.role == User.Role.TUTOR:
        try:
            tutor_profile = user.tutor_profile
            profile_data = TutorProfileSerializer(tutor_profile).data
        except TutorProfile.DoesNotExist:
            profile_data = None
    elif user.role == User.Role.PARENT:
        try:
            parent_profile = user.parent_profile
            profile_data = ParentProfileSerializer(parent_profile).data
        except ParentProfile.DoesNotExist:
            profile_data = None
    else:
        profile_data = None
    
    return Response({
        'user': user_data,
        'profile': profile_data
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Обновление профиля пользователя
    """
    user = request.user
    user_serializer = UserSerializer(user, data=request.data, partial=True)
    
    if user_serializer.is_valid():
        user_serializer.save()
        
        # Обновляем профиль в зависимости от роли
        if user.role == User.Role.STUDENT:
            try:
                student_profile = user.student_profile
                profile_serializer = StudentProfileSerializer(
                    student_profile, data=request.data, partial=True
                )
                if profile_serializer.is_valid():
                    profile_serializer.save()
            except StudentProfile.DoesNotExist:
                pass
        elif user.role == User.Role.TEACHER:
            try:
                teacher_profile = user.teacher_profile
                profile_serializer = TeacherProfileSerializer(
                    teacher_profile, data=request.data, partial=True
                )
                if profile_serializer.is_valid():
                    profile_serializer.save()
            except TeacherProfile.DoesNotExist:
                pass
        elif user.role == User.Role.TUTOR:
            try:
                tutor_profile = user.tutor_profile
                profile_serializer = TutorProfileSerializer(
                    tutor_profile, data=request.data, partial=True
                )
                if profile_serializer.is_valid():
                    profile_serializer.save()
            except TutorProfile.DoesNotExist:
                pass
        elif user.role == User.Role.PARENT:
            try:
                parent_profile = user.parent_profile
                profile_serializer = ParentProfileSerializer(
                    parent_profile, data=request.data, partial=True
                )
                if profile_serializer.is_valid():
                    profile_serializer.save()
            except ParentProfile.DoesNotExist:
                pass
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Профиль обновлен'
        })
    
    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Смена пароля
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Пароль успешно изменен'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentProfileView(generics.RetrieveUpdateAPIView):
    """
    Управление профилем студента
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.student_profile


class TeacherProfileView(generics.RetrieveUpdateAPIView):
    """
    Управление профилем преподавателя
    """
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.teacher_profile


class TutorProfileView(generics.RetrieveUpdateAPIView):
    """
    Управление профилем тьютора
    """
    serializer_class = TutorProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.tutor_profile


class ParentProfileView(generics.RetrieveUpdateAPIView):
    """
    Управление профилем родителя
    """
    serializer_class = ParentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.parent_profile


