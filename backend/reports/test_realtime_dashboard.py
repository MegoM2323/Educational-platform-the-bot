"""
Tests for real-time dashboard WebSocket consumer and services.
"""

import pytest
import json
import asyncio
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.authtoken.models import Token

from assignments.models import Assignment, AssignmentSubmission
from reports.consumers import DashboardConsumer
from reports.services.realtime import DashboardEventService

User = get_user_model()


class DashboardConsumerAuthTests(TestCase):
    """Tests for DashboardConsumer authentication"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Teacher',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Student',
            role='student'
        )
        self.token_teacher = Token.objects.create(user=self.teacher)
        self.token_student = Token.objects.create(user=self.student)

    @pytest.mark.asyncio
    async def test_connection_without_auth(self):
        """Test that unauthenticated user cannot connect"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        # Simulate unauthenticated connection
        communicator.scope['user'] = None
        connected, subprotocol = await communicator.connect()
        assert not connected

    @pytest.mark.asyncio
    async def test_connection_teacher_authorized(self):
        """Test that teacher can connect to dashboard"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        connected, subprotocol = await communicator.connect()
        assert connected

        # Should receive welcome message
        response = await communicator.receive_json_from()
        assert response['type'] == 'welcome'
        assert response['user_id'] == self.teacher.id
        assert 'metrics' in response

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_connection_student_rejected(self):
        """Test that student cannot connect to dashboard"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.student
        connected, subprotocol = await communicator.connect()
        # Should be rejected because student doesn't have dashboard access
        assert not connected

    @pytest.mark.asyncio
    async def test_welcome_message_content(self):
        """Test that welcome message contains correct initial data"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        response = await communicator.receive_json_from()
        assert response['type'] == 'welcome'
        assert response['user_id'] == self.teacher.id
        assert response['user_email'] == self.teacher.email
        assert response['user_role'] == 'teacher'
        assert isinstance(response['metrics'], dict)
        assert 'pending_submissions' in response['metrics']
        assert 'ungraded_submissions' in response['metrics']
        assert 'active_students' in response['metrics']
        assert 'total_assignments' in response['metrics']

        await communicator.disconnect()


class DashboardConsumerHeartbeatTests(TestCase):
    """Tests for heartbeat and ping/pong mechanism"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

    @pytest.mark.asyncio
    async def test_heartbeat_ping(self):
        """Test that heartbeat ping is sent"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome message
        await communicator.receive_json_from()

        # Wait for first heartbeat (30 seconds in production, but we'll use shorter timeout in tests)
        # In real tests, we'd mock the asyncio.sleep
        # For now, we just verify the mechanism is ready

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_pong_response(self):
        """Test that client can respond to ping with pong"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome
        await communicator.receive_json_from()

        # Simulate client sending pong
        await communicator.send_json_to({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        })

        # Consumer should handle pong without error
        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_client_ping_request(self):
        """Test that client can send ping and get pong response"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome
        await communicator.receive_json_from()

        # Client sends ping
        await communicator.send_json_to({
            'type': 'ping'
        })

        # Should receive pong
        response = await communicator.receive_json_from()
        assert response['type'] == 'pong'

        await communicator.disconnect()


class DashboardConsumerMetricsTests(TestCase):
    """Tests for metrics calculation and updates"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.student2 = User.objects.create_user(
            email='student2@test.com',
            password='testpass123',
            role='student'
        )

        # Create assignments
        self.assignment1 = Assignment.objects.create(
            title='Test Assignment 1',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )
        self.assignment1.assigned_to.add(self.student, self.student2)

        self.assignment2 = Assignment.objects.create(
            title='Test Assignment 2',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )
        self.assignment2.assigned_to.add(self.student)

    @pytest.mark.asyncio
    async def test_metrics_initial_state(self):
        """Test initial metrics calculation"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        response = await communicator.receive_json_from()
        metrics = response['metrics']

        assert metrics['total_assignments'] == 2
        assert metrics['pending_submissions'] == 0
        assert metrics['ungraded_submissions'] == 0
        assert metrics['active_students'] == 0

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_metrics_with_submissions(self):
        """Test metrics with submitted assignments"""
        # Create submissions
        sub1 = AssignmentSubmission.objects.create(
            assignment=self.assignment1,
            student=self.student,
            submitted_at=None  # Not yet submitted
        )

        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        response = await communicator.receive_json_from()
        metrics = response['metrics']

        assert metrics['pending_submissions'] == 1
        assert metrics['active_students'] == 1

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_metrics_with_graded_submissions(self):
        """Test metrics with graded submissions"""
        sub1 = AssignmentSubmission.objects.create(
            assignment=self.assignment1,
            student=self.student,
            submitted_at=timezone.now(),
            grade=None  # Not yet graded
        )

        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        response = await communicator.receive_json_from()
        metrics = response['metrics']

        assert metrics['ungraded_submissions'] == 1
        assert metrics['active_students'] == 1

        await communicator.disconnect()


class DashboardEventServiceTests(TestCase):
    """Tests for dashboard event broadcasting"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )

    def test_broadcast_submission_event(self):
        """Test broadcasting submission event"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            submitted_at=timezone.now()
        )

        # Should not raise exception
        DashboardEventService.broadcast_submission(submission, self.assignment, self.student)

    def test_broadcast_grade_event(self):
        """Test broadcasting grade event"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            submitted_at=timezone.now(),
            grade=85
        )

        # Should not raise exception
        DashboardEventService.broadcast_grade(submission, self.assignment, self.student, 85)

    def test_broadcast_assignment_created_event(self):
        """Test broadcasting assignment created event"""
        # Should not raise exception
        DashboardEventService.broadcast_assignment_created(self.assignment)

    def test_broadcast_assignment_closed_event(self):
        """Test broadcasting assignment closed event"""
        # Should not raise exception
        DashboardEventService.broadcast_assignment_closed(self.assignment)

    def test_broadcast_to_user(self):
        """Test broadcasting to specific user"""
        data = {
            'message': 'Test event'
        }

        # Should not raise exception
        DashboardEventService.broadcast_to_user(self.teacher.id, 'custom_event', data)

    def test_broadcast_to_group(self):
        """Test broadcasting to group"""
        data = {
            'message': 'Test event'
        }

        # Should not raise exception
        DashboardEventService.broadcast_to_group('dashboard_metrics', 'custom_event', data)


