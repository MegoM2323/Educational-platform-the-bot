from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class Assignment(models.Model):
    """
    Задания для студентов
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"
        CLOSED = "closed", "Закрыто"

    class Type(models.TextChoices):
        HOMEWORK = "homework", "Домашнее задание"
        TEST = "test", "Тест"
        PROJECT = "project", "Проект"
        ESSAY = "essay", "Эссе"
        PRACTICAL = "practical", "Практическая работа"

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    instructions = models.TextField(verbose_name="Инструкции")

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_assignments", verbose_name="Автор"
    )

    type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.HOMEWORK, verbose_name="Тип"
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="Статус"
    )

    # Настройки задания
    max_score = models.PositiveIntegerField(default=100, verbose_name="Максимальный балл")

    time_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Время выполнения в минутах",
        verbose_name="Временной лимит",
    )

    attempts_limit = models.PositiveIntegerField(default=1, verbose_name="Лимит попыток")

    # Назначение
    assigned_to = models.ManyToManyField(
        User, related_name="assigned_assignments", blank=True, verbose_name="Назначено"
    )

    # Временные рамки
    start_date = models.DateTimeField(verbose_name="Дата начала")
    due_date = models.DateTimeField(
        verbose_name="Срок сдачи", help_text="Основная дата сдачи задания"
    )

    # Метаданные
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги")
    difficulty_level = models.PositiveIntegerField(
        default=1,
        choices=[(i, f"Уровень {i}") for i in range(1, 6)],
        verbose_name="Уровень сложности",
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # T_ASSIGN_012: Late submission policy fields
    late_submission_deadline = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Крайний срок для поздней сдачи",
        help_text="Если установлено, позволяет сдавать только до этого времени",
    )

    late_penalty_type = models.CharField(
        max_length=20,
        choices=[
            ("percentage", "Процент от балла"),
            ("fixed_points", "Фиксированное количество баллов"),
        ],
        default="percentage",
        verbose_name="Тип штрафа за позднюю сдачу",
        help_text="Как считается штраф за позднюю сдачу",
    )

    late_penalty_value = models.DecimalField(
        default=0,
        decimal_places=2,
        max_digits=5,
        verbose_name="Значение штрафа за позднюю сдачу",
        help_text="Процент или количество баллов, на которые снижается оценка за каждую единицу времени",
    )

    penalty_frequency = models.CharField(
        max_length=20,
        choices=[
            ("per_day", "За каждый день"),
            ("per_hour", "За каждый час"),
        ],
        default="per_day",
        verbose_name="Частота штрафа",
        help_text="Как часто применяется штраф (в день или в час)",
    )

    max_penalty = models.DecimalField(
        default=50,
        decimal_places=2,
        max_digits=5,
        verbose_name="Максимальный штраф",
        help_text="Максимальный процент от балла, который можно потерять из-за позднего сдачи",
    )

    allow_late_submission = models.BooleanField(
        default=True,
        verbose_name="Разрешить поздние сдачи",
        help_text="Если включено, студенты могут сдать задание после срока",
    )

    # T_ASN_006: Rubric for structured grading
    rubric = models.ForeignKey(
        "GradingRubric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
        verbose_name="Рубрика оценивания",
        help_text="Опциональная рубрика для структурированного оценивания",
    )

    # T_ASSIGN_001: Answer visibility - show correct answers to students after deadline
    show_correct_answers = models.BooleanField(
        default=False,
        verbose_name="Показать правильные ответы",
        help_text="Разрешить студентам видеть правильные ответы после срока выполнения",
    )

    class Meta:
        verbose_name = "Задание"
        verbose_name_plural = "Задания"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        from django.utils import timezone

        return timezone.now() > self.due_date

    def clone(self, cloner, new_title=None, new_due_date=None, randomize_questions=False):
        """
        Clone this assignment with all related questions and options.

        Args:
            cloner: User who is cloning the assignment
            new_title: Optional new title for cloned assignment (default: "Copy of {original_title}")
            new_due_date: Optional new due date (default: same as original)
            randomize_questions: Whether to randomize question order in cloned assignment

        Returns:
            New Assignment instance (unsaved, caller must save)

        Raises:
            PermissionError: If cloner is not the assignment creator
        """
        if self.author != cloner:
            raise PermissionError("Only the assignment creator can clone it")

        from django.db import transaction
        from django.utils import timezone
        import copy

        with transaction.atomic():
            # Create new assignment instance with cloned data
            cloned_assignment = Assignment.objects.get(pk=self.pk)
            cloned_assignment.pk = None
            cloned_assignment.id = None
            cloned_assignment.title = new_title or f"Copy of {self.title}"
            cloned_assignment.author = cloner
            cloned_assignment.status = Assignment.Status.DRAFT
            cloned_assignment.created_at = timezone.now()
            cloned_assignment.updated_at = timezone.now()

            if new_due_date:
                cloned_assignment.due_date = new_due_date

            cloned_assignment.save()

            # Clone all questions
            questions_map = {}  # Map original question ID to cloned question
            for original_question in self.questions.all():
                cloned_question = AssignmentQuestion.objects.get(pk=original_question.pk)
                cloned_question.pk = None
                cloned_question.id = None
                cloned_question.assignment = cloned_assignment

                # If randomizing, shuffle the options
                if randomize_questions and cloned_question.options:
                    import random

                    options_copy = copy.deepcopy(cloned_question.options)
                    random.shuffle(options_copy)
                    cloned_question.options = options_copy

                cloned_question.save()
                questions_map[original_question.id] = cloned_question

            # Clone rubric reference if exists
            if self.rubric:
                cloned_assignment.rubric = self.rubric
                cloned_assignment.save()

            return cloned_assignment


class AssignmentSubmission(models.Model):
    """
    Ответы студентов на задания
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Сдано"
        GRADED = "graded", "Оценено"
        RETURNED = "returned", "Возвращено на доработку"

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="submissions", verbose_name="Задание"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
        verbose_name="Студент",
    )

    content = models.TextField(verbose_name="Ответ")

    # Файлы
    file = models.FileField(
        upload_to="assignments/submissions/", blank=True, null=True, verbose_name="Файл"
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED, verbose_name="Статус"
    )

    # T066/T_ASSIGN_012: Track late submissions
    is_late = models.BooleanField(default=False, verbose_name="Поздняя сдача")

    # T_ASSIGN_012: Track days late for penalty calculation
    days_late = models.DecimalField(
        default=0,
        decimal_places=2,
        max_digits=10,
        verbose_name="Дней с опозданием",
        help_text="Количество дней/часов просрочки для расчета штрафа",
    )

    # T_ASSIGN_012: Track if penalty was applied
    penalty_applied = models.DecimalField(
        blank=True,
        null=True,
        decimal_places=2,
        max_digits=5,
        verbose_name="Примененный штраф",
        help_text="Размер штрафа, примененный к оценке",
    )

    # Оценка
    score = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(0)], verbose_name="Балл"
    )

    max_score = models.PositiveIntegerField(blank=True, null=True, verbose_name="Максимальный балл")

    feedback = models.TextField(blank=True, verbose_name="Комментарий преподавателя")

    # Временные метки
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ответ на задание"
        verbose_name_plural = "Ответы на задания"
        unique_together = ["assignment", "student"]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment}"

    @property
    def percentage(self):
        if self.max_score and self.score is not None:
            return round((self.score / self.max_score) * 100, 2)
        return None


