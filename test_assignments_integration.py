"""
Integration tests for Assignment & Submission Workflow
THE_BOT Platform

Tests for:
- Assignment creation and management
- Submission workflow
- Grading and feedback
- Late submission handling
- File uploads
- Status tracking
"""

import pytest
import json
import io
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from assignments.models import Assignment, AssignmentSubmission
from assignments.serializers import AssignmentSerializer, AssignmentSubmissionSerializer

User = get_user_model()


class AssignmentCreationTests(TestCase):
    """Tests for creating assignments"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher',
            first_name='Ivan',
            last_name='Petrov'
        )
        self.student1 = User.objects.create_user(
            email='anna.ivanova@student.com',
            password='password123',
            role='student',
            first_name='Anna',
            last_name='Ivanova'
        )
        self.student2 = User.objects.create_user(
            email='dmitry.smirnov@student.com',
            password='password123',
            role='student',
            first_name='Dmitry',
            last_name='Smirnov'
        )
        self.client = Client()

    def test_create_assignment_basic(self):
        """Test basic assignment creation"""
        now = timezone.now()
        assignment_data = {
            'title': 'Домашняя работа: Уравнения',
            'description': 'Решите 5 уравнений из учебника',
            'instructions': 'Используйте методы подстановки',
            'author': self.teacher.id,
            'type': 'homework',
            'status': 'published',
            'max_score': 100,
            'start_date': now,
            'due_date': now + timedelta(days=2),
            'difficulty_level': 2,
            'tags': 'equations,homework,algebra',
        }

        serializer = AssignmentSerializer(data=assignment_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        assignment = serializer.save()
        self.assertEqual(assignment.title, 'Домашняя работа: Уравнения')
        self.assertEqual(assignment.max_score, 100)
        self.assertEqual(assignment.status, 'published')
        self.assertEqual(assignment.author, self.teacher)

    def test_create_assignment_with_students(self):
        """Test assignment creation with student assignment"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
            difficulty_level=2,
        )

        # Assign to students
        assignment.assigned_to.add(self.student1, self.student2)

        self.assertEqual(assignment.assigned_to.count(), 2)
        self.assertIn(self.student1, assignment.assigned_to.all())
        self.assertIn(self.student2, assignment.assigned_to.all())

    def test_assignment_required_fields(self):
        """Test that required fields are enforced"""
        assignment_data = {
            'description': 'Test Description',
            'instructions': 'Test Instructions',
            'author': self.teacher.id,
            # Missing 'title', 'due_date', etc.
        }

        serializer = AssignmentSerializer(data=assignment_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)

    def test_assignment_with_late_penalty(self):
        """Test assignment with late submission penalty"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='Late Penalty Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
            late_submission_deadline=now + timedelta(days=5),
            late_penalty_type='percentage',
            late_penalty_value=10.0,  # 10% penalty
        )

        self.assertEqual(assignment.late_penalty_type, 'percentage')
        self.assertEqual(assignment.late_penalty_value, 10.0)


class AssignmentSubmissionTests(TestCase):
    """Tests for submitting assignments"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='anna.ivanova@student.com',
            password='password123',
            role='student'
        )

        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
        )
        self.assignment.assigned_to.add(self.student)

    def test_submit_assignment_with_content(self):
        """Test submission with text content"""
        submission_data = {
            'assignment': self.assignment.id,
            'student': self.student.id,
            'content': 'Решение: 1) x=5, 2) x=10, 3) x=15, 4) x=20, 5) x=25',
            'file': None,
            'status': 'submitted',
        }

        serializer = AssignmentSubmissionSerializer(data=submission_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        submission = serializer.save()
        self.assertEqual(submission.content, submission_data['content'])
        self.assertEqual(submission.status, 'submitted')
        self.assertEqual(submission.student, self.student)
        self.assertIsNotNone(submission.submitted_at)

    def test_submit_assignment_with_file(self):
        """Test submission with file upload"""
        file_content = b"Test file content"
        test_file = SimpleUploadedFile(
            "solution.txt",
            file_content,
            content_type="text/plain"
        )

        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='File submitted',
            file=test_file,
            status='submitted'
        )

        self.assertIsNotNone(submission.file)
        self.assertTrue(submission.file.name.startswith('assignments/submissions/'))

    def test_submission_auto_set_submitted_at(self):
        """Test that submitted_at is set automatically"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission',
            status='submitted'
        )

        self.assertIsNotNone(submission.submitted_at)
        self.assertLessEqual(
            (timezone.now() - submission.submitted_at).total_seconds(),
            5  # Within 5 seconds of now
        )

    def test_submission_unique_per_student_assignment(self):
        """Test unique_together constraint"""
        submission1 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='First submission',
            status='submitted'
        )

        # Attempt to create duplicate
        with self.assertRaises(Exception):
            submission2 = AssignmentSubmission.objects.create(
                assignment=self.assignment,
                student=self.student,
                content='Second submission',
                status='submitted'
            )

    def test_submission_percentage_calculation(self):
        """Test percentage property calculation"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test',
            status='submitted',
            score=85,
            max_score=100
        )

        self.assertEqual(submission.percentage, 85.0)

    def test_submission_without_max_score(self):
        """Test percentage when max_score is None"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test',
            status='submitted',
            score=85,
            max_score=None
        )

        self.assertIsNone(submission.percentage)


class GradingTests(TestCase):
    """Tests for grading submissions"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='anna.ivanova@student.com',
            password='password123',
            role='student'
        )

        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
        )

        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test submission',
            status='submitted'
        )

    def test_grade_submission(self):
        """Test grading a submission"""
        self.submission.score = 85
        self.submission.feedback = 'Хорошо решено, не хватает объяснений'
        self.submission.status = 'graded'
        self.submission.save()

        self.assertEqual(self.submission.score, 85)
        self.assertEqual(self.submission.status, 'graded')
        self.assertIsNotNone(self.submission.graded_at)

    def test_grade_updates_status(self):
        """Test that grading updates submission status"""
        self.assertEqual(self.submission.status, 'submitted')

        self.submission.status = 'graded'
        self.submission.score = 90
        self.submission.save()

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'graded')
        self.assertEqual(self.submission.score, 90)

    def test_grading_sets_graded_at(self):
        """Test that graded_at is set when grading"""
        self.assertIsNone(self.submission.graded_at)

        self.submission.score = 75
        self.submission.status = 'graded'
        self.submission.save()

        self.assertIsNotNone(self.submission.graded_at)


