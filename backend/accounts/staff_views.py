from typing import Any, Dict

from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import BasePermission, IsAdminUser
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response

from .models import User, TeacherProfile, TutorProfile
from .serializers import UserSerializer, TeacherProfileSerializer, TutorProfileSerializer
from .supabase_service import SupabaseAuthService
from .supabase_sync import SupabaseSyncService


class CSRFExemptSessionAuthentication(SessionAuthentication):
    """
    Кастомный класс аутентификации, который отключает CSRF проверку для API views.
    Используется для POST запросов, где фронтенд использует токены.
    """
    def enforce_csrf(self, request):
        # Отключаем CSRF проверку для API запросов
        return


class IsStaffOrAdmin(BasePermission):
    """
    Разрешение для пользователей с правами staff, superuser или ролью TUTOR.
    Аналогично стандартному IsAdminUser, но с дополнительной поддержкой роли TUTOR.
    """
    def has_permission(self, request, view):
        # Логируем все запросы для отладки
        print(f"[IsStaffOrAdmin.has_permission] Called for method: {request.method}")
        print(f"[IsStaffOrAdmin.has_permission] User: {request.user}")
        print(f"[IsStaffOrAdmin.has_permission] User type: {type(request.user)}")
        
        # Проверяем, что пользователь аутентифицирован
        if not request.user or not request.user.is_authenticated:
            print(f"[IsStaffOrAdmin] User not authenticated: {request.user}")
            return False
        
        # Проверяем, что пользователь активен (как в стандартном IsAdminUser)
        if not request.user.is_active:
            print(f"[IsStaffOrAdmin] User is not active: {request.user.username}")
            return False
        
        # Логируем информацию о пользователе для отладки
        user_info = {
            'username': request.user.username,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'is_active': request.user.is_active,
            'role': getattr(request.user, 'role', None),
            'is_authenticated': request.user.is_authenticated
        }
        print(f"[IsStaffOrAdmin] Checking permission for user: {user_info}")
        
        # Разрешаем доступ для staff, superuser или тьюторов
        # Стандартный IsAdminUser проверяет: user.is_staff and user.is_active
        has_access = (
            (request.user.is_staff and request.user.is_active) or 
            request.user.is_superuser or 
            getattr(request.user, 'role', None) == User.Role.TUTOR
        )
        print(f"[IsStaffOrAdmin] Access granted: {has_access}")
        return has_access


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def list_staff(request):
    """Список преподавателей или тьюторов (admin-only).

    Query params:
      - role: 'teacher' | 'tutor' (обязательный)
    """
    role = request.query_params.get('role')
    if role not in (User.Role.TEACHER, User.Role.TUTOR):
        return Response({
            'detail': "Параметр 'role' обязателен и должен быть 'teacher' или 'tutor'"
        }, status=status.HTTP_400_BAD_REQUEST)

    if role == User.Role.TEACHER:
        # Получаем всех пользователей с ролью TEACHER, а не только тех, у кого есть TeacherProfile
        # Используем prefetch_related для оптимизации запросов к TeacherSubject
        # Сортируем по дате создания (новые первыми)
        users = User.objects.filter(
            role=User.Role.TEACHER, 
            is_active=True
        ).prefetch_related(
            'teacher_subjects__subject'
        ).order_by('-date_joined', '-id')
        
        print(f"[list_staff] Found {users.count()} teachers with role={role}")
        
        # Создаем список результатов с профилями
        results = []
        for user in users:
            try:
                # Пытаемся получить профиль - используем get() для явной проверки
                # Это гарантирует, что мы получим свежие данные из базы
                profile = TeacherProfile.objects.select_related('user').get(user=user)
                # Используем сериализатор профиля, если он существует
                profile_data = TeacherProfileSerializer(profile).data
                results.append(profile_data)
                print(f"[list_staff] Added teacher with profile: {user.username} (id={user.id}, profile_id={profile.id})")
            except TeacherProfile.DoesNotExist:
                # Если профиля нет, создаем данные вручную в формате, который ожидает фронтенд
                from materials.models import TeacherSubject
                # Получаем предметы преподавателя через TeacherSubject
                # Используем prefetched данные, если они есть
                if hasattr(user, '_prefetched_objects_cache') and 'teacher_subjects' in user._prefetched_objects_cache:
                    teacher_subjects = user._prefetched_objects_cache['teacher_subjects']
                    subjects = [ts.subject.name for ts in teacher_subjects if ts.is_active]
                else:
                    # Если prefetch не сработал, делаем отдельный запрос
                    teacher_subjects = TeacherSubject.objects.filter(
                        teacher=user, 
                        is_active=True
                    ).select_related('subject')
                    subjects = [ts.subject.name for ts in teacher_subjects]
                
                # Используем первый предмет как основной, или пустую строку
                main_subject = subjects[0] if subjects else ''
                
                # Используем ID пользователя, так как профиля нет
                # Фронтенд ожидает число в поле id
                results.append({
                    'id': user.id,  # Используем ID пользователя
                    'user': UserSerializer(user).data,
                    'subject': main_subject,
                    'experience_years': 0,
                    'bio': '',
                    'subjects_list': subjects  # Добавляем список предметов для совместимости
                })
                print(f"[list_staff] Added teacher without profile: {user.username} (id={user.id})")
        
        print(f"[list_staff] Returning {len(results)} teachers")
        return Response({'results': results})
    else:
        # Для тьюторов аналогично
        users = User.objects.filter(
            role=User.Role.TUTOR, 
            is_active=True
        ).order_by('-date_joined', '-id')
        
        print(f"[list_staff] Found {users.count()} tutors with role={role}")
        
        results = []
        for user in users:
            try:
                # Пытаемся получить профиль - используем get() для явной проверки
                profile = TutorProfile.objects.select_related('user').get(user=user)
                profile_data = TutorProfileSerializer(profile).data
                results.append(profile_data)
                print(f"[list_staff] Added tutor with profile: {user.username} (id={user.id}, profile_id={profile.id})")
            except TutorProfile.DoesNotExist:
                results.append({
                    'id': user.id,  # Используем ID пользователя
                    'user': UserSerializer(user).data,
                    'specialization': '',
                    'experience_years': 0,
                    'bio': ''
                })
                print(f"[list_staff] Added tutor without profile: {user.username} (id={user.id})")
        
        print(f"[list_staff] Returning {len(results)} tutors")
        return Response({'results': results})


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def create_staff(request):
    """Создание преподавателя или тьютора с одноразовой выдачей логина/пароля (admin-only).

    Body JSON:
      - role: 'teacher' | 'tutor'
      - email: str
      - first_name: str
      - last_name: str
      - subject (для teacher) | specialization (для tutor)
      - experience_years?: number
      - bio?: string
    Возвращает: { user, credentials: { login, password } }
    """
    # Логируем начало запроса
    print(f"[create_staff] POST request received")
    print(f"[create_staff] User: {request.user}")
    print(f"[create_staff] User authenticated: {request.user.is_authenticated if request.user else False}")
    print(f"[create_staff] User is_staff: {request.user.is_staff if request.user else False}")
    print(f"[create_staff] User is_superuser: {request.user.is_superuser if request.user else False}")
    
    payload: Dict[str, Any] = request.data or {}
    role = payload.get('role')
    email = (payload.get('email') or '').strip().lower()
    first_name = (payload.get('first_name') or '').strip()
    last_name = (payload.get('last_name') or '').strip()

    if role not in (User.Role.TEACHER, User.Role.TUTOR):
        return Response({'detail': "role должен быть 'teacher' или 'tutor'"}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'detail': 'email обязателен'}, status=status.HTTP_400_BAD_REQUEST)
    if not first_name or not last_name:
        return Response({'detail': 'first_name и last_name обязательны'}, status=status.HTTP_400_BAD_REQUEST)

    profile_kwargs: Dict[str, Any] = {}
    if role == User.Role.TEACHER:
        subject = (payload.get('subject') or '').strip()
        if not subject:
            return Response({'detail': 'subject обязателен для teacher'}, status=status.HTTP_400_BAD_REQUEST)
        profile_kwargs['subject'] = subject
    else:
        specialization = (payload.get('specialization') or '').strip()
        if not specialization:
            return Response({'detail': 'specialization обязателен для tutor'}, status=status.HTTP_400_BAD_REQUEST)
        profile_kwargs['specialization'] = specialization

    if payload.get('experience_years') is not None:
        try:
            profile_kwargs['experience_years'] = int(payload.get('experience_years'))
        except (TypeError, ValueError):
            return Response({'detail': 'experience_years должен быть числом'}, status=status.HTTP_400_BAD_REQUEST)
    if payload.get('bio') is not None:
        profile_kwargs['bio'] = str(payload.get('bio'))

    # Генерируем надежный пароль
    generated_password = get_random_string(length=12)

    # Регистрируем через Supabase и синхронизируем в Django
    sb_auth = SupabaseAuthService()
    sb_sync = SupabaseSyncService()

    try:
        with transaction.atomic():
            django_user = None
            # Попытка через Supabase Admin API, если доступен service_key
            sb_result: Dict[str, Any] | None = None
            try:
                if getattr(sb_auth, 'service_key', None):
                    # Преобразуем enum роль в строку для Supabase
                    role_str = role.value if hasattr(role, 'value') else str(role)
                    print(f"[create_staff] Creating user in Supabase with role: {role_str}")
                    sb_result = sb_auth.sign_up(
                        email=email,
                        password=generated_password,
                        user_data={
                            'role': role_str,  # Передаем строковую роль
                            'first_name': first_name,
                            'last_name': last_name,
                        }
                    )
            except Exception:
                sb_result = None

            if sb_result and sb_result.get('success') and sb_result.get('user'):
                django_user = sb_sync.create_django_user_from_supabase(sb_result['user'])
                if not django_user:
                    return Response({'detail': 'Не удалось создать пользователя в Django после Supabase'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                # Гарантируем, что username совпадает с email для упрощения входа
                if django_user.username != email:
                    django_user.username = email
                    django_user.save(update_fields=['username'])
                # Гарантируем, что роль правильно установлена
                if django_user.role != role:
                    print(f"[create_staff] Role mismatch: user has {django_user.role}, expected {role}. Updating...")
                    django_user.role = role
                    django_user.save(update_fields=['role'])
            else:
                # Фолбэк: создаем локально в Django без Supabase
                username = email
                if User.objects.filter(username=username).exists():
                    base = email.split('@')[0]
                    i = 1
                    username = f"{base}{i}@local"
                    while User.objects.filter(username=username).exists():
                        i += 1
                        username = f"{base}{i}@local"
                django_user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=True,
                )
                django_user.set_password(generated_password)
                django_user.save()

            # Обновим ФИО/роль на всякий случай
            django_user.first_name = first_name
            django_user.last_name = last_name
            django_user.role = role
            django_user.email = email
            django_user.save(update_fields=['first_name', 'last_name', 'role', 'email'])

            # Создаём/обновляем профиль в зависимости от роли
            if role == User.Role.TEACHER:
                print(f"[create_staff] Creating/updating TeacherProfile for user {django_user.id}")
                profile, created = TeacherProfile.objects.get_or_create(
                    user=django_user,
                    defaults=profile_kwargs
                )
                print(f"[create_staff] TeacherProfile {'created' if created else 'updated'}: id={profile.id}, subject={profile.subject}")
                
                # Если профиль уже существовал, обновляем его
                if not created:
                    for k, v in profile_kwargs.items():
                        setattr(profile, k, v)
                    profile.save()
                    print(f"[create_staff] TeacherProfile updated: subject={profile.subject}")
                
                # Создаем связь TeacherSubject, если указан предмет
                if profile.subject:
                    from materials.models import TeacherSubject, Subject
                    # Ищем предмет по имени или создаем новый
                    subject, subject_created = Subject.objects.get_or_create(
                        name=profile.subject,
                        defaults={'description': '', 'color': '#3b82f6'}
                    )
                    print(f"[create_staff] Subject {'created' if subject_created else 'found'}: id={subject.id}, name={subject.name}")
                    
                    # Создаем связь учитель-предмет
                    teacher_subject, ts_created = TeacherSubject.objects.get_or_create(
                        teacher=django_user,
                        subject=subject,
                        defaults={'is_active': True}
                    )
                    print(f"[create_staff] TeacherSubject {'created' if ts_created else 'found'}: id={teacher_subject.id}, is_active={teacher_subject.is_active}")
            else:
                print(f"[create_staff] Creating/updating TutorProfile for user {django_user.id}")
                profile, created = TutorProfile.objects.get_or_create(
                    user=django_user,
                    defaults=profile_kwargs
                )
                print(f"[create_staff] TutorProfile {'created' if created else 'updated'}: id={profile.id}")
                
                # Если профиль уже существовал, обновляем его
                if not created:
                    for k, v in profile_kwargs.items():
                        setattr(profile, k, v)
                    profile.save()

    except Exception as exc:
        import traceback
        print(f"[create_staff] Error creating user: {exc}")
        print(f"[create_staff] Traceback: {traceback.format_exc()}")
        return Response({'detail': f'Ошибка создания пользователя: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # После завершения транзакции, принудительно обновляем данные из базы
    # Это гарантирует, что новый пользователь будет виден в списке
    django_user.refresh_from_db()
    
    # Возвращаем учётные данные ОДИН раз (логин = email)
    # Возвращаем профиль для мгновенного UI-обновления
    try:
        if role == User.Role.TEACHER:
            profile = TeacherProfile.objects.select_related('user').get(user=django_user)
            profile_data = TeacherProfileSerializer(profile).data
        else:
            profile = TutorProfile.objects.select_related('user').get(user=django_user)
            profile_data = TutorProfileSerializer(profile).data
    except (TeacherProfile.DoesNotExist, TutorProfile.DoesNotExist) as e:
        # Если профиль не найден, создаем минимальные данные
        print(f"[create_staff] Profile not found for user {django_user.id}, creating minimal data")
        if role == User.Role.TEACHER:
            profile_data = {
                'id': django_user.id,
                'user': UserSerializer(django_user).data,
                'subject': profile_kwargs.get('subject', ''),
                'experience_years': profile_kwargs.get('experience_years', 0),
                'bio': profile_kwargs.get('bio', ''),
                'subjects_list': []
            }
        else:
            profile_data = {
                'id': django_user.id,
                'user': UserSerializer(django_user).data,
                'specialization': profile_kwargs.get('specialization', ''),
                'experience_years': profile_kwargs.get('experience_years', 0),
                'bio': profile_kwargs.get('bio', '')
            }

    return Response({
        'user': UserSerializer(django_user).data,
        'profile': profile_data,
        'credentials': {
            'login': email,
            'password': generated_password,
        }
    }, status=status.HTTP_201_CREATED)


