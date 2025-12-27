"""
Real-time dashboard events service.

Handles broadcasting of dashboard events to WebSocket consumers.
"""

import logging
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class DashboardEventService:
    """
    Service для отправки real-time событий на дашборд.
    """

    @staticmethod
    def broadcast_submission(submission, assignment, student):
        """
        Отправляет событие о новой сдаче.

        Args:
            submission: AssignmentSubmission объект
            assignment: Assignment объект
            student: User объект (студент)
        """
        try:
            channel_layer = get_channel_layer()

            # Отправляем событие учителю (автору задания)
            teacher_group = f'dashboard_user_{assignment.author.id}'

            async_to_sync(channel_layer.group_send)(
                teacher_group,
                {
                    'type': 'submission_event',
                    'submission_id': submission.id,
                    'assignment_id': assignment.id,
                    'student': {
                        'id': student.id,
                        'email': student.email,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                    },
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Отправляем также на общую группу метрик
            async_to_sync(channel_layer.group_send)(
                'dashboard_metrics',
                {
                    'type': 'submission_event',
                    'submission_id': submission.id,
                    'assignment_id': assignment.id,
                    'student': {
                        'id': student.id,
                        'email': student.email,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                    },
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast submission event: assignment={assignment.id}, student={student.id}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting submission event: {e}')

    @staticmethod
    def broadcast_grade(submission, assignment, student, grade):
        """
        Отправляет событие о выставленной оценке.

        Args:
            submission: AssignmentSubmission объект
            assignment: Assignment объект
            student: User объект (студент)
            grade: оценка (число или строка)
        """
        try:
            channel_layer = get_channel_layer()

            # Отправляем событие учителю (автору задания)
            teacher_group = f'dashboard_user_{assignment.author.id}'

            async_to_sync(channel_layer.group_send)(
                teacher_group,
                {
                    'type': 'grade_event',
                    'submission_id': submission.id,
                    'assignment_id': assignment.id,
                    'student': {
                        'id': student.id,
                        'email': student.email,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                    },
                    'grade': grade,
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast grade event: assignment={assignment.id}, student={student.id}, grade={grade}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting grade event: {e}')

    @staticmethod
    def broadcast_assignment_created(assignment):
        """
        Отправляет событие о созданном задании.

        Args:
            assignment: Assignment объект
        """
        try:
            channel_layer = get_channel_layer()

            # Отправляем событие всем студентам, назначенным на это задание
            assigned_students = assignment.assigned_to.all()

            for student in assigned_students:
                student_group = f'dashboard_user_{student.id}'
                async_to_sync(channel_layer.group_send)(
                    student_group,
                    {
                        'type': 'assignment_event',
                        'assignment_id': assignment.id,
                        'title': assignment.title,
                        'description': assignment.description[:200] if assignment.description else '',
                        'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                        'timestamp': datetime.now().isoformat()
                    }
                )

            # Отправляем также другим учителям (если система это требует)
            async_to_sync(channel_layer.group_send)(
                'dashboard_metrics',
                {
                    'type': 'assignment_event',
                    'assignment_id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description[:200] if assignment.description else '',
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast assignment created event: assignment={assignment.id}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting assignment created event: {e}')

    @staticmethod
    def broadcast_assignment_closed(assignment):
        """
        Отправляет событие о закрытом задании.

        Args:
            assignment: Assignment объект
        """
        try:
            channel_layer = get_channel_layer()

            # Отправляем событие всем студентам, назначенным на это задание
            assigned_students = assignment.assigned_to.all()

            for student in assigned_students:
                student_group = f'dashboard_user_{student.id}'
                async_to_sync(channel_layer.group_send)(
                    student_group,
                    {
                        'type': 'assignment_closed_event',
                        'assignment_id': assignment.id,
                        'timestamp': datetime.now().isoformat()
                    }
                )

            # Отправляем учителю
            teacher_group = f'dashboard_user_{assignment.author.id}'
            async_to_sync(channel_layer.group_send)(
                teacher_group,
                {
                    'type': 'assignment_closed_event',
                    'assignment_id': assignment.id,
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast assignment closed event: assignment={assignment.id}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting assignment closed event: {e}')

    @staticmethod
    def broadcast_to_user(user_id, event_type, data):
        """
        Отправляет произвольное событие конкретному пользователю.

        Args:
            user_id: ID пользователя
            event_type: тип события
            data: данные события
        """
        try:
            channel_layer = get_channel_layer()
            user_group = f'dashboard_user_{user_id}'

            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    'type': event_type,
                    **data,
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast to user {user_id}: event_type={event_type}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting to user {user_id}: {e}')

    @staticmethod
    def broadcast_to_group(group_name, event_type, data):
        """
        Отправляет произвольное событие группе пользователей.

        Args:
            group_name: имя группы
            event_type: тип события
            data: данные события
        """
        try:
            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': event_type,
                    **data,
                    'timestamp': datetime.now().isoformat()
                }
            )

            logger.info(f'[DashboardEventService] Broadcast to group {group_name}: event_type={event_type}')
        except Exception as e:
            logger.error(f'[DashboardEventService] Error broadcasting to group {group_name}: {e}')
