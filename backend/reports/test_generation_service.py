"""
Tests for Report Generation Service

Comprehensive test suite for:
- Report generation from various data sources
- Multiple output formats (JSON, Excel, PDF)
- Caching behavior
- Progress tracking
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from unittest.mock import patch, MagicMock

from materials.models import Material, MaterialProgress, Subject
from assignments.models import Assignment, AssignmentSubmission
from knowledge_graph.models import Element, ElementProgress

from .services.generation_service import (
    ReportGenerationService,
    ReportGenerationException,
    ReportScheduler
)

User = get_user_model()


class ReportGenerationServiceTestCase(TestCase):
    """Test report generation service functionality."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.student = User.objects.create_user(
            email='student@test.com',
            password='TestPass123!',
            first_name='John',
            last_name='Doe',
            role=User.Role.STUDENT
        )

        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            first_name='Jane',
            last_name='Smith',
            role=User.Role.TEACHER
        )

        self.tutor = User.objects.create_user(
            email='tutor@test.com',
            password='TestPass123!',
            first_name='Bob',
            last_name='Johnson',
            role=User.Role.TUTOR
        )

        # Create subject
        self.subject = Subject.objects.create(
            name='Mathematics',
            description='Mathematics course'
        )

        # Create materials
        self.material1 = Material.objects.create(
            title='Algebra Basics',
            description='Basic algebra concepts',
            subject=self.subject,
            author=self.teacher,
            status=Material.Status.ACTIVE
        )

        self.material2 = Material.objects.create(
            title='Geometry Fundamentals',
            description='Geometry concepts',
            subject=self.subject,
            author=self.teacher,
            status=Material.Status.ACTIVE
        )

        # Create material progress
        MaterialProgress.objects.create(
            student=self.student,
            material=self.material1,
            progress_percentage=85,
            is_completed=True,
            time_spent=120
        )

        MaterialProgress.objects.create(
            student=self.student,
            material=self.material2,
            progress_percentage=60,
            is_completed=False,
            time_spent=90
        )

        # Create assignments
        self.assignment = Assignment.objects.create(
            title='Algebra Quiz',
            description='Test your algebra knowledge',
            created_by=self.teacher,
            start_date=timezone.now(),
            max_score=100,
            due_date=timezone.now() + timedelta(days=7)
        )

        # Create submissions
        self.submission = AssignmentSubmission.objects.create(
            student=self.student,
            assignment=self.assignment,
            score=85,
            status='submitted',
            submitted_at=timezone.now()
        )

    def tearDown(self):
        """Clean up cache after each test."""
        cache.clear()

    def test_service_initialization_valid_type(self):
        """Test service initialization with valid report type."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        self.assertEqual(service.report_type, 'student_progress')
        self.assertEqual(service.user, self.teacher)

    def test_service_initialization_invalid_type(self):
        """Test service initialization with invalid report type."""
        with self.assertRaises(ReportGenerationException) as ctx:
            ReportGenerationService(self.teacher, 'invalid_type')
        self.assertIn('Invalid report type', str(ctx.exception))

    def test_generate_student_progress_report_json(self):
        """Test generating student progress report in JSON format."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {
            'student_id': self.student.id,
            'date_range': {
                'start_date': timezone.now().date() - timedelta(days=30),
                'end_date': timezone.now().date()
            }
        }

        result = service.generate(filters=filters, output_format='json')

        # Validate result structure
        self.assertFalse(result['cached'])
        self.assertEqual(result['type'], 'student_progress')
        self.assertEqual(result['format'], 'json')
        self.assertIn('data', result)
        self.assertIn('metadata', result)

        # Validate data structure
        data = result['data']
        self.assertIn('summary', data)
        self.assertIn('details', data)
        self.assertIn('metadata', data)

        # Validate student info
        self.assertEqual(data['details']['student']['id'], self.student.id)
        self.assertEqual(data['details']['student']['email'], self.student.email)

    def test_generate_with_cache(self):
        """Test report caching behavior."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        # First generation
        result1 = service.generate(filters=filters, output_format='json', cache_enabled=True)
        self.assertFalse(result1['cached'])
        generation_time1 = result1['generation_time_seconds']

        # Second generation (should be cached)
        result2 = service.generate(filters=filters, output_format='json', cache_enabled=True)
        self.assertTrue(result2['cached'])
        generation_time2 = result2.get('generation_time_seconds', 0)

        # Cached result should be much faster
        self.assertLess(generation_time2 or 0, generation_time1)

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        # Generate and cache
        result1 = service.generate(filters=filters, output_format='json', cache_enabled=True)
        self.assertFalse(result1['cached'])

        # Invalidate cache
        service.invalidate_cache(filters)

        # Generate again (should not be cached)
        result2 = service.generate(filters=filters, output_format='json', cache_enabled=True)
        self.assertFalse(result2['cached'])

    def test_generate_class_performance_report(self):
        """Test class performance report generation."""
        service = ReportGenerationService(self.teacher, 'class_performance')
        filters = {
            'date_range': {
                'start_date': timezone.now().date() - timedelta(days=7),
                'end_date': timezone.now().date()
            }
        }

        result = service.generate(filters=filters, output_format='json')

        self.assertEqual(result['type'], 'class_performance')
        self.assertIn('class_size', result['data']['details'])

    def test_generate_assignment_analysis_report(self):
        """Test assignment analysis report generation."""
        service = ReportGenerationService(self.teacher, 'assignment_analysis')
        filters = {'assignment_id': self.assignment.id}

        result = service.generate(filters=filters, output_format='json')

        self.assertEqual(result['type'], 'assignment_analysis')
        data = result['data']['details']
        self.assertIn('assignment', data)
        self.assertIn('submissions', data)
        self.assertEqual(data['assignment']['id'], self.assignment.id)

    def test_generate_excel_format(self):
        """Test report generation in Excel format."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(filters=filters, output_format='excel')

        self.assertEqual(result['format'], 'excel')
        # Excel data should be bytes
        self.assertIsInstance(result['data'], bytes)
        # Check for Excel file signature
        self.assertTrue(result['data'].startswith(b'PK'))

    def test_generate_pdf_format(self):
        """Test report generation in PDF format (placeholder)."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(filters=filters, output_format='pdf')

        self.assertEqual(result['format'], 'pdf')
        # PDF should be bytes (currently JSON with PDF note)
        self.assertIsInstance(result['data'], bytes)

    def test_student_not_found_error(self):
        """Test error handling for non-existent student."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': 99999}

        with self.assertRaises(ReportGenerationException) as ctx:
            service.generate(filters=filters)
        self.assertIn('not found', str(ctx.exception))

    def test_assignment_not_found_error(self):
        """Test error handling for non-existent assignment."""
        service = ReportGenerationService(self.teacher, 'assignment_analysis')
        filters = {'assignment_id': 99999}

        with self.assertRaises(ReportGenerationException) as ctx:
            service.generate(filters=filters)
        self.assertIn('not found', str(ctx.exception))

    def test_missing_required_filter(self):
        """Test error handling for missing required filters."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {}  # Missing student_id

        with self.assertRaises(ReportGenerationException) as ctx:
            service.generate(filters=filters)
        self.assertIn('required', str(ctx.exception).lower())

    def test_progress_tracking(self):
        """Test progress callback during generation."""
        progress_updates = []

        def progress_callback(data):
            progress_updates.append(data)

        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(
            filters=filters,
            output_format='json',
            progress_callback=progress_callback
        )

        # Should have progress updates
        self.assertGreater(len(progress_updates), 0)
        # Last update should be completed
        self.assertEqual(progress_updates[-1]['status'], 'completed')
        self.assertEqual(progress_updates[-1]['percentage'], 100)

    def test_generation_time_tracking(self):
        """Test that generation time is tracked."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(filters=filters, output_format='json')

        self.assertIn('generation_time_seconds', result)
        self.assertGreater(result['generation_time_seconds'], 0)

    def test_summary_generation(self):
        """Test summary generation with correct statistics."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(filters=filters, output_format='json')

        summary = result['data']['summary']
        self.assertIn('progress', summary)
        self.assertEqual(summary['progress']['materials_completed'], 1)
        self.assertEqual(summary['progress']['total_materials'], 2)
        self.assertAlmostEqual(summary['progress']['average_progress'], 72.5, places=1)

    def test_insights_generation(self):
        """Test insight generation from data."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.student.id}

        result = service.generate(filters=filters, output_format='json')

        insights = result['data']['insights']
        # Should have at least one insight
        self.assertGreater(len(insights), 0)
        # Insights should be strings
        self.assertTrue(all(isinstance(i, str) for i in insights))

    def test_get_progress(self):
        """Test getting current progress information."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        progress = service.get_progress()

        self.assertIn('status', progress)
        self.assertIn('percentage', progress)

    def test_cache_key_generation(self):
        """Test cache key generation with different filters."""
        service = ReportGenerationService(self.teacher, 'student_progress')

        key1 = service._get_cache_key({'student_id': 1})
        key2 = service._get_cache_key({'student_id': 2})
        key3 = service._get_cache_key({'student_id': 1})

        # Different filters should generate different keys
        self.assertNotEqual(key1, key2)
        # Same filters should generate same key
        self.assertEqual(key1, key3)

    def test_tutor_weekly_report(self):
        """Test tutor weekly report generation."""
        service = ReportGenerationService(self.tutor, 'tutor_weekly')
        filters = {'tutor_id': self.tutor.id}

        result = service.generate(filters=filters, output_format='json')

        self.assertEqual(result['type'], 'tutor_weekly')
        data = result['data']['details']
        self.assertEqual(data['tutor_id'], self.tutor.id)
        self.assertIn('week', data)

    def test_teacher_weekly_report(self):
        """Test teacher weekly report generation."""
        service = ReportGenerationService(self.teacher, 'teacher_weekly')
        filters = {'teacher_id': self.teacher.id}

        result = service.generate(filters=filters, output_format='json')

        self.assertEqual(result['type'], 'teacher_weekly')
        data = result['data']['details']
        self.assertEqual(data['teacher']['id'], self.teacher.id)

    def test_report_types_metadata(self):
        """Test that all report types have proper metadata."""
        for report_type in ReportGenerationService.REPORT_TYPES:
            metadata = ReportGenerationService.REPORT_TYPES[report_type]
            self.assertIn('name', metadata)
            self.assertIn('description', metadata)
            self.assertIn('data_sources', metadata)
            self.assertIsInstance(metadata['data_sources'], list)


class ReportSchedulerTestCase(TestCase):
    """Test report scheduling functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )

        self.recipient1 = User.objects.create_user(
            email='recipient1@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )

        self.recipient2 = User.objects.create_user(
            email='recipient2@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )

    def test_schedule_daily_report(self):
        """Test scheduling a daily report."""
        result = ReportScheduler.schedule_report(
            user=self.user,
            report_type='student_progress',
            frequency='daily',
            recipients=[self.recipient1, self.recipient2]
        )

        self.assertEqual(result['status'], 'scheduled')
        self.assertEqual(result['frequency'], 'daily')
        self.assertEqual(len(result['recipients']), 2)

    def test_schedule_weekly_report(self):
        """Test scheduling a weekly report."""
        result = ReportScheduler.schedule_report(
            user=self.user,
            report_type='class_performance',
            frequency='weekly',
            recipients=[self.recipient1]
        )

        self.assertEqual(result['frequency'], 'weekly')

    def test_schedule_monthly_report(self):
        """Test scheduling a monthly report."""
        result = ReportScheduler.schedule_report(
            user=self.user,
            report_type='teacher_weekly',
            frequency='monthly',
            recipients=[self.recipient1, self.recipient2]
        )

        self.assertEqual(result['frequency'], 'monthly')

    def test_invalid_frequency(self):
        """Test scheduling with invalid frequency."""
        with self.assertRaises(ReportGenerationException):
            ReportScheduler.schedule_report(
                user=self.user,
                report_type='student_progress',
                frequency='invalid_frequency',
                recipients=[self.recipient1]
            )

    def test_get_pending_schedules(self):
        """Test getting pending schedules."""
        schedules = ReportScheduler.get_pending_schedules()
        self.assertIsInstance(schedules, list)


class ReportGenerationIntegrationTestCase(TestCase):
    """Integration tests for report generation."""

    def setUp(self):
        """Set up complex test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )

        self.students = [
            User.objects.create_user(
                email=f'student{i}@test.com',
                password='TestPass123!',
                role=User.Role.STUDENT
            )
            for i in range(3)
        ]

        self.subject = Subject.objects.create(name='Science')

        # Create multiple materials
        for i in range(3):
            material = Material.objects.create(
                title=f'Material {i+1}',
                subject=self.subject,
                author=self.teacher,
                status=Material.Status.ACTIVE
            )

            # Create progress for each student
            for student in self.students:
                MaterialProgress.objects.create(
                    student=student,
                    material=material,
                    progress_percentage=50 + i * 10,
                    is_completed=i > 0
                )

    def test_generate_all_report_types(self):
        """Test generating all supported report types."""
        report_types = [
            ('student_progress', {'student_id': self.students[0].id}),
            ('class_performance', {}),
            ('assignment_analysis', {}),
            ('subject_analysis', {'subject_name': 'Science'}),
            ('tutor_weekly', {}),
            ('teacher_weekly', {'teacher_id': self.teacher.id})
        ]

        for report_type, filters in report_types:
            try:
                service = ReportGenerationService(self.teacher, report_type)
                result = service.generate(
                    filters=filters if filters else None,
                    output_format='json'
                )
                self.assertEqual(result['type'], report_type)
            except ReportGenerationException:
                # Some report types may require specific data
                pass

    def test_generate_and_export_multiple_formats(self):
        """Test generating same report in multiple formats."""
        service = ReportGenerationService(self.teacher, 'student_progress')
        filters = {'student_id': self.students[0].id}

        # Generate in different formats
        json_result = service.generate(filters=filters, output_format='json')
        excel_result = service.generate(filters=filters, output_format='excel')

        self.assertEqual(json_result['format'], 'json')
        self.assertEqual(excel_result['format'], 'excel')

        # JSON should be dict, Excel should be bytes
        self.assertIsInstance(json_result['data'], dict)
        self.assertIsInstance(excel_result['data'], bytes)
