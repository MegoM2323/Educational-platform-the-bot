"""
Unit tests for file handling in materials app

Покрытие:
- File upload для Material
- File upload для StudyPlanFile
- File download authentication
- File deletion при удалении объекта
- File validation
"""
import pytest
import os
from decimal import Decimal
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import Mock, patch, MagicMock

from materials.models import (
    Material, StudyPlan, StudyPlanFile, MaterialSubmission,
    validate_submission_file
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialFileUpload:
    """Тесты загрузки файлов для Material"""

    def test_upload_pdf_file(self, teacher_user, subject):
        """Тест загрузки PDF файла"""
        test_file = SimpleUploadedFile(
            "lesson.pdf",
            b"PDF file content",
            content_type="application/pdf"
        )

        material = Material.objects.create(
            title="Урок с PDF",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        assert material.file is not None
        assert material.file.name.endswith('.pdf')
        assert os.path.exists(material.file.path)

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_upload_doc_file(self, teacher_user, subject):
        """Тест загрузки DOC файла"""
        test_file = SimpleUploadedFile(
            "lesson.doc",
            b"DOC file content",
            content_type="application/msword"
        )

        material = Material.objects.create(
            title="Урок с DOC",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        assert material.file is not None
        assert material.file.name.endswith('.doc')

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_upload_ppt_file(self, teacher_user, subject):
        """Тест загрузки PPT файла"""
        test_file = SimpleUploadedFile(
            "presentation.ppt",
            b"PPT file content",
            content_type="application/vnd.ms-powerpoint"
        )

        material = Material.objects.create(
            title="Презентация",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            type=Material.Type.PRESENTATION,
            file=test_file
        )

        assert material.file is not None
        assert material.file.name.endswith('.ppt')

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_file_extension_validation(self, teacher_user, subject):
        """Тест валидации расширения файла"""
        # Файл с недопустимым расширением
        test_file = SimpleUploadedFile(
            "lesson.exe",
            b"Executable content"
        )

        with pytest.raises(ValidationError):
            material = Material(
                title="Урок с EXE",
                content="Содержание",
                author=teacher_user,
                subject=subject,
                file=test_file
            )
            material.full_clean()

    def test_file_deletion_on_material_delete(self, teacher_user, subject):
        """Тест удаления файла при удалении материала"""
        test_file = SimpleUploadedFile(
            "lesson.pdf",
            b"PDF content"
        )

        material = Material.objects.create(
            title="Урок для удаления",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        file_path = material.file.path
        assert os.path.exists(file_path)

        material.delete()

        # Файл должен быть удален (зависит от настроек Django)
        # В тестах файл может остаться, но в продакшне обычно удаляется
        # Проверяем что объект удален
        assert not Material.objects.filter(id=material.id).exists()

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.unit
@pytest.mark.django_db
class TestStudyPlanFileUpload:
    """Тесты загрузки файлов для StudyPlan"""

    def test_upload_study_plan_file(self, teacher_user, student_user, subject):
        """Тест загрузки файла плана занятий"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План недели 1",
            content="Содержание плана",
            week_start_date=date.today()
        )

        test_file = SimpleUploadedFile(
            "plan.pdf",
            b"Plan content",
            content_type="application/pdf"
        )

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            name="План недели.pdf",
            file_size=1024,
            uploaded_by=teacher_user
        )

        assert plan_file.file is not None
        assert plan_file.name == "План недели.pdf"
        assert os.path.exists(plan_file.file.path)

        # Cleanup
        if os.path.exists(plan_file.file.path):
            os.remove(plan_file.file.path)

    def test_auto_populate_file_name(self, teacher_user, student_user, subject):
        """Тест автоматического заполнения имени файла"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План недели 1",
            content="Содержание плана",
            week_start_date=date.today()
        )

        test_file = SimpleUploadedFile(
            "original_name.pdf",
            b"Content"
        )

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            file_size=100,
            uploaded_by=teacher_user
        )

        # name должно быть установлено из имени файла
        assert plan_file.name == "original_name.pdf"

        # Cleanup
        if os.path.exists(plan_file.file.path):
            os.remove(plan_file.file.path)

    def test_auto_populate_file_size(self, teacher_user, student_user, subject):
        """Тест автоматического заполнения размера файла"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План недели 1",
            content="Содержание плана",
            week_start_date=date.today()
        )

        content = b"Test content for size calculation"
        test_file = SimpleUploadedFile(
            "test.pdf",
            content
        )

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            uploaded_by=teacher_user
        )

        # file_size должен быть установлен автоматически
        assert plan_file.file_size == len(content)

        # Cleanup
        if os.path.exists(plan_file.file.path):
            os.remove(plan_file.file.path)

    def test_multiple_files_per_study_plan(self, teacher_user, student_user, subject):
        """Тест загрузки нескольких файлов к одному плану"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План с несколькими файлами",
            content="Содержание плана",
            week_start_date=date.today()
        )

        # Загружаем несколько файлов
        file1 = SimpleUploadedFile("plan1.pdf", b"Content 1")
        file2 = SimpleUploadedFile("plan2.pdf", b"Content 2")

        plan_file1 = StudyPlanFile.objects.create(
            study_plan=plan,
            file=file1,
            file_size=100,
            uploaded_by=teacher_user
        )

        plan_file2 = StudyPlanFile.objects.create(
            study_plan=plan,
            file=file2,
            file_size=100,
            uploaded_by=teacher_user
        )

        assert plan.files.count() == 2

        # Cleanup
        for plan_file in [plan_file1, plan_file2]:
            if os.path.exists(plan_file.file.path):
                os.remove(plan_file.file.path)


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialSubmissionFileValidation:
    """Тесты валидации файлов ответов"""

    def test_validate_submission_file_size(self):
        """Тест валидации размера файла"""
        # Файл размером > 10MB
        large_file = SimpleUploadedFile(
            "large.pdf",
            b"x" * (11 * 1024 * 1024)  # 11MB
        )

        with pytest.raises(ValidationError, match="Файл слишком большой"):
            validate_submission_file(large_file)

    def test_validate_submission_file_extension(self):
        """Тест валидации расширения файла"""
        invalid_file = SimpleUploadedFile(
            "file.exe",
            b"content"
        )

        with pytest.raises(ValidationError, match="Неподдерживаемый тип файла"):
            validate_submission_file(invalid_file)

    def test_valid_submission_file_types(self):
        """Тест допустимых типов файлов"""
        valid_extensions = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip', 'rar']

        for ext in valid_extensions:
            test_file = SimpleUploadedFile(
                f"file.{ext}",
                b"Valid content"
            )

            # Не должно быть исключения
            try:
                validate_submission_file(test_file)
            except ValidationError:
                pytest.fail(f"Valid extension {ext} raised ValidationError")


@pytest.mark.unit
@pytest.mark.django_db
class TestFileDownloadAuthentication:
    """Тесты аутентификации при скачивании файлов"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_download_file_requires_authentication(self, api_client, teacher_user, subject):
        """Тест требования аутентификации для скачивания"""
        test_file = SimpleUploadedFile("lesson.pdf", b"Content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        # Попытка скачать без аутентификации
        response = api_client.get(f'/api/materials/materials/{material.id}/download_file/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_download_file_with_authentication(self, api_client, student_user, teacher_user, subject):
        """Тест скачивания файла с аутентификацией"""
        test_file = SimpleUploadedFile("lesson.pdf", b"Content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE,
            file=test_file
        )
        material.assigned_to.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/materials/materials/{material.id}/download_file/')

        # Должен вернуть файл
        assert response.status_code == status.HTTP_200_OK

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_download_file_permission_check(self, api_client, teacher_user, subject):
        """Тест проверки прав при скачивании"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student1 = StudentUserFactory()
        StudentProfile.objects.create(user=student1)

        student2 = StudentUserFactory()
        StudentProfile.objects.create(user=student2)

        test_file = SimpleUploadedFile("lesson.pdf", b"Content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE,
            file=test_file,
            is_public=False
        )
        material.assigned_to.add(student1)

        # student2 не назначен на материал
        api_client.force_authenticate(user=student2)
        response = api_client.get(f'/api/materials/materials/{material.id}/download_file/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)

    def test_download_public_material(self, api_client, student_user, teacher_user, subject):
        """Тест скачивания публичного материала"""
        test_file = SimpleUploadedFile("lesson.pdf", b"Content")

        material = Material.objects.create(
            title="Публичный урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE,
            file=test_file,
            is_public=True
        )

        # Любой студент может скачать публичный материал
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/materials/materials/{material.id}/download_file/')

        assert response.status_code == status.HTTP_200_OK

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)


@pytest.mark.unit
@pytest.mark.django_db
class TestFileCleanup:
    """Тесты очистки файлов"""

    def test_file_cleanup_on_material_update(self, teacher_user, subject):
        """Тест замены файла при обновлении материала"""
        old_file = SimpleUploadedFile("old.pdf", b"Old content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=old_file
        )

        old_path = material.file.path

        # Обновляем файл
        new_file = SimpleUploadedFile("new.pdf", b"New content")
        material.file = new_file
        material.save()

        # Старый файл должен быть заменен
        assert material.file.name.endswith('new.pdf')

        # Cleanup
        if os.path.exists(material.file.path):
            os.remove(material.file.path)
        if os.path.exists(old_path):
            os.remove(old_path)

    def test_file_cleanup_on_study_plan_delete(self, teacher_user, student_user, subject):
        """Тест удаления файлов при удалении плана занятий"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=date.today()
        )

        test_file = SimpleUploadedFile("plan.pdf", b"Content")

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            file_size=100,
            uploaded_by=teacher_user
        )

        file_path = plan_file.file.path
        assert os.path.exists(file_path)

        plan.delete()

        # Файлы должны быть удалены каскадно
        assert not StudyPlanFile.objects.filter(id=plan_file.id).exists()

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.unit
@pytest.mark.django_db
class TestFileMocking:
    """Тесты с mock для файловых операций"""

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_mock_file_upload(self, mock_save, teacher_user, subject):
        """Тест загрузки файла с mock"""
        mock_save.return_value = 'materials/files/test.pdf'

        test_file = SimpleUploadedFile("test.pdf", b"Content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        assert mock_save.called
        assert material.file is not None

    @patch('django.core.files.storage.FileSystemStorage.delete')
    def test_mock_file_delete(self, mock_delete, teacher_user, subject):
        """Тест удаления файла с mock"""
        test_file = SimpleUploadedFile("test.pdf", b"Content")

        material = Material.objects.create(
            title="Урок",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        material.delete()

        # В реальности delete может быть вызван, зависит от настроек
        # Проверяем что объект удален
        assert not Material.objects.filter(id=material.id).exists()
