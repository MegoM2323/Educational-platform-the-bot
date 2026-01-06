"""
Tests for TeacherWeeklyReportService

Tests the functionality of generating teacher weekly reports including:
- Data collection from multiple sources
- Statistical calculations
- Report generation
- Recommendations generation
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from reports.services.teacher_weekly_report_service import TeacherWeeklyReportService
from reports.models import TeacherWeeklyReport
from materials.models import Subject, SubjectEnrollment, Material, MaterialProgress
from assignments.models import Assignment, AssignmentSubmission
from chat.models import ChatRoom, Message, ChatParticipant

User = get_user_model()


@pytest.mark.django_db
class TestTeacherWeeklyReportService:
    """Test TeacherWeeklyReportService functionality"""

    @pytest.fixture
    def teacher(self):
        """Create test teacher"""
        return User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='John',
            last_name='Teacher'
        )

    @pytest.fixture
    def students(self):
        """Create test students"""
        students = []
        for i in range(3):
            student = User.objects.create_user(
                username=f'student{i}@test.com',
                email=f'student{i}@test.com',
                password='testpass123',
                role='student',
                first_name=f'Student{i}',
                last_name='Test'
            )
            students.append(student)
        return students

    @pytest.fixture
    def subject(self):
        """Create test subject"""
        return Subject.objects.create(
            name='Mathematics',
            description='Math subject'
        )

    @pytest.fixture
    def setup_enrollments(self, teacher, students, subject):
        """Setup subject enrollments"""
        for student in students:
            SubjectEnrollment.objects.create(
                teacher=teacher,
                student=student,
                subject=subject,
                is_active=True
            )

    @pytest.fixture
    def assignments_with_submissions(self, teacher, students, subject):
        """Create assignments and submissions for testing"""
        week_start = timezone.now().date() - timedelta(days=7)

        assignments = []
        for i in range(3):
            assignment = Assignment.objects.create(
                title=f'Assignment {i}',
                description='Test assignment',
                teacher=teacher,
                subject=subject,
                created_at=timezone.make_aware(
                    datetime.combine(week_start, datetime.min.time())
                )
            )
            assignments.append(assignment)

            # Create submissions for each student
            for j, student in enumerate(students):
                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    content='Test answer',
                    status=AssignmentSubmission.Status.GRADED,
                    score=70 + (j * 5),
                    max_score=100,
                    feedback='Good work!',
                    is_late=i % 2 == 0,
                    created_at=timezone.make_aware(
                        datetime.combine(
                            week_start + timedelta(days=i),
                            datetime.min.time()
                        )
                    )
                )

    def test_service_initialization(self, teacher):
        """Test service can be initialized"""
        service = TeacherWeeklyReportService(teacher)
        assert service.teacher == teacher
        assert service.teacher.role == 'teacher'

    def test_service_initialization_with_non_teacher_raises_error(self, students):
        """Test service initialization fails for non-teachers"""
        with pytest.raises(ValueError):
            TeacherWeeklyReportService(students[0])

    def test_generate_weekly_report_basic(self, teacher, students, subject, setup_enrollments):
        """Test basic weekly report generation"""
        service = TeacherWeeklyReportService(teacher)
        week_start = timezone.now().date() - timedelta(days=7)

        report_data = service.generate_weekly_report(week_start=week_start)

        assert 'week_start' in report_data
        assert 'week_end' in report_data
        assert 'teacher_id' in report_data
        assert 'students' in report_data
        assert 'summary' in report_data
        assert 'statistics' in report_data
        assert 'recommendations' in report_data

    def test_generate_weekly_report_with_specific_student(
        self, teacher, students, subject, setup_enrollments
    ):
        """Test report generation for specific student"""
        service = TeacherWeeklyReportService(teacher)
        week_start = timezone.now().date() - timedelta(days=7)

        report_data = service.generate_weekly_report(
            week_start=week_start,
            student_id=students[0].id
        )

        assert 'students' in report_data
        # Should only have data for requested student or empty
        if report_data['students']:
            assert all(s['student_id'] == students[0].id for s in report_data['students'])

    def test_student_data_collection(
        self, teacher, students, subject, setup_enrollments, assignments_with_submissions
    ):
        """Test student data collection"""
        service = TeacherWeeklyReportService(teacher)
        week_start = timezone.now().date() - timedelta(days=7)
        week_end = week_start + timedelta(days=6)

        student_data = service._collect_student_data(
            students[0], week_start, week_end, subject.id
        )

        # Check required fields
        assert 'student_id' in student_data
        assert 'student_name' in student_data
        assert 'assignments_completed' in student_data
        assert 'assignments_total' in student_data
        assert 'average_score' in student_data
        assert 'engagement_level' in student_data
        assert student_data['student_id'] == students[0].id

    def test_class_statistics_calculation(self, teacher, students, subject, setup_enrollments):
        """Test class statistics calculation"""
        service = TeacherWeeklyReportService(teacher)

        student_reports = [
            {
                'student_id': s.id,
                'average_score': 70.0 + (i * 10),
                'submission_rate': 80.0,
                'engagement_level': 'High'
            }
            for i, s in enumerate(students)
        ]

        all_scores = [70.0, 80.0, 90.0]
        all_submission_rates = [80.0, 80.0, 80.0]

        stats = service._calculate_class_statistics(
            student_reports, all_scores, all_submission_rates
        )

        assert 'total_students' in stats
        assert 'class_average_score' in stats
        assert 'class_submission_rate' in stats
        assert stats['total_students'] == 3
        assert stats['class_average_score'] > 0

    def test_engagement_level_calculation(self, service=None):
        """Test engagement level calculation"""
        if service is None:
            teacher = User.objects.create_user(
                username='teacher@test.com',
                email='teacher@test.com',
                password='testpass123',
                role='teacher'
            )
            service = TeacherWeeklyReportService(teacher)

        assignments_data = {
            'submission_rate': 90,
            'average_score': 85
        }
        learning_data = {
            'attendance': 90,
            'progress_percentage': 85
        }
        chat_data = {
            'participation_level': 8
        }
        time_spent = 15

        level = service._calculate_engagement_level(
            assignments_data, learning_data, chat_data, time_spent
        )

        assert level in ['Very High', 'High', 'Medium', 'Low', 'Very Low']
        assert level == 'Very High'

    def test_recommendations_generation(self):
        """Test recommendations generation"""
        teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        service = TeacherWeeklyReportService(teacher)

        student_reports = [
            {
                'student_id': 1,
                'engagement_level': 'Low',
                'average_score': 50,
                'submission_rate': 30
            }
        ]

        statistics = {
            'class_average_score': 55,
            'class_submission_rate': 60
        }

        recommendations = service._generate_recommendations(
            student_reports, statistics
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should have recommendations for low performing class
        assert any('low' in r.lower() or 'support' in r.lower() for r in recommendations)

    def test_create_report_record(
        self, teacher, students, subject, setup_enrollments
    ):
        """Test creating a TeacherWeeklyReport database record"""
        service = TeacherWeeklyReportService(teacher)
        week_start = timezone.now().date() - timedelta(days=7)

        report_data = {
            'students': [
                {
                    'student_id': students[0].id,
                    'student_name': students[0].get_full_name(),
                    'assignments_completed': 3,
                    'assignments_total': 5,
                    'average_score': 80.5,
                    'attendance_percentage': 90,
                    'engagement_level': 'High'
                }
            ],
            'week_start': week_start
        }

        report = service.create_weekly_report_record(
            week_start=week_start,
            student_id=students[0].id,
            subject_id=subject.id,
            report_data=report_data
        )

        assert report is not None
        assert report.teacher == teacher
        assert report.student == students[0]
        assert report.subject == subject
        assert report.week_start == week_start
        assert report.status == TeacherWeeklyReport.Status.DRAFT

    def test_cache_functionality(self, teacher, students, subject, setup_enrollments):
        """Test report caching"""
        service = TeacherWeeklyReportService(teacher)
        week_start = timezone.now().date() - timedelta(days=7)

        # Generate first time
        report1 = service.generate_weekly_report(week_start=week_start)

        # Should be cached
        report2 = service.generate_weekly_report(week_start=week_start)

        # With force_refresh, should regenerate
        report3 = service.generate_weekly_report(
            week_start=week_start,
            force_refresh=True
        )

        # All should have same structure
        assert 'summary' in report1
        assert 'summary' in report2
        assert 'summary' in report3

    @pytest.mark.django_db
    def test_permissions(self, teacher, students):
        """Test that only teachers can use service"""
        # Should work for teacher
        service = TeacherWeeklyReportService(teacher)
        assert service.teacher == teacher

        # Should fail for student
        with pytest.raises(ValueError):
            TeacherWeeklyReportService(students[0])
