"""
Celery tasks for data warehouse operations and scheduled report delivery.

Tasks:
- Refresh materialized views (daily)
- Warm analytics cache (before peak hours)
- Generate data warehouse statistics
- Send scheduled reports via email (daily, weekly, monthly)
- Execute scheduled report deliveries
- Send test emails for schedule configuration
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from django.db import connection
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def refresh_materialized_views(self):
    """
    Refresh all data warehouse materialized views.

    Scheduled daily (e.g., 2 AM UTC) to update analytics data.
    Uses CONCURRENTLY to avoid locks.

    Retries up to 3 times on failure.
    """
    try:
        from reports.queries.materialized_views import REFRESH_ALL_VIEWS

        with connection.cursor() as cursor:
            # Split refresh statements
            statements = [
                "REFRESH MATERIALIZED VIEW CONCURRENTLY student_grade_summary;",
                "REFRESH MATERIALIZED VIEW CONCURRENTLY class_progress_summary;",
                "REFRESH MATERIALIZED VIEW CONCURRENTLY teacher_workload;",
                "REFRESH MATERIALIZED VIEW CONCURRENTLY subject_performance;",
            ]

            results = {}
            for idx, stmt in enumerate(statements, 1):
                try:
                    start_time = datetime.now()
                    cursor.execute(stmt)
                    execution_time = (datetime.now() - start_time).total_seconds()
                    results[stmt.split()[4]] = {
                        'status': 'success',
                        'execution_time_seconds': execution_time
                    }
                    logger.info(f"✓ Refreshed view {idx}/4: {execution_time:.2f}s")
                except Exception as e:
                    results[stmt.split()[4]] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    logger.error(f"✗ Failed to refresh view: {e}")

        # Invalidate related caches
        cache.delete_pattern('warehouse_*')
        logger.info("Invalidated warehouse query cache")

        return {
            'task': 'refresh_materialized_views',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")

        # Retry with exponential backoff
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=e, countdown=retry_in)


@shared_task(bind=True, max_retries=2)
def warm_analytics_cache(self):
    """
    Pre-populate analytics cache before peak usage hours.

    Runs before business hours (e.g., 7 AM UTC) to warm commonly
    accessed queries and reduce initial user load times.

    Retries up to 2 times on failure.
    """
    try:
        from reports.services.warehouse import DataWarehouseService

        warehouse = DataWarehouseService(use_replica=True)

        # Warm engagement metrics
        logger.info("Warming engagement metrics cache...")
        warehouse.get_student_engagement_metrics(limit=50)

        # Warm top performers
        logger.info("Warming top performers cache...")
        warehouse.get_top_performers(limit=20)

        # Warm bottom performers
        logger.info("Warming bottom performers cache...")
        warehouse.get_bottom_performers(limit=20)

        logger.info("✓ Analytics cache warmed successfully")

        return {
            'task': 'warm_analytics_cache',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'caches_warmed': 3
        }

    except Exception as e:
        logger.error(f"Error warming analytics cache: {e}")

        # Retry with delay
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s
        raise self.retry(exc=e, countdown=retry_in)


@shared_task
def generate_warehouse_statistics():
    """
    Generate statistics about warehouse operations.

    Useful for monitoring and optimization:
    - Materialized view sizes
    - Query performance metrics
    - Cache hit rates
    """
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'views': {},
            'tables': {}
        }

        with connection.cursor() as cursor:
            # Get materialized view sizes
            views_query = """
                SELECT schemaname, matviewname, pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
                FROM pg_matviews
                WHERE matviewname IN ('student_grade_summary', 'class_progress_summary', 'teacher_workload', 'subject_performance')
                ORDER BY pg_total_relation_size(schemaname||'.'||matviewname) DESC;
            """

            try:
                cursor.execute(views_query)
                for row in cursor.fetchall():
                    schema, view_name, size = row
                    stats['views'][view_name] = {'size': size}
            except Exception as e:
                logger.debug(f"Could not fetch view sizes: {e}")

            # Get table row counts
            tables_query = """
                SELECT tablename, n_live_tup as row_count
                FROM pg_stat_user_tables
                WHERE tablename IN ('materials_materialsubmission', 'assignments_assignmentsubmission', 'accounts_user')
                ORDER BY n_live_tup DESC;
            """

            try:
                cursor.execute(tables_query)
                for row in cursor.fetchall():
                    table_name, row_count = row
                    stats['tables'][table_name] = {'rows': row_count}
            except Exception as e:
                logger.debug(f"Could not fetch table stats: {e}")

        logger.info(f"Warehouse statistics: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error generating warehouse statistics: {e}")
        return {'error': str(e)}


@shared_task
def create_materialized_views():
    """
    Create materialized views if they don't exist.

    Called during first deployment or migration.
    Safe to run multiple times (uses CREATE IF NOT EXISTS).
    """
    try:
        from reports.queries.materialized_views import (
            STUDENT_GRADE_SUMMARY_VIEW,
            CLASS_PROGRESS_SUMMARY_VIEW,
            TEACHER_WORKLOAD_VIEW,
            SUBJECT_PERFORMANCE_VIEW
        )

        views = [
            ('student_grade_summary', STUDENT_GRADE_SUMMARY_VIEW),
            ('class_progress_summary', CLASS_PROGRESS_SUMMARY_VIEW),
            ('teacher_workload', TEACHER_WORKLOAD_VIEW),
            ('subject_performance', SUBJECT_PERFORMANCE_VIEW),
        ]

        results = {}

        with connection.cursor() as cursor:
            for view_name, view_sql in views:
                try:
                    # Execute view creation (handles multiple statements)
                    for stmt in view_sql.split(';'):
                        if stmt.strip():
                            cursor.execute(stmt)
                    results[view_name] = {'status': 'created'}
                    logger.info(f"✓ Created materialized view: {view_name}")
                except Exception as e:
                    results[view_name] = {'status': 'error', 'error': str(e)}
                    logger.error(f"Error creating {view_name}: {e}")

        return {
            'task': 'create_materialized_views',
            'timestamp': datetime.now().isoformat(),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error creating materialized views: {e}")
        return {'error': str(e)}


# Scheduled Report Email Delivery Tasks

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 minutes
    retry_jitter=True
)
def send_scheduled_report(self, schedule_id: int, recipient_id: int) -> dict:
    """
    Send a scheduled report to a single recipient.

    Args:
        schedule_id: ID of ReportSchedule
        recipient_id: ID of User (recipient)

    Returns:
        dict with status and metadata
    """
    from reports.models import ReportSchedule, ReportScheduleRecipient, StudentReport, TutorWeeklyReport, TeacherWeeklyReport
    from reports.services.email_report import EmailReportService

    try:
        schedule = ReportSchedule.objects.select_related('created_by').get(id=schedule_id)
        recipient = User.objects.get(id=recipient_id)

        # Check if recipient is still subscribed
        try:
            schedule_recipient = ReportScheduleRecipient.objects.get(
                schedule_id=schedule_id,
                recipient_id=recipient_id
            )
            if not schedule_recipient.is_subscribed:
                logger.info(f"Recipient {recipient.email} unsubscribed from schedule {schedule_id}")
                return {
                    'success': False,
                    'status': 'skipped',
                    'reason': 'unsubscribed',
                    'schedule_id': schedule_id,
                    'recipient_id': recipient_id
                }
        except ReportScheduleRecipient.DoesNotExist:
            logger.warning(f"Recipient entry not found for {recipient.email} in schedule {schedule_id}")
            return {
                'success': False,
                'status': 'skipped',
                'reason': 'recipient_entry_not_found',
                'schedule_id': schedule_id,
                'recipient_id': recipient_id
            }

        # Generate report data based on report_type
        report_data = []
        subject = f"Report: {schedule.name or 'Scheduled Report'}"

        if schedule.report_type == ReportSchedule.ReportType.STUDENT_REPORT:
            # For student reports, get reports for this recipient (if teacher)
            if recipient.role == 'teacher':
                student_reports = StudentReport.objects.filter(
                    teacher_id=recipient_id,
                    status='sent'
                ).order_by('-created_at')[:10]

                for report in student_reports:
                    report_data.append({
                        'id': report.id,
                        'student': report.student.get_full_name(),
                        'title': report.title,
                        'type': report.get_report_type_display(),
                        'period': f"{report.period_start} to {report.period_end}",
                        'grade': report.overall_grade,
                        'progress': report.progress_percentage,
                    })

                subject = f"Weekly Student Reports - {datetime.now().strftime('%Y-%m-%d')}"

        elif schedule.report_type == ReportSchedule.ReportType.TUTOR_WEEKLY_REPORT:
            # For tutor reports, get reports for this tutor or parent
            if recipient.role == 'tutor':
                reports = TutorWeeklyReport.objects.filter(
                    tutor_id=recipient_id,
                    status='sent'
                ).order_by('-week_start')[:5]

                for report in reports:
                    report_data.append({
                        'id': report.id,
                        'student': report.student.get_full_name(),
                        'week': f"{report.week_start} to {report.week_end}",
                        'progress': report.progress_percentage,
                        'summary': report.summary[:100],
                    })

                subject = f"Tutor Weekly Reports - {datetime.now().strftime('%Y-%m-%d')}"

            elif recipient.role == 'parent':
                reports = TutorWeeklyReport.objects.filter(
                    parent_id=recipient_id,
                    status='sent'
                ).order_by('-week_start')[:5]

                for report in reports:
                    report_data.append({
                        'id': report.id,
                        'student': report.student.get_full_name(),
                        'week': f"{report.week_start} to {report.week_end}",
                        'progress': report.progress_percentage,
                        'summary': report.summary[:100],
                    })

                subject = f"Student Weekly Reports - {datetime.now().strftime('%Y-%m-%d')}"

        elif schedule.report_type == ReportSchedule.ReportType.TEACHER_WEEKLY_REPORT:
            # For teacher reports, get reports for this tutor
            if recipient.role == 'tutor':
                reports = TeacherWeeklyReport.objects.filter(
                    tutor_id=recipient_id,
                    status='sent'
                ).order_by('-week_start')[:5]

                for report in reports:
                    report_data.append({
                        'id': report.id,
                        'student': report.student.get_full_name(),
                        'subject': report.subject.name if report.subject else 'N/A',
                        'week': f"{report.week_start} to {report.week_end}",
                        'average_score': float(report.average_score) if report.average_score else 0,
                        'summary': report.summary[:100],
                    })

                subject = f"Teacher Weekly Reports - {datetime.now().strftime('%Y-%m-%d')}"

        if not report_data:
            logger.info(f"No reports to send to {recipient.email} for schedule {schedule_id}")
            return {
                'success': True,
                'status': 'skipped',
                'reason': 'no_data',
                'schedule_id': schedule_id,
                'recipient_id': recipient_id
            }

        # Send email
        success = EmailReportService.send_report_email(
            recipient_email=recipient.email,
            recipient_name=recipient.get_full_name(),
            subject=subject,
            report_data=report_data,
            export_format=schedule.export_format,
            report_type=schedule.report_type,
            unsubscribe_token=schedule_recipient.unsubscribe_token
        )

        if success:
            logger.info(f"Report sent successfully to {recipient.email}")
            return {
                'success': True,
                'status': 'sent',
                'schedule_id': schedule_id,
                'recipient_id': recipient_id
            }
        else:
            logger.error(f"Failed to send report to {recipient.email}")
            return {
                'success': False,
                'status': 'failed',
                'schedule_id': schedule_id,
                'recipient_id': recipient_id
            }

    except ReportSchedule.DoesNotExist:
        logger.error(f"Schedule {schedule_id} not found")
        return {'success': False, 'status': 'not_found', 'schedule_id': schedule_id}

    except User.DoesNotExist:
        logger.error(f"Recipient {recipient_id} not found")
        return {'success': False, 'status': 'not_found', 'recipient_id': recipient_id}

    except Exception as e:
        logger.error(f"Error sending report to recipient {recipient_id}: {e}", exc_info=True)
        # Retry on exception
        raise


@shared_task(bind=True)
def execute_scheduled_reports(self) -> dict:
    """
    Main task to execute all active scheduled reports.
    Called by Celery Beat scheduler at configured intervals.

    Returns:
        dict with execution summary
    """
    from reports.models import ReportSchedule, ReportScheduleExecution

    try:
        now = timezone.now()
        current_time = now.time()
        current_weekday = now.weekday() + 1  # Convert to 1-7 (Mon-Sun)
        current_day = now.day

        # Find all active schedules that should run now
        schedules_to_run = []

        for schedule in ReportSchedule.objects.filter(is_active=True).select_related('created_by'):
            should_run = False

            # Check frequency and timing
            if schedule.frequency == ReportSchedule.Frequency.DAILY:
                # Check if current time matches schedule time (within 1 minute window)
                time_diff = abs((datetime.combine(now.date(), schedule.time) - now).total_seconds())
                if time_diff < 60:  # Within 1 minute
                    should_run = True

            elif schedule.frequency == ReportSchedule.Frequency.WEEKLY:
                if schedule.day_of_week == current_weekday:
                    time_diff = abs((datetime.combine(now.date(), schedule.time) - now).total_seconds())
                    if time_diff < 60:
                        should_run = True

            elif schedule.frequency == ReportSchedule.Frequency.MONTHLY:
                if schedule.day_of_month == current_day:
                    time_diff = abs((datetime.combine(now.date(), schedule.time) - now).total_seconds())
                    if time_diff < 60:
                        should_run = True

            if should_run:
                # Check if last execution is too recent (prevent duplicate runs)
                if schedule.last_sent:
                    time_since_last = (now - schedule.last_sent).total_seconds()
                    if time_since_last < 3600:  # Less than 1 hour
                        logger.info(f"Schedule {schedule.id} ran recently, skipping")
                        continue

                schedules_to_run.append(schedule)

        if not schedules_to_run:
            logger.info("No schedules to run at this time")
            return {'success': True, 'schedules_run': 0}

        # Execute all schedules
        total_sent = 0
        total_failed = 0

        for schedule in schedules_to_run:
            execution = ReportScheduleExecution.objects.create(schedule=schedule)

            try:
                # Get active recipients
                from reports.models import ReportScheduleRecipient
                recipients = ReportScheduleRecipient.objects.filter(
                    schedule=schedule,
                    is_subscribed=True
                ).values_list('recipient_id', flat=True)

                if not recipients:
                    logger.warning(f"Schedule {schedule.id} has no active recipients")
                    execution.status = ReportScheduleExecution.ExecutionStatus.COMPLETED
                    execution.completed_at = timezone.now()
                    execution.save()
                    continue

                execution.total_recipients = len(recipients)
                execution.save()

                # Send report to each recipient
                for recipient_id in recipients:
                    result = send_scheduled_report.delay(schedule.id, recipient_id)
                    # Track results
                    total_sent += 1

                # Update schedule timing
                schedule.last_sent = now
                schedule.next_scheduled = _calculate_next_scheduled_time(schedule)
                schedule.save(update_fields=['last_sent', 'next_scheduled'])

                # Mark execution as complete
                execution.status = ReportScheduleExecution.ExecutionStatus.COMPLETED
                execution.successful_sends = len(recipients)
                execution.completed_at = timezone.now()
                execution.save()

                logger.info(f"Schedule {schedule.id} executed successfully")

            except Exception as e:
                logger.error(f"Error executing schedule {schedule.id}: {e}", exc_info=True)
                execution.status = ReportScheduleExecution.ExecutionStatus.FAILED
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save()
                total_failed += 1

        return {
            'success': True,
            'schedules_run': len(schedules_to_run),
            'total_sent': total_sent,
            'total_failed': total_failed
        }

    except Exception as e:
        logger.error(f"Error in execute_scheduled_reports: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def _calculate_next_scheduled_time(schedule) -> datetime:
    """
    Calculate the next scheduled time for a report.

    Args:
        schedule: ReportSchedule instance

    Returns:
        Next scheduled datetime
    """
    now = timezone.now()
    schedule_time = schedule.time
    next_time = datetime.combine(now.date(), schedule_time)

    # If the scheduled time has already passed today, schedule for the next occurrence
    if next_time <= now:
        if schedule.frequency == ReportSchedule.Frequency.DAILY:
            next_time += timedelta(days=1)

        elif schedule.frequency == ReportSchedule.Frequency.WEEKLY:
            days_until_next = (schedule.day_of_week - now.weekday() - 1) % 7 + 1
            if days_until_next == 0:
                days_until_next = 7
            next_time += timedelta(days=days_until_next)

        elif schedule.frequency == ReportSchedule.Frequency.MONTHLY:
            days_in_month = (now + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            if schedule.day_of_month > days_in_month.day:
                # Move to next month
                next_time = next_time.replace(day=days_in_month.day) + timedelta(days=1)
            else:
                # Same day next month
                next_time = next_time.replace(day=schedule.day_of_month) + timedelta(days=32)
                next_time = next_time.replace(day=schedule.day_of_month)

    return next_time


@shared_task(bind=True)
def test_email_report(self, schedule_id: int, recipient_email: str) -> dict:
    """
    Send a test email for schedule configuration.

    Args:
        schedule_id: ID of ReportSchedule
        recipient_email: Email address to send test to

    Returns:
        dict with test result
    """
    from reports.models import ReportSchedule
    from reports.services.email_report import EmailReportService

    try:
        schedule = ReportSchedule.objects.select_related('created_by').get(id=schedule_id)

        # Create test data
        test_data = [
            {'id': 1, 'title': 'Test Report 1', 'status': 'sent'},
            {'id': 2, 'title': 'Test Report 2', 'status': 'sent'},
            {'id': 3, 'title': 'Test Report 3', 'status': 'sent'},
        ]

        # Send test email
        success = EmailReportService.send_report_email(
            recipient_email=recipient_email,
            recipient_name='Test User',
            subject=f'[TEST] {schedule.name or "Scheduled Report"} - {datetime.now().strftime("%Y-%m-%d")}',
            report_data=test_data,
            export_format=schedule.export_format,
            report_type=schedule.report_type or 'test'
        )

        if success:
            logger.info(f"Test email sent to {recipient_email} for schedule {schedule_id}")
            return {
                'success': True,
                'message': f'Test email sent to {recipient_email}'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to send test email'
            }

    except ReportSchedule.DoesNotExist:
        logger.error(f"Schedule {schedule_id} not found")
        return {'success': False, 'message': 'Schedule not found'}

    except Exception as e:
        logger.error(f"Error sending test email: {e}", exc_info=True)
        return {'success': False, 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def generate_teacher_weekly_reports(self, week_start_str: Optional[str] = None) -> dict:
    """
    Generate weekly reports for all teachers.

    Runs every Friday to create reports for the past week.

    Args:
        week_start_str: Optional ISO format date string for week start

    Returns:
        dict with generation results
    """
    from datetime import date
    from reports.services.teacher_weekly_report_service import TeacherWeeklyReportService
    from materials.models import SubjectEnrollment

    try:
        # Determine week start date
        if week_start_str:
            week_start = date.fromisoformat(week_start_str)
        else:
            # Default to Monday of current week
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())

        logger.info(f"Starting teacher weekly report generation for week {week_start}")

        # Get all active teachers
        teachers = User.objects.filter(role='teacher').distinct()

        report_count = 0
        error_count = 0

        for teacher in teachers:
            try:
                service = TeacherWeeklyReportService(teacher)

                # Get all subjects taught by this teacher
                subjects = SubjectEnrollment.objects.filter(
                    teacher=teacher,
                    is_active=True
                ).values('subject').distinct()

                for subject_dict in subjects:
                    subject_id = subject_dict['subject']

                    # Generate the report data
                    report_data = service.generate_weekly_report(
                        week_start=week_start,
                        subject_id=subject_id,
                        force_refresh=True
                    )

                    if 'error' not in report_data:
                        # Create records for each student
                        for student_data in report_data.get('students', []):
                            if 'error' not in student_data:
                                created_report = service.create_weekly_report_record(
                                    week_start=week_start,
                                    student_id=student_data['student_id'],
                                    subject_id=subject_id,
                                    report_data=report_data
                                )

                                if created_report:
                                    report_count += 1
                        logger.info(
                            f"Generated reports for {teacher.get_full_name()} "
                            f"in subject {subject_id}"
                        )

            except Exception as e:
                logger.error(f"Error generating reports for teacher {teacher.id}: {str(e)}")
                error_count += 1

        logger.info(
            f"Teacher weekly report generation completed: "
            f"{report_count} reports created, {error_count} errors"
        )

        return {
            'success': True,
            'reports_generated': report_count,
            'errors': error_count,
            'week_start': week_start.isoformat()
        }

    except Exception as e:
        logger.error(f"Error in generate_teacher_weekly_reports: {str(e)}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_teacher_weekly_reports(self, week_start_str: Optional[str] = None) -> dict:
    """
    Send generated weekly reports to tutors.

    Runs on Friday evening after reports are generated.
    Sends unsent reports to assigned tutors via email.

    Args:
        week_start_str: Optional ISO format date string

    Returns:
        dict with sending results
    """
    from datetime import date
    from reports.models import TeacherWeeklyReport
    from reports.services.email_report import EmailReportService

    try:
        if week_start_str:
            week_start = date.fromisoformat(week_start_str)
        else:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())

        logger.info(f"Starting teacher weekly report delivery for week {week_start}")

        # Get all unsent reports for this week
        reports_to_send = TeacherWeeklyReport.objects.filter(
            week_start=week_start,
            status=TeacherWeeklyReport.Status.DRAFT
        ).select_related('teacher', 'student', 'tutor', 'subject')

        sent_count = 0
        error_count = 0

        for report in reports_to_send:
            try:
                # Only send if tutor is assigned
                if not report.tutor:
                    logger.warning(
                        f"Report {report.id} has no tutor assigned. Skipping."
                    )
                    continue

                # Prepare report data for email
                report_data = {
                    'teacher': report.teacher.get_full_name(),
                    'student': report.student.get_full_name(),
                    'subject': report.subject.name,
                    'week_start': report.week_start,
                    'week_end': report.week_end,
                    'summary': report.summary,
                    'academic_progress': report.academic_progress,
                    'performance_notes': report.performance_notes,
                    'achievements': report.achievements,
                    'concerns': report.concerns,
                    'recommendations': report.recommendations,
                    'assignments_completed': report.assignments_completed,
                    'assignments_total': report.assignments_total,
                    'average_score': float(report.average_score) if report.average_score else None,
                    'attendance_percentage': report.attendance_percentage,
                }

                # Send email
                email_subject = (
                    f"Weekly Report: {report.student.get_full_name()} - "
                    f"{report.week_start.strftime('%b %d, %Y')}"
                )

                success = EmailReportService.send_report_email(
                    recipient_email=report.tutor.email,
                    recipient_name=report.tutor.get_full_name(),
                    subject=email_subject,
                    report_data=[report_data],
                    export_format='json',
                    report_type='teacher_weekly'
                )

                if success:
                    # Mark as sent
                    report.status = TeacherWeeklyReport.Status.SENT
                    report.sent_at = timezone.now()
                    report.save()
                    sent_count += 1
                    logger.info(f"Sent report {report.id} to {report.tutor.email}")
                else:
                    error_count += 1
                    logger.error(f"Failed to send report {report.id}")

            except Exception as e:
                logger.error(f"Error sending report {report.id}: {str(e)}")
                error_count += 1

        logger.info(
            f"Teacher weekly report delivery completed: "
            f"{sent_count} sent, {error_count} errors"
        )

        return {
            'success': True,
            'reports_sent': sent_count,
            'errors': error_count,
            'week_start': week_start.isoformat()
        }

    except Exception as e:
        logger.error(f"Error in send_teacher_weekly_reports: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def schedule_teacher_weekly_reports() -> dict:
    """
    Schedule weekly report generation and delivery.

    Runs on Friday at configured time. Triggers:
    1. Report generation (Friday morning)
    2. Report sending (Friday evening)

    Returns:
        dict with scheduling results
    """
    from datetime import date

    try:
        today = timezone.now().date()
        # Get the start of the current week (Monday)
        week_start = today - timedelta(days=today.weekday())

        logger.info(f"Scheduling teacher weekly reports for week {week_start}")

        # Chain the tasks: generate then send
        from celery import chain

        # Schedule generation immediately
        task_chain = chain(
            generate_teacher_weekly_reports.s(week_start.isoformat()),
            send_teacher_weekly_reports.s(week_start.isoformat())
        )

        result = task_chain.apply_async()

        logger.info(f"Teacher weekly report tasks scheduled. Task ID: {result.id}")

        return {
            'success': True,
            'task_id': result.id,
            'week_start': week_start.isoformat()
        }

    except Exception as e:
        logger.error(f"Error scheduling teacher weekly reports: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
