from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .serializers import (
    UserLoginSerializer, UserSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, TutorProfileSerializer,
    ParentProfileSerializer, ChangePasswordSerializer, CurrentUserProfileSerializer
)
from .supabase_service import SupabaseAuthService


@ratelimit(key='ip', rate='5/m', method='POST')  # 5 попыток входа в минуту с одного IP
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
@csrf_exempt
def login_view(request):
    """
    Вход пользователя через Django аутентификацию (поддерживает email и username)
    """
    try:
        # Логируем входящие данные БЕЗ пароля для безопасности
        safe_data = {k: v for k, v in request.data.items() if k != 'password'}
        print(f"Login attempt - Request data: {safe_data}")

        # Валидируем данные
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Логируем ошибки БЕЗ пароля
            safe_errors = {k: v for k, v in serializer.errors.items() if k != 'password'}
            print(f"Validation errors: {safe_errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data.get('email')
        username = serializer.validated_data.get('username')
        password = serializer.validated_data['password']

        # Логируем попытку входа с идентификатором (БЕЗ пароля)
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
            # ВАЖНО: Только если Supabase ДЕЙСТВИТЕЛЬНО настроен (не в development режиме)
            try:
                supabase = SupabaseAuthService()

                # Проверяем что Supabase реально настроен (не mock mode)
                if not supabase.is_mock:
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
                else:
                    # Supabase в mock режиме (development), не фоллбэчим на него
                    # Возвращаем ошибку аутентификации Django
                    print(f"Login failed for {identifier}: Invalid credentials (Supabase disabled in development)")
                    return Response({
                        'success': False,
                        'error': 'Неверные учетные данные'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                # Если ошибка при работе с Supabase - считаем что он недоступен
                print(f"Supabase error (ignoring in development): {str(e)}")
                return Response({
                    'success': False,
                    'error': 'Неверные учетные данные'
                }, status=status.HTTP_401_UNAUTHORIZED)

        # Если дошли до сюда — пользователь аутентифицирован (либо Django, либо Supabase)
        if authenticated_user and authenticated_user.is_active:
            # Удаляем старый токен и создаем новый, чтобы избежать проблем с устаревшими токенами
            Token.objects.filter(user=authenticated_user).delete()
            token = Token.objects.create(user=authenticated_user)

            print(f"[login] Created new token for user: {authenticated_user.username}, role: {authenticated_user.role}")
            
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def refresh_token_view(request):
    """
    Обновление токена аутентификации
    Удаляет старый токен и создает новый для текущего пользователя
    """
    try:
        user = request.user

        # Удаляем старый токен
        Token.objects.filter(user=user).delete()

        # Создаем новый токен
        new_token = Token.objects.create(user=user)

        print(f"[refresh_token] Created new token for user: {user.username}, role: {user.role}")

        return Response({
            'success': True,
            'data': {
                'token': new_token.key,
                'user': UserSerializer(user).data,
                'message': 'Токен успешно обновлен'
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"[refresh_token] Error: {str(e)}")
        return Response({
            'success': False,
            'error': f'Ошибка обновления токена: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    Получить список пользователей с фильтрацией по роли
    Доступно для аутентифицированных пользователей (тьюторы, администраторы)

    Query parameters:
    - role: фильтр по роли (student, teacher, tutor, parent)
    - limit: ограничение количества результатов (по умолчанию 50, максимум 100)
    """
    role = request.query_params.get('role')
    limit = request.query_params.get('limit', 50)

    try:
        limit = int(limit)
        if limit < 1 or limit > 100:
            limit = 50
    except (ValueError, TypeError):
        limit = 50

    # Фильтруем по роли, если указана
    # Оптимизация: используем select_related для профилей
    queryset = User.objects.filter(is_active=True).select_related('student_profile', 'teacher_profile', 'parent_profile')
    if role:
        queryset = queryset.filter(role=role)
    
    # Подсчитываем количество до применения лимита
    total_count = queryset.count()
    
    # Сортируем по дате создания и применяем лимит
    queryset = queryset.order_by('-date_joined')
    if limit and limit > 0:
        queryset = queryset[:limit]
    
    # Сериализуем данные
    serializer = UserSerializer(queryset, many=True)
    
    # Логируем для отладки
    print(f"[list_users] Role filter: {role}, Limit: {limit}, Total users: {total_count}")
    print(f"[list_users] Serialized data count: {len(serializer.data)}")
    if len(serializer.data) > 0:
        print(f"[list_users] First user sample: id={serializer.data[0].get('id')}, email={serializer.data[0].get('email')}")
    else:
        print(f"[list_users] WARNING: No users returned! Total count was: {total_count}")
    
    # Возвращаем массив напрямую
    return Response(serializer.data, status=status.HTTP_200_OK)


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


class CurrentUserProfileView(APIView):
    """
    API endpoint для получения профиля текущего авторизованного пользователя.

    Поддерживает все 4 роли:
    - Student (StudentProfile)
    - Teacher (TeacherProfile)
    - Tutor (TutorProfile)
    - Parent (ParentProfile)

    Методы:
    - GET: Получить полный профиль текущего пользователя с соответствующими данными

    Возвращает:
    {
        "data": {
            "user": {
                "id": int,
                "email": str,
                "first_name": str,
                "last_name": str,
                "role": str,
                "role_display": str,
                ...
            },
            "profile": {
                // role-specific profile data
                // или null если профиль не существует
            }
        },
        "message": "Профиль успешно получен",
        "errors": null
    }

    Возвращаемые статус коды:
    - 200 OK: Профиль успешно получен
    - 401 Unauthorized: Пользователь не авторизован
    - 404 Not Found: Профиль пользователя не существует
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        """
        Получить профиль текущего авторизованного пользователя.
        Возвращает 404 если профиля нет (не создает автоматически).

        Returns:
            Response: JSON с профилем пользователя или 404 если профиля нет
        """
        try:
            user = request.user

            # Проверяем что пользователь существует
            if not user or not user.is_authenticated:
                return Response(
                    {
                        'data': None,
                        'message': 'Пользователь не авторизован',
                        'errors': 'Authentication required'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Получаем профиль с one query (БЕЗ автоматического создания)
            profile_found = False
            try:
                if user.role == User.Role.STUDENT:
                    profile = StudentProfile.objects.select_related('user').get(user=user)
                elif user.role == User.Role.TEACHER:
                    profile = TeacherProfile.objects.select_related('user').get(user=user)
                elif user.role == User.Role.TUTOR:
                    profile = TutorProfile.objects.select_related('user').get(user=user)
                elif user.role == User.Role.PARENT:
                    profile = ParentProfile.objects.select_related('user').get(user=user)
                else:
                    profile = None
                profile_found = True
            except (StudentProfile.DoesNotExist, TeacherProfile.DoesNotExist,
                    TutorProfile.DoesNotExist, ParentProfile.DoesNotExist):
                # Профиль не существует - возвращаем 404
                profile = None
                profile_found = False

            # Prepare response data
            user_serializer = UserSerializer(user)
            user_data = user_serializer.data

            if not profile_found:
                # Profile not found - return 200 OK with None profile
                return Response(
                    {
                        'data': {
                            'user': user_data,
                            'profile': None
                        },
                        'message': 'Профиль еще не создан',
                        'errors': None
                    },
                    status=status.HTTP_200_OK
                )

            # Profile found - serialize it based on role
            profile_data = None
            if user.role == User.Role.STUDENT:
                profile_data = StudentProfileSerializer(profile).data
            elif user.role == User.Role.TEACHER:
                profile_data = TeacherProfileSerializer(profile).data
            elif user.role == User.Role.TUTOR:
                profile_data = TutorProfileSerializer(profile).data
            elif user.role == User.Role.PARENT:
                profile_data = ParentProfileSerializer(profile).data

            # Успешный ответ с найденным профилем
            return Response(
                {
                    'data': {
                        'user': user_data,
                        'profile': profile_data
                    },
                    'message': 'Профиль успешно получен',
                    'errors': None
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            print(f"[CurrentUserProfileView] Критическая ошибка: {str(e)}")
            return Response(
                {
                    'data': None,
                    'message': 'Ошибка при получении профиля',
                    'errors': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


