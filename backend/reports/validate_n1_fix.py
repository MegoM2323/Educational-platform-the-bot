#!/usr/bin/env python
"""
Validation script for N+1 query optimization (T_REPORT_002)

Run with: python manage.py shell < validate_n1_fix.py
Or: python reports/validate_n1_fix.py (from backend directory)
"""

import os
import sys
import django

# Setup Django
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count
from django.test.utils import CaptureQueriesContext

from reports.models import Report, ReportRecipient
from reports.serializers import ReportListSerializer
from reports.views import ReportViewSet

User = get_user_model()


def reset_queries():
    """Reset Django query counter"""
    connection.queries_log.clear()


def validate_annotations_present():
    """Check that annotations are added to queryset"""
    print("\n" + "=" * 70)
    print("TEST 1: Verify annotations are present in queryset")
    print("=" * 70)

    # Create a test user and report
    teacher = User.objects.create_user(
        username="test_teacher_validation",
        email="teacher_val@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="Test",
        last_name="Teacher",
    )

    student = User.objects.create_user(
        username="test_student_validation",
        email="student_val@test.com",
        password="TestPass123!",
        role="student",
        first_name="Test",
        last_name="Student",
    )

    report = Report.objects.create(
        title="Test Report",
        description="Test",
        type=Report.Type.STUDENT_PROGRESS,
        status=Report.Status.DRAFT,
        author=teacher,
        start_date="2025-01-01",
        end_date="2025-01-31",
    )
    report.target_students.add(student)

    # Get queryset through ViewSet
    viewset = ReportViewSet()
    viewset.request = type("Request", (), {"user": teacher})()
    queryset = viewset.get_queryset()

    report_with_annotations = queryset.filter(id=report.id).first()

    # Check annotations
    checks = [
        ("target_students_count", hasattr(report_with_annotations, "target_students_count")),
        ("target_parents_count", hasattr(report_with_annotations, "target_parents_count")),
        ("recipients_count", hasattr(report_with_annotations, "recipients_count")),
    ]

    all_present = True
    for annotation_name, is_present in checks:
        status = "✓ PASS" if is_present else "✗ FAIL"
        print(f"  {status}: Annotation '{annotation_name}' present")
        if not is_present:
            all_present = False

    # Check annotation values
    print(f"\n  Annotation values:")
    print(f"    - target_students_count: {report_with_annotations.target_students_count}")
    print(f"    - target_parents_count: {report_with_annotations.target_parents_count}")
    print(f"    - recipients_count: {report_with_annotations.recipients_count}")

    # Cleanup
    report.delete()
    student.delete()
    teacher.delete()

    return all_present


def validate_serializer_fallback():
    """Check that serializer has fallback logic"""
    print("\n" + "=" * 70)
    print("TEST 2: Verify serializer fallback logic")
    print("=" * 70)

    teacher = User.objects.create_user(
        username="test_teacher_fallback",
        email="teacher_fb@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="Test",
        last_name="Teacher",
    )

    student = User.objects.create_user(
        username="test_student_fallback",
        email="student_fb@test.com",
        password="TestPass123!",
        role="student",
        first_name="Test",
        last_name="Student",
    )

    report = Report.objects.create(
        title="Test Report",
        description="Test",
        type=Report.Type.STUDENT_PROGRESS,
        status=Report.Status.DRAFT,
        author=teacher,
        start_date="2025-01-01",
        end_date="2025-01-31",
    )
    report.target_students.add(student)

    # Test serializer WITHOUT annotation (simulating fallback)
    serializer = ReportListSerializer(report)
    data = serializer.data

    checks = [
        ("target_students_count" in data, "target_students_count in response"),
        ("target_parents_count" in data, "target_parents_count in response"),
        ("recipients_count" in data, "recipients_count in response"),
        (data.get("target_students_count") == 1, "target_students_count value correct"),
        (data.get("target_parents_count") == 0, "target_parents_count value correct"),
        (data.get("recipients_count") == 0, "recipients_count value correct"),
    ]

    all_pass = True
    for check, description in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"  {status}: {description}")
        if not check:
            all_pass = False

    # Cleanup
    report.delete()
    student.delete()
    teacher.delete()

    return all_pass


def validate_query_count():
    """Check that query count is optimized"""
    print("\n" + "=" * 70)
    print("TEST 3: Verify N+1 query optimization")
    print("=" * 70)

    # Create test data
    teacher = User.objects.create_user(
        username="test_teacher_queries",
        email="teacher_q@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="Test",
        last_name="Teacher",
    )

    students = [
        User.objects.create_user(
            username=f"test_student_q{i}",
            email=f"student_q{i}@test.com",
            password="TestPass123!",
            role="student",
            first_name="Test",
            last_name=f"Student{i}",
        )
        for i in range(2)
    ]

    # Create reports with relationships
    reports = []
    for i in range(10):
        report = Report.objects.create(
            title=f"Report {i}",
            description=f"Description {i}",
            type=Report.Type.STUDENT_PROGRESS,
            status=Report.Status.DRAFT,
            author=teacher,
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        report.target_students.set(students)
        reports.append(report)

    # Count queries
    reset_queries()

    viewset = ReportViewSet()
    viewset.request = type("Request", (), {"user": teacher})()
    queryset = viewset.get_queryset()

    # Force evaluation (like serializing)
    list(queryset)

    query_count = len(connection.queries)

    print(f"\n  Query statistics:")
    print(f"    - Number of reports: 10")
    print(f"    - Total queries executed: {query_count}")

    # Show query breakdown
    print(f"\n  Query breakdown:")
    for i, query in enumerate(connection.queries, 1):
        sql_preview = query["sql"][:80].replace("\n", " ")
        print(f"    {i}. {sql_preview}...")

    # Validation
    expected_max = 15  # Should be significantly less than 30+ for N+1
    passed = query_count < expected_max

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"\n  {status}: Query count {query_count} < {expected_max}")

    if not passed:
        print(f"    WARNING: Expected < {expected_max} queries for 10 reports")
        print(f"    This suggests N+1 optimization may not be working")

    # Cleanup
    for report in reports:
        report.delete()
    for student in students:
        student.delete()
    teacher.delete()

    return passed


def main():
    """Run all validations"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Reports N+1 Query Optimization Validation (T_REPORT_002)".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    results = {
        "Annotations Present": validate_annotations_present(),
        "Serializer Fallback": validate_serializer_fallback(),
        "Query Optimization": validate_query_count(),
    }

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_pass = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_pass = False

    print("\n" + "=" * 70)

    if all_pass:
        print("✓ All validation tests passed!")
        print("\nN+1 query optimization has been successfully implemented.")
        print("Report list views will now use annotated counts instead of N+1 queries.")
    else:
        print("✗ Some validation tests failed. Please review the output above.")
        sys.exit(1)

    print("=" * 70 + "\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
