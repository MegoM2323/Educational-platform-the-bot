import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import timedelta
from .models import (
    Assignment,
    AssignmentSubmission,
    AssignmentQuestion,
    AssignmentAnswer,
    SubmissionExemption,
    PeerReviewAssignment,
    PeerReview,
    PlagiarismReport,
    AssignmentHistory,
    SubmissionVersion,
    SubmissionVersionDiff,
    SubmissionVersionRestore,
    AssignmentAttempt,
    GradingRubric,
    RubricCriterion,
    RubricScore,
    RubricTemplate,
    StudentDeadlineExtension,
    SubmissionFeedback,
)
from accounts.factories import UserFactory


class AssignmentFactory(DjangoModelFactory):
    class Meta:
        model = Assignment

    title = factory.Sequence(lambda n: f"Assignment {n}")
    description = "Test assignment description"
    instructions = "Complete the assignment"
    author = factory.SubFactory(UserFactory)
    type = Assignment.Type.HOMEWORK
    status = Assignment.Status.PUBLISHED
    max_score = 100
    time_limit = 60
    attempts_limit = 3
    start_date = factory.LazyFunction(timezone.now)
    due_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    difficulty_level = 3
    late_submission_deadline = factory.LazyFunction(lambda: timezone.now() + timedelta(days=14))
    allow_late_submission = True
    late_penalty_type = "percentage"
    late_penalty_value = 5
    penalty_frequency = "per_day"
    max_penalty = 50


class AssignmentQuestionFactory(DjangoModelFactory):
    class Meta:
        model = AssignmentQuestion

    assignment = factory.SubFactory(AssignmentFactory)
    question_text = factory.Sequence(lambda n: f"Question {n}")
    question_type = AssignmentQuestion.Type.SINGLE_CHOICE
    points = 10
    order = factory.Sequence(lambda n: n)
    options = ["Option A", "Option B", "Option C"]
    correct_answer = {"index": 0}
    randomize_options = False


class AssignmentSubmissionFactory(DjangoModelFactory):
    class Meta:
        model = AssignmentSubmission

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory)
    content = "Student submission content"
    status = AssignmentSubmission.Status.SUBMITTED
    is_late = False
    days_late = 0
    score = 85
    max_score = 100


class AssignmentAnswerFactory(DjangoModelFactory):
    class Meta:
        model = AssignmentAnswer

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    question = factory.SubFactory(AssignmentQuestionFactory)
    answer_text = "Student answer"
    answer_choice = [0]
    is_correct = True
    points_earned = 10


class SubmissionExemptionFactory(DjangoModelFactory):
    class Meta:
        model = SubmissionExemption

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    exemption_type = SubmissionExemption.ExemptionType.FULL
    custom_penalty_rate = 0
    reason = "Medical excuse"
    exemption_created_by = factory.SubFactory(UserFactory)


class PeerReviewAssignmentFactory(DjangoModelFactory):
    class Meta:
        model = PeerReviewAssignment

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    reviewer = factory.SubFactory(UserFactory)
    assignment_type = PeerReviewAssignment.AssignmentType.RANDOM
    status = PeerReviewAssignment.Status.PENDING
    deadline = timezone.now() + timedelta(days=3)
    is_anonymous = False


class PeerReviewFactory(DjangoModelFactory):
    class Meta:
        model = PeerReview

    peer_assignment = factory.SubFactory(PeerReviewAssignmentFactory)
    score = 85
    feedback_text = "Good work overall"
    rubric_scores = {"content": 8, "clarity": 9}


class PlagiarismReportFactory(DjangoModelFactory):
    class Meta:
        model = PlagiarismReport

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    similarity_score = 15.50
    detection_status = PlagiarismReport.DetectionStatus.COMPLETED
    sources = [{"source": "https://example.com", "match_percent": 15}]
    service = PlagiarismReport.PlagiarismService.CUSTOM
    service_report_id = "report_12345"


class AssignmentHistoryFactory(DjangoModelFactory):
    class Meta:
        model = AssignmentHistory

    assignment = factory.SubFactory(AssignmentFactory)
    changed_by = factory.SubFactory(UserFactory)
    changes_dict = {"title": {"old": "Old Title", "new": "New Title"}}
    change_summary = "Title updated"
    fields_changed = ["title"]


class SubmissionVersionFactory(DjangoModelFactory):
    class Meta:
        model = SubmissionVersion

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    version_number = 1
    content = factory.Sequence(lambda n: f"Version content {n}")
    is_final = False
    submitted_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def set_submission(obj, create, extracted, **kwargs):
        # Ensure unique submission for testing
        if not create:
            return
        # Counter for version numbers per submission
        if not hasattr(obj.submission, '_version_counter'):
            obj.submission._version_counter = 1
        else:
            obj.submission._version_counter += 1
        obj.version_number = obj.submission._version_counter
        obj.save()


class SubmissionVersionDiffFactory(DjangoModelFactory):
    class Meta:
        model = SubmissionVersionDiff

    version_a = factory.SubFactory(SubmissionVersionFactory, version_number=1)
    version_b = factory.SubFactory(SubmissionVersionFactory, version_number=2)
    diff_content = {"added": ["new line"], "removed": ["old line"]}


class SubmissionVersionRestoreFactory(DjangoModelFactory):
    class Meta:
        model = SubmissionVersionRestore

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    restored_from_version = factory.SubFactory(SubmissionVersionFactory)
    restored_to_version = factory.SubFactory(SubmissionVersionFactory)
    restored_by = factory.SubFactory(UserFactory)
    reason = "Restore requested by student"


class AssignmentAttemptFactory(DjangoModelFactory):
    class Meta:
        model = AssignmentAttempt

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory)
    attempt_number = 1
    score = 80
    max_score = 100
    status = AssignmentAttempt.Status.GRADED
    feedback = "Good attempt"
    content = "Attempt content"


class GradingRubricFactory(DjangoModelFactory):
    class Meta:
        model = GradingRubric

    name = factory.Sequence(lambda n: f"Rubric {n}")
    description = "Test rubric"
    created_by = factory.SubFactory(UserFactory)
    is_template = False
    total_points = 100


class RubricCriterionFactory(DjangoModelFactory):
    class Meta:
        model = RubricCriterion

    rubric = factory.SubFactory(GradingRubricFactory)
    name = factory.Sequence(lambda n: f"Criterion {n}")
    description = "Test criterion"
    max_points = 25
    point_scales = [[25, "Excellent"], [20, "Good"], [15, "Fair"], [0, "Poor"]]
    order = factory.Sequence(lambda n: n)


class RubricScoreFactory(DjangoModelFactory):
    class Meta:
        model = RubricScore

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    criterion = factory.SubFactory(RubricCriterionFactory)
    score = 20
    comment = "Good work"


class RubricTemplateFactory(DjangoModelFactory):
    class Meta:
        model = RubricTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    description = "Test template"
    assignment_type = "essay"
    rubric = factory.SubFactory(GradingRubricFactory, is_template=True)
    is_system = True
    is_active = True


class StudentDeadlineExtensionFactory(DjangoModelFactory):
    class Meta:
        model = StudentDeadlineExtension

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory)
    extended_deadline = timezone.now() + timedelta(days=10)
    reason = "Student requested extension"
    extended_by = factory.SubFactory(UserFactory)


class SubmissionFeedbackFactory(DjangoModelFactory):
    class Meta:
        model = SubmissionFeedback

    submission = factory.SubFactory(AssignmentSubmissionFactory)
    teacher = factory.SubFactory(UserFactory)
    grade = 8
    feedback_text = "Excellent work, well done!"
