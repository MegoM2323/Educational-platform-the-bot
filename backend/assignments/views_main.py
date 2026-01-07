import logging
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import (
    Assignment,
    AssignmentSubmission,
    AssignmentQuestion,
    AssignmentAnswer,
    PeerReviewAssignment,
    PeerReview,
    AssignmentAttempt,
)
from .serializers import (
    AssignmentListSerializer,
    AssignmentDetailSerializer,
    AssignmentCreateSerializer,
    AssignmentSubmissionSerializer,
    AssignmentSubmissionCreateSerializer,
    AssignmentGradingSerializer,
    AssignmentQuestionSerializer,
    AssignmentAnswerSerializer,
    PeerReviewSerializer,
    PeerReviewCreateSerializer,
    PeerReviewAssignmentSerializer,
    PeerReviewAssignmentListSerializer,
    AssignmentAttemptListSerializer,
    AssignmentAttemptDetailSerializer,
    AssignmentAttemptCreateSerializer,
    AssignmentAttemptGradeSerializer,
)
from .services.analytics import GradeDistributionAnalytics
from .services.peer_assignment import PeerAssignmentService
from .services.attempts import (
    AttemptCreationService,
    AttemptValidationService,
    AttemptStatisticsService,
)
from .cache.stats import AssignmentStatsCache

