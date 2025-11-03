from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .serializers import (
    UserLoginSerializer, UserSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, TutorProfileSerializer,
    ParentProfileSerializer, ChangePasswordSerializer
)
from .supabase_service import SupabaseAuthService


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
@csrf_exempt
def login_view(request):
    """
    Вход пользователя через Django аутентификацию (поддерживает email и username)
    """
    try:
        # Логируем входящие данные
        print(f"Login attempt - Request data: {request.data}")
        
        # Валидируем данные
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data.get('email')
        username = serializer.validated_data.get('username')
        password = serializer.validated_data['password']
        
        # Логируем попытку входа
        identifier = email or username
        print(f"Login attempt for: {identifier}")
        
        # Проверяем аутентификацию через Django; если не удалось, пробуем через Supabase
        from django.contrib.auth import authenticate

        # Пытаемся найти локального пользователя по email или username
        user = None
        if email:
            user = User.objects.filter(email=email).first()
            print(f"User found by email: {user}")
        elif username:
            user = User.objects.filter(username=username).first()
            print(f"User found by username: {user}")
        
        # Если пользователь найден по username, но у него есть email, используем email для Supabase
        if user and not email and user.email:
            email = user.email

        authenticated_user = None
        if user:
            # Если это суперпользователь и у него нет пригодного пароля (хэш отсутствует),
            # установим введенный пароль как новый и продолжим обычную аутентификацию.
            try:
                if getattr(user, 'is_superuser', False) and not user.has_usable_password():
                    user.set_password(password)
                    user.save(update_fields=['password'])
            except Exception:
                pass

            authenticated_user = authenticate(username=user.username, password=password)

        if not authenticated_user:
            # Фолбэк на Supabase: в проектах, где пароли не хранятся локально
            try:
                supabase = SupabaseAuthService()
                sb_result = getattr(supabase, 'sign_in', None)
                if callable(sb_result):
                    sb_login = supabase.sign_in(email=email, password=password)
                else:
                    sb_login = {"success": False, "error": "Supabase не настроен"}

                if sb_login.get('success'):
                    # Если локального пользователя нет — сообщаем, чтобы создать/синхронизировать
                    if not user:
                        return Response({
                            'success': False,
                            'error': 'Пользователь найден в Supabase, но отсутствует локально. Обратитесь к администратору.'
                        }, status=status.HTTP_403_FORBIDDEN)

                    # Признаём пользователя аутентифицированным без проверки локального пароля
                    authenticated_user = user if user.is_active else None
                else:
                    # Нет успеха ни в Django, ни в Supabase
                    return Response({
                        'success': False,
                        'error': sb_login.get('error') or 'Неверные учетные данные'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                return Response({
                    'success': False,
                    'error': f'Ошибка аутентификации через Supabase: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Если дошли до сюда — пользователь аутентифицирован (либо Django, либо Supabase)
        if authenticated_user and authenticated_user.is_active:
            token, _ = Token.objects.get_or_create(user=authenticated_user)
            return Response({
                'success': True,
                'data': {
                    'token': token.key,
                    'user': UserSerializer(authenticated_user).data,
                    'message': 'Вход выполнен успешно'
                }
            })

        return Response({
            'success': False,
            'error': 'Учетная запись отключена или недоступна'
        }, status=status.HTTP_403_FORBIDDEN)
            
    except Exception as e:
        return Response({
            'success': False,
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