class AssignmentQuestion(models.Model):
    """
    Вопросы в заданиях (для тестов)
    T_ASN_002: Assignment Question Order - Question ordering, randomization support
    """

    class Type(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Один вариант"
        MULTIPLE_CHOICE = "multiple_choice", "Несколько вариантов"
        TEXT = "text", "Текстовый ответ"
        NUMBER = "number", "Числовой ответ"

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="questions", verbose_name="Задание"
    )

    question_text = models.TextField(verbose_name="Текст вопроса")
    question_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.SINGLE_CHOICE, verbose_name="Тип вопроса"
    )

    points = models.PositiveIntegerField(default=1, verbose_name="Баллы")

    # T_ASN_002: Order field (0-1000, unique per assignment)
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок",
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
    )

    # For questions with answer options
    options = models.JSONField(default=list, blank=True, verbose_name="Варианты ответов")

    correct_answer = models.JSONField(default=dict, blank=True, verbose_name="Правильный ответ")

    # T_ASN_002: Support randomization per student
    randomize_options = models.BooleanField(
        default=False,
        verbose_name="Randomize answer options",
        help_text="If enabled, answer options will be randomized per student",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ["order"]
        # T_ASN_002: Unique ordering per assignment
        unique_together = [["assignment", "order"]]
        indexes = [
            models.Index(fields=["assignment", "order"], name="question_assignment_order_idx"),
            models.Index(fields=["assignment", "randomize_options"], name="question_randomize_idx"),
        ]

    def __str__(self):
        return f"{self.assignment.title} - Вопрос {self.order}"


class AssignmentAnswer(models.Model):
    """
    Ответы студентов на вопросы
    """

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Ответ на задание",
    )

    question = models.ForeignKey(
        AssignmentQuestion, on_delete=models.CASCADE, related_name="answers", verbose_name="Вопрос"
    )

    answer_text = models.TextField(blank=True, verbose_name="Текстовый ответ")
    answer_choice = models.JSONField(default=list, blank=True, verbose_name="Выбранные варианты")

    is_correct = models.BooleanField(default=False, verbose_name="Правильный")
    points_earned = models.PositiveIntegerField(default=0, verbose_name="Заработанные баллы")

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"
        unique_together = ["submission", "question"]

    def __str__(self):
        return f"{self.submission.student} - {self.question.question_text[:50]}"


