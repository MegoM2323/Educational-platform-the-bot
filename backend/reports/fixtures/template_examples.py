"""
Example report templates for different report types.

These templates serve as reference implementations and can be used
as defaults when creating new reports.
"""

from reports.models import ReportTemplate, Report
from django.contrib.auth import get_user_model

User = get_user_model()


def create_example_templates(admin_user=None):
    """
    Create example report templates for different report types.

    Args:
        admin_user: User instance to assign as creator (default: first admin user)
    """
    if not admin_user:
        admin_user = User.objects.filter(role='admin').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            raise ValueError("No admin user found. Please create an admin user first.")

    # Student Progress Template
    student_progress_template = ReportTemplate.objects.create(
        name='Standard Student Progress Report',
        description='Standard template for tracking student progress and performance',
        type=Report.Type.STUDENT_PROGRESS,
        created_by=admin_user,
        is_default=True,
        sections=[
            {
                'name': 'summary',
                'fields': ['period', 'student_name', 'overall_assessment'],
                'description': 'Executive summary of student performance'
            },
            {
                'name': 'progress',
                'fields': ['completed_assignments', 'total_assignments', 'progress_percentage', 'trend'],
                'description': 'Assignment completion and progress metrics'
            },
            {
                'name': 'metrics',
                'fields': ['average_score', 'attendance_percentage', 'time_spent'],
                'description': 'Key performance metrics'
            },
            {
                'name': 'achievements',
                'fields': ['achievements_list', 'improvements'],
                'description': 'Student achievements and improvements'
            },
            {
                'name': 'concerns',
                'fields': ['challenges', 'learning_gaps', 'areas_for_improvement'],
                'description': 'Areas of concern and improvement opportunities'
            },
            {
                'name': 'recommendations',
                'fields': ['next_steps', 'suggested_resources', 'teacher_notes'],
                'description': 'Recommendations for continued progress'
            }
        ],
        layout_config={
            'orientation': 'portrait',
            'page_size': 'a4',
            'margins': {
                'top': 1.0,
                'bottom': 1.0,
                'left': 1.0,
                'right': 1.0
            },
            'include_header': True,
            'include_footer': True,
            'include_page_numbers': True
        },
        default_format=ReportTemplate.Format.PDF
    )

    # Class Performance Template
    class_performance_template = ReportTemplate.objects.create(
        name='Class Performance Analysis',
        description='Template for analyzing overall class performance and statistics',
        type=Report.Type.CLASS_PERFORMANCE,
        created_by=admin_user,
        sections=[
            {
                'name': 'summary',
                'fields': ['class_name', 'total_students', 'reporting_period'],
                'description': 'Class overview'
            },
            {
                'name': 'metrics',
                'fields': ['average_score', 'average_progress', 'completion_rate', 'attendance_rate'],
                'description': 'Class-wide metrics and statistics'
            },
            {
                'name': 'performance',
                'fields': ['top_performers', 'struggling_students', 'score_distribution'],
                'description': 'Student performance breakdown'
            },
            {
                'name': 'engagement',
                'fields': ['participation_rate', 'assignment_submission_rate', 'activity_level'],
                'description': 'Student engagement metrics'
            },
            {
                'name': 'recommendations',
                'fields': ['class_strengths', 'areas_for_improvement', 'instructional_adjustments'],
                'description': 'Recommendations for class improvement'
            }
        ],
        layout_config={
            'orientation': 'landscape',
            'page_size': 'a4',
            'margins': {'top': 0.8, 'bottom': 0.8, 'left': 0.8, 'right': 0.8},
            'include_charts': True,
            'include_tables': True
        },
        default_format=ReportTemplate.Format.EXCEL
    )

    # Subject Analysis Template
    subject_analysis_template = ReportTemplate.objects.create(
        name='Subject Analysis Report',
        description='Detailed analysis of student performance in a specific subject',
        type=Report.Type.SUBJECT_ANALYSIS,
        created_by=admin_user,
        sections=[
            {
                'name': 'summary',
                'fields': ['subject_name', 'teacher_name', 'period'],
                'description': 'Subject overview'
            },
            {
                'name': 'metrics',
                'fields': ['class_average', 'topic_breakdown', 'skill_assessment'],
                'description': 'Subject-specific metrics'
            },
            {
                'name': 'progress',
                'fields': ['topic_progress', 'concept_mastery', 'skill_development'],
                'description': 'Student progress in subject topics'
            },
            {
                'name': 'performance',
                'fields': ['grade_distribution', 'assessment_scores', 'common_mistakes'],
                'description': 'Performance analysis'
            },
            {
                'name': 'recommendations',
                'fields': ['remediation_areas', 'enrichment_opportunities', 'curriculum_adjustments'],
                'description': 'Recommendations for instruction'
            }
        ],
        layout_config={
            'orientation': 'portrait',
            'page_size': 'a4',
            'margins': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0},
            'include_visualizations': True
        },
        default_format=ReportTemplate.Format.PDF
    )

    # Weekly Summary Template
    weekly_summary_template = ReportTemplate.objects.create(
        name='Weekly Summary Report',
        description='Weekly overview of student activities and progress',
        type=Report.Type.WEEKLY_SUMMARY,
        created_by=admin_user,
        sections=[
            {
                'name': 'summary',
                'fields': ['week_start', 'week_end', 'student_name'],
                'description': 'Week overview'
            },
            {
                'name': 'attendance',
                'fields': ['attendance_days', 'total_days', 'attendance_percentage'],
                'description': 'Weekly attendance'
            },
            {
                'name': 'achievements',
                'fields': ['completed_assignments', 'new_skills', 'improvements'],
                'description': 'Week achievements'
            },
            {
                'name': 'concerns',
                'fields': ['missing_assignments', 'challenges', 'areas_for_attention'],
                'description': 'Areas needing attention'
            },
            {
                'name': 'recommendations',
                'fields': ['next_week_focus', 'resources', 'parent_notes'],
                'description': 'Next steps and recommendations'
            }
        ],
        layout_config={
            'orientation': 'portrait',
            'page_size': 'letter',
            'margins': {'top': 0.75, 'bottom': 0.75, 'left': 0.75, 'right': 0.75}
        },
        default_format=ReportTemplate.Format.PDF
    )

    # Monthly Summary Template
    monthly_summary_template = ReportTemplate.objects.create(
        name='Monthly Summary Report',
        description='Comprehensive monthly overview of student progress and activities',
        type=Report.Type.MONTHLY_SUMMARY,
        created_by=admin_user,
        sections=[
            {
                'name': 'summary',
                'fields': ['month', 'year', 'student_name', 'overall_performance'],
                'description': 'Monthly overview'
            },
            {
                'name': 'metrics',
                'fields': ['assignments_completed', 'average_score', 'hours_spent', 'participation_score'],
                'description': 'Monthly metrics'
            },
            {
                'name': 'progress',
                'fields': ['topics_covered', 'concepts_mastered', 'skills_improved'],
                'description': 'Learning progress'
            },
            {
                'name': 'achievements',
                'fields': ['milestones_reached', 'awards_earned', 'growth_areas'],
                'description': 'Notable achievements'
            },
            {
                'name': 'concerns',
                'fields': ['persistent_challenges', 'attendance_issues', 'behavioral_notes'],
                'description': 'Concerns and observations'
            },
            {
                'name': 'recommendations',
                'fields': ['suggested_actions', 'resources', 'parent_communication'],
                'description': 'Forward recommendations'
            }
        ],
        layout_config={
            'orientation': 'portrait',
            'page_size': 'a4',
            'margins': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0},
            'include_summary_charts': True
        },
        default_format=ReportTemplate.Format.PDF
    )

    # Custom Report Template
    custom_template = ReportTemplate.objects.create(
        name='Blank Custom Report',
        description='Blank template for creating custom reports',
        type=Report.Type.CUSTOM,
        created_by=admin_user,
        sections=[
            {
                'name': 'custom',
                'fields': [],
                'description': 'Custom content section'
            }
        ],
        layout_config={
            'orientation': 'portrait',
            'page_size': 'a4',
            'margins': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0}
        },
        default_format=ReportTemplate.Format.PDF
    )

    return {
        'student_progress': student_progress_template,
        'class_performance': class_performance_template,
        'subject_analysis': subject_analysis_template,
        'weekly_summary': weekly_summary_template,
        'monthly_summary': monthly_summary_template,
        'custom': custom_template,
    }


