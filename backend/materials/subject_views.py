"""
API views для работы с предметами
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework import status

from .models import Subject
from .serializers import SubjectSerializer


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_all_subjects(request):
    """
    Получение списка всех предметов.

    Endpoint используется для выбора предметов в UI (мультиселект).
    Доступен всем аутентифицированным пользователям.

    Query params:
        - ordering: поле для сортировки (default: 'name')
        - search: поиск по названию предмета

    Returns:
        [
            {
                "id": 1,
                "name": "Математика",
                "description": "...",
                "color": "#3B82F6",
                "materials_count": 10
            },
            ...
        ]
    """
    # Получаем все предметы
    queryset = Subject.objects.all()

    # Поиск по названию
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(name__icontains=search)

    # Сортировка
    ordering = request.query_params.get('ordering', 'name')
    allowed_ordering = ['name', '-name', 'id', '-id']
    if ordering in allowed_ordering:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('name')

    # Сериализация
    serializer = SubjectSerializer(queryset, many=True)

    return Response({
        'success': True,
        'count': queryset.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)