class SubmissionExemption(models.Model):
    """
    T_ASSIGN_012: Exemption from late submission penalties.

    Allows teachers/tutors to exempt specific students from late submission
    penalties (e.g., due to medical/personal reasons).

    Fields:
        submission: The submission that is exempt from penalties
        exemption_type: Type of exemption (full, partial with custom rate)
        reason: Reason for the exemption
        exemption_created_by: User (teacher/tutor) who created the exemption
        created_at: When the exemption was created
    """

    class ExemptionType(models.TextChoices):
        FULL = "full", "Полное - без штрафа"
        CUSTOM_RATE = "custom_rate", "Пользовательская ставка"

    submission = models.OneToOneField(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="exemption",
        verbose_name="Ответ на задание",
    )

    exemption_type = models.CharField(
        max_length=20,
        choices=ExemptionType.choices,
        default=ExemptionType.FULL,
        verbose_name="Тип освобождения",
    )

    # For custom_rate exemption type
    custom_penalty_rate = models.DecimalField(
        blank=True,
        null=True,
        decimal_places=2,
        max_digits=5,
        verbose_name="Пользовательская ставка штрафа",
        help_text="Используется вместо стандартной ставки если exemption_type='custom_rate'",
    )

    reason = models.TextField(
        verbose_name="Причина освобождения", help_text="Объяснение причины освобождения от штрафа"
    )

    exemption_created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_exemptions", verbose_name="Создано"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Освобождение от штрафа"
        verbose_name_plural = "Освобождения от штрафа"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["submission", "exemption_type"], name="exemption_submission_type_idx"
            ),
            models.Index(
                fields=["exemption_created_by", "-created_at"], name="exemption_creator_date_idx"
            ),
        ]

    def __str__(self):
        return f"Exemption: {self.submission.student} - {self.submission.assignment.title}"


class PeerReviewAssignment(models.Model):
    """
    T_ASSIGN_005: Tracks which student reviews which submission.

    Enables peer review functionality by assigning reviewers to submissions.
    Supports both random assignment and manual assignment of peer reviewers.

    Fields:
        submission: The submission being reviewed
        reviewer: The student who reviews the submission
        assignment_type: How the reviewer was assigned (random, manual, automatic)
        status: Current status of the review (pending, in_progress, completed, skipped)
        deadline: When the review must be completed
        created_at: When the assignment was created
        updated_at: When the assignment was last updated
    """

    class AssignmentType(models.TextChoices):
        RANDOM = "random", "Random Assignment"
        MANUAL = "manual", "Manual Assignment"
        AUTOMATIC = "automatic", "Automatic Assignment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="peer_review_assignments",
        verbose_name="Submission to review",
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="peer_reviews_assigned",
        verbose_name="Reviewer",
    )

    assignment_type = models.CharField(
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.RANDOM,
        verbose_name="Assignment Type",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Status"
    )

    deadline = models.DateTimeField(
        verbose_name="Review Deadline", help_text="When the review must be completed"
    )

    is_anonymous = models.BooleanField(
        default=False,
        verbose_name="Anonymous Review",
        help_text="Hide reviewer identity from the student being reviewed",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Peer Review Assignment"
        verbose_name_plural = "Peer Review Assignments"
        unique_together = ["submission", "reviewer"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["submission", "status"], name="pr_submission_status_idx"),
            models.Index(fields=["reviewer", "status"], name="pr_reviewer_status_idx"),
            models.Index(fields=["deadline"], name="pr_deadline_idx"),
        ]

    def __str__(self):
        return (
            f"Review: {self.reviewer.get_full_name()} -> {self.submission.student.get_full_name()}"
        )

    @property
    def is_overdue(self):
        from django.utils import timezone

        return self.status != self.Status.COMPLETED and timezone.now() > self.deadline