logger = logging.getLogger(__name__)
User = get_user_model()


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for assignment endpoints.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsTeacherOrTutor(permissions.BasePermission):
    """
    Permission class to restrict access to teachers and tutors only.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ["teacher", "tutor"]


class IsAuthor(permissions.BasePermission):
    """
    Permission class to check if user is the assignment author.
    """

    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для заданий
    """

    queryset = Assignment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "status", "author", "difficulty_level"]
    search_fields = ["title", "description", "instructions", "tags"]
    ordering_fields = ["created_at", "due_date", "title", "difficulty_level"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return AssignmentListSerializer
        elif self.action == "create":
            return AssignmentCreateSerializer
        return AssignmentDetailSerializer

    def get_permissions(self):
        """
        Assign permissions based on action
        """
        if self.action == "create":
            permission_classes = [permissions.IsAuthenticated, IsTeacherOrTutor]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [permissions.IsAuthenticated, IsAuthor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Фильтрация заданий в зависимости от роли пользователя
        """
        user = self.request.user

        queryset = Assignment.objects.select_related("author").prefetch_related("assigned_to")

        if user.role == "student":
            # Студенты видят только назначенные им задания
            return queryset.filter(assigned_to=user)
        elif user.role in ["teacher", "tutor"]:
            # Преподаватели и тьюторы видят все задания
            return queryset
        elif user.role == "parent":
            # Родители видят задания своих детей
            children = user.parent_profile.children.all()
            return queryset.filter(assigned_to__in=children).distinct()

        return Assignment.objects.none()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """
        Назначить задание студентам
        """
        assignment = self.get_object()
        student_ids = request.data.get("student_ids", [])

        if not student_ids:
            return Response({"error": "Не указаны ID студентов"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что все указанные пользователи - студенты
        students = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)

        if len(students) != len(student_ids):
            return Response(
                {"error": "Некоторые пользователи не являются студентами"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.assigned_to.set(students)
        return Response({"message": "Задание назначено студентам"})

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        """
        Получить ответы на задание
        """
        assignment = self.get_object()

        if request.user.role == "student":
            # Студент видит только свои ответы
            submissions = assignment.submissions.filter(student=request.user)
        else:
            # Преподаватели и тьюторы видят все ответы
            submissions = assignment.submissions.all()

        serializer = AssignmentSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Сдать ответ на задание
        """
        assignment = self.get_object()
        student = request.user

        if student.role != "student":
            return Response(
                {"error": "Только студенты могут сдавать задания"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Проверяем, что задание назначено студенту
        if not assignment.assigned_to.filter(id=student.id).exists():
            return Response({"error": "Задание не назначено вам"}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем сроки
        if timezone.now() > assignment.due_date:
            return Response(
                {"error": "Срок сдачи задания истек"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем лимит попыток
        existing_submissions = assignment.submissions.filter(student=student).count()
        if existing_submissions >= assignment.attempts_limit:
            return Response({"error": "Превышен лимит попыток"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssignmentSubmissionCreateSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            submission = serializer.save(assignment=assignment)
            from .signals import send_submission_notification

            send_submission_notification(submission)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            {"success": False, "error": "Ошибка валидации данных"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
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
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Только автор задания может просматривать аналитику"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Generate analytics
            analytics_service = GradeDistributionAnalytics(assignment)
            analytics_data = analytics_service.get_analytics()

            return Response(analytics_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to generate analytics for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to generate analytics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def cache_hit_rate(self, request, pk=None):
        """
        T_ASSIGN_013: Get cache hit rate metrics for assignment statistics.

        Returns cache performance metrics including:
        - hits: Number of cache hits
        - misses: Number of cache misses
        - total: Total number of requests
        - hit_rate_percentage: Hit rate as percentage
        - cache_key: The cache key used
        - ttl_seconds: Cache TTL in seconds

        Only teachers/tutors who created the assignment can view metrics.

        Response:
            200 OK: Cache hit rate metrics
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        assignment = self.get_object()

        # Check if user is the assignment author or a teacher/tutor
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Только автор задания может просматривать метрики кэша"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Get cache hit rate metrics
            cache_manager = AssignmentStatsCache(assignment.id)
            hit_rate_data = cache_manager.get_hit_rate()

            return Response(hit_rate_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get cache hit rate for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to get cache hit rate metrics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def bulk_grade(self, request, pk=None):
        """
        T_ASSIGN_011: Grade multiple submissions at once with batch operations.

        Only teachers and tutors who created the assignment can use this endpoint.

        Request Body:
        {
            "grades": [
                {"submission_id": 1, "score": 85, "feedback": "Good work"},
                {"submission_id": 2, "score": 92, "feedback": "Excellent"}
            ],
            "rubric_id": 5,  // optional
            "transaction_mode": "atomic"  // or "partial"
        }

        Response:
            200 OK: Results object with created/failed counts
            400 Bad Request: Validation errors
            403 Forbidden: User is not the assignment author

        Example success response:
        {
            "success": true,
            "created": 5,
            "failed": 0,
            "errors": [],
            "details": [
                {"submission_id": 1, "score": 85.0, "status": "success"},
                ...
            ]
        }
        """
        from .services.bulk_grading import BulkGradingService
        from .serializers import BulkGradeSerializer, BulkGradeResultSerializer

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can grade submissions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate request
        serializer = BulkGradeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply grades
        result = BulkGradingService.apply_bulk_grades(
            grades_data=serializer.validated_data["grades"],
            assignment=assignment,
            user=request.user,
            transaction_mode=serializer.validated_data.get("transaction_mode", "atomic"),
            rubric_id=serializer.validated_data.get("rubric_id"),
        )

        # Log the operation
        logger.info(
            f"Bulk grading for assignment {assignment.id}: " f"{result['created']} created, {result['failed']} failed"
        )

        # Invalidate analytics cache
        GradeDistributionAnalytics.invalidate_assignment_cache(assignment.id)

        result_serializer = BulkGradeResultSerializer(result)
        return Response(result_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def import_grades(self, request, pk=None):
        """
        T_ASSIGN_011: Import grades from CSV file.

        CSV format:
        submission_id,score,feedback
        1,85,Good work
        2,92,Excellent

        Only teachers and tutors who created the assignment can use this endpoint.

        Request Body (multipart/form-data):
        - csv_file: CSV file with grades
        - transaction_mode: "atomic" or "partial" (optional, default "atomic")

        Response:
            200 OK: Results object with created/failed counts
            400 Bad Request: CSV parsing or validation errors
            403 Forbidden: User is not the assignment author
        """
        from .services.bulk_grading import BulkGradingService
        from .serializers import CSVGradeImportSerializer, BulkGradeResultSerializer

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can import grades"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate request
        serializer = CSVGradeImportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Read CSV file
            csv_file = serializer.validated_data["csv_file"]
            csv_content = csv_file.read().decode("utf-8")

            # Parse CSV
            grades_data, parse_errors = BulkGradingService.parse_csv_grades(csv_content, assignment)

            if parse_errors and not grades_data:
                return Response(
                    {
                        "success": False,
                        "created": 0,
                        "failed": 0,
                        "errors": parse_errors,
                        "details": [],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Apply grades
            result = BulkGradingService.apply_bulk_grades(
                grades_data=grades_data,
                assignment=assignment,
                user=request.user,
                transaction_mode=serializer.validated_data.get("transaction_mode", "atomic"),
            )

            # Include parse errors in result
            if parse_errors:
                result["errors"].extend(parse_errors)

            # Log the operation
            logger.info(
                f"CSV grade import for assignment {assignment.id}: "
                f"{result['created']} created, {result['failed']} failed"
            )

            # Invalidate analytics cache
            GradeDistributionAnalytics.invalidate_assignment_cache(assignment.id)

            result_serializer = BulkGradeResultSerializer(result)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"CSV import failed for assignment {assignment.id}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "created": 0,
                    "failed": 0,
                    "errors": [f"CSV import failed: {str(e)}"],
                    "details": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def bulk_grade_stats(self, request, pk=None):
        """
        T_ASSIGN_011: Get statistics for bulk grading.

        Returns submission counts by status and average score for the assignment.
        Useful for planning bulk grading operations.

        Only teachers and tutors who created the assignment can access this.

        Response:
            200 OK: Statistics object
            403 Forbidden: User is not the assignment author

        Example response:
        {
            "total_submissions": 30,
            "graded_count": 25,
            "ungraded_count": 5,
            "pending_count": 0,
            "average_score": 82.5
        }
        """
        from .services.bulk_grading import BulkGradingService
        from .serializers import BulkGradeStatsSerializer

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can view grading statistics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get stats
        stats = BulkGradingService.get_bulk_grade_stats(assignment)

        stats_serializer = BulkGradeStatsSerializer(stats)
        return Response(stats_serializer.data, status=status.HTTP_200_OK)

    def peer_assignments(self, request, pk=None):
        """
        T_ASSIGN_005: Get peer review assignments for an assignment.

        Teachers/tutors see all assignments; students see their own reviews.

        Query Parameters:
        - status: Filter by status (pending, in_progress, completed, skipped)
        - reviewer: Filter by reviewer user ID
        - student: Filter by student user ID

        Returns:
            200 OK: List of peer review assignments
            404 Not Found: Assignment not found
        """
        assignment = self.get_object()

        # Get all submissions for this assignment
        submission_ids = AssignmentSubmission.objects.filter(assignment=assignment).values_list("id", flat=True)

        queryset = PeerReviewAssignment.objects.filter(submission_id__in=submission_ids).select_related(
            "reviewer", "submission__student"
        )

        # Filter by user role
        if request.user.role == "student":
            # Students see their own reviews to do and reviews received
            queryset = queryset.filter(Q(reviewer=request.user) | Q(submission__student=request.user))

        # Apply filters
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        reviewer_id = request.query_params.get("reviewer")
        if reviewer_id:
            queryset = queryset.filter(reviewer_id=reviewer_id)

        student_id = request.query_params.get("student")
        if student_id:
            queryset = queryset.filter(submission__student_id=student_id)

        serializer = PeerReviewAssignmentListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def generate_peer_reviews(self, request, pk=None):
        """
        T_ASSIGN_005: Auto-assign peer reviewers to all submissions.

        Only teachers/tutors can initiate this.

        Request Body:
        {
            "num_reviewers": 3,  # Number of reviewers per submission
            "deadline_offset_days": 7,  # Days from now for deadline
            "is_anonymous": false  # Whether reviews are anonymous
        }

        Returns:
            200 OK: Assignment results
            403 Forbidden: User is not a teacher/tutor
            400 Bad Request: Invalid parameters
        """
        assignment = self.get_object()

        # Check permissions
        if request.user.role not in ["teacher", "tutor"]:
            return Response(
                {"error": "Only teachers/tutors can generate peer reviews"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if assignment.author != request.user:
            return Response(
                {"error": "Only the assignment author can generate peer reviews"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get parameters
        num_reviewers = request.data.get("num_reviewers", 3)
        deadline_offset_days = request.data.get("deadline_offset_days", 7)
        is_anonymous = request.data.get("is_anonymous", False)

        # Validate parameters
        try:
            num_reviewers = int(num_reviewers)
            deadline_offset_days = int(deadline_offset_days)

            if num_reviewers < 1:
                raise ValueError("num_reviewers must be at least 1")
            if deadline_offset_days < 1:
                raise ValueError("deadline_offset_days must be at least 1")
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Perform random peer assignment
            result = PeerAssignmentService.assign_random_peers(
                assignment_id=assignment.id,
                num_reviewers=num_reviewers,
                deadline_offset_days=deadline_offset_days,
            )

            # Update anonymity setting for all assignments
            PeerReviewAssignment.objects.filter(submission__assignment=assignment).update(is_anonymous=is_anonymous)

            logger.info(
                f"Peer reviews generated for assignment {assignment.id}: "
                f"{result['assigned']} assigned, {result['skipped']} skipped"
            )

            return Response(
                {
                    "success": True,
                    "assigned": result["assigned"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                    "deadline_offset_days": deadline_offset_days,
                    "is_anonymous": is_anonymous,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Failed to generate peer reviews: {str(e)}")
            return Response(
                {"error": "Failed to generate peer reviews"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def clone(self, request, pk=None):
        """
        T_ASN_008: Clone an assignment with all questions and options.

        Only the assignment creator (author) can clone an assignment.

        Request Body:
        {
            "new_title": "Copy of Original Assignment",  // optional, auto-generated if not provided
            "new_due_date": "2025-12-27T18:00:00Z",      // optional, defaults to original
            "randomize_questions": false                  // optional, default false
        }

        Response:
            201 Created: Cloned assignment data
            400 Bad Request: Invalid parameters
            403 Forbidden: User is not the assignment creator
            404 Not Found: Assignment does not exist
        """
        from .serializers import (
            AssignmentCloneSerializer,
            AssignmentCloneResponseSerializer,
        )
        from .services.cloning import AssignmentCloningService

        assignment = self.get_object()

        # Validate permission (only creator can clone)
        if assignment.author != request.user:
            return Response(
                {"error": "Only the assignment creator can clone it"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate and parse request data
        serializer = AssignmentCloneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Perform cloning
            cloned_assignment = AssignmentCloningService.clone_assignment(
                assignment=assignment,
                user=request.user,
                new_title=serializer.validated_data.get("new_title"),
                new_due_date=serializer.validated_data.get("new_due_date"),
                randomize_questions=serializer.validated_data.get("randomize_questions", False),
            )

            # Return response with cloned assignment
            response_serializer = AssignmentCloneResponseSerializer(cloned_assignment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except PermissionError as e:
            logger.warning(f"Clone permission denied: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Failed to clone assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to clone assignment"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def statistics(self, request, pk=None):
        """
        T_ASN_005: Get overall assignment statistics.

        Returns comprehensive analytics including:
        - Descriptive statistics (mean, median, mode, std dev, quartiles)
        - Grade distribution (A-F buckets)
        - Submission metrics (submission rate, grading rate)
        - Class average comparison

        Only teachers/tutors who created the assignment can view.

        Response:
            200 OK: Overall statistics
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        from .services.statistics import AssignmentStatisticsService

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can view statistics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = AssignmentStatisticsService(assignment)
            stats = service.get_overall_statistics()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get statistics for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to generate statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def statistics_by_student(self, request, pk=None):
        """
        T_ASN_005: Get per-student performance breakdown.

        Returns student-level statistics including:
        - Individual student scores and percentages
        - Submission status and timing
        - Late submission tracking
        - Performance tier classification

        Only teachers/tutors who created the assignment can view.

        Response:
            200 OK: Per-student breakdown
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        from .services.statistics import AssignmentStatisticsService

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can view statistics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = AssignmentStatisticsService(assignment)
            stats = service.get_student_breakdown()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get student statistics for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to generate student statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def statistics_by_question(self, request, pk=None):
        """
        T_ASN_005: Get per-question difficulty and performance analysis.

        Returns question-level statistics including:
        - Correct/wrong answer counts
        - Difficulty scoring (based on wrong answer rate)
        - Question difficulty ranking
        - Common wrong answers

        Only teachers/tutors who created the assignment can view.

        Response:
            200 OK: Per-question analysis
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        from .services.statistics import AssignmentStatisticsService

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can view statistics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = AssignmentStatisticsService(assignment)
            stats = service.get_question_analysis()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get question statistics for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to generate question statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def statistics_time_analysis(self, request, pk=None):
        """
        T_ASN_005: Get time spent analysis (submission and grading timing).

        Returns time-related statistics including:
        - Submission timing analysis
        - Grading speed metrics
        - Late submission analysis
        - Teacher response time

        Only teachers/tutors who created the assignment can view.

        Response:
            200 OK: Time analysis
            403 Forbidden: User is not the assignment author
            404 Not Found: Assignment does not exist
        """
        from .services.statistics import AssignmentStatisticsService

        assignment = self.get_object()

        # Permission check
        if request.user.role not in ["teacher", "tutor"] or assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can view statistics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = AssignmentStatisticsService(assignment)
            stats = service.get_time_analysis()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get time analysis for assignment {assignment.id}: {str(e)}")
            return Response(
                {"error": "Failed to generate time analysis"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для ответов на задания
    """

    queryset = AssignmentSubmission.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "assignment", "student"]
    ordering_fields = ["submitted_at", "graded_at", "score"]
    ordering = ["-submitted_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return AssignmentSubmissionCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return AssignmentGradingSerializer
        return AssignmentSubmissionSerializer

    def get_queryset(self):
        user = self.request.user

        queryset = AssignmentSubmission.objects.select_related("student", "assignment", "assignment__author")

        if user.role == "student":
            return queryset.filter(student=user)
        elif user.role in ["teacher", "tutor"]:
            return queryset
        elif user.role == "parent":
            children = user.parent_profile.children.all()
            return queryset.filter(student__in=children)

        return AssignmentSubmission.objects.none()

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        """
        M6: Grade a submission with feedback.

        POST /api/assignments/{assignment_id}/submissions/{submission_id}/grade/

        Request body:
        {
            "grade": 8,
            "feedback": "Good work, but..."
        }

        Returns: SubmissionFeedback object with 200 OK or 201 CREATED
        """
        from .serializers import SubmissionFeedbackSerializer
        from .models import SubmissionFeedback
        from notifications.services import NotificationService

        submission = self.get_object()

        if request.user.role not in ["teacher", "tutor"]:
            return Response(
                {"error": "Только преподаватели и тьюторы могут оценивать задания"},
                status=status.HTTP_403_FORBIDDEN,
            )

        grade = request.data.get("grade")
        feedback = request.data.get("feedback", "")

        if grade is None:
            return Response({"error": "grade field is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            feedback_obj, created = SubmissionFeedback.objects.update_or_create(
                submission=submission,
                defaults={
                    "teacher": request.user,
                    "grade": grade,
                    "feedback_text": feedback,
                },
            )

            submission.status = "graded"
            submission.score = (
                grade * (submission.assignment.max_score / 10) if submission.assignment.max_score else grade
            )
            submission.feedback = feedback
            submission.graded_at = timezone.now()
            submission.save()

            try:
                notif_service = NotificationService()
                notif_service.send(
                    recipient=submission.student,
                    notif_type="assignment_graded",
                    title="Ваше задание оценено",
                    message=f'Преподаватель {request.user.get_full_name()} оценил ваше задание "{submission.assignment.title}" на {grade}/10',
                    related_object_type="submission_feedback",
                    related_object_id=feedback_obj.id,
                    data={
                        "submission_id": submission.id,
                        "feedback_id": feedback_obj.id,
                        "assignment_id": submission.assignment.id,
                        "grade": grade,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {str(e)}")

            GradeDistributionAnalytics.invalidate_assignment_cache(submission.assignment.id)

            serializer = SubmissionFeedbackSerializer(feedback_obj)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)

        except Exception as e:
            logger.error(f"Failed to grade submission {submission.id}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
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
        queryset = AssignmentQuestion.objects.select_related("assignment")
        assignment_id = self.request.query_params.get("assignment")
        if assignment_id:
            return queryset.filter(assignment_id=assignment_id)
        return queryset


class AssignmentAnswerViewSet(viewsets.ModelViewSet):
    """
    ViewSet для ответов на вопросы
    """

    queryset = AssignmentAnswer.objects.all()
    serializer_class = AssignmentAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = AssignmentAnswer.objects.select_related("submission", "question")
        submission_id = self.request.query_params.get("submission")
        if submission_id:
            return queryset.filter(submission_id=submission_id)
        return queryset


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

        queryset = SubmissionComment.objects.filter(submission_id=submission_id).select_related("author", "submission")

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
        if self.action in [
            "update",
            "partial_update",
            "destroy",
            "publish",
            "toggle_pin",
        ]:
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

        logger.info(f"Comment published: id={obj.id}, submission={submission.id}, " f"author={obj.author.email}")

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
        return CommentTemplate.objects.filter(Q(author=user) | Q(is_shared=True), is_active=True).select_related(
            "author"
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
        logger.info(f"Comment template updated: id={serializer.instance.id}, " f"author={self.request.user.email}")

    def perform_destroy(self, instance):
        """Мягкое удаление шаблона"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own templates")

        instance.is_active = False
        instance.save()

        logger.info(f"Comment template deleted: id={instance.id}, author={self.request.user.email}")

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


class PeerReviewAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    T_ASSIGN_005: ViewSet for managing peer review assignments.

    Endpoints:
    - GET /api/peer-assignments/ - list assignments
    - GET /api/peer-assignments/{id}/ - view assignment details
    - POST /api/peer-assignments/{id}/submit_review/ - submit a review
    - POST /api/peer-assignments/{id}/start/ - mark as in progress
    - POST /api/peer-assignments/{id}/skip/ - skip the assignment
    - GET /api/peer-assignments/{id}/reviews/ - view submission reviews
    """

    queryset = PeerReviewAssignment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "reviewer", "assignment_type"]
    ordering_fields = ["deadline", "created_at", "status"]
    ordering = ["deadline"]
    pagination_class = StandardPagination

    def get_queryset(self):
        """
        Students see their assigned reviews.
        Teachers/tutors see all reviews.
        """
        user = self.request.user
        queryset = PeerReviewAssignment.objects.select_related(
            "reviewer", "submission__student", "submission__assignment", "submission__assignment__author"
        )

        if user.role == "student":
            # Students see their own reviews to do
            queryset = queryset.filter(reviewer=user)

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PeerReviewAssignmentSerializer
        return PeerReviewAssignmentListSerializer

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def submit_review(self, request, pk=None):
        """
        T_ASSIGN_005: Submit a peer review.

        Request Body:
        {
            "score": 85,
            "feedback_text": "Good work, but...",
            "rubric_scores": {
                "clarity": 8,
                "completeness": 7,
                "accuracy": 9
            }
        }

        Returns:
            201 Created: Review submitted successfully
            403 Forbidden: User is not the assigned reviewer
            400 Bad Request: Deadline passed or already reviewed
            404 Not Found: Assignment not found
        """
        assignment = self.get_object()

        # Check if user is the assigned reviewer
        if assignment.reviewer != request.user:
            return Response(
                {"error": "You are not assigned to this review"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if review is already submitted
        if hasattr(assignment, "review"):
            return Response(
                {"error": "Review already submitted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PeerReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            review = PeerAssignmentService.submit_review(
                peer_assignment_id=assignment.id,
                score=serializer.validated_data["score"],
                feedback_text=serializer.validated_data["feedback_text"],
                rubric_scores=serializer.validated_data.get("rubric_scores", {}),
            )

            logger.info(
                f"Peer review submitted: reviewer={request.user.id}, "
                f"submission={assignment.submission.id}, score={review.score}"
            )

            response_serializer = PeerReviewSerializer(review)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to submit peer review: {str(e)}")
            return Response(
                {"error": "Failed to submit review"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def start(self, request, pk=None):
        """
        T_ASSIGN_005: Mark peer review assignment as in progress.

        Returns:
            200 OK: Assignment updated
            403 Forbidden: User is not the assigned reviewer
        """
        assignment = self.get_object()

        if assignment.reviewer != request.user:
            return Response(
                {"error": "You are not assigned to this review"},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = PeerAssignmentService.start_review(assignment.id)
        serializer = PeerReviewAssignmentSerializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def skip(self, request, pk=None):
        """
        T_ASSIGN_005: Mark peer review assignment as skipped.

        Request Body (optional):
        {
            "reason": "Cannot evaluate this submission"
        }

        Returns:
            200 OK: Assignment marked as skipped
            403 Forbidden: User is not the assigned reviewer
        """
        assignment = self.get_object()

        if assignment.reviewer != request.user:
            return Response(
                {"error": "You are not assigned to this review"},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = request.data.get("reason", "")
        assignment = PeerAssignmentService.mark_as_skipped(assignment.id, reason)
        serializer = PeerReviewAssignmentSerializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def reviews(self, request, pk=None):
        """
        T_ASSIGN_005: Get all reviews of a submission.

        Returns all peer reviews for the submission associated with this assignment.
        Students can only see reviews of their own submissions.

        Returns:
            200 OK: List of peer reviews
            403 Forbidden: Not authorized to view reviews
        """
        assignment = self.get_object()
        submission = assignment.submission

        # Students can only see reviews of their own submissions
        if request.user.role == "student" and submission.student != request.user:
            return Response(
                {"error": "Not authorized to view reviews"},
                status=status.HTTP_403_FORBIDDEN,
            )

        reviews = PeerReview.objects.filter(peer_assignment__submission=submission).select_related(
            "peer_assignment__reviewer"
        )

        serializer = PeerReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class PeerReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    T_ASSIGN_005: ViewSet for viewing peer reviews.

    Read-only endpoints for accessing peer review data.
    """

    queryset = PeerReview.objects.all()
    serializer_class = PeerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["peer_assignment__submission", "peer_assignment__reviewer"]
    ordering_fields = ["score", "created_at"]
    ordering = ["-created_at"]
    pagination_class = StandardPagination

    def get_queryset(self):
        """
        Students see reviews of their own submissions and reviews they submitted.
        Teachers/tutors see all reviews.
        """
        user = self.request.user
        queryset = PeerReview.objects.select_related(
            "peer_assignment__reviewer",
            "peer_assignment__submission__student",
            "peer_assignment__submission__assignment",
            "peer_assignment__submission__assignment__author",
        )

        if user.role == "student":
            queryset = queryset.filter(Q(peer_assignment__reviewer=user) | Q(peer_assignment__submission__student=user))

        return queryset


class AssignmentAttemptViewSet(viewsets.ModelViewSet):
    """
    T_ASN_003: ViewSet for managing assignment attempts.

    Tracks multiple submission attempts for assignments to support retakes and learning.
    Provides endpoints for creating attempts, listing attempt history, and grading individual attempts.
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["submission", "student", "status", "assignment"]
    ordering_fields = ["attempt_number", "submitted_at", "score"]
    ordering = ["attempt_number"]

    def get_serializer_class(self):
        if self.action == "create":
            return AssignmentAttemptCreateSerializer
        elif self.action == "grade":
            return AssignmentAttemptGradeSerializer
        elif self.action == "list":
            return AssignmentAttemptListSerializer
        return AssignmentAttemptDetailSerializer

    def get_queryset(self):
        """
        Filter attempts based on user role.
        - Students see only their own attempts
        - Teachers/tutors see all attempts for assignments they created
        """
        user = self.request.user
        queryset = AssignmentAttempt.objects.select_related("student", "assignment", "assignment__author", "submission")

        if user.role == "student":
            # Students see only their own attempts
            queryset = queryset.filter(student=user)
        elif user.role in ["teacher", "tutor"]:
            # Teachers/tutors see attempts for assignments they created
            queryset = queryset.filter(assignment__author=user)
        else:
            # Other roles don't see attempts
            queryset = queryset.none()

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create a new attempt for an assignment.

        POST /api/assignments/{assignment_id}/attempts/submit/

        Request body:
        {
            "submission_id": 123,
            "content": "My answer...",
            "file": <optional file>
        }

        Returns 201 Created with the new attempt details.
        Returns 400 if max attempts exceeded or deadline passed.
        """
        submission_id = request.data.get("submission_id")
        if not submission_id:
            return Response(
                {"error": "submission_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
        except AssignmentSubmission.DoesNotExist:
            return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)

        # Validate user owns this submission
        if submission.student != request.user:
            return Response(
                {"error": "Cannot submit attempt for another student"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate attempt can be created
        validation = AttemptValidationService.validate_attempt_submission(submission.assignment, request.user.id)

        if not validation["is_valid"]:
            return Response({"error": validation["error"]}, status=status.HTTP_400_BAD_REQUEST)

        # Create the attempt
        try:
            attempt = AttemptCreationService.create_attempt(
                submission=submission,
                content=request.data.get("content", ""),
                file=request.FILES.get("file"),
            )

            serializer = self.get_serializer(attempt)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create attempt for submission {submission_id}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        """
        Grade an assignment attempt.

        POST /api/attempts/{id}/grade/

        Request body:
        {
            "score": 85,
            "feedback": "Good work!",
            "status": "graded"
        }

        Returns 200 OK with the updated attempt.
        """
        attempt = self.get_object()

        # Permission check: only author of assignment can grade
        if attempt.assignment.author != request.user:
            return Response(
                {"error": "Only assignment author can grade"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AssignmentAttemptGradeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            attempt = AttemptCreationService.grade_attempt(
                attempt=attempt,
                score=serializer.validated_data["score"],
                feedback=serializer.validated_data.get("feedback", ""),
                status=serializer.validated_data.get("status", AssignmentAttempt.Status.GRADED),
            )

            serializer = AssignmentAttemptDetailSerializer(attempt)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to grade attempt {pk}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """
        Get attempt history for a specific submission.

        GET /api/attempts/history/?submission_id=123

        Returns list of all attempts for the submission in order.
        """
        submission_id = request.query_params.get("submission_id")
        if not submission_id:
            return Response(
                {"error": "submission_id query parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
        except AssignmentSubmission.DoesNotExist:
            return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check
        if submission.student != request.user and submission.assignment.author != request.user:
            return Response(
                {"error": "You do not have access to this submission"},
                status=status.HTTP_403_FORBIDDEN,
            )

        attempts = AssignmentAttempt.objects.filter(submission=submission).order_by("attempt_number")

        serializer = self.get_serializer(attempts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get attempt statistics for an assignment or student.

        GET /api/attempts/stats/?assignment_id=123 (for teachers)
        GET /api/attempts/stats/?submission_id=123 (for anyone)

        Returns statistics about attempts.
        """
        assignment_id = request.query_params.get("assignment_id")
        submission_id = request.query_params.get("submission_id")

        if assignment_id:
            try:
                assignment = Assignment.objects.get(id=assignment_id)
            except Assignment.DoesNotExist:
                return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

            # Permission check: only author can view assignment stats
            if assignment.author != request.user:
                return Response(
                    {"error": "Only assignment author can view statistics"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            stats = AttemptStatisticsService.get_attempt_stats(assignment)
            return Response(stats, status=status.HTTP_200_OK)

        elif submission_id:
            try:
                submission = AssignmentSubmission.objects.get(id=submission_id)
            except AssignmentSubmission.DoesNotExist:
                return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)

            # Permission check
            if submission.student != request.user and submission.assignment.author != request.user:
                return Response(
                    {"error": "You do not have access to this submission"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            stats = AttemptStatisticsService.get_student_stats(submission)
            return Response(stats, status=status.HTTP_200_OK)

        return Response(
            {"error": "Either assignment_id or submission_id query parameter required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
