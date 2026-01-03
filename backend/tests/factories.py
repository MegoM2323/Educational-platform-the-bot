"""
Factory Boy factories for all models.
Provides factories for creating test objects efficiently.

Note: All model imports are deferred to avoid circular dependencies
during Django initialization. See bottom of file.
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
from uuid import uuid4


def _get_user_role(role_name):
    """Helper to get User role from Django User model"""
    UserModel = get_user_model()
    return getattr(UserModel.Role, role_name)


User = None
Subject = None
Material = None
MaterialProgress = None
MaterialComment = None
MaterialSubmission = None
MaterialFeedback = None
MaterialDownloadLog = None
SubjectEnrollment = None
Lesson = None
Assignment = None
AssignmentSubmission = None
ChatRoom = None
Message = None
Notification = None
Payment = None
Report = None
ReportTemplate = None
ReportSchedule = None
StudentReport = None
TutorWeeklyReport = None
TeacherWeeklyReport = None
ReportRecipient = None
ParentReportPreference = None
AnalyticsData = None
ReportAccessToken = None
ReportAccessAuditLog = None
ReportSharing = None
CustomReport = None
CustomReportExecution = None
Invoice = None
StudentProfile = None
TeacherProfile = None
TutorProfile = None
ParentProfile = None
TutorStudentCreation = None
TelegramLinkToken = None
Application = None
Element = None
KGLesson = None
KnowledgeGraph = None
LessonProgress = None
ElementProgress = None


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""

    class Meta:
        model = None
        abstract = True

    username = factory.LazyFunction(lambda: f"user_{uuid4().hex[:12]}")
    email = factory.LazyFunction(lambda: f"user_{uuid4().hex[:12]}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = "testpass123!"
    role = factory.LazyFunction(lambda: _get_user_role("STUDENT"))
    is_active = True
    is_verified = False
    phone = "+79991234567"
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override default create to properly hash password"""
        password = kwargs.pop("password", None)
        obj = model_class(*args, **kwargs)
        if password:
            obj.set_password(password)
        else:
            obj.set_password("testpass123!")
        obj.save()
        return obj


class StudentFactory(UserFactory):
    """Factory for creating Student User"""

    class Meta:
        model = None
        abstract = False

    role = factory.LazyFunction(lambda: _get_user_role("STUDENT"))


class TeacherFactory(UserFactory):
    """Factory for creating Teacher User"""

    class Meta:
        model = None
        abstract = False

    role = factory.LazyFunction(lambda: _get_user_role("TEACHER"))


class TutorFactory(UserFactory):
    """Factory for creating Tutor User"""

    class Meta:
        model = None
        abstract = False

    role = factory.LazyFunction(lambda: _get_user_role("TUTOR"))


class ParentFactory(UserFactory):
    """Factory for creating Parent User"""

    class Meta:
        model = None
        abstract = False

    role = factory.LazyFunction(lambda: _get_user_role("PARENT"))


class StudentProfileFactory(DjangoModelFactory):
    """Factory for StudentProfile"""

    class Meta:
        model = None

    user = factory.SubFactory(StudentFactory)
    grade = "10"
    goal = "Улучшить знание английского языка"
    tutor = None
    parent = None
    progress_percentage = 0
    streak_days = 0
    total_points = 0
    accuracy_percentage = 0
    generated_username = factory.Sequence(lambda n: f"gen_user_{n}_{uuid4().hex[:8]}")
    telegram = ""
    telegram_id = ""


class TeacherProfileFactory(DjangoModelFactory):
    """Factory for TeacherProfile"""

    class Meta:
        model = None

    user = factory.SubFactory(TeacherFactory)
    subject = "English"
    experience_years = 5
    bio = "Опытный преподаватель"
    telegram = ""
    telegram_id = ""


class TutorProfileFactory(DjangoModelFactory):
    """Factory for TutorProfile"""

    class Meta:
        model = None

    user = factory.SubFactory(TutorFactory)
    specialization = "English Language"
    experience_years = 3
    bio = "Профессиональный тьютор"
    telegram = ""
    telegram_id = ""


