from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer,
    PeerReviewAssignment, PeerReview, PlagiarismReport, AssignmentAttempt,
    GradingRubric, RubricCriterion, RubricScore, SubmissionExemption,
    StudentDeadlineExtension
)
from .validators import DueDateValidator, validate_soft_deadlines_serializer

User = get_user_model()


class AssignmentListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка заданий
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    assigned_count = serializers.SerializerMethodField()
    submissions_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    submission = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = (
            'id', 'title', 'description', 'author', 'author_name', 'type',
            'status', 'max_score', 'time_limit', 'attempts_limit',
            'assigned_count', 'submissions_count', 'start_date', 'due_date',
            'difficulty_level', 'tags', 'created_at', 'is_overdue', 'submission',
            'publish_at', 'close_at'
        )
    
    def get_assigned_count(self, obj):
        return obj.assigned_to.count()
    
    def get_submissions_count(self, obj):
        return obj.submissions.count()
    
    def get_submission(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'student':
            try:
                submission = obj.submissions.get(student=request.user)
                return {
                    'id': submission.id,
                    'status': submission.status,
                    'score': submission.score,
                    'submitted_at': submission.submitted_at,
                    'graded_at': submission.graded_at
                }
            except AssignmentSubmission.DoesNotExist:
                return None
        return None


class AssignmentDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра задания
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    assigned_to_names = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    submissions = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Assignment
        fields = (
            'id', 'title', 'description', 'instructions', 'author', 'author_name',
            'type', 'status', 'max_score', 'time_limit', 'attempts_limit',
            'assigned_to', 'assigned_to_names', 'start_date', 'due_date',
            'tags', 'difficulty_level', 'created_at', 'updated_at',
            'questions', 'submissions', 'is_overdue', 'publish_at', 'close_at'
        )
    
    def get_assigned_to_names(self, obj):
        return [user.get_full_name() for user in obj.assigned_to.all()]
    
    def get_questions(self, obj):
        return AssignmentQuestionSerializer(obj.questions.all(), many=True).data
    
    def get_submissions(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.role == 'student':
                # Студент видит только свои ответы
                submissions = obj.submissions.filter(student=request.user)
            else:
                # Преподаватели и тьюторы видят все ответы
                submissions = obj.submissions.all()
            return AssignmentSubmissionSerializer(submissions, many=True).data
        return []


class AssignmentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания задания
    T_ASSIGN_006: Added publish_at and close_at fields for scheduling
    T_ASN_001: Added comprehensive due date validation
    """
    class Meta:
        model = Assignment
        fields = (
            'title', 'description', 'instructions', 'type', 'status',
            'max_score', 'time_limit', 'attempts_limit', 'assigned_to',
            'start_date', 'due_date', 'tags', 'difficulty_level',
            'publish_at', 'close_at', 'allow_late_submission',
            'late_submission_deadline', 'late_penalty_type',
            'late_penalty_value', 'penalty_frequency', 'max_penalty'
        )

    def validate_due_date(self, value):
        """T_ASN_001: Validate due date"""
        try:
            DueDateValidator.validate_due_date(value, timezone.now())
        except serializers.ValidationError:
            raise
        return value

    def validate(self, data):
        """T_ASN_001: Validate soft deadlines and scheduling dates"""
        # T_ASSIGN_006: Validate that close_at is after publish_at if both are provided
        if data.get('publish_at') and data.get('close_at'):
            if data['close_at'] <= data['publish_at']:
                raise serializers.ValidationError({
                    'close_at': 'Дата закрытия должна быть позже даты публикации'
                })

        # T_ASN_001: Validate soft deadlines (due_date and late_submission_deadline)
        due_date = data.get('due_date')
        extension_deadline = data.get('late_submission_deadline')

        if due_date:
            try:
                DueDateValidator.validate_soft_deadlines(due_date, extension_deadline)
            except serializers.ValidationError as e:
                # Merge validation errors
                if isinstance(e.detail, dict):
                    raise serializers.ValidationError(e.detail)
                raise

        return data

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class AssignmentQuestionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вопросов в заданиях
    T_ASN_002: Question ordering support
    """
    class Meta:
        model = AssignmentQuestion
        fields = (
            'id', 'assignment', 'question_text', 'question_type',
            'points', 'order', 'options', 'correct_answer', 'randomize_options',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')


class AssignmentQuestionUpdateOrderSerializer(serializers.ModelSerializer):
    """
    T_ASN_002: Serializer for updating question order
    Validates unique ordering per assignment
    """
    class Meta:
        model = AssignmentQuestion
        fields = ('id', 'order')

    def validate(self, data):
        """Validate unique order per assignment"""
        assignment = self.instance.assignment
        new_order = data.get('order', self.instance.order)

        # Check if this order is already taken by another question
        existing = AssignmentQuestion.objects.filter(
            assignment=assignment,
            order=new_order
        ).exclude(id=self.instance.id).exists()

        if existing:
            raise serializers.ValidationError({
                'order': f'Order {new_order} is already used in this assignment'
            })

        return data


class QuestionReorderSerializer(serializers.Serializer):
    """
    T_ASN_002: Serializer for bulk reordering questions
    Accepts list of {id, order} objects
    """
    questions = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
            required=True
        )
    )

    def validate_questions(self, value):
        """Validate that all questions exist and belong to same assignment"""
        if not value:
            raise serializers.ValidationError('Questions list cannot be empty')

        # Extract IDs and validate they exist
        question_ids = [q.get('id') for q in value]
        questions = AssignmentQuestion.objects.filter(id__in=question_ids)

        if len(questions) != len(question_ids):
            raise serializers.ValidationError('Some questions do not exist')

        # Check all questions belong to same assignment
        assignments = set(q.assignment_id for q in questions)
        if len(assignments) > 1:
            raise serializers.ValidationError('All questions must belong to same assignment')

        # Validate orders are unique
        orders = [q.get('order') for q in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError('Order values must be unique')

        # Validate order values are in valid range
        for q in value:
            order = q.get('order')
            if order < 0 or order > 1000:
                raise serializers.ValidationError('Order must be between 0 and 1000')

        return value


class AssignmentAnswerSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответов на вопросы
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = AssignmentAnswer
        fields = (
            'id', 'submission', 'question', 'question_text', 'answer_text',
            'answer_choice', 'is_correct', 'points_earned'
        )


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответов на задания
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    percentage = serializers.FloatField(read_only=True)
    answers = AssignmentAnswerSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AssignmentSubmission
        fields = (
            'id', 'assignment', 'assignment_title', 'student', 'student_name',
            'content', 'file', 'file_url', 'status', 'score', 'max_score', 'percentage',
            'feedback', 'submitted_at', 'graded_at', 'updated_at', 'answers'
        )
        read_only_fields = ('id', 'submitted_at', 'graded_at', 'updated_at')
    
    def get_file_url(self, obj):
        """Возвращает абсолютный URL файла"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)


class AssignmentSubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания ответа на задание
    """
    answers = AssignmentAnswerSerializer(many=True, required=False)
    
    class Meta:
        model = AssignmentSubmission
        fields = (
            'assignment', 'content', 'file', 'answers'
        )
    
    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        submission = super().create(validated_data)
        
        # Создаем ответы на вопросы
        for answer_data in answers_data:
            AssignmentAnswer.objects.create(
                submission=submission,
                **answer_data
            )
        
        return submission


class AssignmentGradingSerializer(serializers.ModelSerializer):
    """
    Сериализатор для оценки заданий
    """
    class Meta:
        model = AssignmentSubmission
        fields = ('score', 'feedback', 'status')

    def update(self, instance, validated_data):
        from django.utils import timezone

        if validated_data.get('score') is not None:
            validated_data['graded_at'] = timezone.now()
            validated_data['status'] = AssignmentSubmission.Status.GRADED

        return super().update(instance, validated_data)


class PeerReviewSerializer(serializers.ModelSerializer):
    """
    T_ASSIGN_005: Serializer for peer reviews.

    Shows review details including score, feedback, and optional rubric scores.
    Includes reviewer information (respects anonymity settings).
    """
    reviewer_name = serializers.SerializerMethodField()
    reviewer_id = serializers.SerializerMethodField()
    is_anonymous = serializers.SerializerMethodField()

    class Meta:
        model = PeerReview
        fields = (
            'id', 'peer_assignment', 'score', 'feedback_text', 'rubric_scores',
            'reviewer_name', 'reviewer_id', 'is_anonymous', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_reviewer_name(self, obj):
        """Return reviewer name if not anonymous"""
        if obj.peer_assignment.is_anonymous:
            return "Anonymous"
        return obj.peer_assignment.reviewer.get_full_name()

    def get_reviewer_id(self, obj):
        """Return reviewer ID if not anonymous"""
        if obj.peer_assignment.is_anonymous:
            return None
        return obj.peer_assignment.reviewer.id

    def get_is_anonymous(self, obj):
        return obj.peer_assignment.is_anonymous


class PeerReviewCreateSerializer(serializers.Serializer):
    """
    T_ASSIGN_005: Serializer for creating peer reviews.

    Accepts score, feedback, and optional rubric scores.
    """
    score = serializers.IntegerField(min_value=0, max_value=100)
    feedback_text = serializers.CharField(max_length=5000)
    rubric_scores = serializers.JSONField(required=False, default=dict)

    def validate_feedback_text(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Feedback cannot be empty")
        return value


class PeerReviewAssignmentSerializer(serializers.ModelSerializer):
    """
    T_ASSIGN_005: Serializer for peer review assignments.

    Shows assignment details, deadline, status, and nested review if completed.
    """
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    student_name = serializers.CharField(source='submission.student.get_full_name', read_only=True)
    submission_id = serializers.IntegerField(source='submission.id', read_only=True)
    assignment_title = serializers.CharField(source='submission.assignment.title', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    review = PeerReviewSerializer(read_only=True)

    class Meta:
        model = PeerReviewAssignment
        fields = (
            'id', 'submission_id', 'reviewer', 'reviewer_name', 'student_name',
            'assignment_title', 'assignment_type', 'status', 'deadline',
            'is_anonymous', 'is_overdue', 'created_at', 'updated_at', 'review'
        )
        read_only_fields = (
            'id', 'submission_id', 'assignment_type', 'created_at', 'updated_at'
        )


class PeerReviewAssignmentListSerializer(serializers.ModelSerializer):
    """
    T_ASSIGN_005: Simplified serializer for listing peer review assignments.
    """
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    student_name = serializers.CharField(source='submission.student.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='submission.assignment.title', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = PeerReviewAssignment
        fields = (
            'id', 'reviewer_name', 'student_name', 'assignment_title',
            'status', 'deadline', 'is_overdue', 'has_review', 'created_at'
        )

    def get_has_review(self, obj):
        return hasattr(obj, 'review') and obj.review is not None


# T_ASSIGN_011: Bulk Grading Serializers

class BulkGradeItemSerializer(serializers.Serializer):
    """
    Serializer for individual grade items in bulk operation.
    
    Fields:
        submission_id: ID of the submission to grade
        score: Score to assign (optional)
        feedback: Feedback text (optional)
    """
    submission_id = serializers.IntegerField()
    score = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    feedback = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000
    )


class BulkGradeSerializer(serializers.Serializer):
    """
    Serializer for bulk grading request.
    
    T_ASSIGN_011: Bulk grading with validation and transaction safety.
    
    Fields:
        grades: List of BulkGradeItemSerializer objects
        rubric_id: Optional grading rubric ID
        transaction_mode: 'atomic' (all-or-nothing) or 'partial' (skip failed)
    
    Example request:
    {
        "grades": [
            {"submission_id": 1, "score": 85, "feedback": "Good work"},
            {"submission_id": 2, "score": 92, "feedback": "Excellent"}
        ],
        "rubric_id": 5,
        "transaction_mode": "atomic"
    }
    """
    grades = BulkGradeItemSerializer(many=True)
    rubric_id = serializers.IntegerField(required=False, allow_null=True)
    transaction_mode = serializers.ChoiceField(
        choices=['atomic', 'partial'],
        default='atomic'
    )

    def validate_grades(self, value):
        """Validate grades list is not empty"""
        if not value:
            raise serializers.ValidationError("At least one grade entry is required")
        return value


class BulkGradeDetailSerializer(serializers.Serializer):
    """
    Serializer for bulk grade operation result detail item.
    
    Fields:
        submission_id: ID of the submission
        score: Score assigned (if successful)
        status: 'success' or 'failed'
        error: Error message (if failed)
    """
    submission_id = serializers.IntegerField()
    score = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    status = serializers.CharField()
    error = serializers.CharField(required=False, allow_null=True)


class BulkGradeResultSerializer(serializers.Serializer):
    """
    Serializer for bulk grading response.
    
    T_ASSIGN_011: Results of bulk grading operation.
    
    Fields:
        success: Whether operation completed successfully
        created: Number of successfully graded submissions
        failed: Number of failed gradings
        errors: List of validation/operation errors
        details: Detailed result for each submission
    
    Example response:
    {
        "success": true,
        "created": 5,
        "failed": 0,
        "errors": [],
        "details": [
            {"submission_id": 1, "score": 85.0, "status": "success"},
            {"submission_id": 2, "score": 92.0, "status": "success"},
            ...
        ]
    }
    """
    success = serializers.BooleanField()
    created = serializers.IntegerField()
    failed = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())
    details = BulkGradeDetailSerializer(many=True)


class CSVGradeImportSerializer(serializers.Serializer):
    """
    Serializer for CSV grade import.
    
    T_ASSIGN_011: Import grades from CSV file.
    
    Fields:
        csv_file: CSV file upload
        transaction_mode: 'atomic' or 'partial'
    
    CSV format:
    submission_id,score,feedback
    1,85,Good work
    2,92,Excellent
    """
    csv_file = serializers.FileField()
    transaction_mode = serializers.ChoiceField(
        choices=['atomic', 'partial'],
        default='atomic'
    )

    def validate_csv_file(self, value):
        """Validate CSV file is uploaded and has correct extension"""
        if not value.name.lower().endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV file")
        
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must not exceed 5MB")
        
        return value


class BulkGradeStatsSerializer(serializers.Serializer):
    """
    Serializer for bulk grading statistics.
    
    T_ASSIGN_011: Statistics about submissions for bulk grading.
    
    Fields:
        total_submissions: Total number of submissions
        graded_count: Number of graded submissions
        ungraded_count: Number of ungraded submissions
        pending_count: Number of pending submissions
        average_score: Average score of graded submissions
    """
    total_submissions = serializers.IntegerField()
    graded_count = serializers.IntegerField()
    ungraded_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)


class PlagiarismReportSerializer(serializers.ModelSerializer):
    """
    T_ASSIGN_014: Serializer for plagiarism detection reports.

    Student view: Only status and general score (no source details)
    Teacher view: Full details including sources and service info
    """
    processing_time_seconds = serializers.SerializerMethodField()
    is_high_similarity = serializers.BooleanField(read_only=True)

    class Meta:
        model = PlagiarismReport
        fields = (
            'id', 'submission', 'similarity_score', 'detection_status',
            'service', 'service_report_id', 'error_message',
            'is_high_similarity', 'processing_time_seconds',
            'created_at', 'checked_at'
        )
        read_only_fields = (
            'id', 'submission', 'similarity_score', 'detection_status',
            'service', 'service_report_id', 'error_message',
            'is_high_similarity', 'created_at', 'checked_at'
        )

    def get_processing_time_seconds(self, obj):
        """Get processing time in seconds"""
        return obj.processing_time_seconds

    def to_representation(self, instance):
        """
        Customize response based on user role.

        Students: Hide sources and service details
        Teachers: Show full details
        """
        data = super().to_representation(instance)
        request = self.context.get('request')

        # Only teachers/tutors can see full details including sources
        if request and request.user and request.user.role not in ['teacher', 'tutor']:
            # For students, remove service details and sources
            data.pop('service_report_id', None)
            data.pop('error_message', None)
            # Redact sources from response
            if hasattr(instance, 'sources'):
                data['sources_found'] = len(instance.sources)
            else:
                data['sources_found'] = 0
        else:
            # Teachers see everything
            if hasattr(instance, 'sources') and instance.sources:
                data['sources'] = instance.sources

        return data


class PlagiarismReportDetailSerializer(serializers.ModelSerializer):
    """
    T_ASSIGN_014: Detailed plagiarism report (teacher-only view).

    Includes full source details, error messages, and service information.
    Used for teacher review of plagiarism findings.
    """
    student_name = serializers.CharField(
        source='submission.student.get_full_name', read_only=True
    )
    assignment_title = serializers.CharField(
        source='submission.assignment.title', read_only=True
    )
    processing_time_seconds = serializers.SerializerMethodField()
    sources_count = serializers.SerializerMethodField()

    class Meta:
        model = PlagiarismReport
        fields = (
            'id', 'submission', 'student_name', 'assignment_title',
            'similarity_score', 'detection_status', 'sources',
            'service', 'service_report_id', 'error_message',
            'is_high_similarity', 'sources_count',
            'processing_time_seconds', 'created_at', 'checked_at'
        )
        read_only_fields = (
            'id', 'submission', 'student_name', 'assignment_title',
            'similarity_score', 'detection_status', 'sources',
            'service', 'service_report_id', 'error_message',
            'is_high_similarity', 'created_at', 'checked_at'
        )

    def get_processing_time_seconds(self, obj):
        return obj.processing_time_seconds

    def get_sources_count(self, obj):
        return len(obj.sources) if obj.sources else 0


class AssignmentAttemptListSerializer(serializers.ModelSerializer):
    """
    T_ASN_003: Serializer for listing assignment attempts.
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentAttempt
        fields = (
            'id', 'attempt_number', 'score', 'max_score', 'percentage',
            'status', 'student', 'student_name', 'assignment', 'assignment_title',
            'submitted_at', 'graded_at', 'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_percentage(self, obj):
        return obj.percentage


class AssignmentAttemptDetailSerializer(serializers.ModelSerializer):
    """
    T_ASN_003: Detailed serializer for individual assignment attempts.
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_max_score = serializers.IntegerField(source='assignment.max_score', read_only=True)
    percentage = serializers.SerializerMethodField()
    is_graded = serializers.BooleanField(read_only=True)

    class Meta:
        model = AssignmentAttempt
        fields = (
            'id', 'submission', 'assignment', 'assignment_title', 'assignment_max_score',
            'student', 'student_name', 'attempt_number', 'score', 'max_score',
            'percentage', 'status', 'feedback', 'content', 'file',
            'submitted_at', 'graded_at', 'is_graded', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'submission', 'student', 'attempt_number', 'created_at', 'updated_at')

    def get_percentage(self, obj):
        return obj.percentage


class AssignmentAttemptCreateSerializer(serializers.ModelSerializer):
    """
    T_ASN_003: Serializer for creating new assignment attempts.
    """
    class Meta:
        model = AssignmentAttempt
        fields = ('content', 'file')
        extra_kwargs = {
            'content': {'required': True},
            'file': {'required': False}
        }


class AssignmentAttemptGradeSerializer(serializers.ModelSerializer):
    """
    T_ASN_003: Serializer for grading assignment attempts.
    """
    class Meta:
        model = AssignmentAttempt
        fields = ('score', 'feedback', 'status')
        extra_kwargs = {
            'score': {'required': True},
            'feedback': {'required': False},
            'status': {'required': False}
        }


# T_ASN_006: Assignment Rubric Support Serializers
# ==================================================

class RubricCriterionSerializer(serializers.ModelSerializer):
    """
    T_ASN_006: Serializer for rubric criteria.

    Serializes individual criteria within a rubric with their scoring scales.
    """

    class Meta:
        model = RubricCriterion
        fields = [
            'id', 'rubric', 'name', 'description', 'max_points',
            'point_scales', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_point_scales(self, value):
        """Validate point scales format and values."""
        if not isinstance(value, list):
            raise serializers.ValidationError(
                'Шкала оценивания должна быть списком'
            )

        if not value:
            raise serializers.ValidationError(
                'Шкала оценивания не может быть пустой'
            )

        max_points = self.initial_data.get('max_points', 0)

        for scale_entry in value:
            if not isinstance(scale_entry, (list, tuple)) or len(scale_entry) != 2:
                raise serializers.ValidationError(
                    'Каждая запись должна быть [баллы, описание]'
                )

            points, description = scale_entry

            if not isinstance(points, (int, float)):
                raise serializers.ValidationError(
                    'Баллы должны быть числом'
                )

            if points > max_points:
                raise serializers.ValidationError(
                    f'Баллы ({points}) не могут быть больше максимума ({max_points})'
                )

            if not description or not str(description).strip():
                raise serializers.ValidationError(
                    'Описание уровня не может быть пустым'
                )

        return value


class GradingRubricListSerializer(serializers.ModelSerializer):
    """
    T_ASN_006: Serializer for listing grading rubrics.

    Returns a simplified view of rubrics for list endpoints.
    """

    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    criteria_count = serializers.SerializerMethodField()

    class Meta:
        model = GradingRubric
        fields = [
            'id', 'name', 'created_by', 'created_by_name', 'is_template',
            'total_points', 'criteria_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_criteria_count(self, obj):
        return obj.criteria.count()


class GradingRubricDetailSerializer(serializers.ModelSerializer):
    """
    T_ASN_006: Serializer for detailed rubric view.

    Includes all criteria and full rubric information.
    """

    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = GradingRubric
        fields = [
            'id', 'name', 'description', 'created_by', 'created_by_name',
            'is_template', 'total_points', 'criteria', 'is_deleted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GradingRubricCreateSerializer(serializers.ModelSerializer):
    """
    T_ASN_006: Serializer for creating rubrics.

    Validates all fields and creates the rubric. Criteria are managed separately.
    """

    criteria = RubricCriterionSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = GradingRubric
        fields = [
            'id', 'name', 'description', 'is_template', 'total_points', 'criteria'
        ]
        read_only_fields = ['id']

    def validate_name(self, value):
        """Ensure name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError('Название рубрики не может быть пустым')
        return value.strip()

    def validate_total_points(self, value):
        """Ensure total points is positive."""
        if value <= 0:
            raise serializers.ValidationError('Всего баллов должно быть больше 0')
        return value

    def create(self, validated_data):
        """Create rubric and criteria."""
        criteria_data = validated_data.pop('criteria', [])

        # Create rubric
        rubric = GradingRubric.objects.create(
            **validated_data
        )

        # Create criteria
        for criterion_data in criteria_data:
            criterion_data['rubric'] = rubric
            RubricCriterion.objects.create(**criterion_data)

        return rubric


class RubricScoreSerializer(serializers.ModelSerializer):
    """
    T_ASN_006: Serializer for rubric scores assigned during grading.

    Stores scores for each criterion when grading with a rubric.
    """

    criterion_name = serializers.CharField(
        source='criterion.name',
        read_only=True
    )

    class Meta:
        model = RubricScore
        fields = [
            'id', 'submission', 'criterion', 'criterion_name', 'score',
            'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_score(self, value):
        """Validate score is not negative."""
        if value < 0:
            raise serializers.ValidationError('Баллы не могут быть отрицательными')
        return value


class AssignmentCloneSerializer(serializers.Serializer):
    """
    T_ASN_008: Serializer for cloning assignments.

    Handles clone request parameters and returns cloned assignment data.
    """
    new_title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=False,
        help_text='New title for cloned assignment (default: "Copy of {original_title}")'
    )
    new_due_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='New due date for cloned assignment (default: same as original)'
    )
    randomize_questions = serializers.BooleanField(
        default=False,
        help_text='Whether to randomize question order and options'
    )

    def validate_new_title(self, value):
        """Validate new title."""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError('Title cannot be empty or whitespace only')
        return value

    def validate_new_due_date(self, value):
        """Validate new due date is in the future."""
        if value:
            from django.utils import timezone
            if value < timezone.now():
                raise serializers.ValidationError('Due date cannot be in the past')
        return value

    def validate(self, data):
        """Additional validation."""
        # Both fields are optional, just validate their individual constraints
        return data


class AssignmentCloneResponseSerializer(serializers.ModelSerializer):
    """
    T_ASN_008: Serializer for clone response.

    Returns the cloned assignment with all relevant data.
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    questions_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assignment
        fields = (
            'id', 'title', 'description', 'instructions', 'author', 'author_name',
            'type', 'status', 'max_score', 'time_limit', 'attempts_limit',
            'start_date', 'due_date', 'tags', 'difficulty_level',
            'created_at', 'updated_at', 'questions_count', 'is_overdue',
            'rubric', 'allow_late_submission'
        )

    def get_questions_count(self, obj):
        return obj.questions.count()


# T_ASN_007: Late Submission and Deadline Extension Serializers
# ===============================================================

class SubmissionExemptionSerializer(serializers.ModelSerializer):
    """
    Serializer for submission exemptions from late penalties.

    Fields:
        id: Exemption ID
        submission: Submission ID
        exemption_type: Type of exemption (full or custom_rate)
        custom_penalty_rate: Custom penalty rate if applicable
        reason: Reason for exemption
        exemption_created_by: User who created exemption
        created_at: When exemption was created
    """

    exemption_created_by_name = serializers.CharField(
        source='exemption_created_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = SubmissionExemption
        fields = (
            'id', 'submission', 'exemption_type', 'custom_penalty_rate',
            'reason', 'exemption_created_by', 'exemption_created_by_name',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')


class StudentDeadlineExtensionSerializer(serializers.ModelSerializer):
    """
    Serializer for student deadline extensions.

    Fields:
        id: Extension ID
        assignment: Assignment ID
        student: Student ID
        student_name: Student full name
        extended_deadline: New deadline
        reason: Reason for extension
        extended_by: User who granted extension
        extended_by_name: Name of user who granted extension
        created_at: When extension was created
    """

    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    extended_by_name = serializers.CharField(source='extended_by.get_full_name', read_only=True)

    class Meta:
        model = StudentDeadlineExtension
        fields = (
            'id', 'assignment', 'student', 'student_name', 'extended_deadline',
            'reason', 'extended_by', 'extended_by_name', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class LateSubmissionDetailSerializer(serializers.Serializer):
    """
    Serializer for late submission details with penalty information.

    Returns comprehensive information about a late submission including
    penalty calculation, exemption status, and deadline information.
    """

    submission_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    due_date = serializers.DateTimeField()
    is_late = serializers.BooleanField()
    days_late = serializers.DecimalField(max_digits=10, decimal_places=2)
    hours_late = serializers.DecimalField(max_digits=10, decimal_places=2)
    original_score = serializers.IntegerField(allow_null=True)
    penalty_applied = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    final_score = serializers.IntegerField(allow_null=True)
    is_exempt = serializers.BooleanField()
    exemption_type = serializers.CharField(allow_null=True)
    exemption_reason = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class LateSubmissionReportSerializer(serializers.Serializer):
    """
    Serializer for late submission report and analytics.

    Returns comprehensive statistics about late submissions for an assignment.
    """

    assignment_id = serializers.IntegerField()
    assignment_title = serializers.CharField()
    due_date = serializers.DateTimeField()

    # Summary statistics
    total_submissions = serializers.IntegerField()
    late_submissions = serializers.IntegerField()
    late_percentage = serializers.FloatField()
    on_time_submissions = serializers.IntegerField()
    on_time_percentage = serializers.FloatField()

    # Exemption statistics
    total_exemptions = serializers.IntegerField()
    full_exemptions = serializers.IntegerField()
    custom_rate_exemptions = serializers.IntegerField()

    # Distribution by time
    same_day = serializers.IntegerField()
    one_day = serializers.IntegerField()
    two_to_three_days = serializers.IntegerField()
    four_to_seven_days = serializers.IntegerField()
    one_to_two_weeks = serializers.IntegerField()
    over_two_weeks = serializers.IntegerField()

    # Penalty statistics
    total_penalties_applied = serializers.IntegerField()
    average_penalty = serializers.FloatField()


class AdjustPenaltyRequestSerializer(serializers.Serializer):
    """
    Serializer for penalty adjustment requests.

    Validates the action and required parameters for adjusting late penalties.
    """

    ACTIONS = [
        ('full_exemption', 'Full Exemption from Penalty'),
        ('custom_penalty', 'Custom Penalty Rate'),
        ('remove_exemption', 'Remove Exemption'),
    ]

    action = serializers.ChoiceField(choices=ACTIONS)
    custom_penalty_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    reason = serializers.CharField(max_length=500, required=False, default='Teacher override')

    def validate(self, data):
        """Validate action-specific requirements."""
        action = data.get('action')

        if action == 'custom_penalty':
            if 'custom_penalty_rate' not in data or data['custom_penalty_rate'] is None:
                raise serializers.ValidationError(
                    {'custom_penalty_rate': 'Required when action is custom_penalty'}
                )

            rate = data['custom_penalty_rate']
            if rate < 0 or rate > 100:
                raise serializers.ValidationError(
                    {'custom_penalty_rate': 'Rate must be between 0 and 100'}
                )

        return data


class ExtendDeadlineRequestSerializer(serializers.Serializer):
    """
    Serializer for deadline extension requests.

    Validates student IDs, new deadline, and reason.
    """

    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of student IDs to extend deadline for'
    )
    new_deadline = serializers.DateTimeField(
        help_text='New deadline in ISO format (e.g., 2025-12-31T23:59:59Z)'
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        default='Teacher extension',
        help_text='Reason for the extension'
    )

    def validate_student_ids(self, value):
        """Validate that student_ids list is not empty."""
        if not value:
            raise serializers.ValidationError('At least one student ID required')
        return value

    def validate_new_deadline(self, value):
        """Validate that new deadline is in the future."""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError('New deadline must be in the future')
        return value
