"""
Tests for Custom Report Builder System - Core Tests

Comprehensive test suite covering:
- Custom report creation and CRUD operations
- Report configuration validation
- Report generation with filters
- Permission checks
- Soft delete functionality
"""

import json
from datetime import datetime, timedelta

import pytest
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

User = get_user_model()

# Import models after User is defined
from .models import CustomReport, CustomReportExecution, CustomReportBuilderTemplate
from .services.report_builder import ReportBuilder, ReportBuilderException

# Alias for backwards compatibility in tests
ReportTemplate = CustomReportBuilderTemplate


class CustomReportModelTests(TestCase):
    """Tests for CustomReport model."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='John',
            last_name='Doe'
        )
        self.teacher2 = User.objects.create_user(
            email='teacher2@test.com',
            password='testpass123',
            role='teacher',
            first_name='Jane',
            last_name='Smith'
        )

    def test_create_custom_report(self):
        """Test creating a custom report."""
        config = {
            'fields': ['student_name', 'grade', 'submission_count'],
            'filters': {'subject_id': 1},
            'chart_type': 'bar'
        }

        report = CustomReport.objects.create(
            name='Class Progress Report',
            description='Shows class progress',
            created_by=self.teacher,
            config=config
        )

        self.assertEqual(report.name, 'Class Progress Report')
        self.assertEqual(report.created_by, self.teacher)
        self.assertEqual(report.status, CustomReport.Status.DRAFT)
        self.assertFalse(report.is_shared)
        self.assertFalse(report.is_deleted())

    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = {
            'fields': ['student_name', 'grade'],
            'filters': {'subject_id': 1},
            'chart_type': 'bar'
        }

        report = CustomReport(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        # Should not raise exception
        report.validate_config()

    def test_validate_config_missing_fields(self):
        """Test config validation fails without fields."""
        config = {
            'filters': {'subject_id': 1}
        }

        report = CustomReport(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        with self.assertRaises(ValidationError):
            report.validate_config()

    def test_validate_config_empty_fields(self):
        """Test config validation fails with empty fields."""
        config = {
            'fields': [],
            'filters': {}
        }

        report = CustomReport(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        with self.assertRaises(ValidationError):
            report.validate_config()

    def test_validate_config_invalid_chart_type(self):
        """Test config validation fails with invalid chart type."""
        config = {
            'fields': ['student_name'],
            'chart_type': 'invalid_chart'
        }

        report = CustomReport(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        with self.assertRaises(ValidationError):
            report.validate_config()

    def test_validate_config_valid_chart_types(self):
        """Test config validation with all valid chart types."""
        valid_chart_types = ['bar', 'line', 'pie', 'histogram', 'scatter']

        for chart_type in valid_chart_types:
            config = {
                'fields': ['student_name'],
                'chart_type': chart_type
            }

            report = CustomReport(
                name='Test Report',
                created_by=self.teacher,
                config=config
            )

            # Should not raise exception
            report.validate_config()

    def test_soft_delete(self):
        """Test soft delete functionality."""
        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        self.assertFalse(report.is_deleted())

        report.soft_delete()

        self.assertTrue(report.is_deleted())
        self.assertIsNotNone(report.deleted_at)

    def test_restore_deleted_report(self):
        """Test restoring a soft-deleted report."""
        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        report.soft_delete()
        self.assertTrue(report.is_deleted())

        report.restore()
        self.assertFalse(report.is_deleted())
        self.assertIsNone(report.deleted_at)

    def test_share_report(self):
        """Test sharing report with colleagues."""
        report = CustomReport.objects.create(
            name='Shared Report',
            created_by=self.teacher,
            config={'fields': ['student_name']},
            is_shared=False
        )

        report.shared_with.add(self.teacher2)
        report.is_shared = True
        report.save()

        self.assertTrue(report.is_shared)
        self.assertIn(self.teacher2, report.shared_with.all())

    def test_get_field_options(self):
        """Test getting available field options."""
        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        options = report.get_field_options()

        self.assertIn('student', options)
        self.assertIn('student_name', options['student'])
        self.assertIn('assignment', options)
        self.assertIn('title', options['assignment'])

    def test_get_filter_options(self):
        """Test getting available filter options."""
        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        options = report.get_filter_options()

        self.assertIn('subject_id', options)
        self.assertIn('date_range', options)
        self.assertIn('grade_range', options)
        self.assertIn('status', options)

    def test_str_representation(self):
        """Test string representation of report."""
        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        expected = f"Test Report (by {self.teacher.get_full_name()})"
        self.assertEqual(str(report), expected)

    def test_queryset_ordering(self):
        """Test that reports are ordered by created_at descending."""
        report1 = CustomReport.objects.create(
            name='Report 1',
            created_by=self.teacher,
            config={'fields': ['student_name']}
        )

        # Create second report (should be more recent)
        report2 = CustomReport.objects.create(
            name='Report 2',
            created_by=self.teacher,
            config={'fields': ['grade']}
        )

        reports = CustomReport.objects.filter(created_by=self.teacher)
        self.assertEqual(reports[0].id, report2.id)
        self.assertEqual(reports[1].id, report1.id)


class ReportBuilderTests(TestCase):
    """Tests for ReportBuilder service."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='John',
            last_name='Doe'
        )

        self.student1 = User.objects.create_user(
            email='student1@test.com',
            password='testpass123',
            role='student',
            first_name='Alice',
            last_name='Student'
        )

    def test_report_builder_initialization(self):
        """Test initializing report builder."""
        config = {
            'fields': ['student_name', 'grade'],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)

        self.assertEqual(builder.report, report)
        self.assertEqual(builder.config, config)

    def test_validate_fields_valid(self):
        """Test field validation with valid fields."""
        config = {
            'fields': ['student_name', 'grade', 'submission_count'],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        fields = builder._validate_fields()

        self.assertEqual(len(fields), 3)
        self.assertIn('student_name', fields)

    def test_validate_fields_invalid(self):
        """Test field validation fails with invalid fields."""
        config = {
            'fields': ['invalid_field'],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)

        with self.assertRaises(ReportBuilderException):
            builder._validate_fields()

    def test_validate_fields_empty(self):
        """Test field validation fails with no fields."""
        config = {
            'fields': [],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Test Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)

        with self.assertRaises(ReportBuilderException):
            builder._validate_fields()

    def test_build_simple_report(self):
        """Test building a simple report."""
        config = {
            'fields': ['student_name', 'student_email'],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Simple Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        result = builder.build()

        self.assertIn('report_name', result)
        self.assertIn('data', result)
        self.assertIn('row_count', result)
        self.assertIn('execution_time_ms', result)
        self.assertEqual(result['report_name'], 'Simple Report')

    def test_build_report_with_chart(self):
        """Test building report with chart generation."""
        config = {
            'fields': ['student_name', 'grade'],
            'filters': {},
            'chart_type': 'bar'
        }

        report = CustomReport.objects.create(
            name='Chart Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        result = builder.build()

        self.assertIn('chart', result)

    def test_parse_date_range_valid(self):
        """Test parsing valid date range."""
        config = {
            'fields': ['student_name'],
            'filters': {
                'date_range': {
                    'start': '2025-01-01T00:00:00Z',
                    'end': '2025-12-31T23:59:59Z'
                }
            }
        }

        report = CustomReport.objects.create(
            name='Date Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        start, end = builder._parse_date_range(config['filters']['date_range'])

        self.assertIsNotNone(start)
        self.assertIsNotNone(end)

    def test_parse_date_range_invalid(self):
        """Test parsing invalid date range."""
        config = {
            'fields': ['student_name'],
            'filters': {
                'date_range': {
                    'start': 'invalid_date'
                }
            }
        }

        report = CustomReport.objects.create(
            name='Bad Date Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        start, end = builder._parse_date_range(config['filters']['date_range'])

        # Should return (None, None) on invalid date
        self.assertIsNone(start)

    def test_record_execution(self):
        """Test recording report execution."""
        config = {
            'fields': ['student_name'],
            'filters': {}
        }

        report = CustomReport.objects.create(
            name='Execution Test Report',
            created_by=self.teacher,
            config=config
        )

        builder = ReportBuilder(report)
        result = builder.build()

        # Check execution was recorded
        execution = CustomReportExecution.objects.filter(report=report).first()

        self.assertIsNotNone(execution)
        self.assertEqual(execution.executed_by, self.teacher)
        self.assertEqual(execution.rows_returned, result['row_count'])
        self.assertGreater(execution.execution_time_ms, 0)


class ReportTemplateTests(TestCase):
    """Tests for ReportTemplate model."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='John',
            last_name='Doe'
        )

    def test_create_template(self):
        """Test creating a report template."""
        template = ReportTemplate.objects.create(
            name='Class Progress Template',
            description='Template for class progress',
            template_type=ReportTemplate.TemplateType.CLASS_PROGRESS,
            base_config={
                'fields': ['student_name', 'grade', 'progress'],
                'chart_type': 'bar'
            },
            is_system=True
        )

        self.assertEqual(template.name, 'Class Progress Template')
        self.assertEqual(template.template_type, ReportTemplate.TemplateType.CLASS_PROGRESS)
        self.assertTrue(template.is_system)

    def test_create_custom_report_from_template(self):
        """Test creating a custom report from template."""
        template = ReportTemplate.objects.create(
            name='Class Progress Template',
            description='Template for class progress',
            template_type=ReportTemplate.TemplateType.CLASS_PROGRESS,
            base_config={
                'fields': ['student_name', 'grade'],
                'chart_type': 'bar'
            },
            is_system=True
        )

        custom_report = template.create_custom_report(
            user=self.teacher,
            name='My Custom Report',
            chart_type='line'
        )

        self.assertEqual(custom_report.name, 'My Custom Report')
        self.assertEqual(custom_report.created_by, self.teacher)
        self.assertEqual(custom_report.config['chart_type'], 'line')

    def test_template_str_representation(self):
        """Test string representation of template."""
        template = ReportTemplate.objects.create(
            name='Test Template',
            template_type=ReportTemplate.TemplateType.STUDENT_GRADES,
            base_config={'fields': ['student_name']},
            is_system=True
        )

        expected = 'Test Template (student_grades)'
        self.assertEqual(str(template), expected)