class ParentProfileFactory(DjangoModelFactory):
    """Factory for ParentProfile"""

    class Meta:
        model = None

    user = factory.SubFactory(ParentFactory)
    telegram = ""
    telegram_id = ""


class TutorStudentCreationFactory(DjangoModelFactory):
    """Factory for TutorStudentCreation"""

    class Meta:
        model = None

    tutor = factory.SubFactory(TutorFactory)
    student = factory.SubFactory(StudentFactory)
    parent = factory.SubFactory(ParentFactory)
    student_username = factory.Sequence(lambda n: f"student_{n}_{uuid4().hex[:8]}")
    parent_username = factory.Sequence(lambda n: f"parent_{n}_{uuid4().hex[:8]}")


class TelegramLinkTokenFactory(DjangoModelFactory):
    """Factory for TelegramLinkToken"""

    class Meta:
        model = None

    user = factory.SubFactory(StudentFactory)
    token = factory.LazyFunction(lambda: uuid4().hex)
    created_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    is_used = False
    used_at = None


class AssignmentFactory(DjangoModelFactory):
    """Factory for Assignment"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Assignment {n}")
    description = "Test assignment description"
    instructions = "Do this task"
    author = factory.SubFactory(TeacherFactory)
    type = factory.LazyAttribute(lambda o: Assignment.Type.HOMEWORK)
    status = factory.LazyAttribute(lambda o: Assignment.Status.DRAFT)
    max_score = 100
    time_limit = 60
    start_date = factory.LazyFunction(timezone.now)
    due_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))


class AssignmentSubmissionFactory(DjangoModelFactory):
    """Factory for AssignmentSubmission"""

    class Meta:
        model = None

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(StudentFactory)
    content = "Student submission content"
    status = factory.LazyAttribute(lambda o: AssignmentSubmission.Status.SUBMITTED)
    score = 85
    max_score = 100
    feedback = "Good work"


class SubjectFactory(DjangoModelFactory):
    """Factory for Subject"""

    class Meta:
        model = None

    name = factory.Sequence(lambda n: f"Subject {n}_{uuid4().hex[:8]}")
    description = "Test subject"


class MaterialFactory(DjangoModelFactory):
    """Factory for Material"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Material {n}_{uuid4().hex[:8]}")
    description = "Test material description"
    content = "Material content"
    author = factory.SubFactory(TeacherFactory)
    subject = factory.SubFactory(SubjectFactory)
    type = factory.LazyFunction(lambda: "lesson")
    status = factory.LazyFunction(lambda: "draft")
    is_public = False
    difficulty_level = 1


class MaterialProgressFactory(DjangoModelFactory):
    """Factory for MaterialProgress"""

    class Meta:
        model = None

    student = factory.SubFactory(StudentFactory)
    material = factory.SubFactory(MaterialFactory)
    is_completed = False
    progress_percentage = 0
    time_spent = 0


class MaterialCommentFactory(DjangoModelFactory):
    """Factory for MaterialComment"""

    class Meta:
        model = None

    material = factory.SubFactory(MaterialFactory)
    author = factory.SubFactory(StudentFactory)
    content = "Test material comment"
    is_question = False
    parent_comment = None
    is_deleted = False
    is_approved = True


class MaterialSubmissionFactory(DjangoModelFactory):
    """Factory for MaterialSubmission"""

    class Meta:
        model = None

    material = factory.SubFactory(MaterialFactory)
    student = factory.SubFactory(StudentFactory)
    submission_text = "Student submission"
    is_late = False


class MaterialFeedbackFactory(DjangoModelFactory):
    """Factory for MaterialFeedback"""

    class Meta:
        model = None

    submission = factory.SubFactory(MaterialSubmissionFactory)
    teacher = factory.SubFactory(TeacherFactory)
    feedback_text = "Good work"
    grade = 5


