"""
API Views for ElementFile management
T004: File Upload API Endpoints
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from knowledge_graph.models import Element, ElementFile
from knowledge_graph.element_file_serializers import ElementFileSerializer


class ElementFileListCreateView(APIView):
    """
    GET: List all files for an element
    POST: Upload new file to element
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, element_id):
        """List all files for element"""
        element = get_object_or_404(Element, id=element_id)
        files = element.files.all()
        serializer = ElementFileSerializer(
            files, many=True, context={"request": request}
        )
        return Response(
            {"success": True, "data": serializer.data, "count": files.count()}
        )

    def post(self, request, element_id):
        """Upload new file to element"""
        element = get_object_or_404(Element, id=element_id)

        # Проверка прав доступа - только создатель элемента или admin
        if element.created_by != request.user and not request.user.is_staff:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"success": False, "error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Валидация размера файла (10MB)
        if file.size > 10 * 1024 * 1024:
            return Response(
                {"success": False, "error": "File too large (max 10MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            element_file = ElementFile.objects.create(
                element=element,
                file=file,
                original_filename=file.name,
                file_size=file.size,
                uploaded_by=request.user,
            )
            # Запуск валидации модели (включая расширения файлов)
            element_file.full_clean()
        except ValidationError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ElementFileSerializer(element_file, context={"request": request})
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED
        )


class ElementFileDeleteView(APIView):
    """
    DELETE: Remove file from element
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, element_id, file_id):
        """Delete file from element"""
        element = get_object_or_404(Element, id=element_id)
        element_file = get_object_or_404(ElementFile, id=file_id, element=element)

        # Проверка прав доступа
        if element.created_by != request.user and not request.user.is_staff:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Удаление физического файла из хранилища
        if element_file.file:
            element_file.file.delete()

        # Удаление записи из БД
        element_file.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
