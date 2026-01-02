import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from reports.models import (
    Report, ReportTemplate, ReportRecipient, AnalyticsData,
    StudentReport, ReportSchedule, TutorWeeklyReport,
    ParentReportPreference, TeacherWeeklyReport, ReportScheduleRecipient,
    ReportScheduleExecution, CustomReport, CustomReportExecution,
    CustomReportBuilderTemplate, ReportAccessToken, ReportAccessAuditLog,
    ReportSharing
)

User = get_user_model()


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    title = factory.Sequence(lambda n: f"Report {n}")
    description = "Test report"
    type = Report.Type.CUSTOM
    status = Report.Status.DRAFT
    author = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    start_date = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=30)).date())
    end_date = factory.LazyFunction(lambda: timezone.now().date())
    content = {}
    is_auto_generated = False


class ReportTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    description = "Test template"
    type = Report.Type.CUSTOM
    sections = [{"name": "summary", "fields": ["title"]}]
    layout_config = {"orientation": "portrait", "page_size": "a4"}
    default_format = ReportTemplate.Format.PDF
    version = 1
    is_default = False
    is_archived = False
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )


class ReportRecipientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportRecipient

    report = factory.SubFactory(ReportFactory)
    recipient = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    is_sent = False


class AnalyticsDataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticsData

    student = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    metric_type = AnalyticsData.MetricType.STUDENT_PROGRESS
    value = 85.5
    unit = "%"
    date = factory.LazyFunction(lambda: timezone.now().date())
    period_start = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=30)).date())
    period_end = factory.LazyFunction(lambda: timezone.now().date())
    metadata = {}


class StudentReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentReport

    title = factory.Sequence(lambda n: f"Student Report {n}")
    description = "Test student report"
    report_type = StudentReport.ReportType.PROGRESS
    status = StudentReport.Status.DRAFT
    teacher = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    student = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    period_start = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=30)).date())
    period_end = factory.LazyFunction(lambda: timezone.now().date())
    content = {}
    overall_grade = "A"
    progress_percentage = 85
    attendance_percentage = 90
    behavior_rating = 8
    show_to_parent = True
    parent_acknowledged = False


class ReportScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportSchedule

    report_template = factory.SubFactory(ReportTemplateFactory)
    name = factory.Sequence(lambda n: f"Schedule {n}")
    report_type = ReportSchedule.ReportType.STUDENT_REPORT
    frequency = ReportSchedule.Frequency.WEEKLY
    time = "09:00"
    export_format = ReportSchedule.ExportFormat.CSV
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    is_active = True


class TutorWeeklyReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TutorWeeklyReport

    tutor = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    student = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    week_start = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=7)).date())
    week_end = factory.LazyFunction(lambda: timezone.now().date())
    title = "Weekly Report"
    summary = "Test summary"
    academic_progress = "Good"
    behavior_notes = "Excellent"
    achievements = "Achieved goals"
    concerns = "None"
    recommendations = "Continue"
    attendance_days = 5
    progress_percentage = 80
    status = TutorWeeklyReport.Status.DRAFT


class ParentReportPreferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ParentReportPreference

    parent = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    notify_on_report_created = True
    notify_on_grade_posted = True
    show_grades = True
    show_progress = True


class TeacherWeeklyReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeacherWeeklyReport

    teacher = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    student = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    week_start = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=7)).date())
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
    status = TeacherWeeklyReport.Status.DRAFT


class ReportScheduleRecipientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportScheduleRecipient

    schedule = factory.SubFactory(ReportScheduleFactory)
    recipient = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    is_subscribed = True


class ReportScheduleExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportScheduleExecution

    schedule = factory.SubFactory(ReportScheduleFactory)
    status = ReportScheduleExecution.ExecutionStatus.COMPLETED
    total_recipients = 10
    successful_sends = 10
    failed_sends = 0
    error_message = ""


class CustomReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomReport

    name = factory.Sequence(lambda n: f"Custom Report {n}")
    description = "Test custom report"
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    is_shared = False
    config = {
        "fields": ["student_name", "grade"],
        "filters": {}
    }
    status = CustomReport.Status.DRAFT


class CustomReportExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomReportExecution

    report = factory.SubFactory(CustomReportFactory)
    executed_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    rows_returned = 100
    execution_time_ms = 1500
    result_summary = {}


class CustomReportBuilderTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomReportBuilderTemplate

    name = factory.Sequence(lambda n: f"Builder Template {n}")
    description = "Test template"
    template_type = CustomReportBuilderTemplate.TemplateType.CLASS_PROGRESS
    base_config = {
        "fields": ["student_name", "grade"],
        "filters": {}
    }
    is_system = False
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )


class ReportAccessTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportAccessToken

    token = factory.Sequence(lambda n: f"token_{n}_abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmno")
    report = factory.SubFactory(ReportFactory)
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    status = ReportAccessToken.Status.ACTIVE
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    access_count = 0


class ReportAccessAuditLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportAccessAuditLog

    access_type = ReportAccessAuditLog.AccessType.VIEW
    report = factory.SubFactory(ReportFactory)
    accessed_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    access_method = "direct"
    ip_address = "127.0.0.1"
    access_duration_seconds = 60


class ReportSharingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportSharing

    report = factory.SubFactory(ReportFactory)
    shared_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    shared_with_user = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last() or
        User.objects.create_user(
            username=f"user_{id(object())}",
            email=f"user_{id(object())}@test.com"
        )
    )
    share_type = ReportSharing.ShareType.USER
    permission = ReportSharing.Permission.VIEW
    is_active = True