class MaterialDownloadLogFactory(DjangoModelFactory):
    """Factory for MaterialDownloadLog"""

    class Meta:
        model = None

    material = factory.SubFactory(MaterialFactory)
    user = factory.SubFactory(StudentFactory)
    ip_address = "127.0.0.1"
    user_agent = "Mozilla/5.0 Test"
    file_size = 1024


class SubjectEnrollmentFactory(DjangoModelFactory):
    """Factory for SubjectEnrollment"""

    class Meta:
        model = None

    student = factory.SubFactory(StudentFactory)
    subject = factory.SubFactory(SubjectFactory)
    teacher = factory.SubFactory(TeacherFactory)
    assigned_by = None
    custom_subject_name = None
    is_active = True
    enrolled_at = factory.LazyFunction(timezone.now)


class LessonFactory(DjangoModelFactory):
    """Factory for Lesson"""

    class Meta:
        model = None

    id = factory.LazyFunction(uuid.uuid4)
    teacher = factory.SubFactory(TeacherFactory)
    student = factory.SubFactory(StudentFactory)
    subject = factory.SubFactory(SubjectFactory)
    start_time = factory.LazyFunction(
        lambda: timezone.now()
        .replace(hour=10, minute=0, second=0, microsecond=0)
        .time()
    )
    end_time = factory.LazyFunction(
        lambda: timezone.now()
        .replace(hour=11, minute=0, second=0, microsecond=0)
        .time()
    )
    date = factory.LazyFunction(lambda: (timezone.now() + timedelta(days=1)).date())
    description = "Test lesson"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to create SubjectEnrollment and skip validation"""
        teacher = kwargs.get("teacher")
        student = kwargs.get("student")
        subject = kwargs.get("subject")

        if teacher and student and subject:
            from materials.models import SubjectEnrollment

            SubjectEnrollment.objects.get_or_create(
                teacher=teacher,
                student=student,
                subject=subject,
                defaults={"is_active": True},
            )

        obj = model_class(*args, **kwargs)
        obj.save(skip_validation=True)
        return obj


class ChatRoomFactory(DjangoModelFactory):
    """Factory for ChatRoom"""

    class Meta:
        model = None

    name = factory.Sequence(lambda n: f"Room {n}_{uuid4().hex[:8]}")
    description = "Test chat room"
    created_by = factory.SubFactory(StudentFactory)
    type = "direct"


class MessageFactory(DjangoModelFactory):
    """Factory for Message"""

    class Meta:
        model = None

    room = factory.SubFactory(ChatRoomFactory)
    sender = factory.SubFactory(StudentFactory)
    content = "Test message content"
    message_type = factory.LazyFunction(lambda: "text")


class NotificationFactory(DjangoModelFactory):
    """Factory for Notification"""

    class Meta:
        model = None

    recipient = factory.SubFactory(StudentFactory)
    title = "Test Notification"
    message = "Test notification message"
    type = "system"
    priority = "normal"
    is_read = False


class InvoiceFactory(DjangoModelFactory):
    """Factory for Invoice"""

    class Meta:
        model = None

    tutor = factory.SubFactory(TutorFactory)
    student = factory.SubFactory(StudentFactory)
    parent = factory.SubFactory(ParentFactory)
    amount = factory.LazyFunction(lambda: Decimal("1000.00"))
    description = "Test invoice for tuition"
    status = "draft"
    due_date = factory.LazyFunction(
        lambda: (timezone.now() + timedelta(days=30)).date()
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to create StudentProfile if needed"""
        student = kwargs.get("student")
        parent = kwargs.get("parent")

        if student and parent:
            from accounts.models import StudentProfile

            StudentProfile.objects.get_or_create(
                user=student,
                defaults={"parent": parent},
            )

        obj = model_class(*args, **kwargs)
        obj.save()
        return obj


