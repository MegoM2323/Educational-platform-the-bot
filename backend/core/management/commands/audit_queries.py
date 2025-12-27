"""
Django management command for query performance audit.

Usage:
    python manage.py audit_queries
"""

from django.core.management.base import BaseCommand
from django.test.utils import CaptureQueriesContext
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal
from datetime import time, timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Audit query performance for all critical endpoints'

    def handle(self, *args, **options):
        """Run performance audit"""
        self.stdout.write("=" * 80)
        self.stdout.write("QUERY PERFORMANCE AUDIT")
        self.stdout.write("=" * 80)

        # Setup test data
        self.stdout.write("\nSetting up test data...")
        test_data = self.setup_test_data()
        self.stdout.write("Test data created.\n")

        # Profile endpoints
        results = []
        client = APIClient()

        # Dashboard Endpoints
        self.stdout.write("\n1. DASHBOARD ENDPOINTS")
        self.stdout.write("-" * 80)

        results.append(self.profile_endpoint(
            client, "Student Dashboard", 'GET', '/api/dashboard/student/', test_data['student']
        ))

        results.append(self.profile_endpoint(
            client, "Teacher Dashboard", 'GET', '/api/dashboard/teacher/', test_data['teacher']
        ))

        results.append(self.profile_endpoint(
            client, "Tutor Dashboard", 'GET', '/api/dashboard/tutor/', test_data['tutor']
        ))

        results.append(self.profile_endpoint(
            client, "Parent Dashboard", 'GET', '/api/dashboard/parent/', test_data['parent']
        ))

        # Forum Endpoints
        self.stdout.write("\n2. FORUM ENDPOINTS")
        self.stdout.write("-" * 80)

        results.append(self.profile_endpoint(
            client, "Forum Chat List (Student)", 'GET', '/api/chat/forum/', test_data['student']
        ))

        results.append(self.profile_endpoint(
            client, "Forum Chat List (Teacher)", 'GET', '/api/chat/forum/', test_data['teacher']
        ))

        results.append(self.profile_endpoint(
            client, "Forum Messages", 'GET', f'/api/chat/forum/{test_data["chat_id"]}/messages/', test_data['student']
        ))

        # Scheduling Endpoints
        self.stdout.write("\n3. SCHEDULING ENDPOINTS")
        self.stdout.write("-" * 80)

        results.append(self.profile_endpoint(
            client, "Lesson List (Student)", 'GET', '/api/scheduling/lessons/', test_data['student']
        ))

        results.append(self.profile_endpoint(
            client, "Lesson List (Teacher)", 'GET', '/api/scheduling/lessons/', test_data['teacher']
        ))

        # Invoice Endpoints
        self.stdout.write("\n4. INVOICE ENDPOINTS")
        self.stdout.write("-" * 80)

        results.append(self.profile_endpoint(
            client, "Invoice List (Tutor)", 'GET', '/api/invoices/tutor/', test_data['tutor']
        ))

        results.append(self.profile_endpoint(
            client, "Invoice List (Parent)", 'GET', '/api/invoices/parent/', test_data['parent']
        ))

        # Summary
        self.print_summary(results)

        # Cleanup
        self.stdout.write("\nCleaning up test data...")
        User.objects.filter(username__startswith='audit_test_').delete()
        self.stdout.write(self.style.SUCCESS("Cleanup complete."))

    def setup_test_data(self):
        """Setup test data for profiling"""
        # Clean up existing
        User.objects.filter(username__startswith='audit_test_').delete()

        # Create users
        student = User.objects.create_user(
            username='audit_test_student',
            email='audit_student@test.com',
            role='student',
            password='testpass123'
        )

        teacher = User.objects.create_user(
            username='audit_test_teacher',
            email='audit_teacher@test.com',
            role='teacher',
            password='testpass123'
        )

        tutor = User.objects.create_user(
            username='audit_test_tutor',
            email='audit_tutor@test.com',
            role='tutor',
            password='testpass123'
        )

        parent = User.objects.create_user(
            username='audit_test_parent',
            email='audit_parent@test.com',
            role='parent',
            password='testpass123'
        )

        # Create profiles
        from accounts.models import StudentProfile, ParentProfile
        StudentProfile.objects.create(
            user=student, tutor=tutor, parent=parent, grade='10', goal='Pass exam'
        )
        ParentProfile.objects.create(user=parent)

        # Create subjects and enrollments
        from materials.models import Subject, SubjectEnrollment, Material, MaterialProgress
        subject = Subject.objects.create(
            name='Audit Test Math', description='Math for audit', color='#FF0000'
        )

        enrollment = SubjectEnrollment.objects.create(
            student=student, subject=subject, teacher=teacher, assigned_by=tutor, is_active=True
        )

        # Create materials
        for i in range(5):
            material = Material.objects.create(
                title=f'Material {i+1}', type='text', status='active', subject=subject, author=teacher
            )
            material.assigned_to.add(student)
            MaterialProgress.objects.create(
                student=student, material=material, is_completed=(i < 2), progress_percentage=100 if i < 2 else 50
            )

        # Create forum chat
        from chat.models import ChatRoom, Message
        chat = ChatRoom.objects.create(
            name=f'{subject.name} - {student.get_full_name()}',
            type='forum_subject', enrollment=enrollment, is_active=True
        )
        chat.participants.add(student, teacher)

        # Create messages
        for i in range(10):
            Message.objects.create(
                room=chat, sender=teacher if i % 2 == 0 else student,
                content=f'Message {i+1}', message_type='text'
            )

        # Create lessons
        from scheduling.models import Lesson
        today = timezone.now().date()
        for i in range(5):
            Lesson.objects.create(
                teacher=teacher, student=student, subject=subject,
                date=today + timedelta(days=i), start_time=time(10, 0), end_time=time(11, 0),
                description=f'Lesson {i+1}'
            )

        # Create invoices
        from invoices.models import Invoice
        for i in range(5):
            Invoice.objects.create(
                tutor=tutor, student=student, parent=parent, amount=Decimal('5000.00'),
                description=f'Invoice {i+1}', due_date=today + timedelta(days=7),
                status='sent' if i < 3 else 'draft'
            )

        return {'student': student, 'teacher': teacher, 'tutor': tutor, 'parent': parent, 'chat_id': chat.id}

    def profile_endpoint(self, client, name, method, url, user):
        """Profile single endpoint"""
        client.force_authenticate(user=user)
        reset_queries()

        with CaptureQueriesContext(connection) as context:
            if method == 'GET':
                response = client.get(url)

            query_count = len(context.captured_queries)

        # Determine status
        target = 5 if 'Dashboard' in name or 'List' in name else 3
        passed = query_count <= target

        status_icon = self.style.SUCCESS("✓") if passed else self.style.ERROR("✗")
        status_text = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")

        self.stdout.write(
            f"{status_icon} {name:<40} | {query_count:>3} queries | HTTP {response.status_code} | {status_text}"
        )

        if not passed:
            self.stdout.write(self.style.WARNING(f"   Target: ≤ {target} queries, Actual: {query_count}"))

        return {'name': name, 'query_count': query_count, 'passed': passed, 'target': target}

    def print_summary(self, results):
        """Print summary statistics"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)

        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        failed = total - passed

        self.stdout.write(f"\nTotal Endpoints: {total}")
        self.stdout.write(self.style.SUCCESS(f"Passed: {passed}"))
        self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        self.stdout.write(f"Pass Rate: {(passed/total*100):.1f}%")

        # Failed endpoints
        if failed > 0:
            self.stdout.write("\n" + self.style.ERROR("Failed Endpoints:"))
            for r in results:
                if not r['passed']:
                    self.stdout.write(
                        f"  - {r['name']}: {r['query_count']} queries (target: ≤ {r['target']})"
                    )

            self.stdout.write("\n" + self.style.WARNING("Recommendations:"))
            self.stdout.write("  1. Review dashboard services for missing select_related/prefetch_related")
            self.stdout.write("  2. Check for N+1 queries in related object access")
            self.stdout.write("  3. Use Django Debug Toolbar for detailed query analysis")
            self.stdout.write("  4. Consider adding database indexes for frequently filtered fields")
