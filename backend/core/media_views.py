"""
Views для раздачи медиа-файлов в продакшене
"""
import os
import logging
from django.http import Http404, FileResponse, HttpResponse, HttpResponseForbidden
from django.conf import settings
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import authentication_classes

logger = logging.getLogger(__name__)


def check_file_access_permission(user, file_path):
    """
    Проверяет, имеет ли пользователь доступ к файлу.

    Args:
        user: User объект
        file_path: Путь к файлу относительно MEDIA_ROOT

    Returns:
        tuple: (bool, str) - (имеет ли доступ, причина отказа)
    """
    # Администраторы имеют доступ ко всем файлам
    if user.is_staff or user.is_superuser:
        return True, None

    # Определяем тип файла по пути
    if file_path.startswith('avatars/'):
        # Аватары доступны всем аутентифицированным пользователям
        return True, None

    elif file_path.startswith('materials/files/'):
        # Файлы материалов - проверяем через модель Material
        return _check_material_file_access(user, file_path)

    elif file_path.startswith('study_plans/files/'):
        # Файлы планов занятий - проверяем через модель StudyPlanFile
        return _check_study_plan_file_access(user, file_path)

    elif file_path.startswith('study_plans/generated/'):
        # Сгенерированные файлы учебных планов через AI
        return _check_generated_file_access(user, file_path)

    else:
        # Для остальных файлов требуется явная проверка
        logger.warning(f"Unknown file path type: {file_path}")
        return False, "Неизвестный тип файла"


def _check_material_file_access(user, file_path):
    """Проверка доступа к файлам материалов"""
    from materials.models import Material

    try:
        # Ищем материал с этим файлом
        material = Material.objects.select_related(
            'author', 'subject'
        ).prefetch_related('assigned_to').filter(
            file__icontains=file_path.split('/')[-1]
        ).first()

        if not material:
            return False, "Материал не найден"

        # Автор материала имеет доступ
        if material.author_id == user.id:
            return True, None

        # Пользователи, которым назначен материал
        if material.assigned_to.filter(id=user.id).exists():
            return True, None

        # Публичные материалы доступны всем
        if material.is_public:
            return True, None

        # Студенты, зачисленные на предмет
        if user.role == 'student':
            from materials.models import SubjectEnrollment
            if SubjectEnrollment.objects.filter(
                student=user,
                subject=material.subject,
                is_active=True
            ).exists():
                return True, None

        # Тьютор студента, которому назначен материал
        if user.role == 'tutor':
            if material.assigned_to.filter(
                student_profile__tutor=user
            ).exists():
                return True, None

        # Родитель студента, которому назначен материал
        if user.role == 'parent':
            if material.assigned_to.filter(
                student_profile__parent=user
            ).exists():
                return True, None

        return False, "Нет доступа к этому материалу"

    except Exception as e:
        logger.error(f"Error checking material file access: {e}")
        return False, f"Ошибка проверки доступа: {str(e)}"


def _check_study_plan_file_access(user, file_path):
    """Проверка доступа к файлам планов занятий"""
    from materials.models import StudyPlanFile

    try:
        # Ищем файл плана занятий
        plan_file = StudyPlanFile.objects.select_related(
            'study_plan__teacher',
            'study_plan__student',
            'study_plan__student__student_profile',
            'uploaded_by'
        ).filter(
            file__icontains=file_path.split('/')[-1]
        ).first()

        if not plan_file:
            return False, "Файл плана не найден"

        study_plan = plan_file.study_plan

        # Преподаватель, создавший план
        if study_plan.teacher_id == user.id:
            return True, None

        # Студент, для которого создан план
        if study_plan.student_id == user.id:
            return True, None

        # Тьютор студента
        try:
            if hasattr(study_plan.student, 'student_profile'):
                student_profile = study_plan.student.student_profile
                if student_profile.tutor_id == user.id:
                    return True, None

                # Родитель студента
                if student_profile.parent_id == user.id:
                    return True, None
        except Exception as e:
            logger.warning(f"Error checking student profile: {e}")

        return False, "Нет доступа к этому плану занятий"

    except Exception as e:
        logger.error(f"Error checking study plan file access: {e}")
        return False, f"Ошибка проверки доступа: {str(e)}"


