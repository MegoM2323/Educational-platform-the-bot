from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer
from .serializers import (
    AssignmentListSerializer, AssignmentDetailSerializer, AssignmentCreateSerializer,
    AssignmentSubmissionSerializer, AssignmentSubmissionCreateSerializer,
    AssignmentGradingSerializer, AssignmentQuestionSerializer, AssignmentAnswerSerializer
)


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для заданий
    """
    queryset = Assignment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'author', 'difficulty_level']
    search_fields = ['title', 'description', 'instructions', 'tags']
    ordering_fields = ['created_at', 'due_date', 'title', 'difficulty_level']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AssignmentListSerializer
        elif self.action == 'create':
            return AssignmentCreateSerializer
        return AssignmentDetailSerializer
    
    def get_queryset(self):
        """
        Фильтрация заданий в зависимости от роли пользователя
        """
        user = self.request.user
        
        if user.role == 'student':
            # Студенты видят только назначенные им задания
            return Assignment.objects.filter(assigned_to=user)
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели и тьюторы видят все задания
            return Assignment.objects.all()
        elif user.role == 'parent':
            # Родители видят задания своих детей
            children = user.parent_profile.children.all()
            return Assignment.objects.filter(assigned_to__in=children).distinct()
        
        return Assignment.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Назначить задание студентам
        """
        assignment = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return Response(
                {'error': 'Не указаны ID студентов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что все указанные пользователи - студенты
        students = User.objects.filter(
            id__in=student_ids,
            role=User.Role.STUDENT
        )
        
        if len(students) != len(student_ids):
            return Response(
                {'error': 'Некоторые пользователи не являются студентами'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.assigned_to.set(students)
        return Response({'message': 'Задание назначено студентам'})
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """
        Получить ответы на задание
        """
        assignment = self.get_object()
        
        if request.user.role == 'student':
            # Студент видит только свои ответы
            submissions = assignment.submissions.filter(student=request.user)
        else:
            # Преподаватели и тьюторы видят все ответы
            submissions = assignment.submissions.all()
        
        serializer = AssignmentSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Сдать ответ на задание
        """
        assignment = self.get_object()
        student = request.user
        
        if student.role != 'student':
            return Response(
                {'error': 'Только студенты могут сдавать задания'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что задание назначено студенту
        if not assignment.assigned_to.filter(id=student.id).exists():
            return Response(
                {'error': 'Задание не назначено вам'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем сроки
        if timezone.now() > assignment.due_date:
            return Response(
                {'error': 'Срок сдачи задания истек'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем лимит попыток
        existing_submissions = assignment.submissions.filter(student=student).count()
        if existing_submissions >= assignment.attempts_limit:
            return Response(
                {'error': 'Превышен лимит попыток'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AssignmentSubmissionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(assignment=assignment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для ответов на задания
    """
    queryset = AssignmentSubmission.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'assignment', 'student']
    ordering_fields = ['submitted_at', 'graded_at', 'score']
    ordering = ['-submitted_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssignmentSubmissionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AssignmentGradingSerializer
        return AssignmentSubmissionSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'student':
            return AssignmentSubmission.objects.filter(student=user)
        elif user.role in ['teacher', 'tutor']:
            return AssignmentSubmission.objects.all()
        elif user.role == 'parent':
            children = user.parent_profile.children.all()
            return AssignmentSubmission.objects.filter(student__in=children)
        
        return AssignmentSubmission.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """
        Оценить ответ на задание
        """
        submission = self.get_object()
        
        if request.user.role not in ['teacher', 'tutor']:
            return Response(
                {'error': 'Только преподаватели и тьюторы могут оценивать задания'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AssignmentGradingSerializer(
            submission,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def answers(self, request, pk=None):
        """
        Получить ответы на вопросы
        """
        submission = self.get_object()
        answers = submission.answers.all()
        serializer = AssignmentAnswerSerializer(answers, many=True)
        return Response(serializer.data)


class AssignmentQuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для вопросов в заданиях
    """
    queryset = AssignmentQuestion.objects.all()
    serializer_class = AssignmentQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            return AssignmentQuestion.objects.filter(assignment_id=assignment_id)
        return AssignmentQuestion.objects.all()


class AssignmentAnswerViewSet(viewsets.ModelViewSet):
    """
    ViewSet для ответов на вопросы
    """
    queryset = AssignmentAnswer.objects.all()
    serializer_class = AssignmentAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        submission_id = self.request.query_params.get('submission')
        if submission_id:
            return AssignmentAnswer.objects.filter(submission_id=submission_id)
        return AssignmentAnswer.objects.all()