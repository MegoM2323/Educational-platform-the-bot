"""
T_ASN_005: Assignment Statistics Service.

Advanced statistics endpoints for assignment performance analytics.

Provides:
- Per-student performance breakdown
- Per-question difficulty analysis
- Time spent analysis (submission speed, grading time)
- Caching with 1-hour TTL
- Cache invalidation on submission changes

Performance Metrics:
- Question difficulty ranking
- Submission time analysis
- Late submission percentage
"""

from typing import Any, Dict, List, Optional
from django.contrib.auth import get_user_model
from django.db.models import (
    Avg, Count, Max, Min, Q, F, Case, When, Value, FloatField, DurationField, Exists, OuterRef
)
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from assignments.models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer

User = get_user_model()
logger = logging.getLogger(__name__)


class AssignmentStatisticsService:
    """
    Comprehensive statistics service for assignments.

    Features:
    - Per-student performance breakdown with percentiles
    - Per-question difficulty and answer analysis
    - Time spent analysis (submission time, grading speed)
    - Cached results with 1-hour TTL
    - Automatic cache invalidation on submission changes
    """

    # Cache TTL in seconds (1 hour)
    CACHE_TTL = 3600

    def __init__(self, assignment: Assignment):
        """
        Initialize statistics service for an assignment.

        Args:
            assignment: Assignment instance to analyze
        """
        self.assignment = assignment
        self.cache_prefix = f"assignment_stats_{assignment.id}"

    def get_overall_statistics(self) -> Dict[str, Any]:
        """
        Get overall assignment statistics.

        Returns comprehensive analytics matching T_ASSIGN_007 with extended data.

        Returns:
            Dict with:
            - statistics: Descriptive statistics
            - distribution: Grade distribution
            - submission_metrics: Advanced submission metrics
            - performance_summary: Class average comparison
        """
        cache_key = f"{self.cache_prefix}_overall"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Get all submissions with scores
        submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        ).select_related('student')

        result = {
            'assignment_id': self.assignment.id,
            'assignment_title': self.assignment.title,
            'max_score': self.assignment.max_score,
            'statistics': self._calculate_descriptive_statistics(submissions),
            'distribution': self._calculate_distribution(submissions),
            'submission_metrics': self._calculate_submission_metrics(),
            'performance_summary': self._calculate_performance_summary(submissions),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_student_breakdown(self) -> Dict[str, Any]:
        """
        Get per-student performance breakdown.

        Returns:
            Dict with:
            - students: List of student performance data
            - class_metrics: Class-wide metrics
            - performance_tiers: Students grouped by performance level
        """
        cache_key = f"{self.cache_prefix}_by_student"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Get all submissions for this assignment
        submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment
        ).select_related('student')

        all_scores = [s.score for s in submissions if s.score is not None and s.status == AssignmentSubmission.Status.GRADED]

        result = {
            'assignment_id': self.assignment.id,
            'student_count': self.assignment.assigned_to.count(),
            'submitted_count': submissions.count(),
            'students': self._build_student_list(submissions),
            'class_metrics': self._calculate_class_metrics(submissions, all_scores),
            'performance_tiers': self._classify_performance_tiers(submissions),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_question_analysis(self) -> Dict[str, Any]:
        """
        Get per-question difficulty and performance analysis.

        Returns:
            Dict with:
            - questions: Per-question difficulty metrics
            - difficulty_ranking: Questions ranked by difficulty
            - common_errors: Most common wrong answers
        """
        cache_key = f"{self.cache_prefix}_by_question"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        questions = AssignmentQuestion.objects.filter(
            assignment=self.assignment
        ).order_by('order')

        question_data = []
        for question in questions:
            question_data.append(self._analyze_question(question))

        # Sort by difficulty (wrong_answer_rate) descending
        difficulty_ranking = sorted(question_data, key=lambda q: q['difficulty_score'], reverse=True)

        result = {
            'assignment_id': self.assignment.id,
            'total_questions': questions.count(),
            'questions': question_data,
            'difficulty_ranking': difficulty_ranking,
            'average_difficulty': self._calculate_average_difficulty(question_data),
            'common_errors': self._extract_common_errors(questions),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_time_analysis(self) -> Dict[str, Any]:
        """
        Get time spent analysis for submissions.

        Returns:
            Dict with:
            - submission_timing: When submissions were submitted
            - grading_speed: How fast assignments were graded
            - late_submissions: Late submission analysis
            - response_times: Teacher response time metrics
        """
        cache_key = f"{self.cache_prefix}_time_analysis"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment
        ).select_related('student')

        result = {
            'assignment_id': self.assignment.id,
            'submission_timing': self._analyze_submission_timing(submissions),
            'grading_speed': self._analyze_grading_speed(submissions),
            'late_submissions': self._analyze_late_submissions(submissions),
            'response_times': self._analyze_response_times(submissions),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def _calculate_descriptive_statistics(self, submissions: Any) -> Dict[str, Optional[float]]:
        """Calculate mean, median, mode, std dev, min, max, quartiles."""
        scores = [s.score for s in submissions if s.score is not None]

        if not scores:
            return {
                'mean': None,
                'median': None,
                'mode': None,
                'std_dev': None,
                'min': None,
                'max': None,
                'q1': None,
                'q2': None,
                'q3': None,
                'sample_size': 0,
            }

        from statistics import median, mode, StatisticsError

        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        stats = {
            'mean': round(sum(scores) / n, 2),
            'median': round(median(scores), 2),
            'min': min(scores),
            'max': max(scores),
            'sample_size': n,
        }

        # Mode
        try:
            stats['mode'] = round(mode(scores), 2)
        except StatisticsError:
            stats['mode'] = None

        # Standard deviation
        if n > 1:
            mean = stats['mean']
            variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
            stats['std_dev'] = round(variance ** 0.5, 2)
        else:
            stats['std_dev'] = None

        # Quartiles
        if n >= 4:
            stats['q1'] = round(sorted_scores[int(n * 0.25)], 2)
            stats['q2'] = round(sorted_scores[int(n * 0.5)], 2)
            stats['q3'] = round(sorted_scores[int(n * 0.75)], 2)
        else:
            stats['q1'] = None
            stats['q2'] = None
            stats['q3'] = None

        return stats

    def _calculate_distribution(self, submissions: Any) -> Dict[str, Any]:
        """Calculate grade distribution buckets (A-F)."""
        GRADE_BUCKETS = {
            "A": {"min": 90, "max": 100, "label": "Excellent (90-100%)"},
            "B": {"min": 80, "max": 89, "label": "Good (80-89%)"},
            "C": {"min": 70, "max": 79, "label": "Satisfactory (70-79%)"},
            "D": {"min": 60, "max": 69, "label": "Passing (60-69%)"},
            "F": {"min": 0, "max": 59, "label": "Failing (<60%)"},
        }

        # Calculate percentages
        percentages = []
        for submission in submissions:
            if submission.max_score and submission.score is not None and submission.max_score > 0:
                percentage = (submission.score / submission.max_score) * 100
                percentages.append(percentage)

        total = len(percentages)
        if total == 0:
            return {
                'buckets': {b: {'count': 0, 'percentage': 0.0} for b in GRADE_BUCKETS},
                'total': 0,
                'pie_chart_data': [],
            }

        bucket_counts = {b: 0 for b in GRADE_BUCKETS}
        for pct in percentages:
            for bucket, info in GRADE_BUCKETS.items():
                if info['min'] <= pct <= info['max']:
                    bucket_counts[bucket] += 1
                    break

        distribution = {}
        pie_chart_data = []
        for bucket in ['A', 'B', 'C', 'D', 'F']:
            count = bucket_counts[bucket]
            pct = round((count / total) * 100, 2) if total > 0 else 0
            distribution[bucket] = {
                'label': GRADE_BUCKETS[bucket]['label'],
                'count': count,
                'percentage': pct,
            }
            if count > 0:
                pie_chart_data.append({
                    'label': bucket,
                    'value': count,
                    'percentage': pct,
                })

        return {
            'buckets': distribution,
            'total': total,
            'pie_chart_data': pie_chart_data,
        }

    def _calculate_submission_metrics(self) -> Dict[str, Any]:
        """Calculate submission-related metrics."""
        submissions = AssignmentSubmission.objects.filter(assignment=self.assignment)

        total = submissions.count()
        graded = submissions.filter(status=AssignmentSubmission.Status.GRADED).count()
        late = submissions.filter(is_late=True).count()
        assigned = self.assignment.assigned_to.count()

        return {
            'total_submissions': total,
            'graded_submissions': graded,
            'late_submissions': late,
            'assigned_count': assigned,
            'submission_rate': round((total / assigned * 100), 2) if assigned > 0 else 0,
            'grading_rate': round((graded / total * 100), 2) if total > 0 else 0,
            'late_rate': round((late / total * 100), 2) if total > 0 else 0,
        }

    def _calculate_performance_summary(self, submissions: Any) -> Dict[str, Any]:
        """Calculate class average comparison."""
        scores = [s.score for s in submissions if s.score is not None]

        if not scores:
            return {
                'assignment_average': None,
                'class_average': None,
                'difference': None,
                'performance': 'No data',
            }

        assignment_avg = round(sum(scores) / len(scores), 2)

        # Get class average (all assignments by same author)
        class_submissions = AssignmentSubmission.objects.filter(
            assignment__author=self.assignment.author,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        )

        if class_submissions.count() > 0:
            class_scores = [s.score for s in class_submissions]
            class_avg = round(sum(class_scores) / len(class_scores), 2)
            difference = round(assignment_avg - class_avg, 2)

            if difference >= 5:
                performance = "Above average"
            elif difference <= -5:
                performance = "Below average"
            else:
                performance = "Average"

            return {
                'assignment_average': assignment_avg,
                'class_average': class_avg,
                'difference': difference,
                'performance': performance,
            }

        return {
            'assignment_average': assignment_avg,
            'class_average': None,
            'difference': None,
            'performance': 'No class data',
        }

    def _build_student_list(self, submissions: Any) -> List[Dict[str, Any]]:
        """Build detailed per-student performance list."""
        student_data = []

        for submission in submissions:
            student_dict = {
                'student_id': submission.student.id,
                'student_name': submission.student.get_full_name() or submission.student.username,
                'score': submission.score,
                'max_score': submission.max_score,
                'percentage': submission.percentage,
                'status': submission.status,
                'is_late': submission.is_late,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'graded_at': submission.graded_at.isoformat() if submission.graded_at else None,
                'days_late': float(submission.days_late) if submission.days_late else 0,
                'penalty_applied': float(submission.penalty_applied) if submission.penalty_applied else 0,
            }
            student_data.append(student_dict)

        # Sort by score descending
        student_data.sort(key=lambda x: x['score'] if x['score'] is not None else -1, reverse=True)
        return student_data

    def _calculate_class_metrics(self, submissions: Any, scores: List[float]) -> Dict[str, Any]:
        """Calculate class-wide metrics."""
        if not scores:
            return {
                'mean': None,
                'median': None,
                'std_dev': None,
                'highest_score': None,
                'lowest_score': None,
            }

        from statistics import median, StatisticsError

        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        metrics = {
            'mean': round(sum(scores) / n, 2),
            'median': round(median(scores), 2),
            'highest_score': max(scores),
            'lowest_score': min(scores),
        }

        if n > 1:
            mean = metrics['mean']
            variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
            metrics['std_dev'] = round(variance ** 0.5, 2)
        else:
            metrics['std_dev'] = None

        return metrics

    def _classify_performance_tiers(self, submissions: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Classify students into performance tiers."""
        tiers = {
            'excellent': [],
            'good': [],
            'satisfactory': [],
            'passing': [],
            'failing': [],
            'not_submitted': []
        }

        for submission in submissions:
            if submission.score is None:
                tiers['not_submitted'].append({
                    'student_id': submission.student.id,
                    'student_name': submission.student.get_full_name() or submission.student.username,
                })
            else:
                percentage = submission.percentage or 0
                if percentage >= 90:
                    tier = 'excellent'
                elif percentage >= 80:
                    tier = 'good'
                elif percentage >= 70:
                    tier = 'satisfactory'
                elif percentage >= 60:
                    tier = 'passing'
                else:
                    tier = 'failing'

                tiers[tier].append({
                    'student_id': submission.student.id,
                    'student_name': submission.student.get_full_name() or submission.student.username,
                    'score': submission.score,
                    'percentage': percentage,
                })

        # Add counts
        for tier_name in tiers:
            tiers[tier_name] = {
                'count': len(tiers[tier_name]),
                'students': tiers[tier_name],
            }

        return tiers

    def _analyze_question(self, question: AssignmentQuestion) -> Dict[str, Any]:
        """Analyze a single question's performance."""
        answers = AssignmentAnswer.objects.filter(question=question).select_related('submission')
        correct_count = 0
        wrong_count = 0
        total_answers = answers.count()

        # Count correct/wrong answers
        for answer in answers:
            if self._is_answer_correct(answer, question):
                correct_count += 1
            else:
                wrong_count += 1

        correct_rate = (correct_count / total_answers * 100) if total_answers > 0 else 0
        wrong_rate = (wrong_count / total_answers * 100) if total_answers > 0 else 0

        return {
            'question_id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'points': question.points,
            'total_answers': total_answers,
            'correct_answers': correct_count,
            'wrong_answers': wrong_count,
            'correct_rate': round(correct_rate, 2),
            'wrong_rate': round(wrong_rate, 2),
            'difficulty_score': round(wrong_rate, 2),  # Higher = more difficult
        }

    def _is_answer_correct(self, answer: AssignmentAnswer, question: AssignmentQuestion) -> bool:
        """Check if an answer is correct."""
        if question.question_type in ['single_choice', 'multiple_choice']:
            correct = question.correct_answer
            if isinstance(correct, dict):
                if isinstance(answer.answer_choice, list):
                    return set(answer.answer_choice) == set(correct.get('value', []))
                return answer.answer_choice == correct.get('value')
            return answer.answer_choice == correct
        return False  # Text/number questions need manual grading

    def _calculate_average_difficulty(self, question_data: List[Dict[str, Any]]) -> float:
        """Calculate average difficulty across all questions."""
        if not question_data:
            return 0.0
        difficulties = [q['difficulty_score'] for q in question_data]
        return round(sum(difficulties) / len(difficulties), 2)

    def _extract_common_errors(self, questions: Any) -> List[Dict[str, Any]]:
        """Extract most common wrong answers."""
        common_errors = {}

        for question in questions:
            answers = AssignmentAnswer.objects.filter(question=question)

            for answer in answers:
                if not self._is_answer_correct(answer, question):
                    key = f"{question.id}_{str(answer.answer_choice)}"
                    if key not in common_errors:
                        common_errors[key] = {
                            'question_id': question.id,
                            'question_text': question.question_text,
                            'wrong_answer': answer.answer_choice,
                            'count': 0,
                        }
                    common_errors[key]['count'] += 1

        # Sort by frequency and return top 10
        sorted_errors = sorted(common_errors.values(), key=lambda x: x['count'], reverse=True)
        return sorted_errors[:10]

    def _analyze_submission_timing(self, submissions: Any) -> Dict[str, Any]:
        """Analyze when submissions were submitted."""
        if self.assignment.due_date is None:
            return {
                'early_submissions': 0,
                'on_time_submissions': 0,
                'late_submissions': 0,
                'average_days_before_deadline': None,
            }

        early = 0
        on_time = 0
        late = 0
        days_before_list = []

        for submission in submissions:
            if submission.submitted_at:
                if submission.submitted_at < self.assignment.due_date:
                    on_time += 1
                    days_before = (self.assignment.due_date - submission.submitted_at).days
                    days_before_list.append(days_before)
                else:
                    late += 1

        avg_days = round(sum(days_before_list) / len(days_before_list), 2) if days_before_list else None

        return {
            'on_time_submissions': on_time,
            'late_submissions': late,
            'average_days_before_deadline': avg_days,
            'total_submissions': on_time + late,
        }

    def _analyze_grading_speed(self, submissions: Any) -> Dict[str, Any]:
        """Analyze how fast assignments were graded."""
        graded_submissions = submissions.filter(
            status=AssignmentSubmission.Status.GRADED,
            graded_at__isnull=False,
            submitted_at__isnull=False
        )

        if not graded_submissions.exists():
            return {
                'average_time_to_grade_hours': None,
                'average_time_to_grade_days': None,
                'fastest_grade_hours': None,
                'slowest_grade_hours': None,
                'total_graded': 0,
            }

        times_to_grade = []
        for submission in graded_submissions:
            if submission.graded_at and submission.submitted_at:
                delta = submission.graded_at - submission.submitted_at
                hours = delta.total_seconds() / 3600
                times_to_grade.append(hours)

        if not times_to_grade:
            return {
                'average_time_to_grade_hours': None,
                'average_time_to_grade_days': None,
                'fastest_grade_hours': None,
                'slowest_grade_hours': None,
                'total_graded': 0,
            }

        avg_hours = sum(times_to_grade) / len(times_to_grade)
        avg_days = avg_hours / 24

        return {
            'average_time_to_grade_hours': round(avg_hours, 2),
            'average_time_to_grade_days': round(avg_days, 2),
            'fastest_grade_hours': round(min(times_to_grade), 2),
            'slowest_grade_hours': round(max(times_to_grade), 2),
            'total_graded': len(times_to_grade),
        }

    def _analyze_late_submissions(self, submissions: Any) -> Dict[str, Any]:
        """Analyze late submissions."""
        late = submissions.filter(is_late=True)
        total = submissions.count()

        if not late.exists():
            return {
                'late_submission_count': 0,
                'late_submission_rate': 0.0,
                'average_days_late': None,
                'most_days_late': None,
            }

        late_submissions = list(late)
        late_count = len(late_submissions)
        late_rate = round((late_count / total * 100), 2) if total > 0 else 0

        days_late_values = [float(s.days_late) for s in late_submissions if s.days_late]
        avg_days_late = round(sum(days_late_values) / len(days_late_values), 2) if days_late_values else None

        return {
            'late_submission_count': late_count,
            'late_submission_rate': late_rate,
            'average_days_late': avg_days_late,
            'most_days_late': max(days_late_values) if days_late_values else None,
        }

    def _analyze_response_times(self, submissions: Any) -> Dict[str, Any]:
        """Analyze teacher response times (grading speed)."""
        graded = submissions.filter(
            status=AssignmentSubmission.Status.GRADED,
            graded_at__isnull=False
        )

        if not graded.exists():
            return {
                'first_grade_at': None,
                'last_grade_at': None,
                'grading_period_days': None,
                'total_graded': 0,
            }

        graded_list = list(graded.order_by('graded_at'))
        first_grade = graded_list[0].graded_at
        last_grade = graded_list[-1].graded_at

        period = (last_grade - first_grade).days if first_grade else None

        return {
            'first_grade_at': first_grade.isoformat() if first_grade else None,
            'last_grade_at': last_grade.isoformat() if last_grade else None,
            'grading_period_days': period,
            'total_graded': len(graded_list),
        }

    def invalidate_cache(self):
        """Invalidate all cached statistics for this assignment."""
        cache.delete(f"{self.cache_prefix}_overall")
        cache.delete(f"{self.cache_prefix}_by_student")
        cache.delete(f"{self.cache_prefix}_by_question")
        cache.delete(f"{self.cache_prefix}_time_analysis")
        logger.info(f"Invalidated all statistics caches for assignment {self.assignment.id}")

    @staticmethod
    def invalidate_assignment(assignment_id: int):
        """Invalidate all caches for a specific assignment."""
        cache_prefix = f"assignment_stats_{assignment_id}"
        cache.delete(f"{cache_prefix}_overall")
        cache.delete(f"{cache_prefix}_by_student")
        cache.delete(f"{cache_prefix}_by_question")
        cache.delete(f"{cache_prefix}_time_analysis")
        logger.info(f"Invalidated all statistics caches for assignment {assignment_id}")