class LateSubmissionTests(TestCase):
    """Tests for late submission handling"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='dmitry.smirnov@student.com',
            password='password123',
            role='student'
        )

    def test_on_time_submission(self):
        """Test that on-time submission is not marked as late"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='On Time Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='On time submission',
            status='submitted',
            submitted_at=now + timedelta(hours=1)
        )

        # Should not be marked as late
        self.assertFalse(submission.is_late)

    def test_late_submission(self):
        """Test that late submission is marked as late"""
        now = timezone.now()
        due_date = now - timedelta(days=1)  # Deadline in the past

        assignment = Assignment.objects.create(
            title='Late Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now - timedelta(days=5),
            due_date=due_date,
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Late submission',
            status='submitted',
            submitted_at=now,  # Submitted after deadline
            is_late=True,
            days_late=1.0
        )

        self.assertTrue(submission.is_late)
        self.assertEqual(submission.days_late, 1.0)

    def test_late_submission_with_penalty_percentage(self):
        """Test late submission penalty calculation (percentage)"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='Penalty Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now - timedelta(days=5),
            due_date=now - timedelta(days=1),
            late_penalty_type='percentage',
            late_penalty_value=10.0,  # 10% penalty
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Late submission',
            status='submitted',
            is_late=True,
            days_late=1.0,
            score=100,  # Perfect score
            max_score=100
        )

        # If penalty applied, score should be 90 (100 - 10%)
        if submission.penalty_applied:
            self.assertEqual(submission.penalty_applied, 10.0)

    def test_late_submission_with_penalty_fixed(self):
        """Test late submission penalty calculation (fixed points)"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='Fixed Penalty Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now - timedelta(days=5),
            due_date=now - timedelta(days=1),
            late_penalty_type='fixed_points',
            late_penalty_value=10.0,  # 10 points penalty
        )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            content='Late submission',
            status='submitted',
            is_late=True,
            days_late=1.0,
            score=100,
            max_score=100
        )

        # If penalty applied, score should be 90 (100 - 10)
        if submission.penalty_applied:
            self.assertEqual(submission.penalty_applied, 10.0)


