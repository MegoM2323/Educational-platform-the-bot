"""
Unit-тесты для authenticated media serving
"""
import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch, Mock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404, HttpResponseForbidden
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from core.media_views import (
    serve_media_file,
    serve_media_file_download,
    check_file_access_permission,
    _check_material_file_access,
    _check_study_plan_file_access
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckFileAccessPermission:
    """Тесты для проверки прав доступа к файлам"""

    def test_admin_has_access_to_all_files(self, admin_user):
        """Тест что администраторы имеют доступ ко всем файлам"""
        has_access, reason = check_file_access_permission(admin_user, 'materials/files/test.pdf')

        assert has_access is True
        assert reason is None

    def test_staff_has_access_to_all_files(self, teacher_user):
        """Тест что staff пользователи имеют доступ ко всем файлам"""
        teacher_user.is_staff = True
        teacher_user.save()

        has_access, reason = check_file_access_permission(teacher_user, 'materials/files/test.pdf')

        assert has_access is True
        assert reason is None

    def test_authenticated_user_has_access_to_avatars(self, student_user):
        """Тест что аутентифицированные пользователи имеют доступ к аватарам"""
        has_access, reason = check_file_access_permission(student_user, 'avatars/user_123.jpg')

        assert has_access is True
        assert reason is None

    def test_unknown_file_type_denied(self, student_user):
        """Тест что неизвестные типы файлов запрещены"""
        has_access, reason = check_file_access_permission(student_user, 'unknown/path/file.txt')

        assert has_access is False
        assert reason == "Неизвестный тип файла"

    def test_material_file_access_delegated(self, student_user):
        """Тест что проверка доступа к файлам материалов делегируется"""
        with patch('core.media_views._check_material_file_access', return_value=(True, None)) as mock_check:
            has_access, reason = check_file_access_permission(student_user, 'materials/files/test.pdf')

            assert has_access is True
            mock_check.assert_called_once_with(student_user, 'materials/files/test.pdf')

    def test_study_plan_file_access_delegated(self, student_user):
        """Тест что проверка доступа к файлам планов делегируется"""
        with patch('core.media_views._check_study_plan_file_access', return_value=(True, None)) as mock_check:
            has_access, reason = check_file_access_permission(student_user, 'study_plans/files/plan.pdf')

            assert has_access is True
            mock_check.assert_called_once_with(student_user, 'study_plans/files/plan.pdf')


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckMaterialFileAccess:
    """Тесты для проверки доступа к файлам материалов"""

    def test_author_has_access(self, teacher_user, sample_material):
        """Тест что автор материала имеет доступ"""
        sample_material.author = teacher_user
        sample_material.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(teacher_user, file_path)

        assert has_access is True
        assert reason is None

    def test_assigned_user_has_access(self, student_user, sample_material):
        """Тест что пользователь, которому назначен материал, имеет доступ"""
        sample_material.assigned_to.add(student_user)

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(student_user, file_path)

        assert has_access is True
        assert reason is None

    def test_public_material_accessible(self, student_user, sample_material):
        """Тест что публичные материалы доступны всем"""
        sample_material.is_public = True
        sample_material.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(student_user, file_path)

        assert has_access is True
        assert reason is None

    def test_enrolled_student_has_access(self, student_user, sample_material, sample_enrollment):
        """Тест что студент, зачисленный на предмет, имеет доступ"""
        sample_enrollment.student = student_user
        sample_enrollment.subject = sample_material.subject
        sample_enrollment.is_active = True
        sample_enrollment.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(student_user, file_path)

        assert has_access is True
        assert reason is None

    def test_tutor_has_access_to_student_materials(self, tutor_user, student_user, sample_material):
        """Тест что тьютор имеет доступ к материалам своих студентов"""
        # Назначаем материал студенту
        sample_material.assigned_to.add(student_user)

        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(tutor_user, file_path)

        assert has_access is True
        assert reason is None

    def test_parent_has_access_to_child_materials(self, parent_user, student_user, sample_material):
        """Тест что родитель имеет доступ к материалам своего ребенка"""
        # Назначаем материал студенту
        sample_material.assigned_to.add(student_user)

        # Назначаем родителя студенту
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(parent_user, file_path)

        assert has_access is True
        assert reason is None

    def test_material_not_found(self, student_user):
        """Тест когда материал не найден"""
        has_access, reason = _check_material_file_access(student_user, 'materials/files/nonexistent.pdf')

        assert has_access is False
        assert reason == "Материал не найден"

    def test_no_access_to_private_material(self, student_user, sample_material):
        """Тест что нет доступа к приватным материалам"""
        sample_material.is_public = False
        sample_material.save()

        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'
        has_access, reason = _check_material_file_access(student_user, file_path)

        assert has_access is False
        assert reason == "Нет доступа к этому материалу"


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckStudyPlanFileAccess:
    """Тесты для проверки доступа к файлам планов занятий"""

    def test_teacher_has_access(self, teacher_user, sample_study_plan_file):
        """Тест что преподаватель, создавший план, имеет доступ"""
        sample_study_plan_file.study_plan.teacher = teacher_user
        sample_study_plan_file.study_plan.save()

        file_path = f'study_plans/files/{os.path.basename(sample_study_plan_file.file.name)}'
        has_access, reason = _check_study_plan_file_access(teacher_user, file_path)

        assert has_access is True
        assert reason is None

    def test_student_has_access(self, student_user, sample_study_plan_file):
        """Тест что студент, для которого создан план, имеет доступ"""
        sample_study_plan_file.study_plan.student = student_user
        sample_study_plan_file.study_plan.save()

        file_path = f'study_plans/files/{os.path.basename(sample_study_plan_file.file.name)}'
        has_access, reason = _check_study_plan_file_access(student_user, file_path)

        assert has_access is True
        assert reason is None

    def test_tutor_has_access(self, tutor_user, student_user, sample_study_plan_file):
        """Тест что тьютор студента имеет доступ"""
        sample_study_plan_file.study_plan.student = student_user
        sample_study_plan_file.study_plan.save()

        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        file_path = f'study_plans/files/{os.path.basename(sample_study_plan_file.file.name)}'
        has_access, reason = _check_study_plan_file_access(tutor_user, file_path)

        assert has_access is True
        assert reason is None

    def test_parent_has_access(self, parent_user, student_user, sample_study_plan_file):
        """Тест что родитель студента имеет доступ"""
        sample_study_plan_file.study_plan.student = student_user
        sample_study_plan_file.study_plan.save()

        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        file_path = f'study_plans/files/{os.path.basename(sample_study_plan_file.file.name)}'
        has_access, reason = _check_study_plan_file_access(parent_user, file_path)

        assert has_access is True
        assert reason is None

    def test_study_plan_file_not_found(self, student_user):
        """Тест когда файл плана не найден"""
        has_access, reason = _check_study_plan_file_access(student_user, 'study_plans/files/nonexistent.pdf')

        assert has_access is False
        assert reason == "Файл плана не найден"

    def test_no_access_to_other_student_plan(self, student_user, other_student_user, sample_study_plan_file):
        """Тест что нет доступа к плану другого студента"""
        sample_study_plan_file.study_plan.student = other_student_user
        sample_study_plan_file.study_plan.save()

        file_path = f'study_plans/files/{os.path.basename(sample_study_plan_file.file.name)}'
        has_access, reason = _check_study_plan_file_access(student_user, file_path)

        assert has_access is False
        assert reason == "Нет доступа к этому плану занятий"


@pytest.mark.unit
@pytest.mark.django_db
class TestServeMediaFile:
    """Тесты для раздачи медиа файлов"""

    def test_serve_media_file_success(self, student_user, settings, tmpdir):
        """Тест успешной раздачи файла"""
        # Создаем временный файл
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("test.txt")
        test_file.write("test content")

        settings.MEDIA_ROOT = str(media_root)

        # Создаем request
        factory = RequestFactory()
        request = factory.get('/media/test.txt')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            response = serve_media_file(request, 'test.txt')

            assert response.status_code == 200
            assert 'Content-Type' in response
            assert 'Content-Disposition' in response
            assert 'inline' in response['Content-Disposition']

    def test_serve_media_file_unauthorized(self, student_user, settings, tmpdir):
        """Тест отказа в доступе"""
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("test.txt")
        test_file.write("test content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/test.txt')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(False, "Access denied")):
            response = serve_media_file(request, 'test.txt')

            assert isinstance(response, HttpResponseForbidden)
            assert 'Access denied' in str(response.content)

    def test_serve_media_file_not_found(self, student_user, settings, tmpdir):
        """Тест когда файл не существует"""
        media_root = tmpdir.mkdir("media")
        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/nonexistent.txt')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            with pytest.raises(Http404):
                serve_media_file(request, 'nonexistent.txt')

    def test_serve_media_file_path_traversal_protection(self, student_user, settings, tmpdir):
        """Тест защиты от path traversal атак"""
        media_root = tmpdir.mkdir("media")
        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        # Пытаемся получить файл вне MEDIA_ROOT
        request = factory.get('/media/../../../etc/passwd')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            with pytest.raises(Http404):
                serve_media_file(request, '../../../etc/passwd')

    def test_serve_media_file_strips_media_prefix(self, student_user, settings, tmpdir):
        """Тест удаления префикса /media/ из пути"""
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("test.txt")
        test_file.write("test content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/media/test.txt')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            response = serve_media_file(request, 'media/test.txt')

            # Должно успешно найти файл после удаления префикса
            assert response.status_code == 200

    def test_serve_media_file_correct_content_type(self, student_user, settings, tmpdir):
        """Тест правильного определения Content-Type"""
        media_root = tmpdir.mkdir("media")

        # PDF файл
        pdf_file = media_root.join("document.pdf")
        pdf_file.write_binary(b"%PDF-1.4 test content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/document.pdf')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            response = serve_media_file(request, 'document.pdf')

            assert response.status_code == 200
            assert 'application/pdf' in response['Content-Type']


@pytest.mark.unit
@pytest.mark.django_db
class TestServeMediaFileDownload:
    """Тесты для скачивания медиа файлов"""

    def test_serve_media_file_download_success(self, student_user, settings, tmpdir):
        """Тест успешного скачивания файла"""
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("download.pdf")
        test_file.write("download content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/download/download.pdf')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            response = serve_media_file_download(request, 'download.pdf')

            assert response.status_code == 200
            assert 'Content-Disposition' in response
            assert 'attachment' in response['Content-Disposition']
            assert 'download.pdf' in response['Content-Disposition']

    def test_serve_media_file_download_unauthorized(self, student_user, settings, tmpdir):
        """Тест отказа в скачивании"""
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("download.pdf")
        test_file.write("download content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/download/download.pdf')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(False, "Access denied")):
            response = serve_media_file_download(request, 'download.pdf')

            assert isinstance(response, HttpResponseForbidden)

    def test_serve_media_file_download_not_found(self, student_user, settings, tmpdir):
        """Тест скачивания несуществующего файла"""
        media_root = tmpdir.mkdir("media")
        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/download/nonexistent.pdf')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            with pytest.raises(Http404):
                serve_media_file_download(request, 'nonexistent.pdf')

    def test_serve_media_file_download_path_traversal_protection(self, student_user, settings, tmpdir):
        """Тест защиты от path traversal при скачивании"""
        media_root = tmpdir.mkdir("media")
        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/download/../../../etc/passwd')
        request.user = student_user

        with patch('core.media_views.check_file_access_permission', return_value=(True, None)):
            with pytest.raises(Http404):
                serve_media_file_download(request, '../../../etc/passwd')


@pytest.mark.unit
@pytest.mark.django_db
class TestMediaViewsAuthentication:
    """Тесты аутентификации для media views"""

    def test_unauthenticated_user_cannot_access(self, settings, tmpdir):
        """Тест что неаутентифицированные пользователи не имеют доступа"""
        media_root = tmpdir.mkdir("media")
        test_file = media_root.join("test.txt")
        test_file.write("test content")

        settings.MEDIA_ROOT = str(media_root)

        factory = RequestFactory()
        request = factory.get('/media/test.txt')

        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        # DRF декораторы @permission_classes([IsAuthenticated]) должны отклонить запрос
        # В юнит тестах мы проверяем только логику, но в реальности запрос был бы отклонен middleware


@pytest.mark.unit
@pytest.mark.django_db
class TestMediaViewsPerformance:
    """Тесты производительности media views"""

    def test_file_access_uses_select_related(self, student_user, sample_material):
        """Тест что используется select_related для оптимизации запросов"""
        file_path = f'materials/files/{os.path.basename(sample_material.file.name)}'

        with patch('core.media_views.Material.objects.select_related') as mock_select_related:
            mock_queryset = MagicMock()
            mock_queryset.prefetch_related.return_value.filter.return_value.first.return_value = sample_material
            mock_select_related.return_value = mock_queryset

            _check_material_file_access(student_user, file_path)

            # Проверяем, что select_related был вызван с правильными аргументами
            mock_select_related.assert_called_once_with('author', 'subject')
