from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, TutorProfileSerializer,
    ParentProfileSerializer, ChangePasswordSerializer,
    SupabaseUserRegistrationSerializer, SupabaseUserLoginSerializer,
    SupabaseUserProfileSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Регистрация нового пользователя
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Регистрация успешна'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Вход пользователя
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Вход выполнен успешно'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


# Представления для работы с Supabase
@api_view(['POST'])
@permission_classes([AllowAny])
def supabase_register(request):
    """
    Регистрация нового пользователя через Supabase
    """
    serializer = SupabaseUserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        return Response({
            'user': result['user'],
            'session': result.get('session'),
            'message': 'Регистрация успешна'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def supabase_login(request):
    """
    Вход пользователя через Supabase
    """
    serializer = SupabaseUserLoginSerializer(data=request.data)
    if serializer.is_valid():
        supabase_user = serializer.validated_data['supabase_user']
        supabase_session = serializer.validated_data['supabase_session']
        
        return Response({
            'user': supabase_user,
            'session': supabase_session,
            'message': 'Вход выполнен успешно'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def supabase_logout(request):
    """
    Выход пользователя через Supabase
    """
    from .supabase_service import supabase_auth_service
    
    result = supabase_auth_service.sign_out()
    
    if result['success']:
        return Response({
            'message': 'Выход выполнен успешно'
        })
    else:
        return Response({
            'error': result.get('error', 'Ошибка выхода')
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def supabase_profile(request):
    """
    Получение профиля пользователя из Supabase
    """
    from .supabase_service import supabase_auth_service
    
    # Получаем токен из заголовка Authorization
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return Response({
            'error': 'Требуется токен авторизации'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    token = auth_header.split(' ')[1]
    
    try:
        # Устанавливаем токен в клиент
        supabase_auth_service.client.auth.set_session(token)
        
        # Получаем текущего пользователя
        user = supabase_auth_service.get_user()
        
        if user:
            # Получаем профиль пользователя
            profile = supabase_auth_service.get_user_profile(user['id'])
            roles = supabase_auth_service.get_user_roles(user['id'])
            
            return Response({
                'user': user,
                'profile': profile,
                'roles': roles
            })
        else:
            return Response({
                'error': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': f'Ошибка получения профиля: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
def supabase_update_profile(request):
    """
    Обновление профиля пользователя в Supabase
    """
    from .supabase_service import supabase_auth_service
    
    # Получаем токен из заголовка Authorization
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return Response({
            'error': 'Требуется токен авторизации'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    token = auth_header.split(' ')[1]
    
    try:
        # Устанавливаем токен в клиент
        supabase_auth_service.client.auth.set_session(token)
        
        # Получаем текущего пользователя
        user = supabase_auth_service.get_user()
        
        if user:
            # Подготавливаем данные для обновления
            profile_data = {}
            
            if 'full_name' in request.data:
                profile_data['full_name'] = request.data['full_name']
            if 'phone' in request.data:
                profile_data['phone'] = request.data['phone']
            if 'avatar_url' in request.data:
                profile_data['avatar_url'] = request.data['avatar_url']
            
            # Обновляем профиль
            result = supabase_auth_service.update_user_profile(user['id'], profile_data)
            
            if result['success']:
                return Response({
                    'message': 'Профиль обновлен успешно',
                    'profile': result['data']
                })
            else:
                return Response({
                    'error': result.get('error', 'Ошибка обновления профиля')
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': f'Ошибка обновления профиля: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
