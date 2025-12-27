#!/usr/bin/env python
"""
Simple test script to verify the recurring lesson validation fix.
This bypasses the migration issues and tests the core fix directly.
"""
import os
import django
from datetime import date, time, timedelta

# Setup Django
os.environ['ENVIRONMENT'] = 'test'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Add backend to path
import sys
backend_path = '/home/mego/Python Projects/THE_BOT_platform/backend'
sys.path.insert(0, backend_path)
os.chdir(backend_path)

django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from materials.models import Subject, SubjectEnrollment
from scheduling.models import RecurringLesson
from scheduling.services.recurring_service import RecurringLessonService

User = get_user_model()

def test_validation_with_valid_enrollment():
    """Test that lessons are generated successfully with valid enrollment"""
    print("\n=== TEST 1: Generate lessons with VALID enrollment ===")

    # Create users
    teacher = User.objects.create_user(
        username="teacher1",
        email="teacher1@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="John",
        last_name="Teacher",
    )

    student = User.objects.create_user(
        username="student1",
        email="student1@test.com",
        password="TestPass123!",
        role="student",
        first_name="Jane",
        last_name="Student",
    )

    subject = Subject.objects.create(
        name="Mathematics",
        description="Math subject",
        level="beginner",
    )

    # Create valid enrollment
    enrollment = SubjectEnrollment.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        is_active=True,
    )

    # Create recurring lesson
    recurring_lesson = RecurringLesson.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        start_time=time(10, 0),
        end_time=time(11, 0),
        pattern="weekly",
        interval=1,
        weekdays=[0, 2, 4],
        is_active=True,
    )

    # Generate lessons
    try:
        result = RecurringLessonService.generate_lessons(recurring_lesson)
        print(f"SUCCESS: Generated {len(result['created'])} lessons")
        print(f"  Total dates: {result['total']}")
        print(f"  Created: {len(result['created'])}")
        print(f"  Skipped: {len(result['skipped'])}")
        print(f"  Conflicts: {len(result['conflicts'])}")
        return True
    except ValidationError as e:
        print(f"FAILED: {e}")
        return False


def test_validation_without_enrollment():
    """Test that ValidationError is raised when NO enrollment exists"""
    print("\n=== TEST 2: Generate lessons WITHOUT enrollment (should FAIL) ===")

    # Create users
    teacher = User.objects.create_user(
        username="teacher2",
        email="teacher2@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="John",
        last_name="Teacher",
    )

    student = User.objects.create_user(
        username="student2",
        email="student2@test.com",
        password="TestPass123!",
        role="student",
        first_name="Jane",
        last_name="Student",
    )

    subject = Subject.objects.create(
        name="Physics",
        description="Physics subject",
        level="beginner",
    )

    # DO NOT create enrollment - this is the test

    # Create recurring lesson
    recurring_lesson = RecurringLesson.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        start_time=time(10, 0),
        end_time=time(11, 0),
        pattern="weekly",
        interval=1,
        weekdays=[0, 2, 4],
        is_active=True,
    )

    # Try to generate lessons - should fail
    try:
        result = RecurringLessonService.generate_lessons(recurring_lesson)
        print(f"FAILED: Should have raised ValidationError but didn't!")
        print(f"  Generated {len(result['created'])} lessons (ORPHANED)")
        return False
    except ValidationError as e:
        print(f"SUCCESS: Caught ValidationError as expected")
        print(f"  Error message: {e}")
        return True


def test_validation_with_inactive_enrollment():
    """Test that ValidationError is raised when enrollment is INACTIVE"""
    print("\n=== TEST 3: Generate lessons with INACTIVE enrollment (should FAIL) ===")

    # Create users
    teacher = User.objects.create_user(
        username="teacher3",
        email="teacher3@test.com",
        password="TestPass123!",
        role="teacher",
        first_name="John",
        last_name="Teacher",
    )

    student = User.objects.create_user(
        username="student3",
        email="student3@test.com",
        password="TestPass123!",
        role="student",
        first_name="Jane",
        last_name="Student",
    )

    subject = Subject.objects.create(
        name="Chemistry",
        description="Chemistry subject",
        level="beginner",
    )

    # Create INACTIVE enrollment
    enrollment = SubjectEnrollment.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        is_active=False,  # INACTIVE
    )

    # Create recurring lesson
    recurring_lesson = RecurringLesson.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        start_time=time(10, 0),
        end_time=time(11, 0),
        pattern="weekly",
        interval=1,
        weekdays=[0, 2, 4],
        is_active=True,
    )

    # Try to generate lessons - should fail
    try:
        result = RecurringLessonService.generate_lessons(recurring_lesson)
        print(f"FAILED: Should have raised ValidationError but didn't!")
        print(f"  Generated {len(result['created'])} lessons (ORPHANED)")
        return False
    except ValidationError as e:
        print(f"SUCCESS: Caught ValidationError as expected")
        print(f"  Error message: {e}")
        return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SCHEDULING VALIDATION FIX - TEST SUITE")
    print("="*70)

    results = []

    # Test 1: Valid enrollment
    results.append(("Valid enrollment", test_validation_with_valid_enrollment()))

    # Test 2: No enrollment
    results.append(("No enrollment (should fail)", test_validation_without_enrollment()))

    # Test 3: Inactive enrollment
    results.append(("Inactive enrollment (should fail)", test_validation_with_inactive_enrollment()))

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"[{status}] {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Validation fix is working correctly!")
        exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) FAILED")
        exit(1)
