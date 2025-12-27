"""
Teacher Weekly Report Service

Generates comprehensive weekly summaries for teachers.
Includes class statistics, student progress, activity summaries, and recommendations.

Features:
- Weekly summary generation for all teacher's students
- Class performance metrics (average scores, submission rates)
- Per-student performance tracking
- Assignment statistics
- Chat activity analysis
- Automatic recommendations generation
- Report scheduling and auto-sending to parents
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.db.models import Q, Avg, Count, Sum, Case, When, Value, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from assignments.models import Assignment, AssignmentSubmission
from materials.models import Material, MaterialProgress, SubjectEnrollment
from chat.models import Message, ChatRoom, ChatParticipant
from knowledge_graph.models import LessonProgress

from ..models import TeacherWeeklyReport

User = get_user_model()
logger = logging.getLogger(__name__)


class TeacherWeeklyReportService:
    """
    Service for generating teacher weekly reports.

    Provides methods to:
    - Collect student progress data
    - Calculate assignment statistics
    - Analyze chat activity
    - Generate recommendations
    - Create and schedule reports
    """

    # Cache configuration
    CACHE_TTL = 3600  # 1 hour

    def __init__(self, teacher: User, subject=None):
        """
        Initialize service for a specific teacher.

        Args:
            teacher: User object with role='teacher'
            subject: Optional subject to limit report scope
        """
        if teacher.role != User.Role.TEACHER:
            raise ValueError("User must have teacher role")

        self.teacher = teacher
        self.subject = subject
        self.now = timezone.now()

    def generate_weekly_report(
        self,
        week_start: date,
        student_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Generate weekly report for teacher's students.

        Args:
            week_start: Start date of the week (typically Monday)
            student_id: Optional specific student ID
            subject_id: Optional specific subject ID
            force_refresh: Force cache refresh

        Returns:
            Dictionary containing report data
        """
        try:
            week_end = week_start + timedelta(days=6)

            # Check cache first
            cache_key = self._get_cache_key(week_start, student_id, subject_id)
            if not force_refresh:
                cached_report = cache.get(cache_key)
                if cached_report:
                    return cached_report

            # Collect report data
            report_data = {
                'week_start': week_start,
                'week_end': week_end,
                'teacher_id': self.teacher.id,
                'teacher_name': self.teacher.get_full_name(),
                'generated_at': self.now,
                'summary': {},
                'students': [],
                'statistics': {},
                'recommendations': []
            }

            # Get students to include in report
            students = self._get_students(student_id, subject_id)

            if not students:
                report_data['summary'] = {
                    'total_students': 0,
                    'message': 'No students found for report'
                }
                return report_data

            # Collect data for each student
            student_reports = []
            all_scores = []
            all_submission_rates = []

            for student in students:
                student_data = self._collect_student_data(
                    student, week_start, week_end, subject_id
                )
                student_reports.append(student_data)

                # Collect metrics for class summary
                if student_data['average_score'] is not None:
                    all_scores.append(float(student_data['average_score']))
                if student_data['submission_rate'] is not None:
                    all_submission_rates.append(student_data['submission_rate'])

            # Calculate class statistics
            report_data['statistics'] = self._calculate_class_statistics(
                student_reports, all_scores, all_submission_rates
            )

            # Sort students by performance
            student_reports = self._sort_students(student_reports)
            report_data['students'] = student_reports

            # Generate summary
            report_data['summary'] = self._generate_summary(
                student_reports, report_data['statistics']
            )

            # Generate recommendations
            report_data['recommendations'] = self._generate_recommendations(
                student_reports, report_data['statistics']
            )

            # Cache the report
            cache.set(cache_key, report_data, self.CACHE_TTL)

            return report_data

        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}")
            return {
                'error': str(e),
                'week_start': week_start,
                'teacher_id': self.teacher.id
            }

    def create_weekly_report_record(
        self,
        week_start: date,
        student_id: int,
        subject_id: int,
        report_data: Dict[str, Any]
    ) -> Optional[TeacherWeeklyReport]:
        """
        Create a TeacherWeeklyReport database record.

        Args:
            week_start: Start of week
            student_id: Student ID
            subject_id: Subject ID
            report_data: Report data dictionary

        Returns:
            Created TeacherWeeklyReport instance or None
        """
        try:
            from materials.models import Subject

            week_end = week_start + timedelta(days=6)

            # Check if student data exists
            student_report = None
            for student_data in report_data.get('students', []):
                if student_data['student_id'] == student_id:
                    student_report = student_data
                    break

            if not student_report:
                logger.warning(f"No data found for student {student_id}")
                return None

            subject = Subject.objects.get(id=subject_id)
            student = User.objects.get(id=student_id)

            # Try to get tutor from student profile
            tutor = None
            try:
                from accounts.models import StudentProfile
                student_profile = StudentProfile.objects.select_related('tutor').get(user=student)
                tutor = student_profile.tutor
            except:
                pass

            # Create report
            report = TeacherWeeklyReport.objects.create(
                teacher=self.teacher,
                student=student,
                subject=subject,
                tutor=tutor,
                week_start=week_start,
                week_end=week_end,
                title=f"Weekly Report - {student.get_full_name()} - {week_start.strftime('%b %d, %Y')}",
                summary=self._format_summary_text(student_report, report_data),
                academic_progress=self._format_academic_progress(student_report),
                performance_notes=self._format_performance_notes(student_report),
                achievements=self._format_achievements(student_report),
                concerns=self._format_concerns(student_report),
                recommendations=self._format_recommendations_text(student_report),
                assignments_completed=student_report.get('assignments_completed', 0),
                assignments_total=student_report.get('assignments_total', 0),
                average_score=Decimal(str(student_report.get('average_score') or 0)),
                attendance_percentage=student_report.get('attendance_percentage', 0),
                status=TeacherWeeklyReport.Status.DRAFT
            )

            logger.info(f"Created weekly report {report.id} for student {student_id}")
            return report

        except Exception as e:
            logger.error(f"Error creating report record: {str(e)}")
            return None

    def _get_students(
        self,
        student_id: Optional[int] = None,
        subject_id: Optional[int] = None
    ) -> List[User]:
        """Get students for the report."""
        # Get enrollments for this teacher
        enrollments = SubjectEnrollment.objects.filter(
            teacher=self.teacher,
            is_active=True
        ).select_related('student', 'subject')

        if subject_id:
            enrollments = enrollments.filter(subject_id=subject_id)

        if student_id:
            enrollments = enrollments.filter(student_id=student_id)

        # Get unique students
        student_ids = enrollments.values_list('student_id', flat=True).distinct()
        students = User.objects.filter(id__in=student_ids).order_by('last_name', 'first_name')

        return list(students)

    def _collect_student_data(
        self,
        student: User,
        week_start: date,
        week_end: date,
        subject_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Collect data for a single student."""
        try:
            # Get assignments data
            assignments_data = self._get_student_assignments(
                student, week_start, week_end, subject_id
            )

            # Get materials/learning data
            learning_data = self._get_student_learning_data(
                student, week_start, week_end, subject_id
            )

            # Get chat activity
            chat_data = self._get_student_chat_activity(
                student, week_start, week_end
            )

            # Calculate time spent
            time_spent = self._calculate_time_spent(
                student, week_start, week_end, subject_id
            )

            return {
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'student_email': student.email,
                'week_start': week_start,
                'week_end': week_end,
                # Assignment metrics
                'assignments_total': assignments_data['total'],
                'assignments_completed': assignments_data['completed'],
                'assignments_submitted': assignments_data['submitted'],
                'assignments_graded': assignments_data['graded'],
                'average_score': assignments_data['average_score'],
                'submission_rate': assignments_data['submission_rate'],
                'on_time_submissions': assignments_data['on_time'],
                'late_submissions': assignments_data['late'],
                # Learning metrics
                'materials_assigned': learning_data['assigned'],
                'materials_completed': learning_data['completed'],
                'learning_progress': learning_data['progress_percentage'],
                'attendance_percentage': learning_data['attendance'],
                # Feedback metrics
                'feedback_given': assignments_data['feedback_count'],
                'feedback_quality_score': assignments_data['feedback_quality'],
                # Activity
                'chat_messages_sent': chat_data['messages_sent'],
                'chat_messages_received': chat_data['messages_received'],
                'chat_participation': chat_data['participation_level'],
                'time_spent_hours': time_spent,
                # Status
                'engagement_level': self._calculate_engagement_level(
                    assignments_data, learning_data, chat_data, time_spent
                )
            }
        except Exception as e:
            logger.error(f"Error collecting data for student {student.id}: {str(e)}")
            return {
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'error': str(e)
            }

    def _get_student_assignments(
        self,
        student: User,
        week_start: date,
        week_end: date,
        subject_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get assignment data for a student."""
        # Get assignments created by this teacher for this student
        assignments_query = Assignment.objects.filter(
            teacher=self.teacher,
            assigned_to=student
        )

        if subject_id:
            assignments_query = assignments_query.filter(subject_id=subject_id)

        total_assignments = assignments_query.count()

        # Get submissions for the week
        submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment__teacher=self.teacher,
            created_at__date__range=[week_start, week_end]
        ).select_related('assignment')

        if subject_id:
            submissions = submissions.filter(assignment__subject_id=subject_id)

        submitted_count = submissions.count()
        graded_count = submissions.filter(status=AssignmentSubmission.Status.GRADED).count()

        # Calculate scores
        scores = submissions.filter(
            score__isnull=False
        ).values_list('score', flat=True)

        average_score = None
        if scores:
            average_score = float(sum(scores) / len(scores))

        submission_rate = (submitted_count / total_assignments * 100) if total_assignments > 0 else 0

        # Count on-time vs late submissions
        on_time = submissions.filter(is_late=False).count()
        late = submissions.filter(is_late=True).count()

        # Count feedback comments
        feedback_count = submissions.filter(feedback__isnull=False).exclude(feedback='').count()

        # Calculate feedback quality (simple heuristic: longer feedback = better)
        feedback_quality = 0.0
        if feedback_count > 0:
            avg_feedback_length = submissions.filter(
                feedback__isnull=False
            ).exclude(feedback='').aggregate(
                avg_length=Avg('feedback__length')
            )['avg_length'] or 0
            # Score: 0-50 chars = 3, 50-150 = 6, 150+ = 8
            if avg_feedback_length > 150:
                feedback_quality = 8.0
            elif avg_feedback_length > 50:
                feedback_quality = 6.0
            elif avg_feedback_length > 0:
                feedback_quality = 3.0

        return {
            'total': total_assignments,
            'completed': submitted_count,
            'submitted': submitted_count,
            'graded': graded_count,
            'average_score': average_score,
            'submission_rate': submission_rate,
            'on_time': on_time,
            'late': late,
            'feedback_count': feedback_count,
            'feedback_quality': feedback_quality
        }

    def _get_student_learning_data(
        self,
        student: User,
        week_start: date,
        week_end: date,
        subject_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get learning/material progress data for a student."""
        # Get materials assigned by this teacher
        materials_query = Material.objects.filter(
            author=self.teacher,
            assigned_to=student
        )

        if subject_id:
            materials_query = materials_query.filter(subject_id=subject_id)

        assigned_count = materials_query.count()

        # Get progress
        progress_query = MaterialProgress.objects.filter(
            student=student,
            material__author=self.teacher
        )

        if subject_id:
            progress_query = progress_query.filter(material__subject_id=subject_id)

        completed_count = progress_query.filter(is_completed=True).count()

        # Get average progress
        avg_progress = progress_query.aggregate(
            avg=Avg('progress_percentage')
        )['avg'] or 0

        # Attendance - materials accessed this week
        accessed_this_week = MaterialProgress.objects.filter(
            student=student,
            material__author=self.teacher,
            last_accessed__date__range=[week_start, week_end]
        ).count()

        attendance_percentage = (accessed_this_week / assigned_count * 100) if assigned_count > 0 else 0

        return {
            'assigned': assigned_count,
            'completed': completed_count,
            'progress_percentage': avg_progress,
            'attendance': attendance_percentage
        }

    def _get_student_chat_activity(
        self,
        student: User,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """Get chat activity for a student."""
        week_start_datetime = timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
        week_end_datetime = timezone.make_aware(datetime.combine(week_end, datetime.max.time()))

        # Get messages sent by student
        sent_messages = Message.objects.filter(
            sender=student,
            created_at__range=[week_start_datetime, week_end_datetime]
        ).count()

        # Get messages received by student
        received_messages = Message.objects.filter(
            chat_room__participants__user=student,
            created_at__range=[week_start_datetime, week_end_datetime]
        ).exclude(sender=student).count()

        # Participation level (0-10 scale based on activity)
        total_activity = sent_messages + received_messages
        participation = min(10, total_activity / 5) if total_activity > 0 else 0

        return {
            'messages_sent': sent_messages,
            'messages_received': received_messages,
            'participation_level': participation
        }

    def _calculate_time_spent(
        self,
        student: User,
        week_start: date,
        week_end: date,
        subject_id: Optional[int] = None
    ) -> float:
        """Calculate total time spent (in hours) on materials."""
        progress_query = MaterialProgress.objects.filter(
            student=student,
            material__author=self.teacher,
            last_accessed__date__range=[week_start, week_end]
        )

        if subject_id:
            progress_query = progress_query.filter(material__subject_id=subject_id)

        # Sum time_spent in seconds and convert to hours
        total_seconds = progress_query.aggregate(
            total=Sum('time_spent')
        )['total'] or 0

        return round(total_seconds / 3600, 2)

    def _calculate_engagement_level(
        self,
        assignments_data: Dict,
        learning_data: Dict,
        chat_data: Dict,
        time_spent: float
    ) -> str:
        """Calculate engagement level based on multiple factors."""
        score = 0
        factors = 0

        # Assignment engagement (30%)
        if assignments_data.get('submission_rate', 0) >= 80:
            score += 3
        elif assignments_data.get('submission_rate', 0) >= 50:
            score += 2
        elif assignments_data.get('submission_rate', 0) > 0:
            score += 1
        factors += 3

        # Learning engagement (30%)
        if learning_data.get('attendance') >= 80:
            score += 3
        elif learning_data.get('attendance') >= 50:
            score += 2
        elif learning_data.get('attendance') > 0:
            score += 1
        factors += 3

        # Chat engagement (20%)
        if chat_data.get('participation_level', 0) >= 7:
            score += 2
        elif chat_data.get('participation_level', 0) >= 4:
            score += 1
        factors += 2

        # Time spent (20%)
        if time_spent >= 10:
            score += 2
        elif time_spent >= 5:
            score += 1
        factors += 2

        # Calculate final level
        avg_score = score / factors if factors > 0 else 0

        if avg_score >= 2.5:
            return 'Very High'
        elif avg_score >= 2.0:
            return 'High'
        elif avg_score >= 1.5:
            return 'Medium'
        elif avg_score >= 1.0:
            return 'Low'
        else:
            return 'Very Low'

    def _calculate_class_statistics(
        self,
        student_reports: List[Dict],
        all_scores: List[float],
        all_submission_rates: List[float]
    ) -> Dict[str, Any]:
        """Calculate class-wide statistics."""
        if not student_reports:
            return {}

        class_stats = {
            'total_students': len(student_reports),
            'active_students': len([s for s in student_reports if not s.get('error')]),
        }

        # Score statistics
        if all_scores:
            class_stats['class_average_score'] = round(sum(all_scores) / len(all_scores), 2)
            class_stats['highest_score'] = max(all_scores)
            class_stats['lowest_score'] = min(all_scores)
        else:
            class_stats['class_average_score'] = None

        # Submission statistics
        if all_submission_rates:
            class_stats['class_submission_rate'] = round(sum(all_submission_rates) / len(all_submission_rates), 2)

        # Engagement summary
        engagement_counts = {}
        for student in student_reports:
            level = student.get('engagement_level', 'Unknown')
            engagement_counts[level] = engagement_counts.get(level, 0) + 1

        class_stats['engagement_distribution'] = engagement_counts

        return class_stats

    def _sort_students(self, student_reports: List[Dict]) -> List[Dict]:
        """Sort students by performance."""
        def sort_key(student):
            score = student.get('average_score') or 0
            submission_rate = student.get('submission_rate') or 0
            return (float(score), float(submission_rate))

        return sorted(student_reports, key=sort_key, reverse=True)

    def _generate_summary(
        self,
        student_reports: List[Dict],
        statistics: Dict
    ) -> Dict[str, Any]:
        """Generate summary for the report."""
        return {
            'total_students': len(student_reports),
            'report_period': 'Weekly',
            'class_average_score': statistics.get('class_average_score'),
            'class_submission_rate': statistics.get('class_submission_rate'),
            'engagement_distribution': statistics.get('engagement_distribution', {}),
            'students_with_concerns': len([
                s for s in student_reports
                if s.get('engagement_level') in ['Low', 'Very Low']
            ]),
            'top_performers': len([
                s for s in student_reports
                if s.get('engagement_level') in ['High', 'Very High']
            ])
        }

    def _generate_recommendations(
        self,
        student_reports: List[Dict],
        statistics: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Class-level recommendations
        class_avg = statistics.get('class_average_score')
        if class_avg and class_avg < 65:
            recommendations.append(
                "Class average score is below 65%. Consider reviewing lesson content "
                "and providing additional support materials."
            )

        submission_rate = statistics.get('class_submission_rate', 0)
        if submission_rate < 75:
            recommendations.append(
                f"Class submission rate is {submission_rate:.1f}%. Set clear deadlines "
                "and send reminders to students."
            )

        # Student-level recommendations
        low_engagement = [
            s for s in student_reports
            if s.get('engagement_level') in ['Low', 'Very Low']
        ]

        if low_engagement:
            names = ", ".join([s['student_name'] for s in low_engagement[:3]])
            recommendations.append(
                f"Students with low engagement: {names}. Consider reaching out for "
                "individual support or tutoring."
            )

        # Late submissions
        late_submission_students = [
            s for s in student_reports
            if s.get('late_submissions', 0) > 2
        ]

        if late_submission_students:
            recommendations.append(
                "Several students are submitting assignments late. Review deadline "
                "policies and discuss time management."
            )

        return recommendations

    def _format_summary_text(self, student_data: Dict, report_data: Dict) -> str:
        """Format summary text for report."""
        lines = [
            f"Weekly Summary for {student_data['student_name']}",
            f"Period: {student_data['week_start']} to {student_data['week_end']}",
            "",
            f"Assignments: {student_data['assignments_completed']}/{student_data['assignments_total']} completed",
            f"Average Score: {student_data.get('average_score', 'N/A')}",
            f"Engagement Level: {student_data['engagement_level']}",
        ]
        return "\n".join(lines)

    def _format_academic_progress(self, student_data: Dict) -> str:
        """Format academic progress text."""
        lines = [
            f"Learning Progress: {student_data['learning_progress']:.1f}%",
            f"Materials Completed: {student_data['materials_completed']}/{student_data['materials_assigned']}",
            f"Time Spent: {student_data['time_spent_hours']} hours",
        ]
        return "\n".join(lines)

    def _format_performance_notes(self, student_data: Dict) -> str:
        """Format performance notes."""
        notes = []

        # Assignment performance
        if student_data['submission_rate'] > 90:
            notes.append("Excellent submission rate. Student is consistently turning in assignments.")
        elif student_data['submission_rate'] < 50:
            notes.append("Low submission rate. Student needs support with assignment completion.")

        # Score performance
        avg_score = student_data.get('average_score')
        if avg_score and avg_score >= 85:
            notes.append("High quality work. Strong understanding of concepts.")
        elif avg_score and avg_score < 60:
            notes.append("Low scores indicate difficulty with material. Additional support recommended.")

        # Late submissions
        if student_data['late_submissions'] > 0:
            notes.append(f"{student_data['late_submissions']} late submissions this week.")

        return "\n".join(notes) if notes else "No specific notes."

    def _format_achievements(self, student_data: Dict) -> str:
        """Format achievements text."""
        achievements = []

        if student_data['assignments_completed'] > 0:
            achievements.append(f"Completed {student_data['assignments_completed']} assignments")

        if student_data.get('average_score', 0) >= 85:
            achievements.append("Demonstrated strong academic performance")

        if student_data['chat_participation'] >= 7:
            achievements.append("Active participation in class discussions")

        if student_data['time_spent_hours'] >= 10:
            achievements.append("Dedicated significant time to learning")

        return "\n".join(achievements) if achievements else "No notable achievements this week."

    def _format_concerns(self, student_data: Dict) -> str:
        """Format concerns text."""
        concerns = []

        if student_data['submission_rate'] < 50:
            concerns.append("Low assignment submission rate")

        if student_data.get('average_score', 100) < 60:
            concerns.append("Struggling with assignment content")

        if student_data['time_spent_hours'] < 2:
            concerns.append("Limited time spent on materials")

        if student_data['chat_participation'] < 3:
            concerns.append("Low participation in class discussions")

        return "\n".join(concerns) if concerns else "No specific concerns."

    def _format_recommendations_text(self, student_data: Dict) -> str:
        """Format recommendations text."""
        recommendations = []

        if student_data['submission_rate'] < 75:
            recommendations.append("Encourage student to submit assignments on time")

        if student_data.get('average_score', 100) < 70:
            recommendations.append("Provide additional practice materials and tutoring support")

        if student_data['chat_participation'] < 4:
            recommendations.append("Encourage student to participate more in class discussions")

        if student_data['time_spent_hours'] < 5:
            recommendations.append("Suggest increased study time for better understanding")

        return "\n".join(recommendations) if recommendations else "Continue current study approach."

    def _get_cache_key(
        self,
        week_start: date,
        student_id: Optional[int],
        subject_id: Optional[int]
    ) -> str:
        """Generate cache key for report."""
        key_parts = [
            'teacher_weekly_report',
            str(self.teacher.id),
            week_start.isoformat(),
        ]

        if student_id:
            key_parts.append(f'student_{student_id}')
        if subject_id:
            key_parts.append(f'subject_{subject_id}')

        return ':'.join(key_parts)

    def clear_cache(self, week_start: Optional[date] = None) -> None:
        """Clear cached reports."""
        if week_start:
            # Clear specific week
            keys_to_delete = []
            for student_id in [None]:
                for subject_id in [None]:
                    key = self._get_cache_key(week_start, student_id, subject_id)
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                cache.delete(key)
        else:
            # Clear all reports for this teacher
            cache.delete_pattern(f'teacher_weekly_report:{self.teacher.id}:*')
