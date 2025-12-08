#!/usr/bin/env python
"""
Performance Audit Script - Direct Query Analysis

Bypasses Daphne/Twisted issues by running directly with Django test client.
"""

import os, sys, django

# Setup Django (disable daphne to avoid OpenSSL issues)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Patch settings to remove daphne
import config.settings as settings_module
settings_module.INSTALLED_APPS = [app for app in settings_module.INSTALLED_APPS if 'daphne' not in app]

django.setup()

from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import time, timedelta
from django.utils import timezone

User = get_user_model()


def setup_test_data():
    """Create test data for profiling"""
    print("Setting up test data...")

    # Try to reuse existing users or create new ones
    student, _ = User.objects.get_or_create(
        username='perf_student',
        defaults={'email': 'perf_student@test.com', 'role': 'student', 'password': 'test123'}
    )
    teacher, _ = User.objects.get_or_create(
        username='perf_teacher',
        defaults={'email': 'perf_teacher@test.com', 'role': 'teacher', 'password': 'test123'}
    )
    tutor, _ = User.objects.get_or_create(
        username='perf_tutor',
        defaults={'email': 'perf_tutor@test.com', 'role': 'tutor', 'password': 'test123'}
    )
    parent, _ = User.objects.get_or_create(
        username='perf_parent',
        defaults={'email': 'perf_parent@test.com', 'role': 'parent', 'password': 'test123'}
    )


    # Profiles (auto-created by signals, just update - with error handling)
    try:
        student.student_profile.tutor = tutor
        student.student_profile.parent = parent
        student.student_profile.grade = '10'
        student.student_profile.goal = 'Pass'
        student.student_profile.save()
    except Exception as e:
        print(f"Note: Profile update skipped: {e}")

    # Subject & enrollment
    from django.apps import apps
    Subject = apps.get_model('materials', 'Subject')
    SubjectEnrollment = apps.get_model('materials', 'SubjectEnrollment')
    Material = apps.get_model('materials', 'Material')
    MaterialProgress = apps.get_model('materials', 'MaterialProgress')
    subject = Subject.objects.create(name='Perf Test Math', color='#FF0000')
    enrollment = SubjectEnrollment.objects.create(
        student=student, subject=subject, teacher=teacher, assigned_by=tutor, is_active=True
    )

    # Materials
    for i in range(5):
        m = Material.objects.create(
            title=f'Material {i+1}', type='text', status='active', subject=subject, author=teacher
        )
        m.assigned_to.add(student)
        MaterialProgress.objects.create(
            student=student, material=m, is_completed=(i < 2), progress_percentage=100 if i < 2 else 50
        )

    # Forum chat
    ChatRoom = apps.get_model('chat', 'ChatRoom')
    Message = apps.get_model('chat', 'Message')
    chat = ChatRoom.objects.create(
        name=f'{subject.name} - {student.get_full_name()}',
        type='forum_subject', enrollment=enrollment, is_active=True
    )
    chat.participants.add(student, teacher)
    for i in range(10):
        Message.objects.create(
            room=chat, sender=teacher if i % 2 == 0 else student,
            content=f'Msg {i+1}', message_type='text'
        )

    # Lessons
    Lesson = apps.get_model('scheduling', 'Lesson')
    today = timezone.now().date()
    for i in range(5):
        Lesson.objects.create(
            teacher=teacher, student=student, subject=subject,
            date=today + timedelta(days=i), start_time=time(10, 0), end_time=time(11, 0)
        )

    # Invoices
    Invoice = apps.get_model('invoices', 'Invoice')
    for i in range(5):
        Invoice.objects.create(
            tutor=tutor, student=student, parent=parent, amount=Decimal('5000.00'),
            description=f'Inv {i+1}', due_date=today + timedelta(days=7),
            status='sent' if i < 3 else 'draft'
        )

    print("✓ Test data created\n")
    return {'student': student, 'teacher': teacher, 'tutor': tutor, 'parent': parent, 'chat_id': chat.id}


