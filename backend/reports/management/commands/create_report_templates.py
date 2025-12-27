"""
Management command to create default system report templates for the Custom Report Builder.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from reports.models import CustomReportBuilderTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default system report templates for custom report builder'

    def handle(self, *args, **options):
        """Create default system templates."""

        templates = [
            {
                'name': 'Class Progress Report',
                'description': 'Track overall class progress on assigned materials',
                'template_type': CustomReportBuilderTemplate.TemplateType.CLASS_PROGRESS,
                'base_config': {
                    'fields': ['student_name', 'progress', 'submission_count', 'last_submission_date'],
                    'filters': {'subject_id': None},
                    'chart_type': 'bar',
                    'sort_by': 'progress',
                    'sort_order': 'desc'
                },
                'is_system': True
            },
            {
                'name': 'Student Grade Overview',
                'description': 'View overall grades and grade distribution',
                'template_type': CustomReportBuilderTemplate.TemplateType.STUDENT_GRADES,
                'base_config': {
                    'fields': ['student_name', 'student_email', 'grade', 'submission_count'],
                    'filters': {},
                    'chart_type': 'bar',
                    'sort_by': 'grade',
                    'sort_order': 'desc'
                },
                'is_system': True
            },
            {
                'name': 'Assignment Performance Analysis',
                'description': 'Analyze how students performed on specific assignments',
                'template_type': CustomReportBuilderTemplate.TemplateType.ASSIGNMENT_ANALYSIS,
                'base_config': {
                    'fields': ['title', 'avg_score', 'submission_rate', 'completion_rate', 'late_submissions'],
                    'filters': {},
                    'chart_type': 'bar',
                    'sort_by': 'avg_score',
                    'sort_order': 'desc'
                },
                'is_system': True
            },
            {
                'name': 'Attendance Tracking',
                'description': 'Track student attendance rates',
                'template_type': CustomReportBuilderTemplate.TemplateType.ATTENDANCE,
                'base_config': {
                    'fields': ['student_name', 'attendance', 'submission_count'],
                    'filters': {},
                    'chart_type': 'pie',
                    'sort_by': 'attendance',
                    'sort_order': 'desc'
                },
                'is_system': True
            },
            {
                'name': 'Student Engagement Metrics',
                'description': 'Measure student engagement based on activity',
                'template_type': CustomReportBuilderTemplate.TemplateType.ENGAGEMENT,
                'base_config': {
                    'fields': ['student_name', 'submission_count', 'progress', 'last_submission_date'],
                    'filters': {},
                    'chart_type': 'line',
                    'sort_by': 'submission_count',
                    'sort_order': 'desc'
                },
                'is_system': True
            },
        ]

        created_count = 0
        skipped_count = 0

        for template_data in templates:
            name = template_data['name']
            template_type = template_data['template_type']

            # Check if template already exists
            existing = CustomReportBuilderTemplate.objects.filter(
                name=name,
                template_type=template_type,
                is_system=True
            ).exists()

            if existing:
                self.stdout.write(
                    self.style.WARNING(f'⊘ Template "{name}" already exists, skipping')
                )
                skipped_count += 1
                continue

            try:
                CustomReportBuilderTemplate.objects.create(**template_data)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created template "{name}"')
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to create template "{name}": {str(e)}')
                )

        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} templates'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} templates'))
        self.stdout.write('='*50)
