import logging
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer
from .serializers import (
    AssignmentListSerializer, AssignmentDetailSerializer, AssignmentCreateSerializer,
    AssignmentSubmissionSerializer, AssignmentSubmissionCreateSerializer,
    AssignmentGradingSerializer, AssignmentQuestionSerializer, AssignmentAnswerSerializer
)
from .services.analytics import GradeDistributionAnalytics

logger = logging.getLogger(__name__)
User = get_user_model()


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for assignment endpoints.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsTeacherOrTutor(permissions.BasePermission):
    """
    Permission class to restrict access to teachers and tutors only.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["teacher", "tutor"]
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

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def analytics(self, request, pk=None):
        """
        T_ASSIGN_007: Get grade distribution analytics for an assignment.

        Only teachers and tutors who created the assignment can view analytics.

        Returns:
        - statistics: Descriptive statistics (mean, median, mode, std dev, quartiles)
        - distribution: Grade distribution buckets (A-F)
        - submission_rate: Submission and late submission metrics
        - comparison: Class average comparison
        - generated_at: Timestamp of analytics generation

        Response:
            200 OK: Complete analytics data
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        assignment = self.get_object()

        # Check if user is the assignment author or a teacher/tutor
        if request.user.role not in ['teacher', 'tutor'] or assignment.author != request.user:
            return Response(
                {'error': 'Только автор задания может просматривать аналитику'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Generate analytics
            analytics_service = GradeDistributionAnalytics(assignment)
            analytics_data = analytics_service.get_analytics()

            return Response(analytics_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f'Failed to generate analytics for assignment {assignment.id}: {str(e)}'
            )
            return Response(
                {'error': 'Failed to generate analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
            # T_ASSIGN_007: Invalidate analytics cache when grade changes
            GradeDistributionAnalytics.invalidate_assignment_cache(submission.assignment.id)
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

class SubmissionCommentViewSet(viewsets.ModelViewSet):
    """
    T_ASSIGN_008: API ViewSet для комментариев на ответы.

    Endpoints:
    - GET /api/submissions/{id}/comments/ - список комментариев
    - POST /api/submissions/{id}/comments/ - создать комментарий
    - GET /api/submissions/{id}/comments/{id}/ - детали комментария
    - PATCH /api/submissions/{id}/comments/{id}/ - отредактировать (автор only)
    - DELETE /api/submissions/{id}/comments/{id}/ - удалить (soft delete)
    - POST /api/submissions/{id}/comments/{id}/publish/ - опубликовать черновик
    - POST /api/submissions/{id}/comments/{id}/toggle_pin/ - закрепить/открепить
    - POST /api/submissions/{id}/comments/{id}/mark_read/ - отметить как прочитано

    Permissions:
    - Только преподаватели/тьюторы могут создавать комментарии
    - Только автор комментария может редактировать/удалять
    - Студенты могут видеть только опубликованные комментарии
    """

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["-is_pinned", "-created_at"]
    ordering = ["-is_pinned", "-created_at"]

    def get_queryset(self):
        """Получить комментарии с учетом видимости"""
        from .models import SubmissionComment

        user = self.request.user
        submission_id = self.kwargs.get("submission_id")

        if not submission_id:
            return SubmissionComment.objects.none()

        queryset = SubmissionComment.objects.filter(submission_id=submission_id)

        # Студенты видят только опубликованные и не удаленные комментарии
        if user.role == "student":
            queryset = queryset.filter(is_draft=False, is_deleted=False)

        return queryset

    def get_serializer_class(self):
        """Выбрать подходящий сериализатор"""
        from .serializers import (
            SubmissionCommentSerializer,
            SubmissionCommentCreateUpdateSerializer,
            SubmissionCommentDetailSerializer,
        )

        if self.action == "create":
            return SubmissionCommentCreateUpdateSerializer
        elif self.action == "retrieve":
            return SubmissionCommentDetailSerializer
        elif self.action in ["update", "partial_update"]:
            return SubmissionCommentCreateUpdateSerializer
        return SubmissionCommentSerializer

    def get_permissions(self):
        """Определить permissions на основе action"""
        from rest_framework.permissions import IsAuthenticated

        if self.action == "create":
            # Только преподаватели/тьюторы могут создавать комментарии
            return [
                IsAuthenticated(),
                IsTeacherOrTutor(),
            ]
        elif self.action in ["update", "partial_update", "destroy"]:
            # Только автор может редактировать/удалять
            return [IsAuthenticated()]
        elif self.action in ["publish", "toggle_pin"]:
            # Только автор может публиковать и закреплять
            return [IsAuthenticated()]

        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Сохранить комментарий"""
        from notifications.services import NotificationService

        comment = serializer.save()

        # Отправить уведомление студенту если комментарий не черновик
        if not comment.is_draft:
            submission = comment.submission
            student = submission.student

            notif_service = NotificationService()
            notif_service.send(
                recipient=student,
                notif_type="assignment_feedback",
                title=f"Новый комментарий на ваш ответ",
                message=f"Преподаватель {comment.author.get_full_name()} оставил комментарий на ваш ответ",
                related_object_type="submission_comment",
                related_object_id=comment.id,
                data={
                    "submission_id": submission.id,
                    "comment_id": comment.id,
                    "assignment_title": submission.assignment.title,
                },
            )

            logger.info(
                f"Comment created: id={comment.id}, submission={submission.id}, "
                f"author={comment.author.email}, is_draft={comment.is_draft}"
            )

    def check_object_permission(self, request, obj):
        """Проверить permissions на уровне объекта"""
        if self.action in ["update", "partial_update", "destroy", "publish", "toggle_pin"]:
            # Только автор может редактировать/удалять
            if obj.author != request.user and request.user.role != "admin":
                raise PermissionDenied("You can only edit your own comments")

        # Студенты не могут видеть черновики других преподавателей
        if request.user.role == "student" and not obj.is_visible_to_student():
            raise PermissionDenied("This comment is not visible to you")

    def retrieve(self, request, *args, **kwargs):
        """Получить детали комментария"""
        response = super().retrieve(request, *args, **kwargs)

        # Отметить как прочитанное для студента
        if request.user.role == "student":
            from .models import SubmissionCommentAcknowledgment

            obj = self.get_object()
            ack, created = SubmissionCommentAcknowledgment.objects.get_or_create(
                comment=obj,
                student=request.user,
            )
            if not ack.is_read:
                ack.mark_as_read()

        return response

    def destroy(self, request, *args, **kwargs):
        """Удалить комментарий (soft delete)"""
        obj = self.get_object()
        self.check_object_permission(request, obj)

        obj.delete_soft()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        """
        Опубликовать черновой комментарий.

        Изменяет is_draft на False и отправляет уведомление студенту.
        """
        from notifications.services import NotificationService

        obj = self.get_object()
        self.check_object_permission(request, obj)

        if not obj.is_draft:
            return Response(
                {"error": "Comment is already published"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj.publish()

        # Отправить уведомление студенту
        submission = obj.submission
        student = submission.student

        notif_service = NotificationService()
        notif_service.send(
            recipient=student,
            notif_type="assignment_feedback",
            title=f"Новый комментарий на ваш ответ",
            message=f"Преподаватель {obj.author.get_full_name()} оставил комментарий на ваш ответ",
            related_object_type="submission_comment",
            related_object_id=obj.id,
            data={
                "submission_id": submission.id,
                "comment_id": obj.id,
                "assignment_title": submission.assignment.title,
            },
        )

        logger.info(
            f"Comment published: id={obj.id}, submission={submission.id}, "
            f"author={obj.author.email}"
        )

        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_pin(self, request, *args, **kwargs):
        """
        Закрепить или открепить комментарий.
        """
        obj = self.get_object()
        self.check_object_permission(request, obj)

        obj.is_pinned = not obj.is_pinned
        obj.save()

        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, *args, **kwargs):
        """
        Отметить комментарий как прочитанный (для студента).
        """
        from .models import SubmissionCommentAcknowledgment

        obj = self.get_object()

        # Проверить что текущий пользователь - это студент из submission
        if request.user != obj.submission.student and request.user.role != "admin":
            raise PermissionDenied("You can only mark your own submissions as read")

        ack, created = SubmissionCommentAcknowledgment.objects.get_or_create(
            comment=obj,
            student=request.user,
        )
        ack.mark_as_read()

        serializer = SubmissionCommentAcknowledgmentSerializer(ack)
        return Response(serializer.data)


class CommentTemplateViewSet(viewsets.ModelViewSet):
    """
    T_ASSIGN_008: API ViewSet для шаблонов комментариев.

    Позволяет преподавателям управлять готовыми шаблонами для быстрого добавления
    комментариев на ответы студентов.

    Endpoints:
    - GET /api/comment-templates/ - список шаблонов
    - POST /api/comment-templates/ - создать шаблон
    - GET /api/comment-templates/{id}/ - детали шаблона
    - PATCH /api/comment-templates/{id}/ - отредактировать
    - DELETE /api/comment-templates/{id}/ - удалить
    """

    permission_classes = [permissions.IsAuthenticated, IsTeacherOrTutor]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "category"]
    ordering_fields = ["-is_shared", "-usage_count", "-updated_at"]
    ordering = ["-is_shared", "-usage_count", "-updated_at"]

    def get_queryset(self):
        """Получить шаблоны пользователя или общие"""
        from .models import CommentTemplate

        user = self.request.user
        # Показать свои шаблоны + общие шаблоны
        return CommentTemplate.objects.filter(
            Q(author=user) | Q(is_shared=True),
            is_active=True
        )

    def get_serializer_class(self):
        from .serializers import CommentTemplateSerializer

        return CommentTemplateSerializer

    def perform_create(self, serializer):
        """Сохранить шаблон с автором"""
        serializer.save(author=self.request.user)

        logger.info(
            f"Comment template created: id={serializer.instance.id}, "
            f"author={self.request.user.email}, title={serializer.instance.title}"
        )

    def perform_update(self, serializer):
        """Обновить шаблон"""
        # Проверить что это автор
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own templates")

        serializer.save()
        logger.info(
            f"Comment template updated: id={serializer.instance.id}, "
            f"author={self.request.user.email}"
        )

    def perform_destroy(self, instance):
        """Мягкое удаление шаблона"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own templates")

        instance.is_active = False
        instance.save()

        logger.info(
            f"Comment template deleted: id={instance.id}, author={self.request.user.email}"
        )

    @action(detail=True, methods=["post"])
    def use(self, request, pk=None):
        """
        Использовать шаблон для создания комментария.

        Увеличивает счетчик usage_count и возвращает содержимое шаблона.
        """
        from .models import CommentTemplate

        obj = self.get_object()
        obj.usage_count += 1
        obj.save()

        from .serializers import CommentTemplateSerializer

        serializer = CommentTemplateSerializer(obj)
        return Response(serializer.data)