class PeerReview(models.Model):
    """
    T_ASSIGN_005: Actual peer review data submitted by a reviewer.

    Stores the feedback and score from a peer reviewer for a submission.

    Fields:
        peer_assignment: Reference to the peer review assignment
        score: Numeric score given by the reviewer (0-100)
        feedback_text: Detailed feedback from the reviewer
        rubric_scores: JSON object storing scores for each rubric criterion (if rubric used)
        created_at: When the review was submitted
        updated_at: When the review was last modified
    """

    peer_assignment = models.OneToOneField(
        PeerReviewAssignment,
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name="Peer Review Assignment",
    )

    score = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score (0-100)",
        help_text="Score given by the peer reviewer",
    )

    feedback_text = models.TextField(
        verbose_name="Feedback", help_text="Detailed feedback from the peer reviewer"
    )

    rubric_scores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Rubric Scores",
        help_text="Scores for each rubric criterion in JSON format",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Peer Review"
        verbose_name_plural = "Peer Reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.peer_assignment.reviewer.get_full_name()}"

    @property
    def rubric_average(self):
        """Calculate average score from rubric criteria if available"""
        if not self.rubric_scores:
            return None
        scores = [v for v in self.rubric_scores.values() if isinstance(v, (int, float))]
        return round(sum(scores) / len(scores), 2) if scores else None


class PlagiarismReport(models.Model):
    """
    T_ASSIGN_014: Plagiarism detection report for a submission.

    Stores plagiarism detection results from external services (Turnitin, Copyscape).
    Includes similarity score, detected sources, and detection status.

    Fields:
        submission: The assignment submission being checked
        similarity_score: Percentage match (0-100%)
        detection_status: Current status (pending, processing, completed, failed)
        sources: JSON list of matched sources with URLs and match percentages
        service: Which plagiarism service was used (turnitin, copyscape, custom)
        service_report_id: External service's report ID for reference
        error_message: Error details if detection failed
        created_at: When the check was queued
        checked_at: When the check completed
    """

    class DetectionStatus(models.TextChoices):
        PENDING = "pending", "Pending - Not yet submitted"
        PROCESSING = "processing", "Processing - Awaiting results"
        COMPLETED = "completed", "Completed - Results available"
        FAILED = "failed", "Failed - Check could not complete"

    class PlagiarismService(models.TextChoices):
        TURNITIN = "turnitin", "Turnitin"
        COPYSCAPE = "copyscape", "Copyscape"
        CUSTOM = "custom", "Custom/Internal"

    submission = models.OneToOneField(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="plagiarism_report",
        verbose_name="Assignment Submission",
    )

    similarity_score = models.DecimalField(
        default=0,
        decimal_places=2,
        max_digits=5,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Similarity Score (%)",
    )

    detection_status = models.CharField(
        max_length=20,
        choices=DetectionStatus.choices,
        default=DetectionStatus.PENDING,
        verbose_name="Detection Status",
    )

    # JSON format: [{"source": "url", "match_percent": 15, "matched_text": "..."}]
    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Detected Sources",
        help_text="List of sources with matched content",
    )

    service = models.CharField(
        max_length=20,
        choices=PlagiarismService.choices,
        default=PlagiarismService.CUSTOM,
        verbose_name="Detection Service",
    )

    service_report_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="External Service Report ID",
        help_text="ID from external plagiarism service for reference",
    )

    error_message = models.TextField(
        blank=True, verbose_name="Error Message", help_text="Error details if detection failed"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Queued at")
    checked_at = models.DateTimeField(blank=True, null=True, verbose_name="Checked at")

    class Meta:
        verbose_name = "Plagiarism Report"
        verbose_name_plural = "Plagiarism Reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["submission", "detection_status"], name="plag_submission_status_idx"
            ),
            models.Index(fields=["detection_status", "-created_at"], name="plag_status_date_idx"),
        ]

    def __str__(self):
        return f"Plagiarism: {self.submission.student.get_full_name()} - {self.similarity_score}%"

    @property
    def is_high_similarity(self):
        """Check if similarity score exceeds threshold (30%)"""
        return self.similarity_score >= 30

    @property
    def processing_time_seconds(self):
        """Calculate time taken for plagiarism check in seconds"""
        if self.checked_at and self.created_at:
            delta = self.checked_at - self.created_at
            return delta.total_seconds()
        return None


# T_ASSIGN_010: Assignment History and Versioning Models
# ====================================================