class PaymentFactory(DjangoModelFactory):
    """Factory for Payment"""

    class Meta:
        model = None

    invoice = factory.SubFactory(InvoiceFactory)
    amount = 1000.00
    status = "pending"
    payment_method = "yookassa"
    transaction_id = factory.Sequence(lambda n: f"txn_{n}_{uuid4().hex[:8]}")


class ReportFactory(DjangoModelFactory):
    """Factory for Report"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Report {n}_{uuid4().hex[:8]}")
    description = "Test report"
    type = "custom"
    status = "draft"
    author = factory.SubFactory(TeacherFactory)
    start_date = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=30)).date()
    )
    end_date = factory.LazyFunction(lambda: timezone.now().date())
    content = {}


class ReportTemplateFactory(DjangoModelFactory):
    """Factory for ReportTemplate"""

    class Meta:
        model = None

    name = factory.Sequence(lambda n: f"Template {n}_{uuid4().hex[:8]}")
    description = "Test template"
    type = "custom"
    sections = [{"name": "summary", "fields": ["title"]}]
    layout_config = {"orientation": "portrait", "page_size": "a4"}
    default_format = "pdf"
    version = 1
    is_default = False
    is_archived = False
    created_by = factory.SubFactory(TeacherFactory)


class ReportScheduleFactory(DjangoModelFactory):
    """Factory for ReportSchedule"""

    class Meta:
        model = None

    name = factory.Sequence(lambda n: f"Schedule {n}")
    report_template = factory.SubFactory(ReportTemplateFactory)
    frequency = "weekly"
    day_of_week = 1
    time = factory.LazyFunction(lambda: timezone.now().time())
    export_format = "csv"
    created_by = factory.SubFactory(TeacherFactory)
    is_active = True


class StudentReportFactory(DjangoModelFactory):
    """Factory for StudentReport"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Student Report {n}_{uuid4().hex[:8]}")
    description = "Student progress report"
    report_type = "progress"
    status = "draft"
    teacher = factory.SubFactory(TeacherFactory)
    student = factory.SubFactory(StudentFactory)
    period_start = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=7)).date()
    )
    period_end = factory.LazyFunction(lambda: timezone.now().date())
    content = {}
    overall_grade = "A"
    progress_percentage = 85
    attendance_percentage = 90
    behavior_rating = 8


class TutorWeeklyReportFactory(DjangoModelFactory):
    """Factory for TutorWeeklyReport"""

    class Meta:
        model = None

    tutor = factory.SubFactory(TutorFactory)
    student = factory.SubFactory(StudentFactory)
    parent = factory.SubFactory(ParentFactory)
    week_start = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=7)).date()
    )
    week_end = factory.LazyFunction(lambda: timezone.now().date())
    title = "Weekly Report"
    summary = "Test summary"
    academic_progress = "Good"
    behavior_notes = "Excellent"
    achievements = "Achieved goals"
    concerns = "None"
    recommendations = "Continue"
    attendance_days = 5
    total_days = 7
    progress_percentage = 80
    status = "draft"


class TeacherWeeklyReportFactory(DjangoModelFactory):
    """Factory for TeacherWeeklyReport"""

    class Meta:
        model = None

    teacher = factory.SubFactory(TeacherFactory)
    student = factory.SubFactory(StudentFactory)
    subject = factory.SubFactory(SubjectFactory)
    week_start = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=7)).date()
    )
    week_end = factory.LazyFunction(lambda: timezone.now().date())
    title = "Weekly Report"
    summary = "Test summary"
    academic_progress = "Good"
    performance_notes = "Excellent"
    achievements = "Goals"
    concerns = "None"
    recommendations = "Continue"
    assignments_completed = 5
    assignments_total = 10
    average_score = 85.5
    attendance_percentage = 90
    status = "draft"


class ReportRecipientFactory(DjangoModelFactory):
    """Factory for ReportRecipient"""

    class Meta:
        model = None

    report = factory.SubFactory(ReportFactory)
    recipient = factory.SubFactory(ParentFactory)


