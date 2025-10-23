from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Subject, Material, MaterialProgress, MaterialComment
from .serializers import (
    SubjectSerializer, MaterialListSerializer, MaterialDetailSerializer,
    MaterialCreateSerializer, MaterialProgressSerializer, MaterialCommentSerializer
)


class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet для предметов
    """
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialViewSet(viewsets.ModelViewSet):
    """
    ViewSet для материалов
    """
    queryset = Material.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'type', 'status', 'author', 'difficulty_level']
    search_fields = ['title', 'description', 'content', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'title', 'difficulty_level']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialListSerializer
        elif self.action == 'create':
            return MaterialCreateSerializer
        return MaterialDetailSerializer
    
    def get_queryset(self):
        """
        Фильтрация материалов в зависимости от роли пользователя
        """
        user = self.request.user
        
        if user.role == 'student':
            # Студенты видят только назначенные им материалы или публичные
            return Material.objects.filter(
                Q(assigned_to=user) | Q(is_public=True)
            ).distinct()
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели и тьюторы видят все материалы
            return Material.objects.all()
        elif user.role == 'parent':
            # Родители видят материалы своих детей
            children = user.parent_profile.children.all()
            return Material.objects.filter(assigned_to__in=children).distinct()
        
        return Material.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Назначить материал студентам
        """
        material = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return Response(
                {'error': 'Не указаны ID студентов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что все указанные пользователи - студенты
        from django.contrib.auth import get_user_model
        User = get_user_model()
        students = User.objects.filter(
            id__in=student_ids,
            role=User.Role.STUDENT
        )
        
        if len(students) != len(student_ids):
            return Response(
                {'error': 'Некоторые пользователи не являются студентами'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        material.assigned_to.set(students)
        return Response({'message': 'Материал назначен студентам'})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """
        Обновить прогресс изучения материала
        """
        material = self.get_object()
        student = request.user
        
        if student.role != 'student':
            return Response(
                {'error': 'Только студенты могут обновлять прогресс'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        progress_percentage = request.data.get('progress_percentage', 0)
        time_spent = request.data.get('time_spent', 0)
        
        progress, created = MaterialProgress.objects.get_or_create(
            student=student,
            material=material
        )
        
        progress.progress_percentage = progress_percentage
        progress.time_spent += time_spent
        
        if progress_percentage >= 100:
            progress.is_completed = True
            progress.completed_at = timezone.now()
        
        progress.save()
        
        return Response(MaterialProgressSerializer(progress).data)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Получить прогресс изучения материала
        """
        material = self.get_object()
        
        if request.user.role == 'student':
            try:
                progress = material.progress.get(student=request.user)
                return Response(MaterialProgressSerializer(progress).data)
            except MaterialProgress.DoesNotExist:
                return Response({'message': 'Прогресс не найден'})
        
        # Для преподавателей и тьюторов показываем прогресс всех студентов
        progress_list = material.progress.all()
        return Response(MaterialProgressSerializer(progress_list, many=True).data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """
        Получить или добавить комментарии к материалу
        """
        material = self.get_object()
        
        if request.method == 'GET':
            comments = material.comments.all()
            return Response(MaterialCommentSerializer(comments, many=True).data)
        
        elif request.method == 'POST':
            serializer = MaterialCommentSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save(material=material)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MaterialProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра прогресса материалов
    """
    queryset = MaterialProgress.objects.all()
    serializer_class = MaterialProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'student':
            return MaterialProgress.objects.filter(student=user)
        elif user.role in ['teacher', 'tutor']:
            return MaterialProgress.objects.all()
        elif user.role == 'parent':
            children = user.parent_profile.children.all()
            return MaterialProgress.objects.filter(student__in=children)
        
        return MaterialProgress.objects.none()


class MaterialCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для комментариев к материалам
    """
    queryset = MaterialComment.objects.all()
    serializer_class = MaterialCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)