class AssignmentHistory(models.Model):
    """
    Tracks all changes made to an Assignment.

    Fields:
        assignment: ForeignKey to the Assignment being tracked
        changed_by: User who made the change
        change_time: When the change was made
        changes_dict: JSON object containing the diff (fields changed and old/new values)
        change_summary: Human-readable summary of what changed
        fields_changed: JSON list of field names that were modified
    """

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="history", verbose_name="Assignment"
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_changes",
        verbose_name="Changed By",
    )

    change_time = models.DateTimeField(auto_now_add=True, verbose_name="Change Time")

    # JSON diff: {'field_name': {'old': old_value, 'new': new_value}}
    changes_dict = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Changes Dictionary",
        help_text="JSON object with field diffs: {field_name: {old: value, new: value}}",
    )

    change_summary = models.TextField(
        blank=True,
        verbose_name="Change Summary",
        help_text="Human-readable description of what changed",
    )

    # JSON list of field names changed
    fields_changed = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Fields Changed",
        help_text="List of field names that were modified",
    )

    class Meta:
        verbose_name = "Assignment History"
        verbose_name_plural = "Assignment Histories"
        ordering = ["-change_time"]
        indexes = [
            models.Index(fields=["assignment", "-change_time"]),
            models.Index(fields=["changed_by", "-change_time"]),
        ]

    def __str__(self):
        return f"{self.assignment.title} - {self.change_time.strftime('%Y-%m-%d %H:%M:%S')}"

    def get_field_change(self, field_name):
        """Get the old and new values for a specific field."""
        return self.changes_dict.get(field_name, {})


class SubmissionVersion(models.Model):
    """
    Tracks submission versions when resubmitting.

    Fields:
        submission: ForeignKey to the AssignmentSubmission
        version_number: Sequential version number (1, 2, 3, ...)
        file_path: Path to the submitted file (for this version)
        content: Content of the submission (for text-based)
        submitted_at: When this version was submitted
        is_final: Whether this is the final/current submission to be graded
        submitted_by: User who made this submission (usually the student)
    """

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Submission",
    )

    version_number = models.PositiveIntegerField(
        verbose_name="Version Number", help_text="Sequential version number (1, 2, 3, ...)"
    )

    # File content
    file = models.FileField(
        upload_to="assignments/submissions/versions/", blank=True, null=True, verbose_name="File"
    )

    # Text content
    content = models.TextField(blank=True, verbose_name="Content")

    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Submitted At")

    is_final = models.BooleanField(
        default=False, verbose_name="Is Final", help_text="This is the submission used for grading"
    )

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submission_versions",
        verbose_name="Submitted By",
    )

    # Link to previous version for version history traversal
    previous_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_version",
        verbose_name="Previous Version",
    )

    class Meta:
        verbose_name = "Submission Version"
        verbose_name_plural = "Submission Versions"
        ordering = ["version_number"]
        unique_together = ["submission", "version_number"]
        indexes = [
            models.Index(fields=["submission", "version_number"]),
            models.Index(fields=["is_final"]),
        ]

    def __str__(self):
        return f"{self.submission.student} - {self.submission.assignment.title} - v{self.version_number}"


class SubmissionVersionDiff(models.Model):
    """
    Stores pre-computed diffs between submission versions.

    Fields:
        version_a: First version being compared
        version_b: Second version being compared
        diff_content: JSON containing the diff
        created_at: When the diff was computed
    """

    version_a = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.CASCADE,
        related_name="diffs_as_a",
        verbose_name="Version A",
    )

    version_b = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.CASCADE,
        related_name="diffs_as_b",
        verbose_name="Version B",
    )

    # JSON diff containing added/removed/changed lines
    diff_content = models.JSONField(default=dict, blank=True, verbose_name="Diff Content")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Submission Version Diff"
        verbose_name_plural = "Submission Version Diffs"
        unique_together = ["version_a", "version_b"]
        indexes = [
            models.Index(fields=["version_a", "version_b"]),
        ]

    def __str__(self):
        return f"Diff between v{self.version_a.version_number} and v{self.version_b.version_number}"


class SubmissionVersionRestore(models.Model):
    """
    Audit trail for when a teacher/admin restores a previous submission version.

    Fields:
        submission: The submission being restored
        restored_from_version: Which version was restored
        restored_to_version: The new version created by restoring
        restored_by: User who performed the restore
        restored_at: When the restore happened
        reason: Why the version was restored
    """

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="version_restores",
        verbose_name="Submission",
    )

    restored_from_version = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.SET_NULL,
        null=True,
        related_name="restored_as_source",
        verbose_name="Restored From Version",
    )

    restored_to_version = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_as_target",
        verbose_name="Restored To Version",
    )

    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="restored_submissions",
        verbose_name="Restored By",
    )

    restored_at = models.DateTimeField(auto_now_add=True, verbose_name="Restored At")

    reason = models.TextField(
        blank=True, verbose_name="Reason", help_text="Reason for restoring a previous version"
    )

    class Meta:
        verbose_name = "Submission Version Restore"
        verbose_name_plural = "Submission Version Restores"
        ordering = ["-restored_at"]
        indexes = [
            models.Index(fields=["submission", "-restored_at"]),
            models.Index(fields=["restored_by", "-restored_at"]),
        ]

    def __str__(self):
        return f"Restored v{self.restored_from_version.version_number if self.restored_from_version else '?'} at {self.restored_at}"