class ParentReportPreferenceFactory(DjangoModelFactory):
    """Factory for ParentReportPreference"""

    class Meta:
        model = None

    parent = factory.SubFactory(ParentFactory)
    notify_on_report_created = True
    notify_on_grade_posted = True
    show_grades = True
    show_progress = True


class ReportAccessTokenFactory(DjangoModelFactory):
    """Factory for ReportAccessToken"""

    class Meta:
        model = None

    token = factory.Sequence(
        lambda n: f"token_{n}_abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmno"
    )
    report = factory.SubFactory(ReportFactory)
    created_by = factory.SubFactory(TeacherFactory)
    status = "active"
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    access_count = 0


class ReportAccessAuditLogFactory(DjangoModelFactory):
    """Factory for ReportAccessAuditLog"""

    class Meta:
        model = None

    access_type = "view"
    report = factory.SubFactory(ReportFactory)
    accessed_by = factory.SubFactory(StudentFactory)
    access_method = "direct"
    ip_address = "127.0.0.1"
    access_duration_seconds = 60


class ReportSharingFactory(DjangoModelFactory):
    """Factory for ReportSharing"""

    class Meta:
        model = None

    report = factory.SubFactory(ReportFactory)
    shared_by = factory.SubFactory(TeacherFactory)
    shared_with_user = factory.SubFactory(StudentFactory)
    share_type = "user"
    permission = "view"
    is_active = True


class CustomReportFactory(DjangoModelFactory):
    """Factory for CustomReport"""

    class Meta:
        model = None

    name = factory.Sequence(lambda n: f"Custom Report {n}_{uuid4().hex[:8]}")
    description = "Test custom report"
    created_by = factory.SubFactory(TeacherFactory)
    is_shared = False
    config = {"fields": ["student_name", "grade"], "filters": {}}
    status = "draft"


class CustomReportExecutionFactory(DjangoModelFactory):
    """Factory for CustomReportExecution"""

    class Meta:
        model = None

    report = factory.SubFactory(CustomReportFactory)
    executed_by = factory.SubFactory(TeacherFactory)
    rows_returned = 100
    execution_time_ms = 1500
    result_summary = {}


class AnalyticsDataFactory(DjangoModelFactory):
    """Factory for AnalyticsData"""

    class Meta:
        model = None

    student = factory.SubFactory(StudentFactory)
    metric_type = "score"
    value = 85.5
    unit = "percent"
    date = factory.LazyFunction(timezone.now)


class KnowledgeGraphFactory(DjangoModelFactory):
    """Factory for KnowledgeGraph"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Graph {n}_{uuid4().hex[:8]}")
    description = "Test knowledge graph"


class ElementFactory(DjangoModelFactory):
    """Factory for Element"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"Element {n}_{uuid4().hex[:8]}")
    description = "Test element"
    content = "Element content"
    order = 1


class LessonProgressFactory(DjangoModelFactory):
    """Factory for LessonProgress"""

    class Meta:
        model = None

    student = factory.SubFactory(StudentFactory)
    status = "not_started"
    progress = 0

    @factory.lazy_attribute
    def lesson(self):
        return KGLessonFactory()


class ElementProgressFactory(DjangoModelFactory):
    """Factory for ElementProgress"""

    class Meta:
        model = None

    element = factory.SubFactory(ElementFactory)
    student = factory.SubFactory(StudentFactory)
    status = "not_started"
    progress = 0


class KGLessonFactory(DjangoModelFactory):
    """Factory for knowledge_graph Lesson"""

    class Meta:
        model = None

    title = factory.Sequence(lambda n: f"KG Lesson {n}_{uuid4().hex[:8]}")
    description = "Test KG lesson"
    order = 1


