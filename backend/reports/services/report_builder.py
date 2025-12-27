"""
Custom Report Builder Service

Generates reports from user-defined configurations.
Handles data fetching, filtering, field selection, and chart generation.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal

from django.db.models import Q, Avg, Count, Sum, Case, When, Value, CharField, F
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from assignments.models import Assignment, AssignmentSubmission, AssignmentAnswer
from materials.models import MaterialProgress
from ..models import CustomReport, CustomReportExecution

User = get_user_model()
logger = logging.getLogger(__name__)


class ReportBuilderException(Exception):
    """Custom exception for report building errors."""
    pass


class ReportBuilder:
    """
    Builds custom reports based on user-defined configurations.
    Handles data fetching, filtering, field selection, and aggregation.
    """

    # Field definitions and their source
    FIELD_SOURCES = {
        'student_name': {
            'source': 'user',
            'field': 'get_full_name',
            'description': 'Student full name'
        },
        'student_email': {
            'source': 'user',
            'field': 'email',
            'description': 'Student email address'
        },
        'grade': {
            'source': 'calculated',
            'description': 'Overall grade (0-100)'
        },
        'submission_count': {
            'source': 'calculated',
            'description': 'Number of submissions'
        },
        'progress': {
            'source': 'calculated',
            'description': 'Progress percentage'
        },
        'attendance': {
            'source': 'calculated',
            'description': 'Attendance percentage'
        },
        'last_submission_date': {
            'source': 'calculated',
            'description': 'Date of last submission'
        },
        'title': {
            'source': 'assignment',
            'field': 'title',
            'description': 'Assignment title'
        },
        'due_date': {
            'source': 'assignment',
            'field': 'due_date',
            'description': 'Assignment due date'
        },
        'avg_score': {
            'source': 'calculated',
            'description': 'Average score on assignment'
        },
        'submission_rate': {
            'source': 'calculated',
            'description': 'Submission rate (%)'
        },
        'completion_rate': {
            'source': 'calculated',
            'description': 'Completion rate (%)'
        },
        'late_submissions': {
            'source': 'calculated',
            'description': 'Number of late submissions'
        },
        'total_submissions': {
            'source': 'calculated',
            'description': 'Total submissions received'
        },
        'score': {
            'source': 'submission',
            'field': 'score',
            'description': 'Submission score'
        },
        'feedback': {
            'source': 'submission',
            'field': 'feedback',
            'description': 'Grading feedback'
        },
        'graded_by': {
            'source': 'submission',
            'field': 'graded_by',
            'description': 'Name of grader'
        },
        'graded_at': {
            'source': 'submission',
            'field': 'graded_at',
            'description': 'Grading date/time'
        },
        'status': {
            'source': 'submission',
            'field': 'status',
            'description': 'Submission status'
        },
    }

    def __init__(self, report: CustomReport):
        """
        Initialize report builder.

        Args:
            report: CustomReport instance
        """
        self.report = report
        self.config = report.config
        self.start_time = time.time()

    def build(self) -> Dict[str, Any]:
        """
        Build the report based on configuration.

        Returns:
            Report data with metadata
        """
        try:
            # Extract and validate config
            fields = self._validate_fields()
            filters = self.config.get('filters', {})

            # Fetch data
            data = self._fetch_data(fields, filters)

            # Apply sorting if specified
            if 'sort_by' in self.config:
                data = self._sort_data(data, self.config['sort_by'], self.config.get('sort_order', 'asc'))

            # Apply pagination if specified
            limit = self.config.get('limit')
            if limit:
                data = data[:limit]

            # Generate chart if requested
            chart_data = None
            if 'chart_type' in self.config:
                chart_data = self._generate_chart_data(data, self.config['chart_type'])

            execution_time = int((time.time() - self.start_time) * 1000)

            result = {
                'report_name': self.report.name,
                'description': self.report.description,
                'config': self.config,
                'fields': fields,
                'data': data,
                'row_count': len(data),
                'execution_time_ms': execution_time,
                'chart': chart_data,
                'generated_at': timezone.now().isoformat(),
            }

            # Record execution
            self._record_execution(len(data), execution_time, result)

            return result

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}", exc_info=True)
            raise ReportBuilderException(f"Failed to build report: {str(e)}")

    def _validate_fields(self) -> List[str]:
        """
        Validate requested fields are available.

        Returns:
            List of validated field names
        """
        fields = self.config.get('fields', [])

        if not fields:
            raise ReportBuilderException("No fields specified in config")

        invalid_fields = [f for f in fields if f not in self.FIELD_SOURCES]
        if invalid_fields:
            raise ReportBuilderException(
                f"Invalid fields: {', '.join(invalid_fields)}"
            )

        return fields

    def _fetch_data(self, fields: List[str], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch data based on requested fields and filters.

        Args:
            fields: List of fields to include
            filters: Filter configuration

        Returns:
            List of data rows
        """
        data = []

        # Determine data source based on fields
        if any(f in ['student_name', 'student_email', 'grade', 'submission_count', 'progress', 'attendance', 'last_submission_date'] for f in fields):
            data = self._fetch_student_data(fields, filters)
        elif any(f in ['title', 'due_date', 'avg_score', 'submission_rate', 'completion_rate', 'late_submissions', 'total_submissions'] for f in fields):
            data = self._fetch_assignment_data(fields, filters)
        elif any(f in ['score', 'feedback', 'graded_by', 'graded_at', 'status'] for f in fields):
            data = self._fetch_submission_data(fields, filters)

        return data

    def _fetch_student_data(self, fields: List[str], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch student report data.

        Args:
            fields: Fields to include
            filters: Filter configuration

        Returns:
            List of student data rows
        """
        # Get students
        students = User.objects.filter(role='student')

        # Apply subject filter
        if 'subject_id' in filters:
            subject_id = filters['subject_id']
            students = students.filter(
                Q(enrolled_subjects__subject_id=subject_id) |
                Q(student_profile__subjects__id=subject_id)
            )

        # Apply class filter
        if 'class_id' in filters:
            students = students.filter(student_profile__class_id=filters['class_id'])

        # Apply date range filter
        date_start, date_end = self._parse_date_range(filters.get('date_range'))
        if date_start:
            students = students.filter(
                submissions__submitted_at__gte=date_start
            )
        if date_end:
            students = students.filter(
                submissions__submitted_at__lte=date_end
            )

        # Build result rows
        rows = []
        for student in students.distinct():
            row = {}

            for field in fields:
                if field == 'student_name':
                    row[field] = student.get_full_name()
                elif field == 'student_email':
                    row[field] = student.email
                elif field == 'grade':
                    row[field] = self._calculate_student_grade(student, filters)
                elif field == 'submission_count':
                    row[field] = self._count_submissions(student, filters)
                elif field == 'progress':
                    row[field] = self._calculate_progress(student, filters)
                elif field == 'attendance':
                    row[field] = self._calculate_attendance(student, filters)
                elif field == 'last_submission_date':
                    row[field] = self._get_last_submission_date(student, filters)

            rows.append(row)

        return rows

    def _fetch_assignment_data(self, fields: List[str], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch assignment report data.

        Args:
            fields: Fields to include
            filters: Filter configuration

        Returns:
            List of assignment data rows
        """
        # Get assignments
        assignments = Assignment.objects.all()

        # Apply subject filter
        if 'subject_id' in filters:
            assignments = assignments.filter(subject_id=filters['subject_id'])

        # Apply assignment filter
        if 'assignment_id' in filters:
            assignments = assignments.filter(id=filters['assignment_id'])

        # Apply date range filter
        date_start, date_end = self._parse_date_range(filters.get('date_range'))
        if date_start:
            assignments = assignments.filter(created_at__gte=date_start)
        if date_end:
            assignments = assignments.filter(created_at__lte=date_end)

        # Build result rows
        rows = []
        for assignment in assignments:
            row = {}

            for field in fields:
                if field == 'title':
                    row[field] = assignment.title
                elif field == 'due_date':
                    row[field] = assignment.due_date.isoformat() if assignment.due_date else None
                elif field == 'avg_score':
                    row[field] = self._calculate_avg_score(assignment, filters)
                elif field == 'submission_rate':
                    row[field] = self._calculate_submission_rate(assignment, filters)
                elif field == 'completion_rate':
                    row[field] = self._calculate_completion_rate(assignment, filters)
                elif field == 'late_submissions':
                    row[field] = self._count_late_submissions(assignment, filters)
                elif field == 'total_submissions':
                    row[field] = self._count_total_submissions(assignment, filters)

            rows.append(row)

        return rows

    def _fetch_submission_data(self, fields: List[str], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch submission/grading report data.

        Args:
            fields: Fields to include
            filters: Filter configuration

        Returns:
            List of submission data rows
        """
        # Get submissions
        submissions = AssignmentSubmission.objects.select_related(
            'assignment', 'student', 'graded_by'
        )

        # Apply status filter
        if 'status' in filters:
            status_filter = filters['status']
            if status_filter == 'submitted':
                submissions = submissions.exclude(submitted_at__isnull=True)
            elif status_filter == 'graded':
                submissions = submissions.exclude(graded_at__isnull=True)
            elif status_filter == 'pending':
                submissions = submissions.filter(graded_at__isnull=True, submitted_at__isnull=False)
            elif status_filter == 'late':
                submissions = submissions.filter(
                    submitted_at__gt=F('assignment__due_date')
                )

        # Apply date range filter
        date_start, date_end = self._parse_date_range(filters.get('date_range'))
        if date_start:
            submissions = submissions.filter(submitted_at__gte=date_start)
        if date_end:
            submissions = submissions.filter(submitted_at__lte=date_end)

        # Apply assignment filter
        if 'assignment_id' in filters:
            submissions = submissions.filter(assignment_id=filters['assignment_id'])

        # Apply student filter
        if 'student_id' in filters:
            submissions = submissions.filter(student_id=filters['student_id'])

        # Apply grade range filter
        if 'grade_range' in filters:
            grade_range = filters['grade_range']
            min_grade = grade_range.get('min', 0)
            max_grade = grade_range.get('max', 100)
            submissions = submissions.filter(score__gte=min_grade, score__lte=max_grade)

        # Build result rows
        rows = []
        for submission in submissions:
            row = {}

            for field in fields:
                if field == 'score':
                    row[field] = float(submission.score) if submission.score else None
                elif field == 'feedback':
                    row[field] = submission.feedback
                elif field == 'graded_by':
                    row[field] = submission.graded_by.get_full_name() if submission.graded_by else None
                elif field == 'graded_at':
                    row[field] = submission.graded_at.isoformat() if submission.graded_at else None
                elif field == 'status':
                    if submission.graded_at:
                        row[field] = 'graded'
                    elif submission.submitted_at:
                        if submission.submitted_at > submission.assignment.due_date:
                            row[field] = 'late'
                        else:
                            row[field] = 'submitted'
                    else:
                        row[field] = 'pending'

            rows.append(row)

        return rows

    def _sort_data(self, data: List[Dict[str, Any]], sort_field: str, sort_order: str = 'asc') -> List[Dict[str, Any]]:
        """
        Sort report data.

        Args:
            data: Data to sort
            sort_field: Field to sort by
            sort_order: 'asc' or 'desc'

        Returns:
            Sorted data
        """
        reverse = sort_order == 'desc'
        try:
            return sorted(data, key=lambda x: x.get(sort_field, 0), reverse=reverse)
        except Exception as e:
            logger.warning(f"Sorting failed: {str(e)}")
            return data

    def _generate_chart_data(self, data: List[Dict[str, Any]], chart_type: str) -> Dict[str, Any]:
        """
        Generate chart data from report data.

        Args:
            data: Report data
            chart_type: Type of chart (bar, line, pie, histogram, scatter)

        Returns:
            Chart data for frontend
        """
        if not data:
            return None

        try:
            if chart_type == 'bar':
                return self._generate_bar_chart(data)
            elif chart_type == 'line':
                return self._generate_line_chart(data)
            elif chart_type == 'pie':
                return self._generate_pie_chart(data)
            elif chart_type == 'histogram':
                return self._generate_histogram(data)
            elif chart_type == 'scatter':
                return self._generate_scatter_plot(data)
        except Exception as e:
            logger.error(f"Chart generation failed: {str(e)}")
            return None

        return None

    def _generate_bar_chart(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate bar chart data."""
        if not data:
            return None

        # Get first text field as labels and first numeric field as values
        labels = []
        values = []

        for row in data[:50]:  # Limit to 50 items for chart readability
            for key, value in row.items():
                if key not in labels:
                    if isinstance(value, (int, float)):
                        labels.append(next((k for k, v in row.items() if isinstance(v, str)), 'item'))
                        values.append(value)
                        break

        return {
            'type': 'bar',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Values',
                    'data': values,
                    'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 1
                }
            ]
        }

    def _generate_line_chart(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate line chart data."""
        if not data:
            return None

        # Similar to bar chart but for line
        return self._generate_bar_chart(data)

    def _generate_pie_chart(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate pie chart data."""
        if not data:
            return None

        labels = []
        values = []

        for row in data[:8]:  # Limit pie slices
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    labels.append(list(row.values())[0] if isinstance(list(row.values())[0], str) else key)
                    values.append(value)
                    break

        return {
            'type': 'pie',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Values',
                    'data': values,
                    'backgroundColor': [
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(153, 102, 255, 0.6)',
                        'rgba(255, 159, 64, 0.6)',
                        'rgba(199, 199, 199, 0.6)',
                        'rgba(83, 102, 255, 0.6)',
                    ]
                }
            ]
        }

    def _generate_histogram(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate histogram data."""
        return self._generate_bar_chart(data)

    def _generate_scatter_plot(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate scatter plot data."""
        if not data:
            return None

        # Extract numeric columns
        points = []
        for row in data:
            numeric_values = [v for v in row.values() if isinstance(v, (int, float))]
            if len(numeric_values) >= 2:
                points.append(numeric_values[:2])

        return {
            'type': 'scatter',
            'data': points,
            'label': 'Data points'
        }

    # Helper methods for calculations
    def _calculate_student_grade(self, student: User, filters: Dict[str, Any]) -> float:
        """Calculate overall student grade."""
        submissions = AssignmentSubmission.objects.filter(student=student)

        if 'subject_id' in filters:
            submissions = submissions.filter(assignment__subject_id=filters['subject_id'])

        date_start, date_end = self._parse_date_range(filters.get('date_range'))
        if date_start:
            submissions = submissions.filter(graded_at__gte=date_start)
        if date_end:
            submissions = submissions.filter(graded_at__lte=date_end)

        avg = submissions.filter(score__isnull=False).aggregate(Avg('score'))['score__avg']
        return float(avg) if avg else 0.0

    def _count_submissions(self, student: User, filters: Dict[str, Any]) -> int:
        """Count student submissions."""
        submissions = AssignmentSubmission.objects.filter(
            student=student,
            submitted_at__isnull=False
        )

        if 'subject_id' in filters:
            submissions = submissions.filter(assignment__subject_id=filters['subject_id'])

        date_start, date_end = self._parse_date_range(filters.get('date_range'))
        if date_start:
            submissions = submissions.filter(submitted_at__gte=date_start)
        if date_end:
            submissions = submissions.filter(submitted_at__lte=date_end)

        return submissions.count()

    def _calculate_progress(self, student: User, filters: Dict[str, Any]) -> float:
        """Calculate student progress percentage."""
        progress_data = MaterialProgress.objects.filter(student=student)

        if 'subject_id' in filters:
            progress_data = progress_data.filter(material__subject_id=filters['subject_id'])

        completed = progress_data.filter(is_completed=True).count()
        total = progress_data.count()

        return (completed / total * 100) if total > 0 else 0.0

    def _calculate_attendance(self, student: User, filters: Dict[str, Any]) -> float:
        """Calculate attendance percentage."""
        # This is a placeholder - actual attendance tracking would depend on your system
        return 0.0

    def _get_last_submission_date(self, student: User, filters: Dict[str, Any]) -> Optional[str]:
        """Get date of last submission."""
        submission = AssignmentSubmission.objects.filter(
            student=student,
            submitted_at__isnull=False
        ).order_by('-submitted_at').first()

        return submission.submitted_at.isoformat() if submission else None

    def _calculate_avg_score(self, assignment: Assignment, filters: Dict[str, Any]) -> float:
        """Calculate average score for assignment."""
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            score__isnull=False
        )

        if 'student_id' in filters:
            submissions = submissions.filter(student_id=filters['student_id'])

        avg = submissions.aggregate(Avg('score'))['score__avg']
        return float(avg) if avg else 0.0

    def _calculate_submission_rate(self, assignment: Assignment, filters: Dict[str, Any]) -> float:
        """Calculate submission rate percentage."""
        total_students = User.objects.filter(role='student').count()
        submitted = AssignmentSubmission.objects.filter(
            assignment=assignment,
            submitted_at__isnull=False
        ).values('student').distinct().count()

        return (submitted / total_students * 100) if total_students > 0 else 0.0

    def _calculate_completion_rate(self, assignment: Assignment, filters: Dict[str, Any]) -> float:
        """Calculate completion rate percentage."""
        total_students = User.objects.filter(role='student').count()
        completed = AssignmentSubmission.objects.filter(
            assignment=assignment,
            graded_at__isnull=False
        ).values('student').distinct().count()

        return (completed / total_students * 100) if total_students > 0 else 0.0

    def _count_late_submissions(self, assignment: Assignment, filters: Dict[str, Any]) -> int:
        """Count late submissions."""
        if not assignment.due_date:
            return 0

        return AssignmentSubmission.objects.filter(
            assignment=assignment,
            submitted_at__gt=assignment.due_date
        ).count()

    def _count_total_submissions(self, assignment: Assignment, filters: Dict[str, Any]) -> int:
        """Count total submissions."""
        return AssignmentSubmission.objects.filter(
            assignment=assignment,
            submitted_at__isnull=False
        ).count()

    def _parse_date_range(self, date_range: Optional[Dict[str, str]]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse date range from config."""
        if not date_range:
            return None, None

        start = None
        end = None

        try:
            if 'start' in date_range:
                start = datetime.fromisoformat(date_range['start']).replace(tzinfo=timezone.utc)
            if 'end' in date_range:
                end = datetime.fromisoformat(date_range['end']).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            logger.warning(f"Invalid date range: {date_range}")

        return start, end

    def _record_execution(self, row_count: int, execution_time: int, result_summary: Dict[str, Any]):
        """Record report execution for audit trail."""
        try:
            CustomReportExecution.objects.create(
                report=self.report,
                executed_by=self.report.created_by,
                rows_returned=row_count,
                execution_time_ms=execution_time,
                result_summary={
                    'field_count': len(self.config.get('fields', [])),
                    'has_chart': 'chart_type' in self.config,
                    'filter_count': len(self.config.get('filters', {}))
                }
            )
        except Exception as e:
            logger.error(f"Failed to record execution: {str(e)}")
