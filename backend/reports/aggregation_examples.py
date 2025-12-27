"""
Examples of using ReportDataAggregationService

This module demonstrates how to use the aggregation service
for common report generation and analysis tasks.
"""

from reports.aggregation import ReportDataAggregationService
from datetime import datetime, timedelta


def example_student_progress_report():
    """Generate a comprehensive student progress report."""
    service = ReportDataAggregationService()

    # Get progress metrics for a specific student
    student_id = 123
    result = service.get_student_progress_metrics(
        student_id=student_id,
        date_from='2025-01-01',
        date_to='2025-12-31'
    )

    print(f"Student {student_id} Progress Report")
    print("=" * 50)
    print(f"Overall Progress: {result['overall_progress']}%")

    # Material progress
    materials = result['materials']
    print(f"\nMaterials:")
    print(f"  - Total: {materials['total']}")
    print(f"  - Completed: {materials['completed']}")
    print(f"  - Average Progress: {materials['avg_progress']}%")

    # Assignment metrics
    assignments = result['assignments']
    print(f"\nAssignments:")
    print(f"  - Total: {assignments['total']}")
    print(f"  - Submitted: {assignments['submitted']}")
    print(f"  - Average Score: {assignments['avg_score']}")
    print(f"  - Late Submissions: {assignments['late_submissions']}")

    # Engagement
    engagement = result['engagement']
    print(f"\nEngagement:")
    print(f"  - Time Spent: {engagement['total_time_spent_hours']} hours")
    print(f"  - Active Days: {engagement['activity_days']}")

    # Trends
    trends = result['trends']
    print(f"\nTrends:")
    print(f"  - Previous Period: {trends['previous_period_progress']}%")
    print(f"  - Change: {trends['progress_change']:+.1f}%")
    print(f"  - Status: {'Improving' if trends['is_improving'] else 'Not improving'}")


def example_assignment_statistics():
    """Generate assignment statistics for a teacher."""
    service = ReportDataAggregationService()

    # Get statistics for all assignments by a teacher
    teacher_id = 456
    result = service.get_assignment_statistics(
        teacher_id=teacher_id,
        date_from='2025-11-01',
        date_to='2025-12-31'
    )

    print(f"Assignment Statistics (Teacher {teacher_id}, Nov-Dec 2025)")
    print("=" * 60)
    print(f"Total Assignments: {result['total_assignments']}")
    print(f"Total Submissions: {result['total_submissions']}")
    print(f"Completion Rate: {result['completion_rate']}%")
    print(f"Late Submission Rate: {result['late_submission_rate']}%")

    # Score statistics
    scores = result['score_statistics']
    print(f"\nScore Statistics:")
    print(f"  - Average: {scores['average']}")
    print(f"  - Median: {scores['median']}")
    print(f"  - Range: {scores['min']} - {scores['max']}")
    print(f"  - Std Dev: {scores['std_dev']}")

    # Percentiles
    print(f"\nPercentiles:")
    for pct, value in scores['percentiles'].items():
        print(f"  - {pct}: {value}")

    # Grade distribution
    dist = result['score_distribution']
    print(f"\nGrade Distribution:")
    print(f"  - A (90+): {dist['a']}")
    print(f"  - B (80-89): {dist['b']}")
    print(f"  - C (70-79): {dist['c']}")
    print(f"  - D (60-69): {dist['d']}")
    print(f"  - F (<60): {dist['f']}")


def example_learning_metrics():
    """Get learning metrics for a student."""
    service = ReportDataAggregationService()

    student_id = 789
    result = service.get_learning_metrics(
        student_id=student_id,
        date_from='2025-11-01',
        date_to='2025-12-31'
    )

    print(f"Learning Metrics (Student {student_id}, Nov-Dec 2025)")
    print("=" * 50)
    print(f"Engagement Score: {result['engagement_score']}/100")
    print(f"Performance Score: {result['performance_score']}/100")
    print(f"Activity Level: {result['activity_level'].upper()}")
    print(f"Time Spent: {result['time_spent_hours']} hours")
    print(f"Participation Rate: {result['participation_rate']}%")
    print(f"Consistency Score: {result['consistency_score']}/100")
    print(f"Improvement Trend: {result['improvement_trend'].upper()}")


def example_weekly_report():
    """Generate a weekly aggregation report."""
    service = ReportDataAggregationService()

    teacher_id = 456
    result = service.aggregate_weekly(
        teacher_id=teacher_id,
        include_metrics=['submissions', 'avg_score', 'completion_rate', 'engagement']
    )

    print(f"Weekly Report (Teacher {teacher_id})")
    print("=" * 60)
    print(f"Period: {result['date_from']} to {result['date_to']}")
    print("\nWeekly Aggregations:")
    print("-" * 60)

    for agg in result['aggregations']:
        print(f"\nWeek starting: {agg.get('period_start', 'Unknown')}")
        print(f"  Submissions: {agg.get('submissions', 'N/A')}")
        print(f"  Average Score: {agg.get('avg_score', 'N/A')}")
        print(f"  Completion Rate: {agg.get('completion_rate', 'N/A')}%")


def example_subject_performance():
    """Get performance metrics by subject."""
    service = ReportDataAggregationService()

    teacher_id = 456
    result = service.aggregate_by_subject(
        teacher_id=teacher_id,
        date_from='2025-11-01',
        date_to='2025-12-31'
    )

    print(f"Subject Performance Analysis (Teacher {teacher_id})")
    print("=" * 70)
    print(f"Total Subjects: {result['total_subjects']}\n")

    for subject in result['subjects']:
        print(f"Subject: {subject['subject_name']} (ID: {subject['subject_id']})")
        print(f"  - Average Score: {subject['avg_score']}/100")
        print(f"  - Students: {subject['student_count']}")
        print(f"  - Submissions: {subject['submission_count']}")
        print()


def example_monthly_trend_analysis():
    """Analyze monthly trends."""
    service = ReportDataAggregationService()

    teacher_id = 456
    result = service.aggregate_monthly(
        teacher_id=teacher_id,
        date_from='2025-09-01',
        date_to='2025-12-31',
        include_metrics=['submissions', 'avg_score', 'completion_rate']
    )

    print(f"Monthly Trend Analysis (Teacher {teacher_id})")
    print("=" * 60)

    for month_data in result['aggregations']:
        print(f"\nMonth: {month_data.get('period_start', 'Unknown')}")
        print(f"  Submissions: {month_data.get('submissions', 'N/A')}")
        print(f"  Average Score: {month_data.get('avg_score', 'N/A')}")
        print(f"  Completion Rate: {month_data.get('completion_rate', 'N/A')}%")


def example_caching_usage():
    """Demonstrate caching functionality."""
    service = ReportDataAggregationService()

    student_id = 123

    # First call will hit database and cache result
    print("First call (database)...")
    result1 = service.get_student_progress_metrics(
        student_id=student_id,
        use_cache=True
    )

    # Second call will use cache (faster)
    print("Second call (cache)...")
    result2 = service.get_student_progress_metrics(
        student_id=student_id,
        use_cache=True
    )

    # Results should be identical
    assert result1['overall_progress'] == result2['overall_progress']
    print(f"✓ Cache works! Progress: {result1['overall_progress']}%")


if __name__ == '__main__':
    # Uncomment examples to run them
    # example_student_progress_report()
    # example_assignment_statistics()
    # example_learning_metrics()
    # example_weekly_report()
    # example_subject_performance()
    # example_monthly_trend_analysis()
    # example_caching_usage()

    print("Aggregation service examples available!")
    print("See ReportDataAggregationService documentation for usage.")
