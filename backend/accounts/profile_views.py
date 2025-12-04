"""
API Views для управления профилями пользователей.

Этот модуль содержит REST API Views для всех типов профилей:
- StudentProfileView - GET/PATCH /api/profile/student/
- TeacherProfileView - GET/PATCH /api/profile/teacher/
- TutorProfileView - GET/PATCH /api/profile/tutor/

Каждый View поддерживает:
- GET - получить свой профиль (User + Profile данные)
- PATCH - обновить свой профиль (User + Profile данные + avatar upload)
"""

import logging
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.db import transaction
from typing import Dict, Any

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from .profile_serializers import (
    StudentProfileDetailSerializer,
    TeacherProfileDetailSerializer,
    TutorProfileDetailSerializer,
    ParentProfileDetailSerializer,
    UserProfileUpdateSerializer
)
from .profile_service import ProfileService

# Logger for profile operations
logger = logging.getLogger(__name__)


class CustomTokenAuthentication(TokenAuthentication):
    """
    Custom authentication class that returns 401 instead of 403
    for unauthenticated requests.
    """
    def authenticate(self, request):
        try:
            result = super().authenticate(request)
            if result is None:
                # No token provided - return None to trigger 401
                return None
            return result
        except AuthenticationFailed:
            # Invalid token - re-raise to get 401
            raise


