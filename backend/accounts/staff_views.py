from typing import Any, Dict

from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import User, TeacherProfile, TutorProfile
from .serializers import UserSerializer, TeacherProfileSerializer, TutorProfileSerializer
from .supabase_service import SupabaseAuthService
from .supabase_sync import SupabaseSyncService


@api_view(['GET'])
@permission_classes([IsAdminUser])
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
        qs = TeacherProfile.objects.select_related('user').all().order_by('user__date_joined')
        data = TeacherProfileSerializer(qs, many=True).data
        return Response({'results': data})
    else:
        qs = TutorProfile.objects.select_related('user').all().order_by('user__date_joined')
        data = TutorProfileSerializer(qs, many=True).data
        return Response({'results': data})


@api_view(['POST'])
@permission_classes([IsAdminUser])
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
                    sb_result = sb_auth.sign_up(
                        email=email,
                        password=generated_password,
                        user_data={
                            'role': role,
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
                profile, _ = TeacherProfile.objects.get_or_create(user=django_user)
                for k, v in profile_kwargs.items():
                    setattr(profile, k, v)
                profile.save()
            else:
                profile, _ = TutorProfile.objects.get_or_create(user=django_user)
                for k, v in profile_kwargs.items():
                    setattr(profile, k, v)
                profile.save()

    except Exception as exc:
        return Response({'detail': f'Ошибка создания пользователя: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Возвращаем учётные данные ОДИН раз (логин = email)
    # Возвращаем профиль для мгновенного UI-обновления
    if role == User.Role.TEACHER:
        profile = TeacherProfile.objects.select_related('user').get(user=django_user)
        profile_data = TeacherProfileSerializer(profile).data
    else:
        profile = TutorProfile.objects.select_related('user').get(user=django_user)
        profile_data = TutorProfileSerializer(profile).data

    return Response({
        'user': UserSerializer(django_user).data,
        'profile': profile_data,
        'credentials': {
            'login': email,
            'password': generated_password,
        }
    }, status=status.HTTP_201_CREATED)


