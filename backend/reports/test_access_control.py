"""
Comprehensive tests for Report Access Control (T_RPT_008)

Tests for:
- Role-based access (student, parent, teacher, tutor, admin)
- Report sharing (user-specific and role-based)
- Temporary access tokens with expiration
- Access audit logging
- Permission enforcement
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from accounts.models import StudentProfile, ParentProfile
from .models import (
    Report, ReportAccessToken, ReportAccessAuditLog, ReportSharing
)
from .permissions import ReportAccessService, CanAccessReport, CanShareReport, CanEditReport
from .access_control_service import ReportAccessControlService

User = get_user_model()


class ReportAccessServiceTest(TestCase):
    """Test ReportAccessService permission checking logic"""

    def setUp(self):
        """Create test users and reports"""
        # Create users
        self.student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='pass123',
            role='student'
        )

        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='pass123',
            role='parent'
        )

        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='pass123',
            role='teacher'
        )

        self.tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@test.com',
            password='pass123',
            role='tutor'
        )

        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='pass123',
            role='admin',
            is_staff=True
        )

        # Create student profile
        StudentProfile.objects.create(
            user=self.student,
            parent=self.parent
        )

        # Create report
        self.report = Report.objects.create(
            title='Test Report',
            author=self.teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        self.report.target_students.add(self.student)

    def test_student_can_view_own_report(self):
        """Test student can view reports about themselves"""
        can_view = ReportAccessService.can_user_view_report(self.student, self.report)
        self.assertTrue(can_view)

    def test_student_cannot_view_other_student_report(self):
        """Test student cannot view other student's reports"""
        other_student = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='pass123',
            role='student'
        )

        other_report = Report.objects.create(
            title='Other Report',
            author=self.teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        other_report.target_students.add(other_student)

        can_view = ReportAccessService.can_user_view_report(self.student, other_report)
        self.assertFalse(can_view)

    def test_parent_can_view_child_report(self):
        """Test parent can view reports about their children"""
        can_view = ReportAccessService.can_user_view_report(self.parent, self.report)
        self.assertTrue(can_view)

    def test_parent_cannot_view_other_child_report(self):
        """Test parent cannot view reports about other children"""
        other_student = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='pass123',
            role='student'
        )

        other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='pass123',
            role='parent'
        )

        other_report = Report.objects.create(
            title='Other Report',
            author=self.teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        other_report.target_students.add(other_student)

        can_view = ReportAccessService.can_user_view_report(other_parent, other_report)
        self.assertFalse(can_view)

    def test_teacher_can_view_own_report(self):
        """Test teacher can view their own reports"""
        can_view = ReportAccessService.can_user_view_report(self.teacher, self.report)
        self.assertTrue(can_view)

    def test_teacher_cannot_view_other_teacher_report(self):
        """Test teacher cannot view other teacher's reports"""
        other_teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='pass123',
            role='teacher'
        )

        other_report = Report.objects.create(
            title='Other Report',
            author=other_teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        other_report.target_students.add(self.student)

        can_view = ReportAccessService.can_user_view_report(self.teacher, other_report)
        self.assertFalse(can_view)

    def test_admin_can_view_any_report(self):
        """Test admin can view any report"""
        can_view = ReportAccessService.can_user_view_report(self.admin, self.report)
        self.assertTrue(can_view)

    def test_report_sharing_user_specific(self):
        """Test report sharing with specific user"""
        other_teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='pass123',
            role='teacher'
        )

        # Create sharing
        ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            shared_with_user=other_teacher,
            permission='view'
        )

        # Other teacher should now have access
        can_view = ReportAccessService.can_user_view_report(other_teacher, self.report)
        self.assertTrue(can_view)

    def test_report_sharing_role_based(self):
        """Test report sharing with role"""
        # Create sharing with all tutors
        ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            share_type='role',
            shared_role='tutor',
            permission='view'
        )

        # Tutor should now have access
        can_view = ReportAccessService.can_user_view_report(self.tutor, self.report)
        self.assertTrue(can_view)

    def test_expired_sharing_denied(self):
        """Test expired sharing doesn't grant access"""
        other_teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='pass123',
            role='teacher'
        )

        # Create expired sharing
        ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            shared_with_user=other_teacher,
            permission='view',
            expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )

        # Access should be denied
        can_view = ReportAccessService.can_user_view_report(other_teacher, self.report)
        self.assertFalse(can_view)

    def test_can_user_share_report_owner(self):
        """Test report owner can share"""
        can_share = ReportAccessService.can_user_share_report(self.teacher, self.report)
        self.assertTrue(can_share)

    def test_can_user_share_report_non_owner(self):
        """Test non-owner cannot share"""
        can_share = ReportAccessService.can_user_share_report(self.student, self.report)
        self.assertFalse(can_share)

    def test_can_user_edit_report_owner(self):
        """Test report owner can edit"""
        can_edit = ReportAccessService.can_user_edit_report(self.teacher, self.report)
        self.assertTrue(can_edit)

    def test_can_user_edit_report_non_owner(self):
        """Test non-owner cannot edit"""
        can_edit = ReportAccessService.can_user_edit_report(self.student, self.report)
        self.assertFalse(can_edit)


