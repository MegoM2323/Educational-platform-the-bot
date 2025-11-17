from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer

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
            'difficulty_level', 'tags', 'created_at', 'is_overdue', 'submission'
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
            'questions', 'submissions', 'is_overdue'
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
    """
    class Meta:
        model = Assignment
        fields = (
            'title', 'description', 'instructions', 'type', 'status',
            'max_score', 'time_limit', 'attempts_limit', 'assigned_to',
            'start_date', 'due_date', 'tags', 'difficulty_level'
        )
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class AssignmentQuestionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вопросов в заданиях
    """
    class Meta:
        model = AssignmentQuestion
        fields = (
            'id', 'assignment', 'question_text', 'question_type',
            'points', 'order', 'options', 'correct_answer'
        )


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