# Section type reference
VALID_SECTION_TYPES = {
    'summary': 'Executive summary or overview of the report',
    'metrics': 'Key performance indicators and statistics',
    'progress': 'Progress tracking and milestone updates',
    'achievements': 'Student achievements and accomplishments',
    'concerns': 'Areas of concern or challenges',
    'recommendations': 'Recommendations and next steps',
    'attendance': 'Attendance and participation data',
    'grades': 'Grade information and assessment results',
    'performance': 'Overall performance analysis',
    'engagement': 'Student engagement metrics',
    'behavioral': 'Behavioral observations and notes',
    'custom': 'Custom content section',
}

# Layout configuration reference
LAYOUT_DEFAULTS = {
    'orientation': 'portrait',  # portrait, landscape
    'page_size': 'a4',  # a4, letter, legal, a3, a5
    'margins': {
        'top': 1.0,  # in inches
        'bottom': 1.0,
        'left': 1.0,
        'right': 1.0,
    },
    'include_header': True,
    'include_footer': True,
    'include_page_numbers': True,
}

# Format options
FORMAT_OPTIONS = {
    'pdf': 'PDF - Best for printing and sharing',
    'excel': 'Excel - Spreadsheet format with data',
    'json': 'JSON - Machine-readable format',
    'csv': 'CSV - Comma-separated values',
}
