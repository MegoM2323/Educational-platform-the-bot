"""
Email Report Service - Handles generation and delivery of reports via email.

Features:
- Report data generation (StudentReport, TutorWeeklyReport, TeacherWeeklyReport)
- CSV/Excel export with email attachment
- Email template rendering with summary
- Recipient management with unsubscribe functionality
- HTML email body with formatting
"""

import io
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from reports.models import StudentReport, TutorWeeklyReport, TeacherWeeklyReport
from reports.services.export import ReportExportService

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailReportService:
    """Service for generating and delivering reports via email."""

    # Report type mapping
    REPORT_TYPES = {
        'student_report': StudentReport,
        'tutor_weekly_report': TutorWeeklyReport,
        'teacher_weekly_report': TeacherWeeklyReport,
    }

    @staticmethod
    def generate_student_report_data(teacher_id: int, student_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate student report data for email.

        Args:
            teacher_id: ID of teacher
            student_id: ID of student
            limit: Maximum number of reports to include

        Returns:
            List of report dictionaries
        """
        reports = StudentReport.objects.filter(
            teacher_id=teacher_id,
            student_id=student_id
        ).select_related('teacher', 'student', 'parent').order_by('-created_at')[:limit]

        data = []
        for report in reports:
            data.append({
                'id': report.id,
                'title': report.title,
                'report_type': report.get_report_type_display(),
                'status': report.get_status_display(),
                'period_start': report.period_start.strftime('%Y-%m-%d'),
                'period_end': report.period_end.strftime('%Y-%m-%d'),
                'overall_grade': report.overall_grade or 'N/A',
                'progress_percentage': report.progress_percentage,
                'attendance_percentage': report.attendance_percentage,
                'behavior_rating': report.behavior_rating,
                'summary': report.description[:100] if report.description else 'No description',
            })

        return data

    @staticmethod
    def generate_tutor_weekly_report_data(tutor_id: int, student_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Generate tutor weekly report data for email.

        Args:
            tutor_id: ID of tutor
            student_id: ID of student
            limit: Maximum number of reports to include

        Returns:
            List of report dictionaries
        """
        reports = TutorWeeklyReport.objects.filter(
            tutor_id=tutor_id,
            student_id=student_id
        ).select_related('tutor', 'student', 'parent').order_by('-week_start')[:limit]

        data = []
        for report in reports:
            data.append({
                'id': report.id,
                'week_start': report.week_start.strftime('%Y-%m-%d'),
                'week_end': report.week_end.strftime('%Y-%m-%d'),
                'title': report.title,
                'status': report.get_status_display(),
                'summary': report.summary[:200] if report.summary else 'No summary',
                'progress_percentage': report.progress_percentage,
                'attendance_days': report.attendance_days,
                'total_days': report.total_days,
            })

        return data

    @staticmethod
    def generate_teacher_weekly_report_data(teacher_id: int, student_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Generate teacher weekly report data for email.

        Args:
            teacher_id: ID of teacher
            student_id: ID of student
            limit: Maximum number of reports to include

        Returns:
            List of report dictionaries
        """
        reports = TeacherWeeklyReport.objects.filter(
            teacher_id=teacher_id,
            student_id=student_id
        ).select_related('teacher', 'student', 'tutor', 'subject').order_by('-week_start')[:limit]

        data = []
        for report in reports:
            data.append({
                'id': report.id,
                'week_start': report.week_start.strftime('%Y-%m-%d'),
                'week_end': report.week_end.strftime('%Y-%m-%d'),
                'title': report.title,
                'subject': report.subject.name if report.subject else 'No subject',
                'status': report.get_status_display(),
                'summary': report.summary[:200] if report.summary else 'No summary',
                'average_score': float(report.average_score) if report.average_score else 0.0,
                'assignments_completed': report.assignments_completed,
                'assignments_total': report.assignments_total,
            })

        return data

    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]]) -> bytes:
        """
        Export data to CSV format.

        Args:
            data: List of dictionaries to export

        Returns:
            CSV file as bytes
        """
        if not data:
            return b""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue().encode('utf-8')

    @staticmethod
    def export_to_excel(data: List[Dict[str, Any]]) -> bytes:
        """
        Export data to Excel format.

        Args:
            data: List of dictionaries to export

        Returns:
            Excel file as bytes
        """
        import csv as csv_module
        if not data:
            return b""

        output = io.BytesIO()
        workbook = ReportExportService.create_workbook(data)
        workbook.save(output)
        output.seek(0)

        return output.getvalue()

    @staticmethod
    def send_report_email(
        recipient_email: str,
        recipient_name: str,
        subject: str,
        report_data: List[Dict[str, Any]],
        export_format: str = 'csv',
        report_type: str = 'general',
        unsubscribe_token: Optional[str] = None,
    ) -> bool:
        """
        Send report via email with attachment.

        Args:
            recipient_email: Email address of recipient
            recipient_name: Full name of recipient
            subject: Email subject
            report_data: List of report dictionaries
            export_format: Export format (csv, xlsx, pdf)
            report_type: Type of report
            unsubscribe_token: Token for unsubscribe link

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Validate email address
            if not recipient_email:
                logger.warning(f"No email address for recipient {recipient_name}")
                return False

            # Prepare attachment
            attachment_filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if export_format == 'xlsx':
                attachment_content = EmailReportService.export_to_excel(report_data)
                attachment_filename += ".xlsx"
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                # Default to CSV
                attachment_content = EmailReportService.export_to_csv(report_data)
                attachment_filename += ".csv"
                content_type = "text/csv"

            # Create HTML email body
            html_body = EmailReportService.render_email_template(
                recipient_name=recipient_name,
                report_type=report_type,
                report_summary=EmailReportService.get_report_summary(report_data),
                unsubscribe_token=unsubscribe_token,
            )

            # Create email message
            email = EmailMessage(
                subject=subject,
                body=html_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )

            # Attach file
            email.attach(
                filename=attachment_filename,
                content=attachment_content,
                mimetype=content_type
            )

            # Set HTML content type
            email.content_subtype = "html"

            # Send email
            email.send(fail_silently=False)

            logger.info(f"Report email sent to {recipient_email} (type={report_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to send report email to {recipient_email}: {e}", exc_info=True)
            return False

    @staticmethod
    def render_email_template(
        recipient_name: str,
        report_type: str,
        report_summary: str,
        unsubscribe_token: Optional[str] = None,
    ) -> str:
        """
        Render email template with report summary.

        Args:
            recipient_name: Name of recipient
            report_type: Type of report
            report_summary: Summary of report content
            unsubscribe_token: Token for unsubscribe link

        Returns:
            HTML email body
        """
        try:
            context = {
                'recipient_name': recipient_name,
                'report_type': EmailReportService._get_report_type_label(report_type),
                'report_summary': report_summary,
                'unsubscribe_token': unsubscribe_token,
                'current_year': datetime.now().year,
                'platform_name': getattr(settings, 'PLATFORM_NAME', 'THE BOT Platform'),
            }

            html_body = render_to_string(
                'emails/report_schedule_email.html',
                context
            )

            return html_body

        except Exception as e:
            logger.error(f"Failed to render email template: {e}", exc_info=True)
            # Fallback to plain text
            return f"""
            <html>
            <body>
                <h2>Report: {EmailReportService._get_report_type_label(report_type)}</h2>
                <p>Dear {recipient_name},</p>
                <p>Your scheduled report is attached below:</p>
                <p>{report_summary}</p>
                <p>Best regards,<br/>THE BOT Platform</p>
            </body>
            </html>
            """

    @staticmethod
    def get_report_summary(data: List[Dict[str, Any]], max_items: int = 3) -> str:
        """
        Generate summary of report data for email body.

        Args:
            data: List of report dictionaries
            max_items: Maximum items to include in summary

        Returns:
            HTML summary string
        """
        if not data:
            return "<p>No reports available.</p>"

        summary = "<ul>"
        for item in data[:max_items]:
            title = item.get('title') or item.get('summary', 'Report')
            if len(title) > 100:
                title = title[:97] + "..."
            summary += f"<li>{title}</li>"

        if len(data) > max_items:
            summary += f"<li>... and {len(data) - max_items} more</li>"

        summary += "</ul>"

        return summary

    @staticmethod
    def _get_report_type_label(report_type: str) -> str:
        """Get readable label for report type."""
        labels = {
            'student_report': 'Student Report',
            'tutor_weekly_report': 'Tutor Weekly Report',
            'teacher_weekly_report': 'Teacher Weekly Report',
            'general': 'General Report',
        }
        return labels.get(report_type, report_type.replace('_', ' ').title())


# CSV import for export service
import csv