class ReportAccessTokenTest(TestCase):
    """Test temporary access token functionality"""

    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(
            username='user1',
            email='user@test.com',
            password='pass123',
            role='teacher'
        )

        self.report = Report.objects.create(
            title='Test Report',
            author=self.user,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )

    def test_create_access_token(self):
        """Test creating an access token"""
        token = ReportAccessControlService.create_access_token(
            self.report,
            self.user,
            expires_in_hours=24,
            max_accesses=10
        )

        self.assertIsNotNone(token.token)
        self.assertEqual(token.status, ReportAccessToken.Status.ACTIVE)
        self.assertEqual(token.max_accesses, 10)
        self.assertEqual(token.report_id, self.report.id)

    def test_token_validity_active(self):
        """Test token is valid when active and not expired"""
        token = ReportAccessToken.objects.create(
            token='test_token_123',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        self.assertTrue(token.is_valid())

    def test_token_validity_expired(self):
        """Test token is invalid when expired"""
        token = ReportAccessToken.objects.create(
            token='test_token_456',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertFalse(token.is_valid())

    def test_token_validity_revoked(self):
        """Test token is invalid when revoked"""
        token = ReportAccessToken.objects.create(
            token='test_token_789',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            status=ReportAccessToken.Status.REVOKED
        )

        self.assertFalse(token.is_valid())

    def test_token_access_counting(self):
        """Test token access count increments"""
        token = ReportAccessToken.objects.create(
            token='test_token_count',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            max_accesses=10
        )

        self.assertEqual(token.access_count, 0)

        token.increment_access()
        token.refresh_from_db()

        self.assertEqual(token.access_count, 1)

    def test_token_max_accesses_limit(self):
        """Test token becomes invalid after max accesses"""
        token = ReportAccessToken.objects.create(
            token='test_token_limit',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            max_accesses=2,
            access_count=2
        )

        # Should be invalid because max accesses reached
        self.assertFalse(token.is_valid())

    def test_token_revoke(self):
        """Test revoking a token"""
        token = ReportAccessToken.objects.create(
            token='test_token_revoke',
            report=self.report,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        self.assertTrue(token.is_valid())

        token.revoke()
        token.refresh_from_db()

        self.assertFalse(token.is_valid())
        self.assertEqual(token.status, ReportAccessToken.Status.REVOKED)


class ReportAccessAuditLoggingTest(TestCase):
    """Test audit logging for report access"""

    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(
            username='user1',
            email='user@test.com',
            password='pass123',
            role='teacher'
        )

        self.report = Report.objects.create(
            title='Test Report',
            author=self.user,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )

        self.factory = RequestFactory()

    def test_log_report_access_view(self):
        """Test logging report view access"""
        log = ReportAccessControlService.log_report_access(
            self.report,
            self.user,
            access_type='view',
            access_method='direct'
        )

        self.assertEqual(log.report_id, self.report.id)
        self.assertEqual(log.accessed_by_id, self.user.id)
        self.assertEqual(log.access_type, 'view')
        self.assertEqual(log.access_method, 'direct')

    def test_log_report_access_download(self):
        """Test logging report download"""
        log = ReportAccessControlService.log_report_access(
            self.report,
            self.user,
            access_type='download',
            access_method='direct',
            duration_seconds=45
        )

        self.assertEqual(log.access_type, 'download')
        self.assertEqual(log.access_duration_seconds, 45)

    def test_log_access_with_request(self):
        """Test logging with HTTP request context"""
        request = self.factory.get('/api/reports/1/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        log = ReportAccessControlService.log_report_access(
            self.report,
            self.user,
            request=request,
            access_type='view'
        )

        self.assertEqual(str(log.ip_address), '192.168.1.100')
        self.assertIn('Mozilla', log.user_agent)

    def test_get_access_logs_filtered(self):
        """Test retrieving filtered access logs"""
        # Create multiple logs
        for i in range(3):
            ReportAccessAuditLog.objects.create(
                report=self.report,
                accessed_by=self.user,
                access_type='view',
                access_method='direct',
                ip_address='127.0.0.1'
            )

        logs = ReportAccessControlService.get_access_audit_logs(report=self.report)
        self.assertEqual(len(logs), 3)

    def test_access_statistics(self):
        """Test generating access statistics"""
        # Create various access logs
        ReportAccessAuditLog.objects.create(
            report=self.report,
            accessed_by=self.user,
            access_type='view',
            ip_address='127.0.0.1'
        )

        ReportAccessAuditLog.objects.create(
            report=self.report,
            accessed_by=self.user,
            access_type='download',
            ip_address='127.0.0.1'
        )

        stats = ReportAccessControlService.get_access_statistics(self.report)

        self.assertEqual(stats['total_accesses'], 2)
        self.assertEqual(stats['unique_users'], 1)
        self.assertEqual(stats['access_by_type']['view'], 1)
        self.assertEqual(stats['access_by_type']['download'], 1)


class ReportSharingTest(TestCase):
    """Test report sharing functionality"""

    def setUp(self):
        """Create test data"""
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='pass123',
            role='teacher'
        )

        self.other_teacher = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='pass123',
            role='teacher'
        )

        self.report = Report.objects.create(
            title='Test Report',
            author=self.teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )

    def test_share_report_with_user(self):
        """Test sharing report with specific user"""
        sharing = ReportAccessControlService.share_report(
            self.report,
            self.teacher,
            shared_with_user=self.other_teacher,
            permission='view'
        )

        self.assertEqual(sharing.report_id, self.report.id)
        self.assertEqual(sharing.shared_with_user_id, self.other_teacher.id)
        self.assertEqual(sharing.permission, 'view')
        self.assertTrue(sharing.is_active)

    def test_share_report_with_role(self):
        """Test sharing report with a role"""
        sharing = ReportAccessControlService.share_report(
            self.report,
            self.teacher,
            shared_role='tutor',
            permission='view_download'
        )

        self.assertEqual(sharing.shared_role, 'tutor')
        self.assertEqual(sharing.permission, 'view_download')

    def test_share_report_with_expiration(self):
        """Test sharing with expiration"""
        sharing = ReportAccessControlService.share_report(
            self.report,
            self.teacher,
            shared_with_user=self.other_teacher,
            permission='view',
            expires_in_days=7
        )

        self.assertIsNotNone(sharing.expires_at)

    def test_unshare_report(self):
        """Test removing sharing"""
        sharing = ReportAccessControlService.share_report(
            self.report,
            self.teacher,
            shared_with_user=self.other_teacher,
            permission='view'
        )

        self.assertTrue(sharing.is_active)

        ReportAccessControlService.unshare_report(sharing)
        sharing.refresh_from_db()

        self.assertFalse(sharing.is_active)

    def test_cannot_share_if_unauthorized(self):
        """Test non-owner cannot share report"""
        with self.assertRaises(ValueError):
            ReportAccessControlService.share_report(
                self.report,
                self.other_teacher,
                shared_with_user=User.objects.create_user(
                    username='user1',
                    email='user@test.com',
                    password='pass123'
                ),
                permission='view'
            )

    def test_sharing_validity_not_expired(self):
        """Test sharing is valid when not expired"""
        sharing = ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            shared_with_user=self.other_teacher,
            permission='view',
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.assertTrue(sharing.is_valid())

    def test_sharing_validity_expired(self):
        """Test sharing is invalid when expired"""
        sharing = ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            shared_with_user=self.other_teacher,
            permission='view',
            is_active=True,
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertFalse(sharing.is_valid())

    def test_sharing_validity_inactive(self):
        """Test sharing is invalid when inactive"""
        sharing = ReportSharing.objects.create(
            report=self.report,
            shared_by=self.teacher,
            shared_with_user=self.other_teacher,
            permission='view',
            is_active=False
        )

        self.assertFalse(sharing.is_valid())


class PermissionClassesTest(TestCase):
    """Test DRF permission classes"""

    def setUp(self):
        """Create test data"""
        self.factory = RequestFactory()

        self.student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='pass123',
            role='student'
        )

        StudentProfile.objects.create(
            user=self.student
        )

        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='pass123',
            role='teacher'
        )

        self.report = Report.objects.create(
            title='Test Report',
            author=self.teacher,
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        self.report.target_students.add(self.student)

    def test_can_access_report_student(self):
        """Test CanAccessReport permission for student"""
        request = self.factory.get('/api/reports/1/')
        request.user = self.student

        permission = CanAccessReport()
        has_perm = permission.has_object_permission(request, None, self.report)

        self.assertTrue(has_perm)

    def test_can_share_report_owner(self):
        """Test CanShareReport permission for owner"""
        request = self.factory.post('/api/reports/1/share/')
        request.user = self.teacher

        permission = CanShareReport()
        has_perm = permission.has_object_permission(request, None, self.report)

        self.assertTrue(has_perm)

    def test_can_share_report_non_owner(self):
        """Test CanShareReport permission for non-owner"""
        request = self.factory.post('/api/reports/1/share/')
        request.user = self.student

        permission = CanShareReport()
        has_perm = permission.has_object_permission(request, None, self.report)

        self.assertFalse(has_perm)

    def test_can_edit_report_owner(self):
        """Test CanEditReport permission for owner"""
        request = self.factory.put('/api/reports/1/')
        request.user = self.teacher

        permission = CanEditReport()
        has_perm = permission.has_object_permission(request, None, self.report)

        self.assertTrue(has_perm)

    def test_can_edit_report_non_owner(self):
        """Test CanEditReport permission for non-owner"""
        request = self.factory.put('/api/reports/1/')
        request.user = self.student

        permission = CanEditReport()
        has_perm = permission.has_object_permission(request, None, self.report)

        self.assertFalse(has_perm)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