class AssignmentAttempt(models.Model):
    """
    T_ASN_003: Track multiple submission attempts for assignments.

    Enables support for retakes and learning by tracking each attempt separately.
    Each attempt is tied to an assignment submission and tracks the attempt number,
    score, and grading status independently.

    Fields:
        submission: Reference to the original assignment submission
        assignment: Reference to the assignment being attempted
        student: The student making the attempt
        attempt_number: Which attempt this is (1, 2, 3, etc.)
        score: Score for this specific attempt (null if not graded yet)
        max_score: Maximum possible score for this attempt
        status: Current status (submitted, graded, in_review, returned)
        submitted_at: When this attempt was submitted
        graded_at: When this attempt was graded (if applicable)
        feedback: Grading feedback for this attempt
        content: The submission content for this attempt
        file: File attachment for this attempt
        created_at: When the attempt was created
        updated_at: When the attempt was last modified
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In Review"
        GRADED = "graded", "Graded"
        RETURNED = "returned", "Returned for Revision"

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Assignment Submission",
    )

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="student_attempts",
        verbose_name="Assignment",
    )

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="assignment_attempts", verbose_name="Student"
    )

    attempt_number = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name="Attempt Number"
    )

    score = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(0)], verbose_name="Score"
    )

    max_score = models.PositiveIntegerField(blank=True, null=True, verbose_name="Maximum Score")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED, verbose_name="Status"
    )

    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Submitted At")

    graded_at = models.DateTimeField(blank=True, null=True, verbose_name="Graded At")

    feedback = models.TextField(blank=True, verbose_name="Feedback")

    content = models.TextField(verbose_name="Submission Content")

    file = models.FileField(
        upload_to="assignments/attempts/", blank=True, null=True, verbose_name="File Attachment"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assignment Attempt"
        verbose_name_plural = "Assignment Attempts"
        unique_together = ["submission", "attempt_number"]
        ordering = ["attempt_number"]
        indexes = [
            models.Index(
                fields=["submission", "attempt_number"], name="attempt_submission_number_idx"
            ),
            models.Index(
                fields=["student", "assignment", "attempt_number"],
                name="attempt_student_assignment_idx",
            ),
            models.Index(fields=["status", "-submitted_at"], name="attempt_status_date_idx"),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_number}: {self.student.get_full_name()} - {self.assignment.title}"

    @property
    def percentage(self):
        """Calculate percentage score for this attempt"""
        if self.max_score and self.score is not None:
            return round((self.score / self.max_score) * 100, 2)
        return None

    @property
    def is_graded(self):
        """Check if this attempt has been graded"""
        return self.status in [self.Status.GRADED, self.Status.RETURNED]


# T_ASN_006: Assignment Rubric Support Models
# =============================================


class GradingRubric(models.Model):
    """
    T_ASN_006: Structured grading rubric for assignments.

    Rubrics provide a standardized way to grade assignments based on multiple criteria.
    Supports reusable templates and customizable scoring scales.

    Fields:
        name: Name of the rubric
        description: Detailed description of what the rubric measures
        created_by: User (teacher/tutor) who created the rubric
        is_template: Whether this is a reusable template
        total_points: Total possible points for the rubric
        is_deleted: Soft delete flag
        created_at: When the rubric was created
        updated_at: When the rubric was last modified
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Название рубрики",
        help_text='Например: "Рубрика для оценки эссе"',
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание рубрики",
        help_text="Подробное описание критериев оценивания",
    )

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_rubrics", verbose_name="Создано"
    )

    is_template = models.BooleanField(
        default=False,
        verbose_name="Является шаблоном",
        help_text="Если включено, рубрика будет доступна как шаблон для других преподавателей",
    )

    total_points = models.PositiveIntegerField(
        default=100,
        verbose_name="Всего баллов",
        help_text="Максимальное количество баллов по этой рубрике",
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалено",
        help_text="Мягкое удаление - рубрика не отображается в списках",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    class Meta:
        verbose_name = "Рубрика оценивания"
        verbose_name_plural = "Рубрики оценивания"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_by", "-created_at"]),
            models.Index(fields=["is_template", "is_deleted"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.total_points} баллов)"

    def clone(self, new_creator):
        """
        Clone this rubric with all its criteria.

        Args:
            new_creator: User who will own the cloned rubric

        Returns:
            GradingRubric: New rubric instance with all criteria cloned
        """
        # Create new rubric with cloned name
        cloned_rubric = GradingRubric.objects.create(
            name=f"{self.name} (копия)",
            description=self.description,
            created_by=new_creator,
            is_template=self.is_template,
            total_points=self.total_points,
        )

        # Clone all criteria
        for criterion in self.criteria.all():
            RubricCriterion.objects.create(
                rubric=cloned_rubric,
                name=criterion.name,
                description=criterion.description,
                max_points=criterion.max_points,
                point_scales=criterion.point_scales,
                order=criterion.order,
            )

        return cloned_rubric


class RubricCriterion(models.Model):
    """
    T_ASN_006: Individual criterion in a grading rubric.

    Each criterion represents one dimension of assessment with associated
    point scales for different performance levels.

    Fields:
        rubric: Reference to parent rubric
        name: Name of the criterion (e.g., "Content Quality")
        description: What this criterion measures
        max_points: Maximum points possible for this criterion
        point_scales: JSON list of [points, description] pairs
        order: Display order within the rubric
    """

    rubric = models.ForeignKey(
        GradingRubric, on_delete=models.CASCADE, related_name="criteria", verbose_name="Рубрика"
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Название критерия",
        help_text='Например: "Качество содержания"',
    )

    description = models.TextField(
        verbose_name="Описание критерия", help_text="Что оценивает этот критерий"
    )

    max_points = models.PositiveIntegerField(
        verbose_name="Максимум баллов", help_text="Максимальное количество баллов за этот критерий"
    )

    # JSON list: [[points, description], [points, description], ...]
    point_scales = models.JSONField(
        default=list,
        verbose_name="Шкала оценивания",
        help_text="Массив [баллы, описание] для каждого уровня выполнения",
    )

    order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок", help_text="Порядок отображения критерия в рубрике"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Критерий рубрики"
        verbose_name_plural = "Критерии рубрики"
        unique_together = ["rubric", "name"]
        ordering = ["order"]
        indexes = [
            models.Index(fields=["rubric", "order"]),
        ]

    def __str__(self):
        return f"{self.rubric.name} - {self.name}"

    def clean(self):
        """Validate point scales format and values."""
        from django.core.exceptions import ValidationError

        # Validate point_scales is a list
        if not isinstance(self.point_scales, list):
            raise ValidationError({"point_scales": "Шкала оценивания должна быть списком"})

        # Validate point_scales is not empty
        if not self.point_scales:
            raise ValidationError({"point_scales": "Шкала оценивания не может быть пустой"})

        # Validate each scale entry format
        for scale_entry in self.point_scales:
            if not isinstance(scale_entry, (list, tuple)) or len(scale_entry) != 2:
                raise ValidationError(
                    {"point_scales": "Каждая запись должна быть [баллы, описание]"}
                )

            points, description = scale_entry

            # Validate points is a number
            if not isinstance(points, (int, float)):
                raise ValidationError({"point_scales": "Баллы должны быть числом"})

            # Validate points don't exceed max_points
            if points > self.max_points:
                raise ValidationError(
                    {
                        "point_scales": f"Баллы ({points}) не могут быть больше максимума ({self.max_points})"
                    }
                )

            # Validate description is not empty
            if not description or not str(description).strip():
                raise ValidationError({"point_scales": "Описание уровня не может быть пустым"})


class RubricScore(models.Model):
    """
    T_ASN_006: Rubric scores for a graded submission.

    Stores the score assigned to each criterion when grading a submission with a rubric.

    Fields:
        submission: The assignment submission being graded
        criterion: The rubric criterion being scored
        score: Points awarded for this criterion
        comment: Optional comment explaining the score
        created_at: When the score was assigned
    """

    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="rubric_scores",
        verbose_name="Ответ на задание",
    )

    criterion = models.ForeignKey(
        RubricCriterion,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="Критерий рубрики",
    )

    score = models.DecimalField(
        decimal_places=2, max_digits=10, verbose_name="Баллы", validators=[MinValueValidator(0)]
    )

    comment = models.TextField(
        blank=True, verbose_name="Комментарий", help_text="Объяснение выставленной оценки"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    class Meta:
        verbose_name = "Оценка по критерию"
        verbose_name_plural = "Оценки по критериям"
        unique_together = ["submission", "criterion"]
        ordering = ["criterion__order"]
        indexes = [
            models.Index(fields=["submission", "criterion"]),
        ]

    def __str__(self):
        return f"{self.submission.student.get_full_name()} - {self.criterion.name}: {self.score}"

    def clean(self):
        """Validate score doesn't exceed criterion max points."""
        from django.core.exceptions import ValidationError

        if self.score > self.criterion.max_points:
            raise ValidationError(
                {
                    "score": f"Баллы ({self.score}) не могут быть больше максимума ({self.criterion.max_points})"
                }
            )


class RubricTemplate(models.Model):
    """
    T_ASN_006: Pre-defined rubric templates for common assignment types.

    System-wide templates for quickly creating rubrics for common assignment types
    (essay, project, presentation, etc.).

    Fields:
        name: Template name
        description: What this template is for
        assignment_type: Type of assignment this template is for
        rubric: Reference to the template rubric
        is_system: Whether this is a system template (created by admins)
        is_active: Whether the template is currently available
    """

    ASSIGNMENT_TYPES = [
        ("essay", "Эссе"),
        ("project", "Проект"),
        ("presentation", "Презентация"),
        ("research_paper", "Исследовательская работа"),
        ("coding", "Программирование"),
        ("creative", "Творческая работа"),
        ("practical", "Практическая работа"),
    ]

    name = models.CharField(max_length=255, verbose_name="Название шаблона")

    description = models.TextField(blank=True, verbose_name="Описание шаблона")

    assignment_type = models.CharField(
        max_length=50, choices=ASSIGNMENT_TYPES, verbose_name="Тип задания"
    )

    rubric = models.OneToOneField(
        GradingRubric, on_delete=models.CASCADE, related_name="template", verbose_name="Рубрика"
    )

    is_system = models.BooleanField(
        default=True,
        verbose_name="Системный шаблон",
        help_text="Создан администратором, доступен всем",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Активные шаблоны отображаются в списке доступных",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Шаблон рубрики"
        verbose_name_plural = "Шаблоны рубрик"
        unique_together = ["assignment_type", "name"]
        ordering = ["assignment_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_assignment_type_display()})"


class StudentDeadlineExtension(models.Model):
    """
    T_ASN_007: Track deadline extensions for individual students.

    Allows teachers to extend assignment deadlines for specific students
    due to circumstances (medical, personal, etc.).

    Fields:
        assignment: The assignment with extended deadline
        student: The student receiving the extension
        extended_deadline: New deadline for this student
        reason: Reason for the extension
        extended_by: Teacher/tutor who granted the extension
        created_at: When the extension was created
        updated_at: When the extension was last updated
    """

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="deadline_extensions",
        verbose_name="Задание",
    )

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="deadline_extensions", verbose_name="Студент"
    )

    extended_deadline = models.DateTimeField(
        verbose_name="Новый срок сдачи", help_text="Новый срок сдачи для этого студента"
    )

    reason = models.TextField(
        blank=True,
        verbose_name="Причина расширения",
        help_text="Объяснение причины расширения срока",
    )

    extended_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="granted_extensions", verbose_name="Расширено"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Расширение сроков"
        verbose_name_plural = "Расширения сроков"
        unique_together = ["assignment", "student"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assignment", "student"], name="dl_ext_assign_student"),
            models.Index(fields=["student", "-extended_deadline"], name="dl_ext_student_date"),
            models.Index(fields=["extended_by", "-created_at"], name="dl_ext_creator_date"),
        ]

    def __str__(self):
        return f"Extension: {self.student.get_full_name()} - {self.assignment.title} until {self.extended_deadline.date()}"


class SubmissionFeedback(models.Model):
    """
    M6: Feedback record for assignment submissions.

    Stores teacher feedback when grading submissions.
    Linked to AssignmentSubmission and teacher.

    Fields:
        submission: The assignment submission being graded
        teacher: The teacher/tutor who provided the feedback
        grade: Score (0-10)
        feedback_text: Detailed feedback text
        created_at: When feedback was given
        updated_at: Last modification time
    """

    submission = models.OneToOneField(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name="submission_feedback",
        verbose_name="Ответ на задание",
    )

    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="given_feedbacks", verbose_name="Преподаватель"
    )

    grade = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Оценка",
        help_text="Оценка от 0 до 10",
    )

    feedback_text = models.TextField(
        verbose_name="Текст обратной связи", help_text="Детальная обратная связь для студента"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Обратная связь на ответ"
        verbose_name_plural = "Обратная связь на ответы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["submission", "teacher"]),
            models.Index(fields=["teacher", "-created_at"]),
        ]

    def __str__(self):
        return f"Feedback: {self.submission.student.get_full_name()} - {self.grade}/10"
