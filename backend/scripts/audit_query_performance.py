#!/usr/bin/env python
"""
Performance Audit Script - Query Optimization Analysis

This script:
1. Runs all dashboard, forum, scheduling, and invoice endpoints
2. Measures query counts for each endpoint
3. Identifies N+1 query issues
4. Generates performance report

Usage:
    python backend/scripts/audit_query_performance.py

Requirements:
    - Django debug toolbar (optional, for detailed analysis)
    - django.test.utils.CaptureQueriesContext
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test.utils import CaptureQueriesContext
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal
from datetime import date, time, timedelta
from django.utils import timezone
import json

User = get_user_model()


class QueryProfiler:
    """Profile query performance for endpoints"""

    def __init__(self):
        self.results = []
        self.client = APIClient()

    def profile_endpoint(self, name, method, url, user=None, data=None):
        """Profile single endpoint"""
        if user:
            self.client.force_authenticate(user=user)
        else:
            self.client.force_authenticate(user=None)

        reset_queries()

        with CaptureQueriesContext(connection) as context:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, data, format='json')
            else:
                raise ValueError(f'Unsupported method: {method}')

            query_count = len(context.captured_queries)
            queries = context.captured_queries

        result = {
            'name': name,
            'url': url,
            'method': method,
            'query_count': query_count,
            'status_code': response.status_code,
            'queries': queries,
            'passed': query_count < 10  # Target: < 10 queries for most endpoints
        }

        self.results.append(result)
        return result

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "=" * 80)
        print("QUERY PERFORMANCE AUDIT SUMMARY")
        print("=" * 80)

        total_endpoints = len(self.results)
        passed_endpoints = sum(1 for r in self.results if r['passed'])
        failed_endpoints = total_endpoints - passed_endpoints

        print(f"\nTotal Endpoints Tested: {total_endpoints}")
        print(f"Passed (< 10 queries): {passed_endpoints}")
        print(f"Failed (>= 10 queries): {failed_endpoints}")
        print(f"Pass Rate: {(passed_endpoints/total_endpoints*100):.1f}%\n")

        # Group by category
        categories = {}
        for result in self.results:
            category = result['name'].split(' - ')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        # Print by category
        for category, results in sorted(categories.items()):
            print(f"\n{category}")
            print("-" * 80)

            for result in results:
                status = "✓ PASS" if result['passed'] else "✗ FAIL"
                status_code = result['status_code']
                query_count = result['query_count']

                print(f"  {status} | {result['name']:<50} | {query_count:>3} queries | HTTP {status_code}")

                # Show detailed query breakdown if failed
                if not result['passed']:
                    print(f"       Query breakdown:")
                    query_groups = {}
                    for q in result['queries']:
                        sql = q['sql']
                        # Identify query type
                        if 'SELECT' in sql:
                            if 'FROM "accounts_user"' in sql:
                                key = 'User queries'
                            elif 'FROM "materials_' in sql:
                                key = 'Materials queries'
                            elif 'FROM "chat_' in sql:
                                key = 'Chat queries'
                            elif 'FROM "scheduling_' in sql:
                                key = 'Scheduling queries'
                            elif 'FROM "invoices_' in sql:
                                key = 'Invoice queries'
                            else:
                                key = 'Other SELECT'
                        elif 'INSERT' in sql:
                            key = 'INSERT queries'
                        elif 'UPDATE' in sql:
                            key = 'UPDATE queries'
                        else:
                            key = 'Other queries'

                        query_groups[key] = query_groups.get(key, 0) + 1

                    for group, count in sorted(query_groups.items()):
                        print(f"         - {group}: {count}")

        # Detailed recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        for result in self.results:
            if not result['passed']:
                print(f"\n{result['name']} ({result['url']}):")
                print(f"  - Current: {result['query_count']} queries")
                print(f"  - Target: < 10 queries")

                # Analyze queries for common issues
                n_plus_one_detected = False
                for i, q in enumerate(result['queries']):
                    sql = q['sql']

                    # Detect N+1 patterns
                    if i > 0:
                        prev_sql = result['queries'][i-1]['sql']
                        # Check if similar queries repeated
                        if 'SELECT' in sql and 'WHERE' in sql and 'SELECT' in prev_sql:
                            if sql.split('WHERE')[0] == prev_sql.split('WHERE')[0]:
                                n_plus_one_detected = True
                                break

                if n_plus_one_detected:
                    print(f"  - N+1 query pattern detected!")
                    print(f"  - Recommendation: Use select_related() or prefetch_related()")

        print("\n" + "=" * 80)


def setup_test_data():
    """Setup test data for profiling"""
    print("Setting up test data...")

    # Clean up existing test users
    User.objects.filter(username__startswith='perf_test_').delete()

    # Create users
    student = User.objects.create_user(
        username='perf_test_student',
        email='perf_student@test.com',
        role='student',
        password='testpass123'
    )

    teacher = User.objects.create_user(
        username='perf_test_teacher',
        email='perf_teacher@test.com',
        role='teacher',
        password='testpass123'
    )

    tutor = User.objects.create_user(
        username='perf_test_tutor',
        email='perf_tutor@test.com',
        role='tutor',
        password='testpass123'
    )

    parent = User.objects.create_user(
        username='perf_test_parent',
        email='perf_parent@test.com',
        role='parent',
        password='testpass123'
    )

    # Create profiles
    from accounts.models import StudentProfile, ParentProfile
    student_profile = StudentProfile.objects.create(
        user=student,
        tutor=tutor,
        parent=parent,
        grade='10',
        goal='Pass exam'
    )

    parent_profile = ParentProfile.objects.create(user=parent)

    # Create subjects and enrollments
    from materials.models import Subject, SubjectEnrollment, Material, MaterialProgress
    subject = Subject.objects.create(
        name='Performance Test Math',
        description='Math course for performance testing',
        color='#FF0000'
    )

    enrollment = SubjectEnrollment.objects.create(
        student=student,
        subject=subject,
        teacher=teacher,
        assigned_by=tutor,
        is_active=True
    )

    # Create materials with progress (5 materials)
    for i in range(5):
        material = Material.objects.create(
            title=f'Test Material {i+1}',
            description=f'Description {i+1}',
            type='text',
            status='active',
            subject=subject,
            author=teacher
        )
        material.assigned_to.add(student)

        MaterialProgress.objects.create(
            student=student,
            material=material,
            is_completed=(i < 2),  # First 2 completed
            progress_percentage=100 if i < 2 else 50
        )

    # Create forum chat
    from chat.models import ChatRoom, Message
    chat = ChatRoom.objects.create(
        name=f'{subject.name} - {student.get_full_name()}',
        type='forum_subject',
        enrollment=enrollment,
        is_active=True
    )
    chat.participants.add(student, teacher)

    # Create messages
    for i in range(10):
        Message.objects.create(
            room=chat,
            sender=teacher if i % 2 == 0 else student,
            content=f'Performance test message {i+1}',
            message_type='text'
        )

    # Create lessons
    from scheduling.models import Lesson
    today = timezone.now().date()
    for i in range(5):
        Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=subject,
            date=today + timedelta(days=i),
            start_time=time(10, 0),
            end_time=time(11, 0),
            description=f'Performance test lesson {i+1}',
            telemost_link='https://telemost.example.com'
        )

    # Create invoices
    from invoices.models import Invoice
    for i in range(5):
        Invoice.objects.create(
            tutor=tutor,
            student=student,
            parent=parent,
            amount=Decimal('5000.00'),
            description=f'Performance test invoice {i+1}',
            due_date=today + timedelta(days=7),
            status='sent' if i < 3 else 'draft'
        )

    print("Test data created successfully!\n")

    return {
        'student': student,
        'teacher': teacher,
        'tutor': tutor,
        'parent': parent,
        'chat_id': chat.id
    }


def run_audit():
    """Run complete performance audit"""
    print("\n" + "=" * 80)
    print("STARTING QUERY PERFORMANCE AUDIT")
    print("=" * 80)

    # Setup test data
    test_data = setup_test_data()

    profiler = QueryProfiler()

    # Dashboard Endpoints
    print("\nProfiling Dashboard Endpoints...")
    profiler.profile_endpoint(
        "Dashboard - Student",
        'GET',
        '/api/dashboard/student/',
        user=test_data['student']
    )

    profiler.profile_endpoint(
        "Dashboard - Teacher",
        'GET',
        '/api/dashboard/teacher/',
        user=test_data['teacher']
    )

    profiler.profile_endpoint(
        "Dashboard - Tutor",
        'GET',
        '/api/dashboard/tutor/',
        user=test_data['tutor']
    )

    profiler.profile_endpoint(
        "Dashboard - Parent",
        'GET',
        '/api/dashboard/parent/',
        user=test_data['parent']
    )

    # Forum Endpoints
    print("Profiling Forum Endpoints...")
    profiler.profile_endpoint(
        "Forum - Chat List (Student)",
        'GET',
        '/api/chat/forum/',
        user=test_data['student']
    )

    profiler.profile_endpoint(
        "Forum - Chat List (Teacher)",
        'GET',
        '/api/chat/forum/',
        user=test_data['teacher']
    )

    profiler.profile_endpoint(
        "Forum - Messages",
        'GET',
        f'/api/chat/forum/{test_data["chat_id"]}/messages/',
        user=test_data['student']
    )

    # Scheduling Endpoints
    print("Profiling Scheduling Endpoints...")
    profiler.profile_endpoint(
        "Scheduling - Lesson List (Student)",
        'GET',
        '/api/scheduling/lessons/',
        user=test_data['student']
    )

    profiler.profile_endpoint(
        "Scheduling - Lesson List (Teacher)",
        'GET',
        '/api/scheduling/lessons/',
        user=test_data['teacher']
    )

    # Invoice Endpoints
    print("Profiling Invoice Endpoints...")
    profiler.profile_endpoint(
        "Invoice - Tutor List",
        'GET',
        '/api/invoices/tutor/',
        user=test_data['tutor']
    )

    profiler.profile_endpoint(
        "Invoice - Parent List",
        'GET',
        '/api/invoices/parent/',
        user=test_data['parent']
    )

    # Print summary
    profiler.print_summary()

    # Cleanup
    print("\nCleaning up test data...")
    User.objects.filter(username__startswith='perf_test_').delete()
    print("Cleanup complete.")

    return profiler.results


if __name__ == '__main__':
    results = run_audit()

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r['passed'])
    sys.exit(1 if failed > 0 else 0)