def _check_generated_file_access(user, file_path):
    """
    Проверка доступа к сгенерированным файлам учебных планов (AI-генерация)

    Файлы в study_plans/generated/ создаются через StudyPlanGeneratorService.
    Доступ имеют: teacher (создатель), student (получатель), tutor, parent.
    """
    from materials.models import GeneratedFile

    try:
        # Извлекаем имя файла из пути
        filename = file_path.split('/')[-1]

        # Ищем GeneratedFile по имени файла
        generated_file = GeneratedFile.objects.select_related(
            'generation__teacher',
            'generation__student',
            'generation__student__student_profile'
        ).filter(
            file__icontains=filename
        ).first()

        if not generated_file:
            return False, "Сгенерированный файл не найден"

        generation = generated_file.generation

        # Преподаватель, который создал генерацию
        if generation.teacher_id == user.id:
            return True, None

        # Студент, для которого создана генерация
        if generation.student_id == user.id:
            return True, None

        # Тьютор студента
        try:
            if hasattr(generation.student, 'student_profile'):
                student_profile = generation.student.student_profile
                if student_profile.tutor_id == user.id:
                    return True, None

                # Родитель студента
                if student_profile.parent_id == user.id:
                    return True, None
        except Exception as e:
            logger.warning(f"Error checking student profile for generated file: {e}")

        return False, "Нет доступа к этому сгенерированному файлу"

    except Exception as e:
        logger.error(f"Error checking generated file access: {e}")
        return False, f"Ошибка проверки доступа: {str(e)}"


@api_view(['GET', 'HEAD'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET", "HEAD"])
@cache_control(max_age=3600, private=True)
def serve_media_file(request, file_path):
    """
    Раздает медиа-файлы с проверкой прав доступа.

    Args:
        request: HTTP запрос
        file_path: Путь к файлу относительно MEDIA_ROOT

    Returns:
        FileResponse с файлом или 404/403 ошибка
    """
    logger.info(f"[serve_media_file] Request for: {file_path}")
    logger.info(f"[serve_media_file] User: {request.user}")
    logger.info(f"[serve_media_file] Is authenticated: {request.user.is_authenticated}")
    logger.info(f"[serve_media_file] Auth header: {request.META.get('HTTP_AUTHORIZATION', 'MISSING')[:50]}")

    # Безопасность: проверяем, что путь не выходит за пределы MEDIA_ROOT
    file_path = file_path.lstrip('/')

    # Убираем префикс /media/ если он есть
    if file_path.startswith('media/'):
        file_path = file_path[6:]  # Убираем 'media/'

    # Проверяем права доступа к файлу
    has_access, reason = check_file_access_permission(request.user, file_path)
    if not has_access:
        logger.warning(
            f"Access denied for user {request.user.id} to file {file_path}: {reason}"
        )
        return HttpResponseForbidden(f"Доступ запрещен: {reason}")

    # Полный путь к файлу
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    # Нормализуем путь для предотвращения path traversal атак
    full_path = os.path.normpath(full_path)
    media_root = os.path.normpath(settings.MEDIA_ROOT)

    # Проверяем, что файл находится внутри MEDIA_ROOT
    if not full_path.startswith(media_root):
        raise Http404("File not found")

    # Проверяем существование файла
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("File not found")
    
    # Определяем MIME-тип файла
    import mimetypes
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Открываем файл и возвращаем его
    try:
        file_handle = open(full_path, 'rb')
        response = FileResponse(
            file_handle,
            content_type=content_type,
            as_attachment=False
        )
        
        # Устанавливаем заголовки для кэширования
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(full_path)}"'
        
        return response
    except IOError:
        raise Http404("File not found")


@api_view(['GET', 'HEAD'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET", "HEAD"])
@cache_control(max_age=3600, private=True)
def serve_media_file_download(request, file_path):
    """
    Раздает медиа-файлы для скачивания с проверкой прав доступа.

    Args:
        request: HTTP запрос
        file_path: Путь к файлу относительно MEDIA_ROOT

    Returns:
        FileResponse с файлом для скачивания или 404/403 ошибка
    """
    # Безопасность: проверяем, что путь не выходит за пределы MEDIA_ROOT
    file_path = file_path.lstrip('/')

    # Убираем префикс /media/ если он есть
    if file_path.startswith('media/'):
        file_path = file_path[6:]  # Убираем 'media/'

    # Проверяем права доступа к файлу
    has_access, reason = check_file_access_permission(request.user, file_path)
    if not has_access:
        logger.warning(
            f"Access denied for user {request.user.id} to download file {file_path}: {reason}"
        )
        return HttpResponseForbidden(f"Доступ запрещен: {reason}")

    # Полный путь к файлу
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    # Нормализуем путь для предотвращения path traversal атак
    full_path = os.path.normpath(full_path)
    media_root = os.path.normpath(settings.MEDIA_ROOT)

    # Проверяем, что файл находится внутри MEDIA_ROOT
    if not full_path.startswith(media_root):
        raise Http404("File not found")

    # Проверяем существование файла
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("File not found")
    
    # Определяем MIME-тип файла
    import mimetypes
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Открываем файл и возвращаем его для скачивания
    try:
        file_handle = open(full_path, 'rb')
        response = FileResponse(
            file_handle,
            content_type=content_type,
            as_attachment=True
        )
        
        # Устанавливаем заголовки для скачивания
        filename = os.path.basename(full_path)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except IOError:
        raise Http404("File not found")

