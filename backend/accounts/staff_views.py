from typing import Any, Dict
import logging

from django.db import transaction, IntegrityError
from django.utils.crypto import get_random_string
from django.db.models import Count, Q, Prefetch
from django.conf import settings
from rest_framework import status

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import BasePermission, IsAdminUser
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import User, TeacherProfile, TutorProfile, StudentProfile, ParentProfile
from .serializers import (
    UserSerializer, TeacherProfileSerializer, TutorProfileSerializer,
    StudentProfileSerializer, UserUpdateSerializer, StudentProfileUpdateSerializer,
    TeacherProfileUpdateSerializer, TutorProfileUpdateSerializer,
    ParentProfileUpdateSerializer, UserCreateSerializer, StudentCreateSerializer
)
from .supabase_service import SupabaseAuthService
from .supabase_sync import SupabaseSyncService
from .retry_logic import SupabaseSyncRetry, RetryConfig
from payments.models import Payment


class CSRFExemptSessionAuthentication(SessionAuthentication):
    """
    Кастомный класс аутентификации, который отключает CSRF проверку для API views.
    Используется для POST запросов, где фронтенд использует токены.
    """
    def enforce_csrf(self, request):
        # Отключаем CSRF проверку для API запросов
        return


class StudentPagination(PageNumberPagination):
    """
    Пагинация для списка студентов
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


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
            # Импортируем здесь, чтобы избежать циклических импортов
            from materials.models import TeacherSubject
            from materials.serializers import TeacherSubjectSerializer

            try:
                # Пытаемся получить профиль - используем get() для явной проверки
                # Это гарантирует, что мы получим свежие данные из базы
                profile = TeacherProfile.objects.select_related('user').get(user=user)
                # Используем сериализатор профиля, если он существует
                profile_data = TeacherProfileSerializer(profile).data

                # Получаем полный список предметов преподавателя
                teacher_subjects = TeacherSubject.objects.filter(
                    teacher=user,
                    is_active=True
                ).select_related('subject').order_by('assigned_at')

                subjects_data = TeacherSubjectSerializer(teacher_subjects, many=True).data
                profile_data['subjects'] = subjects_data

                results.append(profile_data)
                print(f"[list_staff] Added teacher with profile: {user.username} (id={user.id}, profile_id={profile.id}, subjects={len(subjects_data)})")
            except TeacherProfile.DoesNotExist:
                # Если профиля нет, создаем данные вручную в формате, который ожидает фронтенд
                # Получаем предметы преподавателя через TeacherSubject
                teacher_subjects = TeacherSubject.objects.filter(
                    teacher=user,
                    is_active=True
                ).select_related('subject').order_by('assigned_at')

                # Сериализуем предметы
                subjects_data = TeacherSubjectSerializer(teacher_subjects, many=True).data

                # Используем первый предмет как основной, или пустую строку (для обратной совместимости)
                main_subject = subjects_data[0]['name'] if subjects_data else ''

                # Используем ID пользователя, так как профиля нет
                # Фронтенд ожидает число в поле id
                results.append({
                    'id': user.id,  # Используем ID пользователя
                    'user': UserSerializer(user).data,
                    'subject': main_subject,
                    'experience_years': 0,
                    'bio': '',
                    'subjects': subjects_data  # Полный список предметов
                })
                print(f"[list_staff] Added teacher without profile: {user.username} (id={user.id}, subjects={len(subjects_data)})")
        
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


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_teacher_subjects(request, teacher_id):
    """
    Обновление списка предметов преподавателя.

    Args:
        teacher_id: ID преподавателя

    Body JSON:
        - subject_ids: [1, 2, 3] - список ID предметов

    Returns:
        - subjects: список обновленных предметов преподавателя

    Raises:
        - 400: неверные данные запроса
        - 404: преподаватель не найден
        - 403: пользователь не имеет прав
    """
    from materials.models import Subject, TeacherSubject
    from materials.serializers import TeacherSubjectUpdateSerializer, TeacherSubjectSerializer

    # Проверяем что пользователь с указанным ID существует и является преподавателем
    try:
        teacher = User.objects.get(id=teacher_id, role=User.Role.TEACHER, is_active=True)
    except User.DoesNotExist:
        return Response({
            'detail': 'Преподаватель не найден'
        }, status=status.HTTP_404_NOT_FOUND)

    # Валидация входных данных
    serializer = TeacherSubjectUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    subject_ids = serializer.validated_data['subject_ids']

    # Используем транзакцию для атомарности операции
    with transaction.atomic():
        # Удаляем все существующие связи преподавателя с предметами
        TeacherSubject.objects.filter(teacher=teacher).delete()

        # Создаем новые связи используя bulk_create для оптимизации
        if subject_ids:
            teacher_subjects = [
                TeacherSubject(
                    teacher=teacher,
                    subject_id=subject_id,
                    is_active=True
                )
                for subject_id in subject_ids
            ]
            TeacherSubject.objects.bulk_create(teacher_subjects)

    # Получаем обновленный список предметов с prefetch для оптимизации
    updated_teacher_subjects = TeacherSubject.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject').order_by('assigned_at')

    # Сериализуем результат
    subjects_data = TeacherSubjectSerializer(updated_teacher_subjects, many=True).data

    return Response({
        'success': True,
        'teacher_id': teacher_id,
        'subjects': subjects_data,
        'message': f'Предметы преподавателя успешно обновлены ({len(subjects_data)} предметов)'
    }, status=status.HTTP_200_OK)


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

    # Инициализируем retry manager для Supabase операций
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0)
    retry_manager = SupabaseSyncRetry(retry_config)

    try:
        with transaction.atomic():
            django_user = None
            # Попытка через Supabase Admin API с retry logic
            sb_result: Dict[str, Any] | None = None
            try:
                if getattr(sb_auth, 'service_key', None):
                    # Преобразуем enum роль в строку для Supabase
                    role_str = role.value if hasattr(role, 'value') else str(role)
                    print(f"[create_staff] Creating user in Supabase with role: {role_str}")

                    # Используем retry manager для надежного создания в Supabase
                    def create_supabase_user():
                        return sb_auth.sign_up(
                            email=email,
                            password=generated_password,
                            user_data={
                                'role': role_str,
                                'first_name': first_name,
                                'last_name': last_name,
                            }
                        )

                    try:
                        sb_result = retry_manager.execute(
                            create_supabase_user,
                            operation_name=f"create_staff (Supabase) for {email}"
                        )
                    except Exception as retry_exc:
                        logger.warning(
                            f"[create_staff] Supabase sync failed after retries for {email}: {retry_exc}. "
                            f"Falling back to Django-only creation."
                        )
                        audit_logger.warning(
                            f"action=supabase_sync_failed user_email={email} role={role_str} error={retry_exc}"
                        )
                        sb_result = None
            except Exception as e:
                logger.error(f"[create_staff] Unexpected error in Supabase block: {e}")
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


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def list_students(request):
    """
    Получить список всех студентов (admin-only)

    Query params:
      - tutor_id: фильтр по ID тьютора
      - grade: фильтр по классу
      - is_active: фильтр по активности (true/false)
      - search: поиск по имени, email, username
      - ordering: сортировка (email, first_name, last_name, date_joined)
      - page: номер страницы (пагинация 50 записей)

    Returns:
        {
            "count": 100,
            "next": "http://...",
            "previous": null,
            "results": [...]
        }
    """
    from .serializers import StudentListSerializer

    # Базовый queryset с оптимизацией запросов
    queryset = StudentProfile.objects.select_related(
        'user', 'tutor', 'parent'
    ).annotate(
        enrollments_count=Count('user__subject_enrollments')
    )

    # Фильтр по активности пользователя (по умолчанию показываем всех)
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        queryset = queryset.filter(user__is_active=is_active_bool)
    # Если is_active не указан - показываем всех пользователей (включая неактивных)

    # Фильтр по тьютору
    tutor_id = request.query_params.get('tutor_id')
    if tutor_id:
        try:
            tutor_id_int = int(tutor_id)
            queryset = queryset.filter(tutor_id=tutor_id_int)
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Неверный формат tutor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Фильтр по классу
    grade = request.query_params.get('grade')
    if grade:
        queryset = queryset.filter(grade=grade)

    # Поиск по имени, email, username
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__username__icontains=search)
        )

    # Сортировка
    ordering = request.query_params.get('ordering', '-user__date_joined')
    allowed_orderings = [
        'user__email', '-user__email',
        'user__first_name', '-user__first_name',
        'user__last_name', '-user__last_name',
        'user__date_joined', '-user__date_joined',
        'grade', '-grade',
        'progress_percentage', '-progress_percentage'
    ]

    if ordering in allowed_orderings:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-user__date_joined')

    # Пагинация
    paginator = StudentPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = StudentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Fallback без пагинации (не должно произойти)
    serializer = StudentListSerializer(queryset, many=True)
    return Response({'results': serializer.data})


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def get_student_detail(request, student_id):
    """
    Получить детальную информацию о студенте (admin-only)

    Args:
        student_id: ID студента (User ID)

    Returns:
        Полная информация о студенте включая:
        - Данные пользователя и профиля
        - Информация о тьюторе и родителе
        - Зачисления на предметы с прогрессом
        - История платежей (последние 10)
        - Количество отчетов
        - Статистика по материалам и заданиям

    Raises:
        404: студент не найден
    """
    from .serializers import StudentDetailSerializer

    try:
        # Получаем студента с оптимизацией запросов
        student_profile = StudentProfile.objects.select_related(
            'user', 'tutor', 'parent'
        ).get(user_id=student_id, user__role=User.Role.STUDENT)
    except StudentProfile.DoesNotExist:
        return Response(
            {'detail': 'Студент не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Сериализуем данные
    serializer = StudentDetailSerializer(student_profile)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ============= ENDPOINTS ДЛЯ РЕДАКТИРОВАНИЯ ПОЛЬЗОВАТЕЛЕЙ (ADMIN) =============
@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_user(request, user_id):
    """
    Обновление данных пользователя и профиля (admin-only)

    Args:
        user_id: ID пользователя

    Body JSON:
        Базовые поля пользователя:
        - email: Email (с валидацией уникальности)
        - first_name: Имя
        - last_name: Фамилия
        - phone: Телефон
        - is_active: Активация/деактивация

        Профильные данные (опционально, через вложенный объект profile_data):

        Для student:
        - profile_data.grade: Класс обучения
        - profile_data.goal: Цель обучения
        - profile_data.tutor: ID тьютора (nullable)
        - profile_data.parent: ID родителя (nullable)

        Для teacher:
        - profile_data.experience_years: Опыт работы (лет)
        - profile_data.bio: Биография

        Для tutor:
        - profile_data.specialization: Специализация
        - profile_data.experience_years: Опыт работы (лет)
        - profile_data.bio: Биография

    Returns:
        {
            "success": true,
            "user": {...},
            "profile": {...},
            "message": "Пользователь и профиль успешно обновлены"
        }

    Raises:
        - 400: Невалидные данные
        - 403: Попытка деактивировать себя
        - 404: Пользователь не найден
    """
    try:
        user = User.objects.select_related(
            'student_profile', 'teacher_profile', 'tutor_profile', 'parent_profile'
        ).get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Проверка: нельзя деактивировать самого себя
    if 'is_active' in request.data:
        if not request.data['is_active'] and user.id == request.user.id:
            return Response(
                {'detail': 'Вы не можете деактивировать сам себя'},
                status=status.HTTP_403_FORBIDDEN
            )

    # Извлекаем данные профиля из запроса (если есть)
    profile_data = request.data.get('profile_data', {})

    # Используем транзакцию для атомарности
    with transaction.atomic():
        # 1. Обновляем базовые поля пользователя
        user_serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_user = user_serializer.save()

        # 2. Обновляем профиль в зависимости от роли (если переданы данные профиля)
        profile_serializer_data = None

        if profile_data and user.role == User.Role.STUDENT:
            try:
                student_profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(user=user)
                profile_serializer = StudentProfileUpdateSerializer(
                    student_profile,
                    data=profile_data,
                    partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                updated_profile = profile_serializer.save()
                profile_serializer_data = StudentProfileSerializer(updated_profile).data
            except StudentProfile.DoesNotExist:
                # Если профиля нет - создаем
                profile_serializer = StudentProfileUpdateSerializer(data=profile_data)
                if not profile_serializer.is_valid():
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                updated_profile = StudentProfile.objects.create(
                    user=user,
                    **profile_serializer.validated_data
                )
                profile_serializer_data = StudentProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.TEACHER:
            try:
                teacher_profile = TeacherProfile.objects.select_related('user').get(user=user)
                profile_serializer = TeacherProfileUpdateSerializer(
                    teacher_profile,
                    data=profile_data,
                    partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                updated_profile = profile_serializer.save()
                profile_serializer_data = TeacherProfileSerializer(updated_profile).data
            except TeacherProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = TeacherProfile.objects.create(
                    user=user,
                    experience_years=profile_data.get('experience_years', 0),
                    bio=profile_data.get('bio', '')
                )
                profile_serializer_data = TeacherProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.TUTOR:
            try:
                tutor_profile = TutorProfile.objects.select_related('user').get(user=user)
                profile_serializer = TutorProfileUpdateSerializer(
                    tutor_profile,
                    data=profile_data,
                    partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                updated_profile = profile_serializer.save()
                profile_serializer_data = TutorProfileSerializer(updated_profile).data
            except TutorProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = TutorProfile.objects.create(
                    user=user,
                    specialization=profile_data.get('specialization', ''),
                    experience_years=profile_data.get('experience_years', 0),
                    bio=profile_data.get('bio', '')
                )
                profile_serializer_data = TutorProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.PARENT:
            try:
                parent_profile = ParentProfile.objects.select_related('user').get(user=user)
                profile_serializer = ParentProfileUpdateSerializer(
                    parent_profile,
                    data=profile_data,
                    partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                updated_profile = profile_serializer.save()
                from .serializers import ParentProfileSerializer
                profile_serializer_data = ParentProfileSerializer(updated_profile).data
            except ParentProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = ParentProfile.objects.create(user=user)
                from .serializers import ParentProfileSerializer
                profile_serializer_data = ParentProfileSerializer(updated_profile).data

    # 3. Обновление в Supabase (если используется)
    if hasattr(settings, 'SUPABASE_URL') and settings.SUPABASE_URL:
        try:
            sb_auth = SupabaseAuthService()
            if hasattr(sb_auth, 'service_client') and sb_auth.service_client:
                import requests
                admin_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{updated_user.id}"
                headers = {
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
                update_data = {}
                if 'email' in user_serializer.validated_data:
                    update_data['email'] = user_serializer.validated_data['email']
                if update_data:
                    requests.patch(admin_url, json=update_data, headers=headers)
        except Exception as e:
            logger.warning(f"Не удалось обновить пользователя в Supabase: {e}")

    # 4. Формируем ответ
    response_data = {
        'success': True,
        'user': UserSerializer(updated_user).data,
        'message': 'Пользователь успешно обновлен'
    }

    # Добавляем данные профиля в ответ если они были обновлены
    if profile_serializer_data:
        response_data['profile'] = profile_serializer_data
        response_data['message'] = 'Пользователь и профиль успешно обновлены'

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_student_profile(request, student_id):
    """
    Обновление профиля студента (admin-only)

    Args:
        student_id: ID студента (User ID)

    Body JSON:
        - grade: Класс обучения
        - goal: Цель обучения
        - tutor: ID тьютора (nullable)
        - parent: ID родителя (nullable)

    Returns:
        Обновленный профиль студента

    Raises:
        - 400: Невалидные данные
        - 404: Студент не найден
    """
    try:
        student_profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(
            user_id=student_id,
            user__role=User.Role.STUDENT
        )
    except StudentProfile.DoesNotExist:
        return Response(
            {'detail': 'Профиль студента не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Валидация и обновление
    serializer = StudentProfileUpdateSerializer(
        student_profile,
        data=request.data,
        partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    return Response({
        'success': True,
        'profile': StudentProfileSerializer(updated_profile).data,
        'message': 'Профиль студента успешно обновлен'
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_teacher_profile(request, teacher_id):
    """
    Обновление профиля преподавателя (admin-only)

    Args:
        teacher_id: ID преподавателя (User ID)

    Body JSON:
        - experience_years: Опыт работы (лет)
        - bio: Биография

    Примечание:
        Для обновления списка предметов используйте
        PATCH /api/staff/teachers/{id}/subjects/

    Returns:
        Обновленный профиль преподавателя

    Raises:
        - 400: Невалидные данные
        - 404: Преподаватель не найден
    """
    try:
        teacher_profile = TeacherProfile.objects.select_related('user').get(
            user_id=teacher_id,
            user__role=User.Role.TEACHER
        )
    except TeacherProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            teacher_user = User.objects.get(id=teacher_id, role=User.Role.TEACHER)
            teacher_profile = TeacherProfile.objects.create(
                user=teacher_user,
                subject='',
                experience_years=0,
                bio=''
            )
        except User.DoesNotExist:
            return Response(
                {'detail': 'Преподаватель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление
    serializer = TeacherProfileUpdateSerializer(
        teacher_profile,
        data=request.data,
        partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    return Response({
        'success': True,
        'profile': TeacherProfileSerializer(updated_profile).data,
        'message': 'Профиль преподавателя успешно обновлен'
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_tutor_profile(request, tutor_id):
    """
    Обновление профиля тьютора (admin-only)

    Args:
        tutor_id: ID тьютора (User ID)

    Body JSON:
        - specialization: Специализация
        - experience_years: Опыт работы (лет)
        - bio: Биография

    Returns:
        Обновленный профиль тьютора

    Raises:
        - 400: Невалидные данные
        - 404: Тьютор не найден
    """
    try:
        tutor_profile = TutorProfile.objects.select_related('user').get(
            user_id=tutor_id,
            user__role=User.Role.TUTOR
        )
    except TutorProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            tutor_user = User.objects.get(id=tutor_id, role=User.Role.TUTOR)
            tutor_profile = TutorProfile.objects.create(
                user=tutor_user,
                specialization='',
                experience_years=0,
                bio=''
            )
        except User.DoesNotExist:
            return Response(
                {'detail': 'Тьютор не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление
    serializer = TutorProfileUpdateSerializer(
        tutor_profile,
        data=request.data,
        partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    return Response({
        'success': True,
        'profile': TutorProfileSerializer(updated_profile).data,
        'message': 'Профиль тьютора успешно обновлен'
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def update_parent_profile(request, parent_id):
    """
    Обновление профиля родителя (admin-only)

    Args:
        parent_id: ID родителя (User ID)

    Body JSON:
        Пока ParentProfile не имеет дополнительных полей

    Returns:
        Профиль родителя (всегда успех)

    Raises:
        - 404: Родитель не найден
    """
    try:
        parent_profile = ParentProfile.objects.select_related('user').get(
            user_id=parent_id,
            user__role=User.Role.PARENT
        )
    except ParentProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            parent_user = User.objects.get(id=parent_id, role=User.Role.PARENT)
            parent_profile = ParentProfile.objects.create(user=parent_user)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Родитель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление (пока нет полей)
    serializer = ParentProfileUpdateSerializer(
        parent_profile,
        data=request.data,
        partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    from .serializers import ParentProfileSerializer
    return Response({
        'success': True,
        'profile': ParentProfileSerializer(updated_profile).data,
        'message': 'Профиль родителя успешно обновлен'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def reset_password(request, user_id):
    """
    Сброс пароля пользователя с генерацией нового (admin-only)

    Args:
        user_id: ID пользователя

    Returns:
        {
            "success": true,
            "user_id": 123,
            "email": "user@test.com",
            "new_password": "Abc123!@#Xyz",
            "message": "Пароль успешно изменен. Передайте новый пароль пользователю."
        }

    Raises:
        - 404: Пользователь не найден

    Примечание:
        Новый пароль возвращается ТОЛЬКО ОДИН РАЗ.
        Пароль генерируется автоматически: 12 символов (буквы + цифры + спецсимволы).
    """
    import string
    import secrets

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Генерация надежного пароля: 12 символов
    # Минимум: 1 заглавная, 1 строчная, 1 цифра, 1 спецсимвол
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    # Обновление в Django
    user.set_password(new_password)
    user.save(update_fields=['password'])

    # Обновление в Supabase (если используется)
    if hasattr(settings, 'SUPABASE_URL') and settings.SUPABASE_URL:
        try:
            sb_auth = SupabaseAuthService()
            if hasattr(sb_auth, 'service_client') and sb_auth.service_client:
                import requests
                admin_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.id}"
                headers = {
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
                update_data = {"password": new_password}
                requests.patch(admin_url, json=update_data, headers=headers)
        except Exception as e:
            logger.warning(f"Не удалось обновить пароль в Supabase: {e}")

    return Response({
        'success': True,
        'user_id': user.id,
        'email': user.email,
        'new_password': new_password,
        'message': 'Пароль успешно изменен. Передайте новый пароль пользователю.'
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def delete_user(request, user_id):
    """
    Удаление пользователя (admin-only)

    Args:
        user_id: ID пользователя

    Query params:
        - soft: true/false (по умолчанию false - hard delete)

    Логика:
        - Hard delete (по умолчанию): полное удаление из БД
        - Soft delete (soft=true): is_active = False

    Проверки:
        - Нельзя удалить самого себя
        - Нельзя удалить суперпользователя (is_superuser=True)

    Каскадное удаление (при hard delete):
        - Профиль (StudentProfile, TeacherProfile, etc.)
        - SubjectEnrollment
        - Payment (помечаются как archived)
        - Report
        - Удаление из Supabase (если настроен)

    Returns:
        {
            "success": true,
            "message": "Пользователь полностью удален из системы" | "Пользователь деактивирован (soft delete)"
        }

    Raises:
        - 403: Попытка удалить себя или superuser
        - 404: Пользователь не найден
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Проверка: нельзя удалить самого себя
    if user.id == request.user.id:
        return Response(
            {'detail': 'Вы не можете удалить сам себя'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Проверка: нельзя удалить суперпользователя
    if user.is_superuser:
        return Response(
            {'detail': 'Нельзя удалить суперпользователя'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Проверяем режим удаления (по умолчанию - HARD DELETE, как ожидается фронтендом)
    # Soft delete только если явно указан параметр soft=true
    soft_delete = request.query_params.get('soft', 'false').lower() == 'true'

    with transaction.atomic():
        if soft_delete:
            # Soft delete: деактивация аккаунта
            user.is_active = False
            user.save(update_fields=['is_active'])
            message = 'Пользователь деактивирован (soft delete)'
            logger.info(f"[delete_user] Soft deleted user {user.id} ({user.email})")
        else:
            # Hard delete: полное удаление из БД (по умолчанию)

            # Удаление из Supabase (если используется)
            if hasattr(settings, 'SUPABASE_URL') and settings.SUPABASE_URL:
                try:
                    sb_auth = SupabaseAuthService()
                    if hasattr(sb_auth, 'service_client') and sb_auth.service_client:
                        import requests
                        admin_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.id}"
                        headers = {
                            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        }
                        requests.delete(admin_url, headers=headers)
                        logger.info(f"[delete_user] Deleted user from Supabase: {user.id}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить пользователя из Supabase: {e}")

            # Каскадное удаление в Django происходит автоматически благодаря CASCADE
            # models: Profile, SubjectEnrollment, Payment, Report
            user_id = user.id
            user_email = user.email
            user.delete()

            logger.info(f"[delete_user] Hard deleted user {user_id} ({user_email}) from database")
            message = 'Пользователь полностью удален из системы'

    return Response({
        'success': True,
        'message': message
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def create_user_with_profile(request):
    """
    Создание пользователя с профилем (admin-only)

    Body JSON:
        Обязательные поля:
        - email: Email пользователя (уникальный)
        - first_name: Имя
        - last_name: Фамилия
        - role: Роль (student, teacher, tutor, parent)

        Опциональные общие поля:
        - phone: Телефон
        - password: Пароль (если не указан - генерируется)

        Роль-специфичные поля:

        Для student:
        - grade: Класс (обязательно)
        - goal: Цель обучения (опционально)
        - tutor_id: ID тьютора (опционально)
        - parent_id: ID родителя (опционально)

        Для teacher:
        - subject: Основной предмет (опционально, deprecated)
        - experience_years: Опыт работы (опционально)
        - bio: Биография (опционально)

        Для tutor:
        - specialization: Специализация (обязательно)
        - experience_years: Опыт работы (опционально)
        - bio: Биография (опционально)

        Для parent:
        - Пока нет дополнительных полей

    Returns:
        {
            "success": true,
            "user": {...},
            "profile": {...},
            "credentials": {
                "login": "user@test.com",
                "password": "GeneratedPass123"
            }
        }

    Raises:
        - 400: Невалидные данные
        - 409: Email уже существует

    Примечание:
        Пароль возвращается ТОЛЬКО ОДИН РАЗ при создании.
        Если что-то не удалось, вся транзакция откатывается.
    """
    # Валидация данных
    serializer = UserCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data

    # Генерация пароля если не указан
    password = validated_data.get('password')
    if not password:
        password = get_random_string(length=12)

    email = validated_data['email']
    first_name = validated_data['first_name']
    last_name = validated_data['last_name']
    role = validated_data['role']
    phone = validated_data.get('phone', '')

    # Создание через Supabase и синхронизация с Django
    sb_auth = SupabaseAuthService()
    sb_sync = SupabaseSyncService()

    # Инициализируем retry manager для Supabase операций
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0)
    retry_manager = SupabaseSyncRetry(retry_config)

    try:
        with transaction.atomic():
            django_user = None

            # Попытка создать в Supabase с retry logic
            sb_result = None
            try:
                if getattr(sb_auth, 'service_key', None):
                    role_str = role.value if hasattr(role, 'value') else str(role)

                    def create_user_supabase():
                        return sb_auth.sign_up(
                            email=email,
                            password=password,
                            user_data={
                                'role': role_str,
                                'first_name': first_name,
                                'last_name': last_name,
                            }
                        )

                    try:
                        sb_result = retry_manager.execute(
                            create_user_supabase,
                            operation_name=f"create_user_with_profile (Supabase) for {email}"
                        )
                    except Exception as retry_exc:
                        logger.warning(
                            f"[create_user_with_profile] Supabase sync failed after retries for {email}: {retry_exc}. "
                            f"Falling back to Django-only creation."
                        )
                        audit_logger.warning(
                            f"action=supabase_sync_failed user_email={email} role={role_str} error={retry_exc}"
                        )
                        sb_result = None
            except Exception as e:
                logger.error(f"[create_user_with_profile] Unexpected error in Supabase block: {e}")
                sb_result = None

            # Если Supabase удался - синхронизируем
            if sb_result and sb_result.get('success') and sb_result.get('user'):
                django_user = sb_sync.create_django_user_from_supabase(sb_result['user'])
                if not django_user:
                    return Response(
                        {'detail': 'Не удалось создать пользователя в Django'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                # Гарантируем username = email
                if django_user.username != email:
                    django_user.username = email
                    django_user.save(update_fields=['username'])
                # Гарантируем роль
                if django_user.role != role:
                    django_user.role = role
                    django_user.save(update_fields=['role'])
            else:
                # Фолбэк: создание только в Django
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
                django_user.set_password(password)
                django_user.save()

            # Обновляем данные на всякий случай
            django_user.first_name = first_name
            django_user.last_name = last_name
            django_user.role = role
            django_user.email = email
            django_user.phone = phone
            django_user.save(update_fields=['first_name', 'last_name', 'role', 'email', 'phone'])

            # Создаем профиль в зависимости от роли
            profile_data = {}

            if role == User.Role.STUDENT:
                grade = validated_data.get('grade')
                goal = validated_data.get('goal', '')
                tutor_id = validated_data.get('tutor_id')
                parent_id = validated_data.get('parent_id')

                tutor = None
                parent = None
                if tutor_id:
                    tutor = User.objects.get(id=tutor_id, role=User.Role.TUTOR)
                if parent_id:
                    parent = User.objects.get(id=parent_id, role=User.Role.PARENT)

                profile = StudentProfile.objects.create(
                    user=django_user,
                    grade=grade,
                    goal=goal,
                    tutor=tutor,
                    parent=parent
                )
                profile_data = StudentProfileSerializer(profile).data

            elif role == User.Role.TEACHER:
                subject = validated_data.get('subject', '')
                experience_years = validated_data.get('experience_years', 0)
                bio = validated_data.get('bio', '')

                profile = TeacherProfile.objects.create(
                    user=django_user,
                    subject=subject,
                    experience_years=experience_years,
                    bio=bio
                )

                profile_data = TeacherProfileSerializer(profile).data

            elif role == User.Role.TUTOR:
                specialization = validated_data.get('specialization')
                experience_years = validated_data.get('experience_years', 0)
                bio = validated_data.get('bio', '')

                profile = TutorProfile.objects.create(
                    user=django_user,
                    specialization=specialization,
                    experience_years=experience_years,
                    bio=bio
                )
                profile_data = TutorProfileSerializer(profile).data

            elif role == User.Role.PARENT:
                profile = ParentProfile.objects.create(user=django_user)
                from .serializers import ParentProfileSerializer
                profile_data = ParentProfileSerializer(profile).data

    except Exception as exc:
        import traceback
        logger.error(f"Ошибка создания пользователя: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            {'detail': f'Ошибка создания пользователя: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        'success': True,
        'user': UserSerializer(django_user).data,
        'profile': profile_data,
        'credentials': {
            'login': email,
            'password': password
        },
        'message': 'Пользователь успешно создан'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def create_student(request):
    """
    Создание студента через админ-панель (admin-only)

    Body JSON:
        Обязательные поля:
        - email: Email студента (уникальный)
        - first_name: Имя
        - last_name: Фамилия
        - grade: Класс обучения

        Опциональные поля:
        - phone: Телефон
        - goal: Цель обучения
        - tutor_id: ID тьютора
        - parent_id: ID родителя
        - password: Пароль (если не указан - генерируется)

    Returns:
        {
            "success": true,
            "user": {...},
            "profile": {...},
            "credentials": {
                "username": "student@test.com",
                "email": "student@test.com",
                "temporary_password": "GeneratedPass123"
            },
            "message": "Студент успешно создан"
        }

    Raises:
        - 400: Невалидные данные
        - 403: Недостаточно прав
        - 409: Email уже существует

    Примечание:
        Временный пароль возвращается ТОЛЬКО ОДИН РАЗ при создании.
        username будет установлен равным email для упрощения входа.
    """
    # Валидация данных
    serializer = StudentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data

    # Генерация пароля если не указан
    password = validated_data.get('password')
    if not password:
        password = get_random_string(length=12)

    email = validated_data['email']
    first_name = validated_data['first_name']
    last_name = validated_data['last_name']
    grade = validated_data['grade']
    phone = validated_data.get('phone', '')
    goal = validated_data.get('goal', '')
    tutor_id = validated_data.get('tutor_id')
    parent_id = validated_data.get('parent_id')

    # Создание через Supabase и синхронизация с Django
    sb_auth = SupabaseAuthService()
    sb_sync = SupabaseSyncService()

    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0)
    retry_manager = SupabaseSyncRetry(retry_config)

    try:
        with transaction.atomic():
            # Проверка уникальности email ВНУТРИ транзакции для предотвращения race condition
            if User.objects.filter(email=email).exists():
                return Response(
                    {'detail': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_409_CONFLICT
                )

            django_user = None

            # Попытка создать в Supabase с retry logic
            sb_result = None
            try:
                if getattr(sb_auth, 'service_key', None):
                    def create_user_supabase():
                        return sb_auth.sign_up(
                            email=email,
                            password=password,
                            user_data={
                                'role': 'student',
                                'first_name': first_name,
                                'last_name': last_name,
                            }
                        )

                    try:
                        sb_result = retry_manager.execute(
                            create_user_supabase,
                            operation_name=f"create_student (Supabase) for {email}"
                        )
                    except Exception as retry_exc:
                        logger.warning(
                            f"[create_student] Supabase sync failed after retries for {email}: {retry_exc}. "
                            f"Falling back to Django-only creation."
                        )
                        audit_logger.warning(
                            f"action=supabase_sync_failed user_email={email} role=student error={retry_exc}"
                        )
                        sb_result = None
            except Exception as e:
                logger.error(f"[create_student] Unexpected error in Supabase block: {e}")
                sb_result = None

            # Если Supabase удался - синхронизируем
            if sb_result and sb_result.get('success') and sb_result.get('user'):
                django_user = sb_sync.create_django_user_from_supabase(sb_result['user'])
                if not django_user:
                    return Response(
                        {'detail': 'Не удалось создать пользователя в Django'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                # Гарантируем username = email
                if django_user.username != email:
                    django_user.username = email
                    django_user.save(update_fields=['username'])
                # Гарантируем роль студента
                if django_user.role != User.Role.STUDENT:
                    django_user.role = User.Role.STUDENT
                    django_user.save(update_fields=['role'])
            else:
                # Фолбэк: создание только в Django
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
                    role=User.Role.STUDENT,
                    is_active=True,
                )
                django_user.set_password(password)
                django_user.save()

            # Обновляем данные пользователя
            django_user.first_name = first_name
            django_user.last_name = last_name
            django_user.role = User.Role.STUDENT
            django_user.email = email
            django_user.phone = phone
            django_user.save(update_fields=['first_name', 'last_name', 'role', 'email', 'phone'])

            # Получаем связанные объекты (tutor, parent)
            tutor = None
            parent = None
            if tutor_id:
                try:
                    tutor = User.objects.get(id=tutor_id, role=User.Role.TUTOR, is_active=True)
                except User.DoesNotExist:
                    pass

            if parent_id:
                try:
                    parent = User.objects.get(id=parent_id, role=User.Role.PARENT, is_active=True)
                except User.DoesNotExist:
                    pass

            # Создаем или обновляем профиль студента (на случай если signal уже создал профиль)
            student_profile, profile_created = StudentProfile.objects.get_or_create(
                user=django_user,
                defaults={
                    'grade': grade,
                    'goal': goal,
                    'tutor': tutor,
                    'parent': parent
                }
            )

            # Если профиль уже существовал (создан signal), обновляем его данные
            if not profile_created:
                student_profile.grade = grade
                student_profile.goal = goal
                student_profile.tutor = tutor
                student_profile.parent = parent
                student_profile.save(update_fields=['grade', 'goal', 'tutor', 'parent'])

            # Логируем успешное создание
            logger.info(f"[create_student] Created student: {django_user.email} (id={django_user.id})")
            audit_logger.info(
                f"action=student_created user_id={django_user.id} email={django_user.email} "
                f"grade={grade} tutor_id={tutor_id} parent_id={parent_id} created_by={request.user.id}"
            )

    except IntegrityError as exc:
        # Ловим race condition: два параллельных запроса создали пользователя с одним email
        logger.warning(f"[create_student] IntegrityError (race condition?) for email {email}: {exc}")
        if 'email' in str(exc).lower() or 'unique' in str(exc).lower():
            return Response(
                {'detail': 'Пользователь с таким email уже существует'},
                status=status.HTTP_409_CONFLICT
            )
        # Если IntegrityError не связан с email, пробрасываем дальше
        logger.error(f"[create_student] Unexpected IntegrityError: {exc}")
        return Response(
            {'detail': f'Ошибка целостности данных: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        import traceback
        logger.error(f"[create_student] Error creating student: {exc}")
        logger.error(f"[create_student] Traceback: {traceback.format_exc()}")
        return Response(
            {'detail': f'Ошибка создания студента: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Обновляем данные из базы
    django_user.refresh_from_db()
    student_profile.refresh_from_db()

    # Возвращаем учетные данные ОДИН раз
    return Response({
        'success': True,
        'user': UserSerializer(django_user).data,
        'profile': StudentProfileSerializer(student_profile).data,
        'credentials': {
            'login': django_user.email,
            'password': password
        },
        'message': 'Студент успешно создан'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def create_parent(request):
    """
    Создание родителя через админ-панель (admin-only)

    Body JSON:
        Обязательные поля:
        - email: Email родителя (уникальный)
        - first_name: Имя
        - last_name: Фамилия

        Опциональные поля:
        - phone: Телефон
        - password: Пароль (если не указан - генерируется)

    Returns:
        {
            "success": true,
            "user": {...},
            "profile": {...},
            "credentials": {
                "username": "parent@test.com",
                "email": "parent@test.com",
                "temporary_password": "GeneratedPass123"
            },
            "message": "Родитель успешно создан"
        }

    Raises:
        - 400: Невалидные данные
        - 403: Недостаточно прав
        - 409: Email уже существует

    Примечание:
        Временный пароль возвращается ТОЛЬКО ОДИН РАЗ при создании.
        username будет установлен равным email для упрощения входа.
    """
    from accounts.serializers import ParentCreateSerializer

    # Валидация данных через serializer
    serializer = ParentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # Извлекаем валидированные данные
    validated_data = serializer.validated_data
    email = validated_data['email']
    first_name = validated_data['first_name']
    last_name = validated_data['last_name']
    phone = validated_data.get('phone', '')

    # Генерация пароля если не указан
    password = validated_data.get('password')
    if not password:
        password = get_random_string(length=12)

    # Создание через Supabase и синхронизация с Django
    sb_auth = SupabaseAuthService()
    sb_sync = SupabaseSyncService()

    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0)
    retry_manager = SupabaseSyncRetry(retry_config)

    try:
        with transaction.atomic():
            # Проверка уникальности email ВНУТРИ транзакции для предотвращения race condition
            if User.objects.filter(email=email).exists():
                return Response(
                    {'detail': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_409_CONFLICT
                )

            django_user = None

            # Попытка создать в Supabase с retry logic
            sb_result = None
            try:
                if getattr(sb_auth, 'service_key', None):
                    def create_user_supabase():
                        return sb_auth.sign_up(
                            email=email,
                            password=password,
                            user_data={
                                'role': 'parent',
                                'first_name': first_name,
                                'last_name': last_name,
                            }
                        )

                    try:
                        sb_result = retry_manager.execute(
                            create_user_supabase,
                            operation_name=f"create_parent (Supabase) for {email}"
                        )
                    except Exception as retry_exc:
                        logger.warning(
                            f"[create_parent] Supabase sync failed after retries for {email}: {retry_exc}. "
                            f"Falling back to Django-only creation."
                        )
                        audit_logger.warning(
                            f"action=supabase_sync_failed user_email={email} role=parent error={retry_exc}"
                        )
                        sb_result = None
            except Exception as e:
                logger.error(f"[create_parent] Unexpected error in Supabase block: {e}")
                sb_result = None

            # Если Supabase удался - синхронизируем
            if sb_result and sb_result.get('success') and sb_result.get('user'):
                django_user = sb_sync.create_django_user_from_supabase(sb_result['user'])
                if not django_user:
                    return Response(
                        {'detail': 'Не удалось создать пользователя в Django'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                # Гарантируем username = email
                if django_user.username != email:
                    django_user.username = email
                    django_user.save(update_fields=['username'])
                # Гарантируем роль
                if django_user.role != User.Role.PARENT:
                    django_user.role = User.Role.PARENT
                    django_user.save(update_fields=['role'])
            else:
                # Фолбэк: создание только в Django
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
                    role=User.Role.PARENT,
                    is_active=True,
                    phone=phone
                )
                django_user.set_password(password)
                django_user.save()

            # Обновляем данные пользователя
            django_user.first_name = first_name
            django_user.last_name = last_name
            django_user.role = User.Role.PARENT
            django_user.email = email
            django_user.phone = phone
            django_user.save(update_fields=['first_name', 'last_name', 'role', 'email', 'phone'])

            # Создаем или обновляем профиль родителя
            parent_profile, profile_created = ParentProfile.objects.get_or_create(
                user=django_user
            )

            # Логируем успешное создание
            logger.info(f"[create_parent] Created parent: {django_user.email} (id={django_user.id})")
            audit_logger.info(
                f"action=parent_created user_id={django_user.id} email={django_user.email} "
                f"created_by={request.user.id}"
            )

    except IntegrityError as exc:
        # Ловим race condition: два параллельных запроса создали пользователя с одним email
        logger.warning(f"[create_parent] IntegrityError (race condition?) for email {email}: {exc}")
        if 'email' in str(exc).lower() or 'unique' in str(exc).lower():
            return Response(
                {'detail': 'Пользователь с таким email уже существует'},
                status=status.HTTP_409_CONFLICT
            )
        # Если IntegrityError не связан с email, пробрасываем дальше
        logger.error(f"[create_parent] Unexpected IntegrityError: {exc}")
        return Response(
            {'detail': f'Ошибка целостности данных: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        import traceback
        logger.error(f"[create_parent] Error creating parent: {exc}")
        logger.error(f"[create_parent] Traceback: {traceback.format_exc()}")
        return Response(
            {'detail': f'Ошибка создания родителя: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Обновляем данные из базы
    django_user.refresh_from_db()

    # Возвращаем учетные данные ОДИН раз
    from .serializers import ParentProfileSerializer
    return Response({
        'success': True,
        'user': UserSerializer(django_user).data,
        'profile': ParentProfileSerializer(parent_profile).data,
        'credentials': {
            'login': django_user.email,
            'password': password
        },
        'message': 'Родитель успешно создан'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def assign_parent_to_students(request):
    """
    Назначение родителя студентам (admin-only)

    Body JSON:
        - parent_id: ID родителя (обязательно)
        - student_ids: [1, 2, 3] - список ID студентов для назначения (обязательно)

    Returns:
        {
            "success": true,
            "parent_id": 1,
            "assigned_students": [1, 2, 3],
            "message": "3 студентов успешно назначено родителю"
        }

    Raises:
        - 400: Невалидные данные
        - 404: Родитель или студент не найден
    """
    payload: Dict[str, Any] = request.data or {}
    parent_id = payload.get('parent_id')
    student_ids = payload.get('student_ids', [])

    # Валидация
    if not parent_id:
        return Response({'detail': 'parent_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(student_ids, list) or not student_ids:
        return Response({'detail': 'student_ids должен быть непустым списком'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        parent_user = User.objects.get(id=parent_id, role=User.Role.PARENT, is_active=True)
    except User.DoesNotExist:
        return Response({'detail': 'Родитель не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Получаем студентов
    students = StudentProfile.objects.filter(
        user_id__in=student_ids,
        user__role=User.Role.STUDENT,
        user__is_active=True
    ).select_related('user')

    if not students.exists():
        return Response({'detail': 'Студенты не найдены'}, status=status.HTTP_404_NOT_FOUND)

    assigned_ids = []
    with transaction.atomic():
        for student_profile in students:
            student_profile.parent = parent_user
            student_profile.save(update_fields=['parent'])
            assigned_ids.append(student_profile.user_id)

    # Логируем назначение
    logger.info(
        f"[assign_parent_to_students] Assigned parent {parent_id} to {len(assigned_ids)} students: {assigned_ids}"
    )
    audit_logger.info(
        f"action=parent_assigned parent_id={parent_id} student_ids={assigned_ids} "
        f"assigned_by={request.user.id}"
    )

    return Response({
        'success': True,
        'parent_id': parent_id,
        'assigned_students': assigned_ids,
        'message': f'{len(assigned_ids)} студентов успешно назначено родителю'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def list_parents(request):
    """
    Получить список всех родителей (admin-only)

    Returns:
        {
            "count": 100,
            "next": "http://...",
            "previous": "http://...",
            "results": [
                {
                    "id": 1,
                    "user": {...},
                    "children_count": 2
                }
            ]
        }
    """
    from django.db.models import Count
    from .serializers import ParentProfileListSerializer

    # Annotate children_count in single query instead of N+1
    # Показываем всех родителей (включая неактивных), если не указан фильтр is_active
    parents_queryset = ParentProfile.objects.select_related('user').annotate(
        children_count=Count('user__children_students')
    )

    # Фильтр по активности (опциональный)
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        parents_queryset = parents_queryset.filter(user__is_active=is_active_bool)

    parents_queryset = parents_queryset.order_by('-user__date_joined', '-user__id')

    # Apply pagination
    paginator = StudentPagination()
    page = paginator.paginate_queryset(parents_queryset, request)

    if page is not None:
        serializer = ParentProfileListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Fallback if pagination fails
    serializer = ParentProfileListSerializer(parents_queryset, many=True)
    return Response({'results': serializer.data})


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def reactivate_user(request, user_id):
    """
    Реактивация деактивированного пользователя (admin-only)

    Args:
        user_id: ID пользователя

    Returns:
        {
            "success": true,
            "message": "Student user@test.com has been reactivated"
        }

    Raises:
        - 400: Пользователь уже активен
        - 404: Пользователь не найден

    Примечание:
        Реактивирует пользователя (устанавливает is_active=True).
        Логирует операцию в audit log.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Проверка: пользователь уже активен
    if user.is_active:
        return Response(
            {'detail': 'User is already active'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Реактивация пользователя
    user.is_active = True
    user.save(update_fields=['is_active'])

    # Логирование в audit log
    audit_logger.info(
        f"action=reactivate_user user_id={user.id} email={user.email} role={user.role} "
        f"reactivated_by={request.user.id} reactivated_by_email={request.user.email}"
    )
    logger.info(f"[reactivate_user] User {user.email} (id={user.id}) reactivated by {request.user.email}")

    return Response(
        {
            'success': True,
            'message': f'{user.role.title()} {user.email} has been reactivated'
        },
        status=status.HTTP_200_OK
    )