class StudentProfileView(APIView):
    """
    API endpoint для управления профилем студента.

    GET /api/profile/student/
    - Возвращает объединенные данные User + StudentProfile
    - Доступно только аутентифицированным студентам

    PATCH /api/profile/student/
    - Обновляет данные User и/или StudentProfile
    - Поддерживает загрузку аватара (multipart/form-data)
    - Поля User: first_name, last_name, email, phone, avatar
    - Поля Profile: grade, goal, telegram
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Получить данные профиля студента"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(user=request.user)
        except StudentProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[StudentProfileView] StudentProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = StudentProfile.objects.create(user=request.user)
            logger.info(
                f"[StudentProfileView] StudentProfile auto-created for user_id={request.user.id}"
            )

        user_data = {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': request.user.phone,
            'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
        }

        profile_serializer = StudentProfileDetailSerializer(profile)

        return Response({
            'user': user_data,
            'profile': profile_serializer.data
        })

    @transaction.atomic
    def patch(self, request) -> Response:
        """Обновить данные профиля студента"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = StudentProfile.objects.select_related('user').get(user=request.user)
        except StudentProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[StudentProfileView] StudentProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = StudentProfile.objects.create(user=request.user)
            logger.info(
                f"[StudentProfileView] StudentProfile auto-created for user_id={request.user.id}"
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone']
        profile_fields = ['grade', 'goal', 'telegram']

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}

        try:
            if user_data:
                user_serializer = UserProfileUpdateSerializer(
                    request.user,
                    data=user_data,
                    partial=True
                )
                if user_serializer.is_valid(raise_exception=True):
                    user_serializer.save()

            if 'avatar' in request.FILES:
                ProfileService.validate_avatar(request.FILES['avatar'])
                avatar_path = ProfileService.handle_avatar_upload(
                    profile=request.user,
                    file=request.FILES['avatar']
                )
                request.user.avatar = avatar_path
                request.user.save(update_fields=['avatar'])

            if profile_data:
                profile_serializer = StudentProfileDetailSerializer(
                    profile,
                    data=profile_data,
                    partial=True
                )
                if profile_serializer.is_valid(raise_exception=True):
                    profile_serializer.save()

            profile.refresh_from_db()
            request.user.refresh_from_db()

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_serializer = StudentProfileDetailSerializer(profile)

            return Response({
                'message': 'Profile updated successfully',
                'user': user_data,
                'profile': profile_serializer.data
            })

        except Exception as e:
            logger.error(f'StudentProfileView.patch - {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TeacherProfileView(APIView):
    """
    API endpoint для управления профилем преподавателя.

    GET /api/profile/teacher/
    - Возвращает объединенные данные User + TeacherProfile + список предметов

    PATCH /api/profile/teacher/
    - Обновляет данные User и/или TeacherProfile
    - Поддерживает загрузку аватара
    - Поддерживает обновление списка предметов (subject_ids)
    - Поля User: first_name, last_name, email, phone, avatar
    - Поля Profile: subject, experience_years, bio, telegram
    - Дополнительно: subject_ids (список ID предметов из materials.Subject)

    PRODUCTION DEPLOYMENT CHECKS:
    ===========================

    Если возникает 404 ошибка на /api/profile/teacher/ в продакшене, проверьте:

    1. Python Version Compatibility (CRITICAL):
       - Python 3.13+ имеет breaking change: collections.MutableSet → collections.abc.MutableSet
       - Проверка: python --version
       - Решение: используйте Python 3.11 или 3.12, или обновите hyperframe пакет

    2. Nginx/Apache Configuration:
       - Проверьте что /api/profile/ проксируется в Django (не статические файлы)
       - Пример Nginx:
         location /api/ {
             proxy_pass http://localhost:8000;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
         }

    3. ASGI Server (Daphne) Running:
       - Проверка: ps aux | grep daphne
       - Должен быть запущен: daphne -b 0.0.0.0 -p 8000 config.asgi:application
       - НЕ используйте runserver в продакшене (не поддерживает WebSocket)

    4. Token Authentication:
       - Проверьте что токены синхронизированы с БД
       - Тест: curl -H "Authorization: Token <TOKEN>" https://the-bot.ru/api/profile/teacher/
       - Должен быть 200 OK, не 404

    5. Django URL Configuration:
       - config/urls.py должен содержать: path('api/profile/', include('accounts.profile_urls'))
       - accounts/profile_urls.py должен содержать: path('teacher/', TeacherProfileView.as_view())

    6. Логи (для отладки):
       - Все запросы логируются с уровнем INFO
       - Автосоздание профиля логируется с WARNING/INFO
       - Ошибки доступа (неверная роль) - WARNING
       - Проверка: grep "TeacherProfileView" /var/log/django/app.log

    Если эндпоинт работает в development но не в production, проблема НЕ в коде Django,
    а в окружении (Python version, nginx config, ASGI server).
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Получить данные профиля преподавателя"""
        # Production debugging: log request start
        logger.info(
            f"[TeacherProfileView] GET request from user_id={request.user.id} "
            f"email={request.user.email} role={request.user.role}"
        )

        if request.user.role != 'teacher':
            logger.warning(
                f"[TeacherProfileView] Access denied for non-teacher user_id={request.user.id} "
                f"role={request.user.role}"
            )
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = TeacherProfile.objects.select_related('user').get(user=request.user)
            logger.debug(
                f"[TeacherProfileView] TeacherProfile found for user_id={request.user.id} "
                f"profile_id={profile.id}"
            )
        except TeacherProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[TeacherProfileView] TeacherProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = TeacherProfile.objects.create(user=request.user)
            logger.info(
                f"[TeacherProfileView] TeacherProfile auto-created for user_id={request.user.id} "
                f"profile_id={profile.id}"
            )

        user_data = {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': request.user.phone,
            'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
        }

        profile_serializer = TeacherProfileDetailSerializer(profile)

        logger.info(
            f"[TeacherProfileView] Successfully returning profile for user_id={request.user.id}"
        )
        return Response({
            'user': user_data,
            'profile': profile_serializer.data
        })

    @transaction.atomic
    def patch(self, request) -> Response:
        """Обновить данные профиля преподавателя"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = TeacherProfile.objects.select_related('user').get(user=request.user)
        except TeacherProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[TeacherProfileView] TeacherProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = TeacherProfile.objects.create(user=request.user)
            logger.info(
                f"[TeacherProfileView] TeacherProfile auto-created for user_id={request.user.id}"
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone']
        profile_fields = ['subject', 'experience_years', 'bio', 'telegram']

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}

        try:
            if user_data:
                user_serializer = UserProfileUpdateSerializer(
                    request.user,
                    data=user_data,
                    partial=True
                )
                if user_serializer.is_valid(raise_exception=True):
                    user_serializer.save()

            if 'avatar' in request.FILES:
                ProfileService.validate_avatar(request.FILES['avatar'])
                avatar_path = ProfileService.handle_avatar_upload(
                    profile=request.user,
                    file=request.FILES['avatar']
                )
                request.user.avatar = avatar_path
                request.user.save(update_fields=['avatar'])

            if profile_data:
                profile_serializer = TeacherProfileDetailSerializer(
                    profile,
                    data=profile_data,
                    partial=True
                )
                if profile_serializer.is_valid(raise_exception=True):
                    profile_serializer.save()

            if 'subject_ids' in request.data:
                self._update_teacher_subjects(request.user, request.data['subject_ids'])

            profile.refresh_from_db()
            request.user.refresh_from_db()

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_serializer = TeacherProfileDetailSerializer(profile)

            return Response({
                'message': 'Profile updated successfully',
                'user': user_data,
                'profile': profile_serializer.data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _update_teacher_subjects(self, teacher: User, subject_ids: list) -> None:
        """Обновить список предметов преподавателя"""
        from materials.models import TeacherSubject, Subject

        if not isinstance(subject_ids, list):
            raise ValueError('subject_ids must be a list')

        existing_subjects = set(
            TeacherSubject.objects.filter(teacher=teacher, is_active=True)
            .values_list('subject_id', flat=True)
        )
        new_subjects = set(subject_ids)

        to_add = new_subjects - existing_subjects
        to_remove = existing_subjects - new_subjects

        if to_add:
            subjects = Subject.objects.filter(id__in=to_add)
            for subject in subjects:
                TeacherSubject.objects.create(
                    teacher=teacher,
                    subject=subject,
                    is_active=True
                )

        if to_remove:
            TeacherSubject.objects.filter(
                teacher=teacher,
                subject_id__in=to_remove
            ).update(is_active=False)


class TutorProfileView(APIView):
    """
    API endpoint для управления профилем тьютора.

    GET /api/profile/tutor/
    - Возвращает объединенные данные User + TutorProfile

    PATCH /api/profile/tutor/
    - Обновляет данные User и/или TutorProfile
    - Поддерживает загрузку аватара
    - Поля User: first_name, last_name, email, phone, avatar
    - Поля Profile: specialization, experience_years, bio, telegram
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Получить данные профиля тьютора"""
        if request.user.role != 'tutor':
            return Response(
                {'error': 'Only tutors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = TutorProfile.objects.select_related('user').get(user=request.user)
        except TutorProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[TutorProfileView] TutorProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = TutorProfile.objects.create(user=request.user)
            logger.info(
                f"[TutorProfileView] TutorProfile auto-created for user_id={request.user.id}"
            )

        user_data = {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': request.user.phone,
            'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
        }

        profile_serializer = TutorProfileDetailSerializer(profile)

        return Response({
            'user': user_data,
            'profile': profile_serializer.data
        })

    @transaction.atomic
    def patch(self, request) -> Response:
        """Обновить данные профиля тьютора"""
        if request.user.role != 'tutor':
            return Response(
                {'error': 'Only tutors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = TutorProfile.objects.select_related('user').get(user=request.user)
        except TutorProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[TutorProfileView] TutorProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = TutorProfile.objects.create(user=request.user)
            logger.info(
                f"[TutorProfileView] TutorProfile auto-created for user_id={request.user.id}"
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone']
        profile_fields = ['specialization', 'experience_years', 'bio', 'telegram']

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}

        try:
            if user_data:
                user_serializer = UserProfileUpdateSerializer(
                    request.user,
                    data=user_data,
                    partial=True
                )
                if user_serializer.is_valid(raise_exception=True):
                    user_serializer.save()

            if 'avatar' in request.FILES:
                ProfileService.validate_avatar(request.FILES['avatar'])
                avatar_path = ProfileService.handle_avatar_upload(
                    profile=request.user,
                    file=request.FILES['avatar']
                )
                request.user.avatar = avatar_path
                request.user.save(update_fields=['avatar'])

            if profile_data:
                profile_serializer = TutorProfileDetailSerializer(
                    profile,
                    data=profile_data,
                    partial=True
                )
                if profile_serializer.is_valid(raise_exception=True):
                    profile_serializer.save()

            profile.refresh_from_db()
            request.user.refresh_from_db()

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_serializer = TutorProfileDetailSerializer(profile)

            return Response({
                'message': 'Profile updated successfully',
                'user': user_data,
                'profile': profile_serializer.data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ParentProfileView(APIView):
    """
    API endpoint для управления профилем родителя.

    GET /api/profile/parent/
    - Возвращает объединенные данные User + ParentProfile

    PATCH /api/profile/parent/
    - Обновляет данные User и/или ParentProfile
    - Поддерживает загрузку аватара
    - Поля User: first_name, last_name, email, phone, avatar
    - Поля Profile: (parent profile has no specific fields currently)
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Получить данные профиля родителя"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = ParentProfile.objects.select_related('user').get(user=request.user)
        except ParentProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[ParentProfileView] ParentProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = ParentProfile.objects.create(user=request.user)
            logger.info(
                f"[ParentProfileView] ParentProfile auto-created for user_id={request.user.id}"
            )

        user_data = {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': request.user.phone,
            'avatar': request.user.avatar.url if request.user.avatar else None,
            'role': request.user.role,
        }

        profile_serializer = ParentProfileDetailSerializer(profile)

        return Response({
            'user': user_data,
            'profile': profile_serializer.data
        })

    @transaction.atomic
    def patch(self, request) -> Response:
        """Обновить данные профиля родителя"""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parents can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = ParentProfile.objects.select_related('user').get(user=request.user)
        except ParentProfile.DoesNotExist:
            # Auto-create profile if missing (fallback for signal issues)
            logger.warning(
                f"[ParentProfileView] ParentProfile not found for user_id={request.user.id} "
                f"email={request.user.email}, auto-creating..."
            )
            profile = ParentProfile.objects.create(user=request.user)
            logger.info(
                f"[ParentProfileView] ParentProfile auto-created for user_id={request.user.id}"
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone']
        profile_fields = ['telegram']  # ParentProfile has telegram field

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}

        try:
            if user_data:
                user_serializer = UserProfileUpdateSerializer(
                    request.user,
                    data=user_data,
                    partial=True
                )
                if user_serializer.is_valid(raise_exception=True):
                    user_serializer.save()

            if 'avatar' in request.FILES:
                ProfileService.validate_avatar(request.FILES['avatar'])
                avatar_path = ProfileService.handle_avatar_upload(
                    profile=request.user,
                    file=request.FILES['avatar']
                )
                request.user.avatar = avatar_path
                request.user.save(update_fields=['avatar'])

            if profile_data:
                profile_serializer = ParentProfileDetailSerializer(
                    profile,
                    data=profile_data,
                    partial=True
                )
                if profile_serializer.is_valid(raise_exception=True):
                    profile_serializer.save()

            profile.refresh_from_db()
            request.user.refresh_from_db()

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_serializer = ParentProfileDetailSerializer(profile)

            return Response({
                'message': 'Profile updated successfully',
                'user': user_data,
                'profile': profile_serializer.data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileReactivationView(APIView):
    """
    API endpoint для повторной активации деактивированных профилей.

    POST /api/profile/reactivate/
    - Устанавливает is_active=True для текущего пользователя
    - Работает для всех ролей (student, teacher, tutor, parent)
    - Возвращает обновленные данные профиля
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        """Reactivate current user's profile"""
        user = request.user

        if user.is_active:
            return Response(
                {'message': 'Profile is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.save(update_fields=['is_active'])

        profile_data: Dict[str, Any] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'avatar': user.avatar.url if user.avatar else None,
            'role': user.role,
            'is_active': user.is_active,
        }

        return Response({
            'message': 'Profile reactivated successfully',
            'user': profile_data
        }, status=status.HTTP_200_OK)


class AdminTeacherProfileEditView(APIView):
    """
    API endpoint для редактирования профиля преподавателя администратором.

    PATCH /api/admin/teachers/{id}/
    - Обновляет данные User и TeacherProfile
    - Поддерживает управление предметами (subject_ids)
    - Поддерживает обновление статуса активности (is_active)
    - Требует admin permissions (IsStaffOrAdmin)
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, teacher_id: int) -> Response:
        """Update teacher profile (admin only)"""
        from .permissions import IsStaffOrAdmin

        permission = IsStaffOrAdmin()
        if not permission.has_permission(request, self):
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            teacher_user = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone', 'is_active']
        profile_fields = ['subject', 'experience_years', 'bio', 'telegram']

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}
        subject_ids = request.data.get('subject_ids')

        try:
            with transaction.atomic():
                if user_data:
                    for key, value in user_data.items():
                        setattr(teacher_user, key, value)
                    teacher_user.save(update_fields=list(user_data.keys()))

                try:
                    profile = TeacherProfile.objects.select_related('user').get(user=teacher_user)
                except TeacherProfile.DoesNotExist:
                    profile = TeacherProfile.objects.create(user=teacher_user)

                if profile_data:
                    for key, value in profile_data.items():
                        setattr(profile, key, value)
                    profile.save(update_fields=list(profile_data.keys()))

                if subject_ids is not None:
                    self._update_teacher_subjects(teacher_user, subject_ids)

            profile.refresh_from_db()
            teacher_user.refresh_from_db()

            user_response = {
                'id': teacher_user.id,
                'email': teacher_user.email,
                'first_name': teacher_user.first_name,
                'last_name': teacher_user.last_name,
                'phone': teacher_user.phone,
                'is_active': teacher_user.is_active,
                'role': teacher_user.role,
            }

            profile_serializer = TeacherProfileDetailSerializer(profile)

            return Response({
                'success': True,
                'message': 'Teacher profile updated successfully',
                'user': user_response,
                'profile': profile_serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _update_teacher_subjects(self, teacher: User, subject_ids: list) -> None:
        """Update teacher's subject assignments"""
        from materials.models import TeacherSubject, Subject

        if not isinstance(subject_ids, list):
            raise ValueError('subject_ids must be a list')

        existing_subjects = set(
            TeacherSubject.objects.filter(teacher=teacher, is_active=True)
            .values_list('subject_id', flat=True)
        )
        new_subjects = set(subject_ids)

        to_add = new_subjects - existing_subjects
        to_remove = existing_subjects - new_subjects

        if to_add:
            subjects = Subject.objects.filter(id__in=to_add)
            for subject in subjects:
                TeacherSubject.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    defaults={'is_active': True}
                )

        if to_remove:
            TeacherSubject.objects.filter(
                teacher=teacher,
                subject_id__in=to_remove
            ).update(is_active=False)


class AdminTutorProfileEditView(APIView):
    """
    API endpoint для редактирования профиля тьютора администратором.

    PATCH /api/admin/tutors/{id}/
    - Обновляет данные User и TutorProfile
    - Поддерживает обновление статуса активности (is_active)
    - Требует admin permissions (IsStaffOrAdmin)
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, tutor_id: int) -> Response:
        """Update tutor profile (admin only)"""
        from .permissions import IsStaffOrAdmin

        permission = IsStaffOrAdmin()
        if not permission.has_permission(request, self):
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            tutor_user = User.objects.get(id=tutor_id, role='tutor')
        except User.DoesNotExist:
            return Response(
                {'error': 'Tutor not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_fields = ['first_name', 'last_name', 'email', 'phone', 'is_active']
        profile_fields = ['specialization', 'experience_years', 'bio', 'telegram']

        user_data = {k: v for k, v in request.data.items() if k in user_fields}
        profile_data = {k: v for k, v in request.data.items() if k in profile_fields}

        try:
            with transaction.atomic():
                if user_data:
                    for key, value in user_data.items():
                        setattr(tutor_user, key, value)
                    tutor_user.save(update_fields=list(user_data.keys()))

                try:
                    profile = TutorProfile.objects.select_related('user').get(user=tutor_user)
                except TutorProfile.DoesNotExist:
                    profile = TutorProfile.objects.create(user=tutor_user)

                if profile_data:
                    for key, value in profile_data.items():
                        setattr(profile, key, value)
                    profile.save(update_fields=list(profile_data.keys()))

            profile.refresh_from_db()
            tutor_user.refresh_from_db()

            user_response = {
                'id': tutor_user.id,
                'email': tutor_user.email,
                'first_name': tutor_user.first_name,
                'last_name': tutor_user.last_name,
                'phone': tutor_user.phone,
                'is_active': tutor_user.is_active,
                'role': tutor_user.role,
            }

            profile_serializer = TutorProfileDetailSerializer(profile)

            return Response({
                'success': True,
                'message': 'Tutor profile updated successfully',
                'user': user_response,
                'profile': profile_serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CurrentUserProfileView(APIView):
    """
    Universal endpoint that returns current user's profile based on their role.
    GET /api/profile/me/
    - Returns user data + role-specific profile data
    - Works for students, teachers, and tutors
    - Uses user.role to determine which profile to fetch
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Get profile data for current user based on their role"""
        user_role = request.user.role

        if user_role == 'student':
            # Delegate to StudentProfileView logic
            try:
                profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(user=request.user)
            except StudentProfile.DoesNotExist:
                return Response(
                    {'error': 'Student profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_data = {
                'id': profile.id,
                'grade': profile.grade,
                'goal': profile.goal,
                'tutor': {'id': profile.tutor.id, 'name': str(profile.tutor)} if profile.tutor else None,
                'parent': {'id': profile.parent.id, 'name': str(profile.parent)} if profile.parent else None,
                'progress_percentage': profile.progress_percentage,
                'streak_days': profile.streak_days,
                'total_points': profile.total_points,
                'accuracy_percentage': profile.accuracy_percentage,
                'telegram': profile.telegram,
            }

            return Response({
                'user': user_data,
                'profile': profile_data
            })

        elif user_role == 'teacher':
            # Delegate to TeacherProfileView logic
            try:
                profile = TeacherProfile.objects.select_related('user').get(user=request.user)
            except TeacherProfile.DoesNotExist:
                return Response(
                    {'error': 'Teacher profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_data = {
                'id': profile.id,
                'bio': profile.bio,
                'experience_years': profile.experience_years,
                'subject': profile.subject,
                'telegram': profile.telegram,
            }

            return Response({
                'user': user_data,
                'profile': profile_data
            })

        elif user_role == 'tutor':
            # Delegate to TutorProfileView logic
            try:
                profile = TutorProfile.objects.select_related('user').get(user=request.user)
            except TutorProfile.DoesNotExist:
                return Response(
                    {'error': 'Tutor profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            user_data = {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'avatar': request.user.avatar.url if request.user.avatar else None,
                'role': request.user.role,
            }

            profile_data = {
                'id': profile.id,
                'bio': profile.bio,
                'experience_years': profile.experience_years,
                'specialization': profile.specialization,
                'telegram': profile.telegram,
            }

            return Response({
                'user': user_data,
                'profile': profile_data
            })

        else:
            return Response(
                {'error': f'Unknown or unsupported user role: {user_role}'},
                status=status.HTTP_400_BAD_REQUEST
            )
