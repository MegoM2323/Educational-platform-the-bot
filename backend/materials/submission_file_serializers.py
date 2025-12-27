"""
Serializers for SubmissionFile model and file submission operations.

Handles:
- Individual file serialization
- Bulk file submission with validation
- File size and type validation
- Checksum calculation and duplicate detection
"""

from rest_framework import serializers
from core.file_utils import build_secure_file_url


class SubmissionFileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для файлов ответов на материалы.

    Валидирует:
    - Размер файла (максимум 50MB)
    - Тип файла (pdf, doc, docx, txt, jpg, png, zip и т.д.)
    - MIME тип
    - SHA256 контрольную сумму (дубликаты)
    """
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = None  # Will be set to SubmissionFile in __init__
        fields = (
            'id', 'submission', 'file', 'file_url', 'original_filename',
            'file_size', 'file_size_mb', 'file_type', 'mime_type',
            'file_checksum', 'uploaded_at'
        )
        read_only_fields = ('id', 'file_checksum', 'uploaded_at', 'file_size')

    def __init__(self, *args, **kwargs):
        """Dynamically set model to avoid import issues"""
        super().__init__(*args, **kwargs)
        if self.Meta.model is None:
            from materials.models import SubmissionFile
            self.Meta.model = SubmissionFile

    def get_file_url(self, obj):
        """Возвращает URL файла с правильной схемой (HTTP/HTTPS)"""
        request = self.context.get('request')
        return build_secure_file_url(obj.file, request) if obj.file else None

    def get_file_size_mb(self, obj):
        """Возвращает размер файла в МБ"""
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0


class BulkMaterialSubmissionSerializer(serializers.Serializer):
    """
    Сериализатор для массовой загрузки файлов к ответу на материал.

    Поддерживает:
    - Загрузку до 10 файлов за раз
    - Валидацию каждого файла
    - Подсчет контрольных сумм
    - Проверку дубликатов
    """
    material_id = serializers.IntegerField()
    files = serializers.ListField(child=serializers.FileField(), max_length=10)
    submission_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10000
    )

    def validate_files(self, value):
        """Валидация списка файлов"""
        if not value:
            raise serializers.ValidationError("Необходимо загрузить хотя бы один файл")

        if len(value) > 10:
            raise serializers.ValidationError("Максимум 10 файлов на ответ")

        return value

    def validate_material_id(self, value):
        """Проверить что материал существует"""
        from materials.models import Material
        try:
            Material.objects.get(id=value)
        except Material.DoesNotExist:
            raise serializers.ValidationError("Материал не найден")
        return value

    def create(self, validated_data):
        """
        Создать ответ на материал с файлами.

        1. Валидировать все файлы
        2. Создать SubmissionFile для каждого файла
        3. Вернуть созданный ответ
        """
        from materials.models import Material, MaterialSubmission, SubmissionFile
        from materials.utils import SubmissionFileValidator, FileAuditLogger

        request = self.context['request']
        user = request.user

        material_id = validated_data['material_id']
        files = validated_data['files']
        submission_text = validated_data.get('submission_text', '')

        material = Material.objects.get(id=material_id)

        # Валидировать все файлы
        try:
            validation_result = SubmissionFileValidator.validate_submission_files(
                files,
                student_id=user.id
            )
        except serializers.ValidationError as e:
            raise serializers.ValidationError({'files': str(e)})

        # Создать ответ
        submission, created = MaterialSubmission.objects.get_or_create(
            material=material,
            student=user,
            defaults={
                'submission_text': submission_text,
                'status': MaterialSubmission.Status.SUBMITTED
            }
        )

        if not created:
            # Обновить текст если ответ уже существует
            submission.submission_text = submission_text
            submission.save()

        # Создать SubmissionFile для каждого файла
        submission.files.all().delete()  # Удалить старые файлы

        for idx, file_data in enumerate(validation_result['files']):
            file_obj = files[idx]

            SubmissionFile.objects.create(
                submission=submission,
                file=file_obj,
                original_filename=file_data['filename'],
                file_size=file_data['size'],
                file_type=file_data['extension'],
                mime_type=file_obj.content_type or '',
                file_checksum=file_data['checksum']
            )

            # Логировать загрузку
            FileAuditLogger.log_upload(
                user_id=user.id,
                user_email=user.email,
                filename=file_data['filename'],
                file_size=file_data['size'],
                file_type='submission',
                file_hash=file_data['checksum'],
                storage_path=f'submissions/{submission.id}/{file_data["filename"]}',
                validation_result=True
            )

        return submission