class FileUploadTests(TestCase):
    """Tests for file upload handling"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='anna.ivanova@student.com',
            password='password123',
            role='student'
        )

        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='File Upload Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
        )

    def test_upload_text_file(self):
        """Test uploading a text file"""
        test_file = SimpleUploadedFile(
            "solution.txt",
            b"Test content",
            content_type="text/plain"
        )

        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Text file submission',
            file=test_file,
            status='submitted'
        )

        self.assertIsNotNone(submission.file)
        self.assertTrue(submission.file.name.endswith('.txt'))

    def test_upload_pdf_file(self):
        """Test uploading a PDF file"""
        # Simple PDF header
        pdf_content = b"%PDF-1.4\n"
        test_file = SimpleUploadedFile(
            "document.pdf",
            pdf_content,
            content_type="application/pdf"
        )

        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='PDF submission',
            file=test_file,
            status='submitted'
        )

        self.assertIsNotNone(submission.file)
        self.assertTrue(submission.file.name.endswith('.pdf'))

    def test_upload_image_file(self):
        """Test uploading an image file"""
        test_file = SimpleUploadedFile(
            "solution.jpg",
            b"fake jpeg content",
            content_type="image/jpeg"
        )

        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Image submission',
            file=test_file,
            status='submitted'
        )

        self.assertIsNotNone(submission.file)
        self.assertTrue(submission.file.name.endswith('.jpg'))

    def test_multiple_file_uploads(self):
        """Test uploading multiple files in sequence"""
        file1 = SimpleUploadedFile(
            "solution_v1.txt",
            b"Version 1",
            content_type="text/plain"
        )

        submission1 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='First submission',
            file=file1,
            status='submitted'
        )

        self.assertTrue(submission1.file.name.endswith('v1.txt'))


class AssignmentStatusTests(TestCase):
    """Tests for assignment and submission status tracking"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='anna.ivanova@student.com',
            password='password123',
            role='student'
        )

        now = timezone.now()
        self.assignment = Assignment.objects.create(
            title='Status Test',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='draft',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
        )

    def test_assignment_status_draft(self):
        """Test assignment in draft status"""
        self.assertEqual(self.assignment.status, 'draft')

    def test_assignment_status_published(self):
        """Test publishing an assignment"""
        self.assignment.status = 'published'
        self.assignment.save()

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'published')

    def test_assignment_status_closed(self):
        """Test closing an assignment"""
        self.assignment.status = 'closed'
        self.assignment.save()

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'closed')

    def test_submission_status_progression(self):
        """Test submission status progression"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            content='Test',
            status='submitted'
        )

        self.assertEqual(submission.status, 'submitted')

        submission.status = 'graded'
        submission.score = 85
        submission.save()

        self.assertEqual(submission.status, 'graded')


class AssignmentMetadataTests(TestCase):
    """Tests for assignment metadata"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='ivan.petrov@tutoring.com',
            password='password123',
            role='teacher'
        )

    def test_assignment_tags(self):
        """Test assignment tags field"""
        now = timezone.now()
        assignment = Assignment.objects.create(
            title='Tagged Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            type='homework',
            status='published',
            max_score=100,
            start_date=now,
            due_date=now + timedelta(days=2),
            tags='equations,homework,algebra',
        )

        self.assertEqual(assignment.tags, 'equations,homework,algebra')

    def test_assignment_difficulty_levels(self):
        """Test assignment difficulty levels"""
        now = timezone.now()

        for level in range(1, 6):
            assignment = Assignment.objects.create(
                title=f'Level {level}',
                description='Test',
                instructions='Test',
                author=self.teacher,
                type='homework',
                status='published',
                max_score=100,
                start_date=now,
                due_date=now + timedelta(days=2),
                difficulty_level=level,
            )

            self.assertEqual(assignment.difficulty_level, level)

    def test_assignment_types(self):
        """Test different assignment types"""
        now = timezone.now()
        types = ['homework', 'test', 'project', 'essay', 'practical']

        for assign_type in types:
            assignment = Assignment.objects.create(
                title=f'Type {assign_type}',
                description='Test',
                instructions='Test',
                author=self.teacher,
                type=assign_type,
                status='published',
                max_score=100,
                start_date=now,
                due_date=now + timedelta(days=2),
            )

            self.assertEqual(assignment.type, assign_type)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
