"""
Views for handling submission file uploads and management.

Endpoints:
- POST /api/materials/{id}/submit-files/ - Upload files for a material submission
- GET /api/submission-files/{submission_id}/ - Get files for a submission
- DELETE /api/submission-files/{file_id}/ - Delete a submission file
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from materials.models import Material, MaterialSubmission, SubmissionFile
from materials.submission_file_serializers import (
    SubmissionFileSerializer,
    BulkMaterialSubmissionSerializer
)


class SubmissionFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления файлами ответов на материалы.

    Поддерживает:
    - Загрузку до 10 файлов за раз
    - Валидацию размера и типа файлов
    - Проверку дубликатов по контрольной сумме
    - Просмотр файлов ответов
    - Удаление файлов
    """
    queryset = SubmissionFile.objects.all().select_related('submission', 'submission__material', 'submission__student')
    serializer_class = SubmissionFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Фильтрация файлов в зависимости от роли пользователя"""
        user = self.request.user
        base_queryset = SubmissionFile.objects.all().select_related(
            'submission', 'submission__material', 'submission__student'
        )

        if user.role == 'student':
            # Студенты видят только файлы своих ответов
            return base_queryset.filter(submission__student=user)
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели видят файлы всех ответов
            return base_queryset
        elif user.role == 'parent':
            # Родители видят файлы ответов своих детей
            children = user.parent_profile.children.all()
            return base_queryset.filter(submission__student__in=children)

        return SubmissionFile.objects.none()

    def perform_destroy(self, instance):
        """
        Удалить файл ответа.

        Может удалить только:
        - Студент свои файлы
        - Преподаватель любые файлы
        """
        user = self.request.user
        submission = instance.submission

        if user.role == 'student' and submission.student != user:
            raise PermissionError("Вы можете удалять только свои файлы")

        instance.delete()


class MaterialSubmitFilesViewSet(viewsets.ViewSet):
    """
    ViewSet для загрузки файлов к ответам на материалы.

    Endpoint: POST /api/materials/{material_id}/submit-files/
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='submit-files',
        url_name='submit-files'
    )
    def submit_files(self, request, pk=None):
        """
        Загрузить файлы для ответа на материал.

        Request body:
        {
            "material_id": 1,
            "files": [file1, file2, ...],
            "submission_text": "Мой ответ..."  (optional)
        }

        Returns:
        {
            "id": 1,
            "material": 1,
            "student": 1,
            "files": [
                {
                    "id": 1,
                    "original_filename": "solution.pdf",
                    "file_size": 1024000,
                    "file_type": "pdf",
                    "uploaded_at": "2025-12-27T12:00:00Z"
                },
                ...
            ],
            "submitted_at": "2025-12-27T12:00:00Z"
        }

        Errors:
        - 400: Validation error (file size, type, count)
        - 403: Not a student user
        - 404: Material not found
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Доступно только для студентов'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate using BulkMaterialSubmissionSerializer
        serializer = BulkMaterialSubmissionSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            submission = serializer.save()

            # Return submission with files
            from materials.serializers import MaterialSubmissionSerializer
            result_serializer = MaterialSubmissionSerializer(
                submission,
                context={'request': request}
            )

            return Response(
                result_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['get'],
        url_path='submission-files/(?P<submission_id>[^/.]+)',
        url_name='submission-files'
    )
    def get_submission_files(self, request, submission_id=None):
        """
        Получить файлы для ответа на материал.

        URL: GET /api/materials/submission-files/{submission_id}/
        """
        submission = get_object_or_404(MaterialSubmission, id=submission_id)

        # Check permissions
        user = request.user
        if user.role == 'student' and submission.student != user:
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.role == 'parent':
            children = user.parent_profile.children.all()
            if submission.student not in children:
                return Response(
                    {'error': 'Доступ запрещен'},
                    status=status.HTTP_403_FORBIDDEN
                )

        files = submission.files.all()
        serializer = SubmissionFileSerializer(
            files,
            many=True,
            context={'request': request}
        )

        return Response({
            'submission_id': submission.id,
            'material': submission.material.id,
            'student': submission.student.id,
            'file_count': len(files),
            'total_size': sum(f.file_size for f in files),
            'files': serializer.data
        })

    @action(
        detail=False,
        methods=['delete'],
        url_path='submission-files/(?P<file_id>[^/.]+)',
        url_name='delete-submission-file'
    )
    def delete_submission_file(self, request, file_id=None):
        """
        Удалить файл из ответа на материал.

        URL: DELETE /api/materials/submission-files/{file_id}/
        """
        submission_file = get_object_or_404(SubmissionFile, id=file_id)

        # Check permissions
        user = request.user
        if user.role == 'student' and submission_file.submission.student != user:
            return Response(
                {'error': 'Вы можете удалять только свои файлы'},
                status=status.HTTP_403_FORBIDDEN
            )

        filename = submission_file.original_filename
        submission_file.delete()

        return Response({
            'message': f'Файл {filename} удален',
            'file_id': file_id
        })
