from typing import Dict, Any, Optional
import logging

from django.db import transaction, IntegrityError
from django.utils.crypto import get_random_string
from django.db.models import Count, Q, Prefetch
from django.conf import settings
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")

from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.permissions import BasePermission
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import User, TeacherProfile, TutorProfile, StudentProfile, ParentProfile
from .serializers import (
    UserSerializer,
    TeacherProfileSerializer,
    TutorProfileSerializer,
    StudentProfileSerializer,
    ParentProfileSerializer,
    UserUpdateSerializer,
    StudentProfileUpdateSerializer,
    TeacherProfileUpdateSerializer,
    TutorProfileUpdateSerializer,
    ParentProfileUpdateSerializer,
    UserCreateSerializer,
    StudentCreateSerializer,
    ParentCreateSerializer,
)
from .permissions import IsStaffOrAdmin
from payments.models import Payment


class StudentPagination(PageNumberPagination):
    """
    Пагинация для списка студентов
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


def log_object_changes(
    request,
    obj,
    serializer,
    action: str,
    sensitive_fields: Optional[list] = None,
) -> None:
    """
    Helper функция для логирования изменений объектов.

    Args:
        request: HTTP request объект (для получения user.id)
        obj: Объект который был обновлен
        serializer: Serializer с validated_data изменений
        action: Тип действия (update_user, update_student_profile, и т.д.)
        sensitive_fields: Список полей которые не логировать (пароли и т.д.)
    """
    if sensitive_fields is None:
        sensitive_fields = ["password"]

    changes = {}
    for field, new_value in serializer.validated_data.items():
        if field in sensitive_fields:
            continue

        old_value = getattr(obj, field, None)
        if old_value != new_value:
            changes[field] = {"old": str(old_value), "new": str(new_value)}

    if changes:
        audit_logger.info(
            f"User {request.user.id} performed {action}",
            extra={
                "action": action,
                "user_id": request.user.id,
                "target_id": obj.id
                if hasattr(obj, "id")
                else getattr(obj, "user_id", None),
                "changes": changes,
            },
        )


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsStaffOrAdmin])
def list_staff(request):
    """Список преподавателей или тьюторов (admin-only).

    Query params:
      - role: 'teacher' | 'tutor' (обязательный)
    """
    role = request.query_params.get("role")
    if role not in (User.Role.TEACHER, User.Role.TUTOR):
        return Response(
            {
                "detail": "Параметр 'role' обязателен и должен быть 'teacher' или 'tutor'"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if role == User.Role.TEACHER:
        # Получаем всех пользователей с ролью TEACHER, а не только тех, у кого есть TeacherProfile
        # Используем prefetch_related для оптимизации запросов к TeacherSubject
        # Сортируем по дате создания (новые первыми)
        users = (
            User.objects.filter(role=User.Role.TEACHER, is_active=True)
            .prefetch_related("teacher_subjects__subject")
            .order_by("-date_joined", "-id")
        )

        from materials.models import TeacherSubject
        from materials.serializers import TeacherSubjectSerializer

        users = list(users)
        logger.debug(f"[list_staff] Found {len(users)} teachers with role={role}")

        user_ids = [u.id for u in users]
        profiles_qs = TeacherProfile.objects.filter(
            user_id__in=user_ids
        ).select_related("user")
        profiles_map = {p.user_id: p for p in profiles_qs}

        results = []
        for user in users:
            prefetched_subjects = getattr(user, "teacher_subjects", None)
            if prefetched_subjects is not None:
                teacher_subjects = [
                    ts for ts in prefetched_subjects.all() if ts.is_active
                ]
            else:
                teacher_subjects = list(
                    TeacherSubject.objects.filter(teacher=user, is_active=True)
                    .select_related("subject")
                    .order_by("assigned_at")
                )

            subjects_data = TeacherSubjectSerializer(teacher_subjects, many=True).data

            profile = profiles_map.get(user.id)
            if profile:
                profile_data = TeacherProfileSerializer(profile).data
                profile_data["subjects"] = subjects_data
                results.append(profile_data)
                logger.debug(
                    f"[list_staff] Added teacher with profile: {user.username} (id={user.id}, profile_id={profile.id}, subjects={len(subjects_data)})"
                )
            else:
                main_subject = subjects_data[0]["name"] if subjects_data else ""
                results.append(
                    {
                        "id": user.id,
                        "user": UserSerializer(user).data,
                        "subject": main_subject,
                        "experience_years": 0,
                        "bio": "",
                        "subjects": subjects_data,
                    }
                )
                logger.debug(
                    f"[list_staff] Added teacher without profile: {user.username} (id={user.id}, subjects={len(subjects_data)})"
                )

        logger.debug(f"[list_staff] Returning {len(results)} teachers")
        return Response({"results": results})
    else:
        # Для тьюторов аналогично
        users = User.objects.filter(role=User.Role.TUTOR, is_active=True).order_by(
            "-date_joined", "-id"
        )

        logger.debug(f"[list_staff] Found {users.count()} tutors with role={role}")

        results = []
        for user in users:
            try:
                # Пытаемся получить профиль - используем get() для явной проверки
                profile = TutorProfile.objects.select_related("user").get(user=user)
                profile_data = TutorProfileSerializer(profile).data
                results.append(profile_data)
                logger.debug(
                    f"[list_staff] Added tutor with profile: {user.username} (id={user.id}, profile_id={profile.id})"
                )
            except TutorProfile.DoesNotExist:
                results.append(
                    {
                        "id": user.id,  # Используем ID пользователя
                        "user": UserSerializer(user).data,
                        "specialization": "",
                        "experience_years": 0,
                        "bio": "",
                    }
                )
                logger.debug(
                    f"[list_staff] Added tutor without profile: {user.username} (id={user.id})"
                )

        logger.debug(f"[list_staff] Returning {len(results)} tutors")
        return Response({"results": results})


@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    from materials.serializers import (
        TeacherSubjectUpdateSerializer,
        TeacherSubjectSerializer,
    )

    # Проверяем что пользователь с указанным ID существует и является преподавателем
    try:
        teacher = User.objects.get(
            id=teacher_id, role=User.Role.TEACHER, is_active=True
        )
    except User.DoesNotExist:
        return Response(
            {"detail": "Преподаватель не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Валидация входных данных
    serializer = TeacherSubjectUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    subject_ids = serializer.validated_data["subject_ids"]

    # Используем транзакцию для атомарности операции
    with transaction.atomic():
        # Удаляем все существующие связи преподавателя с предметами
        TeacherSubject.objects.filter(teacher=teacher).delete()

        # Создаем новые связи используя bulk_create для оптимизации
        if subject_ids:
            teacher_subjects = [
                TeacherSubject(teacher=teacher, subject_id=subject_id, is_active=True)
                for subject_id in subject_ids
            ]
            TeacherSubject.objects.bulk_create(teacher_subjects)

    # Получаем обновленный список предметов с prefetch для оптимизации
    updated_teacher_subjects = (
        TeacherSubject.objects.filter(teacher=teacher, is_active=True)
        .select_related("subject")
        .order_by("assigned_at")
    )

    # Сериализуем результат
    subjects_data = TeacherSubjectSerializer(updated_teacher_subjects, many=True).data

    return Response(
        {
            "success": True,
            "teacher_id": teacher_id,
            "subjects": subjects_data,
            "message": f"Предметы преподавателя успешно обновлены ({len(subjects_data)} предметов)",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    # Loggging request start

    payload: Dict[str, Any] = request.data or {}
    role = payload.get("role")
    email = (payload.get("email") or "").strip().lower()
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()

    if role not in (User.Role.TEACHER, User.Role.TUTOR):
        return Response(
            {"detail": "role должен быть 'teacher' или 'tutor'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not email:
        return Response(
            {"detail": "email обязателен"}, status=status.HTTP_400_BAD_REQUEST
        )

    validator = EmailValidator()
    try:
        validator(email)
    except DjangoValidationError:
        return Response(
            {"detail": "Невалидный формат email"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not first_name or not last_name:
        return Response(
            {"detail": "first_name и last_name обязательны"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile_kwargs: Dict[str, Any] = {}
    if role == User.Role.TEACHER:
        subject = (payload.get("subject") or "").strip()
        if not subject:
            return Response(
                {"detail": "subject обязателен для teacher"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile_kwargs["subject"] = subject
    else:
        specialization = (payload.get("specialization") or "").strip()
        if not specialization:
            return Response(
                {"detail": "specialization обязателен для tutor"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile_kwargs["specialization"] = specialization

    if payload.get("experience_years") is not None:
        try:
            profile_kwargs["experience_years"] = int(payload.get("experience_years"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "experience_years должен быть числом"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    if payload.get("bio") is not None:
        profile_kwargs["bio"] = str(payload.get("bio"))

    # Генерируем надежный пароль
    generated_password = get_random_string(length=12)

    try:
        with transaction.atomic():
            # Используем SELECT FOR UPDATE для предотвращения race condition
            # при проверке уникальности email
            email_exists = User.objects.select_for_update().filter(email=email).exists()
            if email_exists:
                return Response(
                    {"detail": "Email уже зарегистрирован"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            django_user = None
            # Создаем локально в Django
            username = email
            if User.objects.filter(username=username).exists():
                base = email.split("@")[0]
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
            django_user.save(update_fields=["first_name", "last_name", "role", "email"])

            # Создаём/обновляем профиль в зависимости от роли
            if role == User.Role.TEACHER:
                logger.debug(
                    f"[create_staff] Creating/updating TeacherProfile for user {django_user.id}"
                )
                profile, created = TeacherProfile.objects.get_or_create(
                    user=django_user, defaults=profile_kwargs
                )
                logger.debug(
                    f"[create_staff] TeacherProfile {'created' if created else 'updated'}: id={profile.id}, subject={profile.subject}"
                )

                # Если профиль уже существовал, обновляем его
                if not created:
                    for k, v in profile_kwargs.items():
                        setattr(profile, k, v)
                    profile.save()
                    logger.debug(
                        f"[create_staff] TeacherProfile updated: subject={profile.subject}"
                    )

                # Создаем связь TeacherSubject, если указан предмет
                if profile.subject:
                    from materials.models import TeacherSubject, Subject

                    # Ищем предмет по имени или создаем новый
                    subject, subject_created = Subject.objects.get_or_create(
                        name=profile.subject,
                        defaults={"description": "", "color": "#3b82f6"},
                    )
                    logger.debug(
                        f"[create_staff] Subject {'created' if subject_created else 'found'}: id={subject.id}, name={subject.name}"
                    )

                    # Создаем связь учитель-предмет
                    teacher_subject, ts_created = TeacherSubject.objects.get_or_create(
                        teacher=django_user,
                        subject=subject,
                        defaults={"is_active": True},
                    )
                    logger.debug(
                        f"[create_staff] TeacherSubject {'created' if ts_created else 'found'}: id={teacher_subject.id}, is_active={teacher_subject.is_active}"
                    )
            else:
                logger.debug(
                    f"[create_staff] Creating/updating TutorProfile for user {django_user.id}"
                )
                profile, created = TutorProfile.objects.get_or_create(
                    user=django_user, defaults=profile_kwargs
                )
                logger.debug(
                    f"[create_staff] TutorProfile {'created' if created else 'updated'}: id={profile.id}"
                )

                # Если профиль уже существовал, обновляем его
                if not created:
                    for k, v in profile_kwargs.items():
                        setattr(profile, k, v)
                    profile.save()

    except IntegrityError as exc:
        logger.warning(
            f"[create_staff] IntegrityError (race condition?) for email {email}: {exc}"
        )
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            return Response(
                {"detail": "Email уже зарегистрирован"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.error(
            f"[create_staff] Unexpected IntegrityError: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(f"[create_staff] Error creating user: {str(exc)}", exc_info=True)
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # После завершения транзакции, принудительно обновляем данные из базы
    # Это гарантирует, что новый пользователь будет виден в списке
    django_user.refresh_from_db()

    # Возвращаем учётные данные ОДИН раз (логин = email)
    # Возвращаем профиль для мгновенного UI-обновления
    try:
        if role == User.Role.TEACHER:
            profile = TeacherProfile.objects.select_related("user").get(
                user=django_user
            )
            profile_data = TeacherProfileSerializer(profile).data
        else:
            profile = TutorProfile.objects.select_related("user").get(user=django_user)
            profile_data = TutorProfileSerializer(profile).data
    except (TeacherProfile.DoesNotExist, TutorProfile.DoesNotExist) as e:
        # Если профиль не найден, создаем минимальные данные
        logger.debug(
            f"[create_staff] Profile not found for user {django_user.id}, creating minimal data"
        )
        if role == User.Role.TEACHER:
            profile_data = {
                "id": django_user.id,
                "user": UserSerializer(django_user).data,
                "subject": profile_kwargs.get("subject", ""),
                "experience_years": profile_kwargs.get("experience_years", 0),
                "bio": profile_kwargs.get("bio", ""),
                "subjects_list": [],
            }
        else:
            profile_data = {
                "id": django_user.id,
                "user": UserSerializer(django_user).data,
                "specialization": profile_kwargs.get("specialization", ""),
                "experience_years": profile_kwargs.get("experience_years", 0),
                "bio": profile_kwargs.get("bio", ""),
            }

    return Response(
        {
            "user": UserSerializer(django_user).data,
            "profile": profile_data,
            "credentials": {
                "login": email,
                "password": generated_password,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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

    Note: Only returns StudentProfile entries where user.role='STUDENT'.
    """
    from .serializers import StudentListSerializer

    # Базовый queryset с оптимизацией запросов
    queryset = (
        StudentProfile.objects.filter(user__role=User.Role.STUDENT)
        .select_related("user", "tutor", "parent")
        .prefetch_related(
            "user__subject_enrollments__subject",
            "user__subject_enrollments__teacher",
            "user__payments",
            "user__reports",
        )
        .annotate(enrollments_count=Count("user__subject_enrollments"))
    )

    # Фильтр по активности пользователя (по умолчанию показываем всех)
    is_active = request.query_params.get("is_active")
    if is_active is not None:
        is_active_bool = is_active.lower() == "true"
        queryset = queryset.filter(user__is_active=is_active_bool)
    # Если is_active не указан - показываем всех пользователей (включая неактивных)

    # Фильтр по тьютору
    tutor_id = request.query_params.get("tutor_id")
    if tutor_id:
        try:
            tutor_id_int = int(tutor_id)
            queryset = queryset.filter(tutor_id=tutor_id_int)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Неверный формат tutor_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Фильтр по классу
    grade = request.query_params.get("grade")
    if grade:
        queryset = queryset.filter(grade=grade)

    # Поиск по имени, email, username
    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__username__icontains=search)
        )

    # Сортировка
    ordering = request.query_params.get("ordering", "-user__date_joined")
    allowed_orderings = [
        "user__email",
        "-user__email",
        "user__first_name",
        "-user__first_name",
        "user__last_name",
        "-user__last_name",
        "user__date_joined",
        "-user__date_joined",
        "grade",
        "-grade",
        "progress_percentage",
        "-progress_percentage",
    ]

    if ordering in allowed_orderings:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by("-user__date_joined")

    # Пагинация
    paginator = StudentPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = StudentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Fallback без пагинации (не должно произойти)
    serializer = StudentListSerializer(queryset, many=True)
    return Response({"results": serializer.data})


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
            "user", "tutor", "parent"
        ).get(user_id=student_id, user__role=User.Role.STUDENT)
    except StudentProfile.DoesNotExist:
        return Response(
            {"detail": "Студент не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Сериализуем данные
    serializer = StudentDetailSerializer(student_profile)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ============= ENDPOINTS ДЛЯ РЕДАКТИРОВАНИЯ ПОЛЬЗОВАТЕЛЕЙ (ADMIN) =============
@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
            "student_profile", "teacher_profile", "tutor_profile", "parent_profile"
        ).get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Проверка: нельзя деактивировать самого себя
    if "is_active" in request.data:
        if not request.data["is_active"] and user.id == request.user.id:
            return Response(
                {"detail": "Вы не можете деактивировать сам себя"},
                status=status.HTTP_403_FORBIDDEN,
            )

    # Извлекаем данные профиля из запроса (если есть)
    profile_data = request.data.get("profile_data", {})

    # Используем транзакцию для атомарности
    with transaction.atomic():
        # 1. Обновляем базовые поля пользователя
        user_serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Проверка целостности при изменении role
        if "role" in user_serializer.validated_data:
            new_role = user_serializer.validated_data["role"]
            old_role = user.role

            if new_role != old_role:
                # Проверяем зависимые записи перед сменой роли
                if old_role == User.Role.TUTOR:
                    tutees = StudentProfile.objects.filter(tutor=user).exists()
                    if tutees:
                        return Response(
                            {
                                "error": "Cannot change role from TUTOR: students depend on this tutor",
                                "detail": "Удалите связь между студентами и этим тьютором перед сменой роли",
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                if old_role == User.Role.TEACHER:
                    from materials.models import SubjectEnrollment

                    enrollments = SubjectEnrollment.objects.filter(
                        teacher=user
                    ).exists()
                    if enrollments:
                        return Response(
                            {
                                "error": "Cannot change role from TEACHER: enrollments depend on this teacher",
                                "detail": "Удалите связь между студентами и этим преподавателем перед сменой роли",
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                profile_model = {
                    "STUDENT": StudentProfile,
                    "TEACHER": TeacherProfile,
                    "TUTOR": TutorProfile,
                    "PARENT": ParentProfile,
                }.get(new_role)

                if (
                    profile_model
                    and not profile_model.objects.filter(user=user).exists()
                ):
                    return Response(
                        {
                            "error": f"Cannot change role to {new_role}: profile does not exist"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                audit_logger.info(
                    f"Admin {request.user.id} changed user {user.id} role from {old_role} to {new_role}"
                )

        updated_user = user_serializer.save()

        # 2. Обновляем профиль в зависимости от роли (если переданы данные профиля)
        profile_serializer_data = None

        if profile_data and user.role == User.Role.STUDENT:
            try:
                student_profile = StudentProfile.objects.select_related(
                    "user", "tutor", "parent"
                ).get(user=user)
                profile_serializer = StudentProfileUpdateSerializer(
                    student_profile, data=profile_data, partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(
                        profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_profile = profile_serializer.save()
                profile_serializer_data = StudentProfileSerializer(updated_profile).data

                log_object_changes(
                    request,
                    student_profile,
                    profile_serializer,
                    "update_student_profile",
                )
            except StudentProfile.DoesNotExist:
                # Если профиля нет - создаем
                profile_serializer = StudentProfileUpdateSerializer(data=profile_data)
                if not profile_serializer.is_valid():
                    return Response(
                        profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_profile = StudentProfile.objects.create(
                    user=user, **profile_serializer.validated_data
                )
                profile_serializer_data = StudentProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.TEACHER:
            try:
                teacher_profile = TeacherProfile.objects.select_related("user").get(
                    user=user
                )
                profile_serializer = TeacherProfileUpdateSerializer(
                    teacher_profile, data=profile_data, partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(
                        profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_profile = profile_serializer.save()
                profile_serializer_data = TeacherProfileSerializer(updated_profile).data

                log_object_changes(
                    request,
                    teacher_profile,
                    profile_serializer,
                    "update_teacher_profile",
                )
            except TeacherProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = TeacherProfile.objects.create(
                    user=user,
                    experience_years=profile_data.get("experience_years", 0),
                    bio=profile_data.get("bio", ""),
                )
                profile_serializer_data = TeacherProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.TUTOR:
            try:
                tutor_profile = TutorProfile.objects.select_related("user").get(
                    user=user
                )
                profile_serializer = TutorProfileUpdateSerializer(
                    tutor_profile, data=profile_data, partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(
                        profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_profile = profile_serializer.save()
                profile_serializer_data = TutorProfileSerializer(updated_profile).data

                log_object_changes(
                    request,
                    tutor_profile,
                    profile_serializer,
                    "update_tutor_profile",
                )
            except TutorProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = TutorProfile.objects.create(
                    user=user,
                    specialization=profile_data.get("specialization", ""),
                    experience_years=profile_data.get("experience_years", 0),
                    bio=profile_data.get("bio", ""),
                )
                profile_serializer_data = TutorProfileSerializer(updated_profile).data

        elif profile_data and user.role == User.Role.PARENT:
            try:
                parent_profile = ParentProfile.objects.select_related("user").get(
                    user=user
                )
                profile_serializer = ParentProfileUpdateSerializer(
                    parent_profile, data=profile_data, partial=True
                )
                if not profile_serializer.is_valid():
                    return Response(
                        profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_profile = profile_serializer.save()

                profile_serializer_data = ParentProfileSerializer(updated_profile).data

                log_object_changes(
                    request,
                    parent_profile,
                    profile_serializer,
                    "update_parent_profile",
                )
            except ParentProfile.DoesNotExist:
                # Если профиля нет - создаем
                updated_profile = ParentProfile.objects.create(user=user)

                profile_serializer_data = ParentProfileSerializer(updated_profile).data

    # Логируем изменения пользователя
    log_object_changes(
        request,
        user,
        user_serializer,
        "update_user",
        sensitive_fields=["password"],
    )

    # 3. Формируем ответ
    response_data = {
        "success": True,
        "user": UserSerializer(updated_user).data,
        "message": "Пользователь успешно обновлен",
    }

    # Добавляем данные профиля в ответ если они были обновлены
    if profile_serializer_data:
        response_data["profile"] = profile_serializer_data
        response_data["message"] = "Пользователь и профиль успешно обновлены"

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        student_profile = StudentProfile.objects.select_related(
            "user", "tutor", "parent"
        ).get(user_id=student_id, user__role=User.Role.STUDENT)
    except StudentProfile.DoesNotExist:
        return Response(
            {"detail": "Профиль студента не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Валидация и обновление
    serializer = StudentProfileUpdateSerializer(
        student_profile, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    # Логируем изменения профиля студента
    log_object_changes(
        request,
        student_profile,
        serializer,
        "update_student_profile",
    )

    return Response(
        {
            "success": True,
            "profile": StudentProfileSerializer(updated_profile).data,
            "message": "Профиль студента успешно обновлен",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        teacher_profile = TeacherProfile.objects.select_related("user").get(
            user_id=teacher_id, user__role=User.Role.TEACHER
        )
    except TeacherProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            teacher_user = User.objects.get(id=teacher_id, role=User.Role.TEACHER)
            teacher_profile = TeacherProfile.objects.create(
                user=teacher_user, subject="", experience_years=0, bio=""
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Преподаватель не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление
    serializer = TeacherProfileUpdateSerializer(
        teacher_profile, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    # Логируем изменения профиля преподавателя
    log_object_changes(
        request,
        teacher_profile,
        serializer,
        "update_teacher_profile",
    )

    return Response(
        {
            "success": True,
            "profile": TeacherProfileSerializer(updated_profile).data,
            "message": "Профиль преподавателя успешно обновлен",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        tutor_profile = TutorProfile.objects.select_related("user").get(
            user_id=tutor_id, user__role=User.Role.TUTOR
        )
    except TutorProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            tutor_user = User.objects.get(id=tutor_id, role=User.Role.TUTOR)
            tutor_profile = TutorProfile.objects.create(
                user=tutor_user, specialization="", experience_years=0, bio=""
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Тьютор не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление
    serializer = TutorProfileUpdateSerializer(
        tutor_profile, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    # Логируем изменения профиля тьютора
    log_object_changes(
        request,
        tutor_profile,
        serializer,
        "update_tutor_profile",
    )

    return Response(
        {
            "success": True,
            "profile": TutorProfileSerializer(updated_profile).data,
            "message": "Профиль тьютора успешно обновлен",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        parent_profile = ParentProfile.objects.select_related("user").get(
            user_id=parent_id, user__role=User.Role.PARENT
        )
    except ParentProfile.DoesNotExist:
        # Если профиля нет - создаем
        try:
            parent_user = User.objects.get(id=parent_id, role=User.Role.PARENT)
            parent_profile = ParentProfile.objects.create(user=parent_user)
        except User.DoesNotExist:
            return Response(
                {"detail": "Родитель не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    # Валидация и обновление (пока нет полей)
    serializer = ParentProfileUpdateSerializer(
        parent_profile, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_profile = serializer.save()

    # Логируем изменения профиля родителя
    log_object_changes(
        request,
        parent_profile,
        serializer,
        "update_parent_profile",
    )

    return Response(
        {
            "success": True,
            "profile": ParentProfileSerializer(updated_profile).data,
            "message": "Профиль родителя успешно обновлен",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    if not user.is_active:
        return Response(
            {"detail": "Невозможно сбросить пароль для неактивного пользователя"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Генерация надежного пароля: 12 символов
    # Минимум: 1 заглавная, 1 строчная, 1 цифра, 1 спецсимвол
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = "".join(secrets.choice(alphabet) for _ in range(12))

    # Обновление в Django
    user.set_password(new_password)
    user.save(update_fields=["password"])

    return Response(
        {
            "success": True,
            "user_id": user.id,
            "email": user.email,
            "new_password": new_password,
            "message": "Пароль успешно изменен. Передайте новый пароль пользователю.",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        - Нельзя удалить единственного суперпользователя (is_superuser=True)

    Каскадное удаление (при hard delete):
        - Профиль (StudentProfile, TeacherProfile, etc.)
        - SubjectEnrollment
        - Payment (помечаются как archived)
        - Report

    Returns:
        {
            "success": true,
            "message": "Пользователь полностью удален из системы" | "Пользователь деактивирован (soft delete)"
        }

    Raises:
        - 400: Попытка удалить себя или последнего superuser
        - 404: Пользователь не найден
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    if user.id == request.user.id:
        audit_logger.warning(f"Admin {request.user.id} attempted self-delete")
        return Response(
            {"error": "Cannot delete yourself"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.is_superuser:
        superuser_count = User.objects.filter(is_superuser=True, is_active=True).count()
        if superuser_count <= 1:
            audit_logger.warning(
                f"Admin {request.user.id} attempted to delete last superuser {user_id}"
            )
            return Response(
                {"error": "Cannot delete last superuser"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    soft_delete = request.query_params.get("soft", "false").lower() == "true"

    with transaction.atomic():
        if soft_delete:
            user.is_active = False
            user.save(update_fields=["is_active"])
            message = "Пользователь деактивирован (soft delete)"
            logger.info(f"[delete_user] Soft deleted user {user.id} ({user.email})")
        else:
            user_id_deleted = user.id
            user_email = user.email
            user.delete()

            logger.info(
                f"[delete_user] Hard deleted user {user_id_deleted} ({user_email}) from database"
            )
            message = "Пользователь полностью удален из системы"

    audit_logger.info(f"Admin {request.user.id} deleted user {user_id}")
    return Response({"success": True, "message": message}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    password = validated_data.get("password")
    if not password:
        password = get_random_string(length=12)

    email = validated_data["email"]
    first_name = validated_data["first_name"]
    last_name = validated_data["last_name"]
    role = validated_data["role"]
    phone = validated_data.get("phone", "")

    # Создание пользователя локально в Django
    try:
        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                return Response(
                    {"detail": "Email уже зарегистрирован"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            django_user = None

            # Создание только в Django
            username = email
            if User.objects.filter(username=username).exists():
                base = email.split("@")[0]
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
            django_user.save(
                update_fields=["first_name", "last_name", "role", "email", "phone"]
            )

            # Создаем профиль в зависимости от роли
            profile_data = {}

            if role == User.Role.STUDENT:
                grade = validated_data.get("grade")
                goal = validated_data.get("goal", "")
                tutor_id = validated_data.get("tutor_id")
                parent_id = validated_data.get("parent_id")

                tutor = None
                parent = None
                if tutor_id:
                    tutor = User.objects.get(id=tutor_id, role=User.Role.TUTOR)
                if parent_id:
                    parent = User.objects.get(id=parent_id, role=User.Role.PARENT)

                profile = StudentProfile.objects.create(
                    user=django_user, grade=grade, goal=goal, tutor=tutor, parent=parent
                )
                profile_data = StudentProfileSerializer(profile).data

            elif role == User.Role.TEACHER:
                subject = validated_data.get("subject", "")
                experience_years = validated_data.get("experience_years", 0)
                bio = validated_data.get("bio", "")

                profile = TeacherProfile.objects.create(
                    user=django_user,
                    subject=subject,
                    experience_years=experience_years,
                    bio=bio,
                )

                profile_data = TeacherProfileSerializer(profile).data

            elif role == User.Role.TUTOR:
                specialization = validated_data.get("specialization")
                experience_years = validated_data.get("experience_years", 0)
                bio = validated_data.get("bio", "")

                profile = TutorProfile.objects.create(
                    user=django_user,
                    specialization=specialization,
                    experience_years=experience_years,
                    bio=bio,
                )
                profile_data = TutorProfileSerializer(profile).data

            elif role == User.Role.PARENT:
                profile = ParentProfile.objects.create(user=django_user)

                profile_data = ParentProfileSerializer(profile).data

    except IntegrityError as exc:
        logger.warning(
            f"[create_user_with_profile] IntegrityError (race condition?) for email {email}: {exc}"
        )
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            return Response(
                {"detail": "Email уже зарегистрирован"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "username" in str(exc).lower():
            # Retry с новым username если произошла race condition
            try:
                with transaction.atomic():
                    base = email.split("@")[0]
                    for i in range(1, 100):
                        new_username = f"{base}{i}@local"
                        if not User.objects.filter(username=new_username).exists():
                            django_user = User.objects.create(
                                username=new_username,
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                role=role,
                                is_active=True,
                            )
                            django_user.set_password(password)
                            django_user.save()
                            break
                    else:
                        raise ValueError(
                            "Не удалось создать username после 100 попыток"
                        )
            except Exception as retry_exc:
                logger.error(
                    f"[create_user_with_profile] Retry failed: {str(retry_exc)}",
                    exc_info=True,
                )
                return Response(
                    {"detail": "Internal server error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.error(
                f"[create_user_with_profile] Unexpected IntegrityError: {str(exc)}",
                exc_info=True,
            )
            return Response(
                {"detail": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as exc:
        logger.error(
            f"[create_user_with_profile] Error creating user: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "success": True,
            "user": UserSerializer(django_user).data,
            "profile": profile_data,
            "credentials": {"login": email, "password": password},
            "message": "Пользователь успешно создан",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    password = validated_data.get("password")
    if not password:
        password = get_random_string(length=12)

    email = validated_data["email"]
    first_name = validated_data["first_name"]
    last_name = validated_data["last_name"]
    grade = validated_data["grade"]
    phone = validated_data.get("phone", "")
    goal = validated_data.get("goal", "")
    tutor_id = validated_data.get("tutor_id")
    parent_id = validated_data.get("parent_id")

    # Создание пользователя локально в Django
    try:
        with transaction.atomic():
            # Проверка уникальности email ВНУТРИ транзакции для предотвращения race condition
            if User.objects.filter(email=email).exists():
                return Response(
                    {"detail": "Пользователь с таким email уже существует"},
                    status=status.HTTP_409_CONFLICT,
                )

            django_user = None

            # Создание только в Django
            username = email
            if User.objects.filter(username=username).exists():
                base = email.split("@")[0]
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
            django_user.save(
                update_fields=["first_name", "last_name", "role", "email", "phone"]
            )

            # Получаем связанные объекты (tutor, parent)
            tutor = None
            parent = None
            if tutor_id:
                try:
                    tutor = User.objects.get(
                        id=tutor_id, role=User.Role.TUTOR, is_active=True
                    )
                except User.DoesNotExist:
                    pass

            if parent_id:
                try:
                    parent = User.objects.get(
                        id=parent_id, role=User.Role.PARENT, is_active=True
                    )
                except User.DoesNotExist:
                    pass

            # Создаем или обновляем профиль студента (на случай если signal уже создал профиль)
            student_profile, profile_created = StudentProfile.objects.get_or_create(
                user=django_user,
                defaults={
                    "grade": grade,
                    "goal": goal,
                    "tutor": tutor,
                    "parent": parent,
                },
            )

            # Если профиль уже существовал (создан signal), обновляем его данные
            if not profile_created:
                student_profile.grade = grade
                student_profile.goal = goal
                student_profile.tutor = tutor
                student_profile.parent = parent
                student_profile.save(update_fields=["grade", "goal", "tutor", "parent"])

            # Логируем успешное создание
            logger.info(
                f"[create_student] Created student: {django_user.email} (id={django_user.id})"
            )
            audit_logger.info(
                f"action=student_created user_id={django_user.id} email={django_user.email} "
                f"grade={grade} tutor_id={tutor_id} parent_id={parent_id} created_by={request.user.id}"
            )

    except IntegrityError as exc:
        # Ловим race condition: два параллельных запроса создали пользователя с одним email
        logger.warning(
            f"[create_student] IntegrityError (race condition?) for email {email}: {exc}"
        )
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            return Response(
                {"detail": "Пользователь с таким email уже существует"},
                status=status.HTTP_409_CONFLICT,
            )
        # Если IntegrityError не связан с email, пробрасываем дальше
        logger.error(
            f"[create_student] Unexpected IntegrityError: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(
            f"[create_student] Error creating student: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Обновляем данные из базы
    django_user.refresh_from_db()
    student_profile.refresh_from_db()

    # Возвращаем учетные данные ОДИН раз
    return Response(
        {
            "success": True,
            "user": UserSerializer(django_user).data,
            "profile": StudentProfileSerializer(student_profile).data,
            "credentials": {"login": django_user.email, "password": password},
            "message": "Студент успешно создан",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    # Валидация данных через serializer
    serializer = ParentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Извлекаем валидированные данные
    validated_data = serializer.validated_data
    email = validated_data["email"]
    first_name = validated_data["first_name"]
    last_name = validated_data["last_name"]
    phone = validated_data.get("phone", "")

    # Генерация пароля если не указан
    password = validated_data.get("password")
    if not password:
        password = get_random_string(length=12)

    # Создание пользователя локально в Django
    try:
        with transaction.atomic():
            # Проверка уникальности email ВНУТРИ транзакции для предотвращения race condition
            if User.objects.filter(email=email).exists():
                return Response(
                    {"detail": "Пользователь с таким email уже существует"},
                    status=status.HTTP_409_CONFLICT,
                )

            django_user = None

            # Создание только в Django
            username = email
            if User.objects.filter(username=username).exists():
                base = email.split("@")[0]
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
                phone=phone,
            )
            django_user.set_password(password)
            django_user.save()

            # Обновляем данные пользователя
            django_user.first_name = first_name
            django_user.last_name = last_name
            django_user.role = User.Role.PARENT
            django_user.email = email
            django_user.phone = phone
            django_user.save(
                update_fields=["first_name", "last_name", "role", "email", "phone"]
            )

            # Создаем или обновляем профиль родителя
            parent_profile, profile_created = ParentProfile.objects.get_or_create(
                user=django_user
            )

            # Логируем успешное создание
            logger.info(
                f"[create_parent] Created parent: {django_user.email} (id={django_user.id})"
            )
            audit_logger.info(
                f"action=parent_created user_id={django_user.id} email={django_user.email} "
                f"created_by={request.user.id}"
            )

    except IntegrityError as exc:
        # Ловим race condition: два параллельных запроса создали пользователя с одним email
        logger.warning(
            f"[create_parent] IntegrityError (race condition?) for email {email}: {exc}"
        )
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            return Response(
                {"detail": "Пользователь с таким email уже существует"},
                status=status.HTTP_409_CONFLICT,
            )
        # Если IntegrityError не связан с email, пробрасываем дальше
        logger.error(
            f"[create_parent] Unexpected IntegrityError: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(
            f"[create_parent] Error creating parent: {str(exc)}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Обновляем данные из базы
    django_user.refresh_from_db()

    # Возвращаем учетные данные ОДИН раз
    return Response(
        {
            "success": True,
            "user": UserSerializer(django_user).data,
            "profile": ParentProfileSerializer(parent_profile).data,
            "credentials": {"login": django_user.email, "password": password},
            "message": "Родитель успешно создан",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    parent_id = payload.get("parent_id")
    student_ids = payload.get("student_ids", [])

    # Валидация
    if not parent_id:
        return Response(
            {"detail": "parent_id обязателен"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not isinstance(student_ids, list) or not student_ids:
        return Response(
            {"detail": "student_ids должен быть непустым списком"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        parent_user = User.objects.get(
            id=parent_id, role=User.Role.PARENT, is_active=True
        )
    except User.DoesNotExist:
        return Response(
            {"detail": "Родитель не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Получаем студентов
    students = StudentProfile.objects.filter(
        user_id__in=student_ids, user__role=User.Role.STUDENT, user__is_active=True
    ).select_related("user")

    if not students.exists():
        return Response(
            {"detail": "Студенты не найдены"}, status=status.HTTP_404_NOT_FOUND
        )

    assigned_ids = []
    with transaction.atomic():
        for student_profile in students:
            student_profile.parent = parent_user
            student_profile.save(update_fields=["parent"])
            assigned_ids.append(student_profile.user_id)

    # Логируем назначение
    logger.info(
        f"[assign_parent_to_students] Assigned parent {parent_id} to {len(assigned_ids)} students: {assigned_ids}"
    )
    audit_logger.info(
        f"action=parent_assigned parent_id={parent_id} student_ids={assigned_ids} "
        f"assigned_by={request.user.id}"
    )

    return Response(
        {
            "success": True,
            "parent_id": parent_id,
            "assigned_students": assigned_ids,
            "message": f"{len(assigned_ids)} студентов успешно назначено родителю",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
    parents_queryset = ParentProfile.objects.select_related("user").annotate(
        children_count=Count("user__children_students")
    )

    # Фильтр по активности (опциональный)
    is_active = request.query_params.get("is_active")
    if is_active is not None:
        is_active_bool = is_active.lower() == "true"
        parents_queryset = parents_queryset.filter(user__is_active=is_active_bool)

    parents_queryset = parents_queryset.order_by("-user__date_joined", "-user__id")

    # Apply pagination
    paginator = StudentPagination()
    page = paginator.paginate_queryset(parents_queryset, request)

    if page is not None:
        serializer = ParentProfileListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Fallback if pagination fails
    serializer = ParentProfileListSerializer(parents_queryset, many=True)
    return Response({"results": serializer.data})


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
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
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # Проверка: пользователь уже активен
    if user.is_active:
        return Response(
            {"detail": "User is already active"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Реактивация пользователя
    user.is_active = True
    user.save(update_fields=["is_active"])

    # Логирование в audit log
    audit_logger.info(
        f"action=reactivate_user user_id={user.id} email={user.email} role={user.role} "
        f"reactivated_by={request.user.id} reactivated_by_email={request.user.email}"
    )
    logger.info(
        f"[reactivate_user] User {user.email} (id={user.id}) reactivated by {request.user.email}"
    )

    return Response(
        {
            "success": True,
            "message": f"{user.role.title()} {user.email} has been reactivated",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsStaffOrAdmin])
@transaction.atomic
def assign_students_to_teacher(request, teacher_id):
    """
    Назначение студентов учителю на предмет (admin/staff-only)

    Args:
        teacher_id: ID учителя

    Body JSON:
        - student_ids: [1, 2, 3] - список ID студентов (обязательно)
        - subject_id: ID предмета (обязательно)

    Returns:
        {
            "success": true,
            "assigned_students": [1, 2, 3],
            "message": "3 студентов успешно назначено учителю"
        }

    Raises:
        - 400: Невалидные данные
        - 404: Учитель или предмет не найден

    Примечание:
        Создает SubjectEnrollment для каждого студента.
        При создании SubjectEnrollment автоматически триггерятся сигналы
        для создания FORUM_SUBJECT и FORUM_TUTOR чатов.
    """
    from materials.models import Subject, SubjectEnrollment
    from rest_framework import serializers

    payload: Dict[str, Any] = request.data or {}
    student_ids = payload.get("student_ids", [])
    subject_id = payload.get("subject_id")

    # Валидация входных данных
    if not isinstance(student_ids, list) or not student_ids:
        return Response(
            {"detail": "student_ids должен быть непустым списком"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not subject_id:
        return Response(
            {"detail": "subject_id обязателен"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Проверка существования учителя
    try:
        teacher = User.objects.get(
            id=teacher_id, role=User.Role.TEACHER, is_active=True
        )
    except User.DoesNotExist:
        return Response(
            {"detail": "Учитель не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Проверка существования предмета
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {"detail": "Предмет не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Проверка существования всех студентов
    students = User.objects.filter(
        id__in=student_ids, role=User.Role.STUDENT, is_active=True
    )

    found_student_ids = set(students.values_list("id", flat=True))
    missing_ids = set(student_ids) - found_student_ids

    if missing_ids:
        return Response(
            {"detail": f"Студенты не найдены или неактивны: {sorted(missing_ids)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Создание/обновление SubjectEnrollment для каждого студента
    assigned_ids = []
    created_count = 0
    updated_count = 0

    with transaction.atomic():
        for student in students:
            enrollment, created = SubjectEnrollment.objects.update_or_create(
                student=student,
                subject=subject,
                teacher=teacher,
                defaults={
                    "assigned_by": request.user,
                    "is_active": True,
                },
            )
            assigned_ids.append(student.id)
            if created:
                created_count += 1
            else:
                updated_count += 1

    # Логируем назначение
    logger.info(
        f"[assign_students_to_teacher] Teacher {teacher_id} assigned to {len(assigned_ids)} students "
        f"for subject {subject_id} (created={created_count}, updated={updated_count}): {assigned_ids}"
    )
    audit_logger.info(
        f"action=students_assigned_to_teacher teacher_id={teacher_id} subject_id={subject_id} "
        f"student_ids={assigned_ids} created={created_count} updated={updated_count} "
        f"assigned_by={request.user.id}"
    )

    return Response(
        {
            "success": True,
            "assigned_students": assigned_ids,
            "message": f"{len(assigned_ids)} студентов успешно назначено учителю",
        },
        status=status.HTTP_200_OK,
    )


class UserManagementView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        """
        Получить список пользователей с фильтрацией по роли
        Доступно для аутентифицированных пользователей (тьюторы, администраторы)

        Query parameters:
        - role: фильтр по роли (student, teacher, tutor, parent)
        - limit: ограничение количества результатов (по умолчанию 50, максимум 100)
        """
        user = request.user

        is_admin = user.is_staff or user.is_superuser
        if not (is_admin or user.role == User.Role.TUTOR):
            return Response(
                {
                    "detail": "У вас нет прав доступа к списку пользователей",
                    "allowed_roles": ["admin", "tutor"],
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        role = request.query_params.get("role")
        limit = request.query_params.get("limit", 50)

        try:
            limit = int(limit)
            if limit < 1 or limit > 100:
                limit = 50
        except (ValueError, TypeError):
            limit = 50

        queryset = User.objects.filter(is_active=True).select_related(
            "student_profile", "teacher_profile", "tutor_profile", "parent_profile"
        )
        if role:
            queryset = queryset.filter(role=role)

        total_count = queryset.count()

        queryset = queryset.order_by("-date_joined")
        if limit and limit > 0:
            queryset = queryset[:limit]

        serializer = UserSerializer(queryset, many=True)

        logger.info(
            f"[UserManagementView.get] Retrieved {len(serializer.data)} users (role filter: {role})"
        )
        if len(serializer.data) == 0:
            logger.warning(
                f"[UserManagementView.get] WARNING: No users returned! Total count was: {total_count}"
            )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
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
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        password = validated_data.get("password")
        if not password:
            password = get_random_string(length=12)

        email = validated_data["email"]
        first_name = validated_data["first_name"]
        last_name = validated_data["last_name"]
        role = validated_data["role"]
        phone = validated_data.get("phone", "")

        try:
            with transaction.atomic():
                if User.objects.filter(email=email).exists():
                    return Response(
                        {"detail": "Email уже зарегистрирован"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                django_user = None

                username = email
                if User.objects.filter(username=username).exists():
                    base = email.split("@")[0]
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

                django_user.first_name = first_name
                django_user.last_name = last_name
                django_user.role = role
                django_user.email = email
                django_user.phone = phone
                django_user.save(
                    update_fields=["first_name", "last_name", "role", "email", "phone"]
                )

                profile_data = {}

                if role == User.Role.STUDENT:
                    grade = validated_data.get("grade")
                    goal = validated_data.get("goal", "")
                    tutor_id = validated_data.get("tutor_id")
                    parent_id = validated_data.get("parent_id")

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
                        parent=parent,
                    )
                    profile_data = StudentProfileSerializer(profile).data

                elif role == User.Role.TEACHER:
                    subject = validated_data.get("subject", "")
                    experience_years = validated_data.get("experience_years", 0)
                    bio = validated_data.get("bio", "")

                    profile = TeacherProfile.objects.create(
                        user=django_user,
                        subject=subject,
                        experience_years=experience_years,
                        bio=bio,
                    )

                    profile_data = TeacherProfileSerializer(profile).data

                elif role == User.Role.TUTOR:
                    specialization = validated_data.get("specialization")
                    experience_years = validated_data.get("experience_years", 0)
                    bio = validated_data.get("bio", "")

                    profile = TutorProfile.objects.create(
                        user=django_user,
                        specialization=specialization,
                        experience_years=experience_years,
                        bio=bio,
                    )
                    profile_data = TutorProfileSerializer(profile).data

                elif role == User.Role.PARENT:
                    profile = ParentProfile.objects.create(user=django_user)

                    profile_data = ParentProfileSerializer(profile).data

        except IntegrityError as exc:
            logger.warning(
                f"[UserManagementView.post] IntegrityError (race condition?) for email {email}: {exc}"
            )
            if "email" in str(exc).lower() or "unique" in str(exc).lower():
                return Response(
                    {"detail": "Email уже зарегистрирован"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "username" in str(exc).lower():
                try:
                    with transaction.atomic():
                        base = email.split("@")[0]
                        for i in range(1, 100):
                            new_username = f"{base}{i}@local"
                            if not User.objects.filter(username=new_username).exists():
                                django_user = User.objects.create(
                                    username=new_username,
                                    email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                    role=role,
                                    is_active=True,
                                )
                                django_user.set_password(password)
                                django_user.save()
                                break
                except Exception as inner_exc:
                    logger.error(
                        f"[UserManagementView.post] Failed to retry with new username: {inner_exc}"
                    )
                    return Response(
                        {
                            "detail": "Не удалось создать пользователя (ошибка базы данных)"
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(
                    {
                        "detail": "Не удалось создать пользователя (ошибка целостности данных)"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as exc:
            logger.error(
                f"[UserManagementView.post] Unexpected error for email {email}: {exc}"
            )
            return Response(
                {"detail": "Не удалось создать пользователя"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user_response = UserSerializer(django_user).data

        logger.info(
            f"[UserManagementView.post] User {email} (role={role}) created successfully"
        )
        audit_logger.info(
            f"action=user_created email={email} role={role} created_by={request.user.id}"
        )

        return Response(
            {
                "success": True,
                "user": user_response,
                "profile": profile_data,
                "credentials": {"login": email, "password": password},
            },
            status=status.HTTP_201_CREATED,
        )