def profile_endpoint(client, name, method, url, user, target=10):
    """Profile single endpoint"""
    client.force_authenticate(user=user)
    reset_queries()

    with CaptureQueriesContext(connection) as ctx:
        if method == 'GET':
            response = client.get(url)
        else:
            response = client.post(url, {}, format='json')

        query_count = len(ctx.captured_queries)

    passed = query_count <= target
    status_icon = "✓" if passed else "✗"

    print(f"{status_icon} {name:<45} | {query_count:>3} queries | HTTP {response.status_code} | {'PASS' if passed else 'FAIL'}")

    if not passed:
        print(f"   └─ Target: ≤ {target} queries, Actual: {query_count}")

        # Show query breakdown
        query_types = {}
        for q in ctx.captured_queries:
            sql = q['sql']
            if 'FROM "accounts_user"' in sql:
                key = 'User'
            elif 'FROM "materials_' in sql:
                key = 'Materials'
            elif 'FROM "chat_' in sql:
                key = 'Chat'
            elif 'FROM "scheduling_' in sql:
                key = 'Scheduling'
            elif 'FROM "invoices_' in sql:
                key = 'Invoices'
            elif 'FROM "accounts_studentprofile"' in sql or 'FROM "accounts_parentprofile"' in sql:
                key = 'Profiles'
            else:
                key = 'Other'
            query_types[key] = query_types.get(key, 0) + 1

        for k, v in sorted(query_types.items()):
            print(f"      • {k}: {v}")

    return {'name': name, 'count': query_count, 'passed': passed, 'target': target}


def main():
    """Run complete audit"""
    print("=" * 80)
    print("QUERY PERFORMANCE AUDIT - THE BOT PLATFORM")
    print("=" * 80)
    print()

    # Setup
    data = setup_test_data()
    client = APIClient()
    results = []

    # Dashboard Endpoints
    print("1. DASHBOARD ENDPOINTS (Target: ≤ 10 queries)")
    print("-" * 80)
    results.append(profile_endpoint(client, "Student Dashboard", 'GET', '/api/dashboard/student/', data['student'], 10))
    results.append(profile_endpoint(client, "Teacher Dashboard", 'GET', '/api/dashboard/teacher/', data['teacher'], 10))
    results.append(profile_endpoint(client, "Tutor Dashboard", 'GET', '/api/dashboard/tutor/', data['tutor'], 10))
    results.append(profile_endpoint(client, "Parent Dashboard", 'GET', '/api/dashboard/parent/', data['parent'], 12))

    # Forum Endpoints
    print("\n2. FORUM ENDPOINTS (Target: ≤ 5 queries)")
    print("-" * 80)
    results.append(profile_endpoint(client, "Forum Chat List (Student)", 'GET', '/api/chat/forum/', data['student'], 5))
    results.append(profile_endpoint(client, "Forum Chat List (Teacher)", 'GET', '/api/chat/forum/', data['teacher'], 5))
    results.append(profile_endpoint(client, "Forum Messages", 'GET', f'/api/chat/forum/{data["chat_id"]}/messages/', data['student'], 5))

    # Scheduling Endpoints
    print("\n3. SCHEDULING ENDPOINTS (Target: ≤ 5 queries)")
    print("-" * 80)
    results.append(profile_endpoint(client, "Lesson List (Student)", 'GET', '/api/scheduling/lessons/', data['student'], 5))
    results.append(profile_endpoint(client, "Lesson List (Teacher)", 'GET', '/api/scheduling/lessons/', data['teacher'], 5))

    # Invoice Endpoints
    print("\n4. INVOICE ENDPOINTS (Target: ≤ 5 queries)")
    print("-" * 80)
    results.append(profile_endpoint(client, "Invoice List (Tutor)", 'GET', '/api/invoices/tutor/', data['tutor'], 5))
    results.append(profile_endpoint(client, "Invoice List (Parent)", 'GET', '/api/invoices/parent/', data['parent'], 5))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed

    print(f"\nTotal Endpoints: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {(passed/total*100):.1f}%")

    if failed > 0:
        print("\nFailed Endpoints:")
        for r in results:
            if not r['passed']:
                print(f"  • {r['name']}: {r['count']} queries (target: ≤ {r['target']})")

        print("\nRecommendations:")
        print("  1. Review failed endpoints for missing select_related/prefetch_related")
        print("  2. Use Django Debug Toolbar for detailed query analysis")
        print("  3. Check for N+1 patterns in loops accessing related objects")
        print("  4. Consider database indexing for frequently filtered fields")

    # Cleanup (skip to avoid circular ordering issue)
    print("\n" + "=" * 80)
    print("Test data retained for reuse in next run.")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