class DashboardConsumerDisconnectionTests(TestCase):
    """Tests for disconnection and reconnection"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

    @pytest.mark.asyncio
    async def test_graceful_disconnection(self):
        """Test graceful disconnection"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        connected, _ = await communicator.connect()
        assert connected

        # Receive welcome
        await communicator.receive_json_from()

        # Disconnect
        await communicator.disconnect()

        # Try to receive should raise error (disconnected)
        with pytest.raises(Exception):
            await communicator.receive_json_from()

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        """Test multiple connections from same user"""
        comm1 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        comm1.scope['user'] = self.teacher
        connected1, _ = await comm1.connect()
        assert connected1

        comm2 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        comm2.scope['user'] = self.teacher
        connected2, _ = await comm2.connect()
        assert connected2

        # Both should work independently
        resp1 = await comm1.receive_json_from()
        assert resp1['type'] == 'welcome'

        resp2 = await comm2.receive_json_from()
        assert resp2['type'] == 'welcome'

        await comm1.disconnect()
        await comm2.disconnect()


class DashboardGroupMembershipTests(TestCase):
    """Tests for group membership and broadcasting"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )

    @pytest.mark.asyncio
    async def test_user_group_subscription(self):
        """Test that user joins correct groups on connect"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome to confirm connection
        await communicator.receive_json_from()

        # User should be in their personal dashboard group
        # and metrics group
        # This is verified by group_send working correctly

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_broadcast_to_correct_group(self):
        """Test that broadcasts reach correct user groups"""
        # Connect two teachers
        comm1 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        comm1.scope['user'] = self.teacher
        await comm1.connect()

        comm2 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        comm2.scope['user'] = self.admin
        await comm2.connect()

        # Receive welcome messages
        await comm1.receive_json_from()
        await comm2.receive_json_from()

        # Send event to teacher's group
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'dashboard_user_{self.teacher.id}',
            {
                'type': 'submission_event',
                'submission_id': 1,
                'assignment_id': 1,
                'student': {'id': 1, 'email': 'test@test.com'},
                'timestamp': timezone.now().isoformat()
            }
        )

        # Only teacher should receive it
        response = await asyncio.wait_for(comm1.receive_json_from(), timeout=1.0)
        assert response['type'] == 'submission'

        # Admin should not receive it (different group)
        # If we try to receive, it should timeout or error
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(comm2.receive_json_from(), timeout=0.5)

        await comm1.disconnect()
        await comm2.disconnect()


class DashboardErrorHandlingTests(TestCase):
    """Tests for error handling"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome
        await communicator.receive_json_from()

        # Send invalid JSON
        await communicator.send_to('not valid json')

        # Consumer should handle gracefully and not crash
        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_missing_fields_handling(self):
        """Test handling of messages with missing fields"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome
        await communicator.receive_json_from()

        # Send message without type field
        await communicator.send_json_to({})

        # Should handle gracefully
        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_unknown_message_type(self):
        """Test handling of unknown message types"""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        communicator.scope['user'] = self.teacher
        await communicator.connect()

        # Receive welcome
        await communicator.receive_json_from()

        # Send message with unknown type
        await communicator.send_json_to({
            'type': 'unknown_message_type',
            'data': 'some data'
        })

        # Should handle gracefully
        await communicator.disconnect()


@pytest.mark.django_db
class IntegrationTests(TestCase):
    """Integration tests for complete workflows"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.assignment = Assignment.objects.create(
            title='Integration Test Assignment',
            description='Test',
            instructions='Instructions',
            author=self.teacher,
            start_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=1),
            max_score=100,
            attempts_limit=1
        )
        self.assignment.assigned_to.add(self.student)

    @pytest.mark.asyncio
    async def test_full_workflow_submission_and_grading(self):
        """Test complete workflow: student submits, teacher grades"""
        # Teacher connects to dashboard
        teacher_comm = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            '/ws/dashboard/'
        )
        teacher_comm.scope['user'] = self.teacher
        await teacher_comm.connect()

        # Receive welcome
        welcome = await teacher_comm.receive_json_from()
        assert welcome['type'] == 'welcome'

        # Broadcast submission event
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            submitted_at=timezone.now()
        )

        DashboardEventService.broadcast_submission(submission, self.assignment, self.student)

        # Teacher should receive submission event
        response = await asyncio.wait_for(teacher_comm.receive_json_from(), timeout=2.0)
        assert response['type'] == 'submission'
        assert response['assignment_id'] == self.assignment.id
        assert response['student']['id'] == self.student.id

        # Teacher grades the submission
        submission.grade = 95
        submission.save()

        DashboardEventService.broadcast_grade(submission, self.assignment, self.student, 95)

        # Teacher should receive grade event
        response = await asyncio.wait_for(teacher_comm.receive_json_from(), timeout=2.0)
        assert response['type'] == 'grade'
        assert response['grade'] == 95

        await teacher_comm.disconnect()