class ApplicationFactory(DjangoModelFactory):
    """Factory for Application"""

    class Meta:
        model = None

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"applicant{n}_{uuid4().hex[:8]}@example.com")
    phone = factory.Sequence(lambda n: f"+7999{uuid4().hex[:6]}{n % 10}")
    telegram_id = ""
    applicant_type = None
    status = None
    grade = "10"
    subject = ""
    experience = ""
    motivation = ""
    parent_first_name = factory.Faker("first_name")
    parent_last_name = factory.Faker("last_name")
    parent_email = factory.Sequence(
        lambda n: f"parent{n}_{uuid4().hex[:8]}@example.com"
    )
    parent_phone = factory.Sequence(lambda n: f"+7999{uuid4().hex[:6]}{n % 10}")
    parent_telegram_id = ""
    notes = ""
    created_at = factory.LazyFunction(timezone.now)


def _initialize_factories():
    """Initialize all factory model references and enums - called after Django setup"""
    global User, Subject, Material, MaterialProgress, MaterialComment, MaterialSubmission
    global MaterialFeedback, MaterialDownloadLog, SubjectEnrollment, Lesson, Assignment
    global AssignmentSubmission, ChatRoom, Message, Notification, Payment
    global Report, ReportTemplate, ReportSchedule, StudentReport
    global TutorWeeklyReport, TeacherWeeklyReport, ReportRecipient
    global ParentReportPreference, AnalyticsData, ReportAccessToken, ReportAccessAuditLog
    global ReportSharing, CustomReport, CustomReportExecution
    global Invoice, StudentProfile
    global TeacherProfile, TutorProfile, ParentProfile, TutorStudentCreation
    global TelegramLinkToken, Application, Element, KGLesson, KnowledgeGraph
    global LessonProgress, ElementProgress

    try:
        from django.apps import apps
        from django.contrib.auth import get_user_model as get_auth_user_model

        UserModel = get_auth_user_model()
        SP = apps.get_model("accounts", "StudentProfile")
        TP = apps.get_model("accounts", "TeacherProfile")
        TuP = apps.get_model("accounts", "TutorProfile")
        PP = apps.get_model("accounts", "ParentProfile")
        TSC = apps.get_model("accounts", "TutorStudentCreation")
        TLT = apps.get_model("accounts", "TelegramLinkToken")
        L = apps.get_model("scheduling", "Lesson")
        A = apps.get_model("assignments", "Assignment")
        AS = apps.get_model("assignments", "AssignmentSubmission")
        S = apps.get_model("materials", "Subject")
        M = apps.get_model("materials", "Material")
        MP = apps.get_model("materials", "MaterialProgress")
        MC = apps.get_model("materials", "MaterialComment")
        MSub = apps.get_model("materials", "MaterialSubmission")
        MF = apps.get_model("materials", "MaterialFeedback")
        MDL = apps.get_model("materials", "MaterialDownloadLog")
        SE = apps.get_model("materials", "SubjectEnrollment")
        ChatRoomModel = apps.get_model("chat", "ChatRoom")
        Msg = apps.get_model("chat", "Message")
        N = apps.get_model("notifications", "Notification")
        P = apps.get_model("payments", "Payment")
        R = apps.get_model("reports", "Report")
        RT = apps.get_model("reports", "ReportTemplate")
        RS = apps.get_model("reports", "ReportSchedule")
        SR = apps.get_model("reports", "StudentReport")
        TWR = apps.get_model("reports", "TutorWeeklyReport")
        TeWR = apps.get_model("reports", "TeacherWeeklyReport")
        ReR = apps.get_model("reports", "ReportRecipient")
        PRP = apps.get_model("reports", "ParentReportPreference")
        AD = apps.get_model("reports", "AnalyticsData")
        RAT = apps.get_model("reports", "ReportAccessToken")
        RAAL = apps.get_model("reports", "ReportAccessAuditLog")
        RS_Shr = apps.get_model("reports", "ReportSharing")
        CustomReportModel = apps.get_model("reports", "CustomReport")
        CRE = apps.get_model("reports", "CustomReportExecution")
        I = apps.get_model("invoices", "Invoice")
        App = apps.get_model("applications", "Application")
        E = apps.get_model("knowledge_graph", "Element")
        KGL = apps.get_model("knowledge_graph", "Lesson")
        KG = apps.get_model("knowledge_graph", "KnowledgeGraph")
        LP = apps.get_model("knowledge_graph", "LessonProgress")
        EP = apps.get_model("knowledge_graph", "ElementProgress")

    except Exception as e:
        import warnings

        warnings.warn(f"Failed to initialize factories: {e}", ImportWarning)
        return

    User = UserModel
    StudentProfile = SP
    TeacherProfile = TP
    TutorProfile = TuP
    ParentProfile = PP
    TutorStudentCreation = TSC
    TelegramLinkToken = TLT
    Lesson = L
    Assignment = A
    AssignmentSubmission = AS
    Subject = S
    Material = M
    MaterialProgress = MP
    MaterialComment = MC
    MaterialSubmission = MSub
    MaterialFeedback = MF
    MaterialDownloadLog = MDL
    SubjectEnrollment = SE
    ChatRoom = ChatRoomModel
    Message = Msg
    Notification = N
    Payment = P
    Report = R
    ReportTemplate = RT
    ReportSchedule = RS
    StudentReport = SR
    TutorWeeklyReport = TWR
    TeacherWeeklyReport = TeWR
    ReportRecipient = ReR
    ParentReportPreference = PRP
    AnalyticsData = AD
    ReportAccessToken = RAT
    ReportAccessAuditLog = RAAL
    ReportSharing = RS_Shr
    CustomReport = CustomReportModel
    CustomReportExecution = CRE
    Invoice = I
    Application = App
    Element = E
    KGLesson = KGL
    KnowledgeGraph = KG
    LessonProgress = LP
    ElementProgress = EP

    UserFactory._meta.model = User
    UserFactory._meta.abstract = False
    StudentFactory._meta.model = User
    StudentFactory._meta.abstract = False
    TeacherFactory._meta.model = User
    TeacherFactory._meta.abstract = False
    TutorFactory._meta.model = User
    TutorFactory._meta.abstract = False
    ParentFactory._meta.model = User
    ParentFactory._meta.abstract = False
    StudentProfileFactory._meta.model = StudentProfile
    StudentProfileFactory._meta.abstract = False
    TeacherProfileFactory._meta.model = TeacherProfile
    TeacherProfileFactory._meta.abstract = False
    TutorProfileFactory._meta.model = TutorProfile
    TutorProfileFactory._meta.abstract = False
    ParentProfileFactory._meta.model = ParentProfile
    ParentProfileFactory._meta.abstract = False
    TutorStudentCreationFactory._meta.model = TutorStudentCreation
    TutorStudentCreationFactory._meta.abstract = False
    TelegramLinkTokenFactory._meta.model = TelegramLinkToken
    TelegramLinkTokenFactory._meta.abstract = False
    LessonFactory._meta.model = Lesson
    LessonFactory._meta.abstract = False
    AssignmentFactory._meta.model = Assignment
    AssignmentFactory._meta.abstract = False
    AssignmentSubmissionFactory._meta.model = AssignmentSubmission
    AssignmentSubmissionFactory._meta.abstract = False
    SubjectFactory._meta.model = Subject
    SubjectFactory._meta.abstract = False
    MaterialFactory._meta.model = Material
    MaterialFactory._meta.abstract = False
    MaterialProgressFactory._meta.model = MaterialProgress
    MaterialProgressFactory._meta.abstract = False
    MaterialCommentFactory._meta.model = MaterialComment
    MaterialCommentFactory._meta.abstract = False
    MaterialSubmissionFactory._meta.model = MaterialSubmission
    MaterialSubmissionFactory._meta.abstract = False
    MaterialFeedbackFactory._meta.model = MaterialFeedback
    MaterialFeedbackFactory._meta.abstract = False
    MaterialDownloadLogFactory._meta.model = MaterialDownloadLog
    MaterialDownloadLogFactory._meta.abstract = False
    SubjectEnrollmentFactory._meta.model = SubjectEnrollment
    SubjectEnrollmentFactory._meta.abstract = False
    ChatRoomFactory._meta.model = ChatRoom
    ChatRoomFactory._meta.abstract = False
    MessageFactory._meta.model = Message
    MessageFactory._meta.abstract = False
    NotificationFactory._meta.model = Notification
    NotificationFactory._meta.abstract = False
    InvoiceFactory._meta.model = Invoice
    InvoiceFactory._meta.abstract = False
    PaymentFactory._meta.model = Payment
    PaymentFactory._meta.abstract = False
    ReportFactory._meta.model = Report
    ReportFactory._meta.abstract = False
    ReportTemplateFactory._meta.model = ReportTemplate
    ReportTemplateFactory._meta.abstract = False
    ReportScheduleFactory._meta.model = ReportSchedule
    ReportScheduleFactory._meta.abstract = False
    StudentReportFactory._meta.model = StudentReport
    StudentReportFactory._meta.abstract = False
    TutorWeeklyReportFactory._meta.model = TutorWeeklyReport
    TutorWeeklyReportFactory._meta.abstract = False
    TeacherWeeklyReportFactory._meta.model = TeacherWeeklyReport
    TeacherWeeklyReportFactory._meta.abstract = False
    ReportRecipientFactory._meta.model = ReportRecipient
    ReportRecipientFactory._meta.abstract = False
    ParentReportPreferenceFactory._meta.model = ParentReportPreference
    ParentReportPreferenceFactory._meta.abstract = False
    AnalyticsDataFactory._meta.model = AnalyticsData
    AnalyticsDataFactory._meta.abstract = False
    ReportAccessTokenFactory._meta.model = ReportAccessToken
    ReportAccessTokenFactory._meta.abstract = False
    ReportAccessAuditLogFactory._meta.model = ReportAccessAuditLog
    ReportAccessAuditLogFactory._meta.abstract = False
    ReportSharingFactory._meta.model = ReportSharing
    ReportSharingFactory._meta.abstract = False
    CustomReportFactory._meta.model = CustomReport
    CustomReportFactory._meta.abstract = False
    CustomReportExecutionFactory._meta.model = CustomReportExecution
    CustomReportExecutionFactory._meta.abstract = False
    KnowledgeGraphFactory._meta.model = KnowledgeGraph
    KnowledgeGraphFactory._meta.abstract = False
    ElementFactory._meta.model = Element
    ElementFactory._meta.abstract = False
    LessonProgressFactory._meta.model = LessonProgress
    LessonProgressFactory._meta.abstract = False
    ElementProgressFactory._meta.model = ElementProgress
    ElementProgressFactory._meta.abstract = False
    KGLessonFactory._meta.model = KGLesson
    KGLessonFactory._meta.abstract = False
    ApplicationFactory._meta.model = Application
    ApplicationFactory._meta.abstract = False

    if hasattr(Lesson, "Status"):
        LessonFactory.status = Lesson.Status.PENDING

    if hasattr(Assignment, "Type"):
        AssignmentFactory.type = Assignment.Type.HOMEWORK
    if hasattr(Assignment, "Status"):
        AssignmentFactory.status = Assignment.Status.PUBLISHED

    if hasattr(Material, "Type"):
        MaterialFactory.type = Material.Type.LESSON
    if hasattr(Material, "Status"):
        MaterialFactory.status = Material.Status.DRAFT

    if hasattr(MaterialSubmission, "Status"):
        MaterialSubmissionFactory.status = MaterialSubmission.Status.SUBMITTED

    if hasattr(ChatRoom, "Type"):
        ChatRoomFactory.type = ChatRoom.Type.DIRECT
    if hasattr(Message, "Type"):
        MessageFactory.message_type = Message.Type.TEXT

    if hasattr(Application, "ApplicantType"):
        ApplicationFactory.applicant_type = Application.ApplicantType.STUDENT
    if hasattr(Application, "Status"):
        ApplicationFactory.status = Application.Status.PENDING


_initialize_factories()
