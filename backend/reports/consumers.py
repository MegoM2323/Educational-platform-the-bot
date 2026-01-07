import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from datetime import datetime

User = get_user_model()
logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для real-time обновлений дашборда.

    Подключение: /ws/dashboard/?token=<api_token>

    Отправляет события:
    - submission: {type: 'submission', assignment_id: X, student: Y, timestamp}
    - grade: {type: 'grade', submission_id: X, grade: Y, timestamp}
    - assignment: {type: 'assignment', assignment_id: X, title: Y}
    - assignment_closed: {type: 'assignment_closed', assignment_id: X}
    - metrics: {type: 'metrics', pending: X, ungraded: Y, active: Z, total: W}
    - ping: {type: 'ping'}
    """

    async def connect(self):
        """Подключение к WebSocket для дашборда"""
        self.user = self.scope["user"]

        # Проверяем аутентификацию
        if not self.user.is_authenticated:
            logger.warning(f"[DashboardConsumer] Connection rejected: user not authenticated")
            await self.close()
            return

        # Проверяем, что пользователь может видеть дашборд
        # (teacher, tutor или admin)
        if not self.check_dashboard_access():
            logger.warning(
                f"[DashboardConsumer] Connection rejected: user {self.user.id} has no dashboard access"
            )
            await self.close()
            return

        # Создаем группы для подписки
        self.user_dashboard_group = f"dashboard_user_{self.user.id}"
        self.metrics_group = "dashboard_metrics"

        # Присоединяемся к группам
        await self.channel_layer.group_add(self.user_dashboard_group, self.channel_name)
        await self.channel_layer.group_add(self.metrics_group, self.channel_name)

        logger.info(
            f"[DashboardConsumer] User {self.user.id} ({self.user.email}) connected to dashboard"
        )

        await self.accept()

        # Отправляем приветственное сообщение с начальными данными
        await self.send_welcome()

        # Запускаем heartbeat
        asyncio.create_task(self.heartbeat_loop())

        # Запускаем metrics broadcast
        if self.is_metrics_broadcaster():
            asyncio.create_task(self.metrics_broadcast_loop())

    async def disconnect(self, close_code):
        """Отключение от WebSocket"""
        logger.info(
            f"[DashboardConsumer] User {self.user.id} disconnected from dashboard (code: {close_code})"
        )

        # Отключаемся от групп
        await self.channel_layer.group_discard(self.user_dashboard_group, self.channel_name)
        await self.channel_layer.group_discard(self.metrics_group, self.channel_name)

    async def receive(self, text_data):
        """Обработка входящих сообщений от клиента"""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "pong":
                # Клиент ответил на heartbeat
                self.pong_received = True
            elif message_type == "ping":
                # Клиент отправляет ping (редко, но поддерживаем)
                await self.send(
                    text_data=json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()})
                )
        except json.JSONDecodeError:
            logger.error(f"[DashboardConsumer] Invalid JSON from user {self.user.id}")
        except Exception as e:
            logger.error(f"[DashboardConsumer] Error in receive: {e}")

    # Event handlers (called from group_send)

    async def submission_event(self, event):
        """Отправка события о новой сдаче"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "submission",
                    "assignment_id": event["assignment_id"],
                    "student": event["student"],
                    "submission_id": event["submission_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def grade_event(self, event):
        """Отправка события о выставленной оценке"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "grade",
                    "submission_id": event["submission_id"],
                    "grade": event["grade"],
                    "student": event["student"],
                    "assignment_id": event["assignment_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def assignment_event(self, event):
        """Отправка события о созданном задании"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "assignment",
                    "assignment_id": event["assignment_id"],
                    "title": event["title"],
                    "description": event.get("description", ""),
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def assignment_closed_event(self, event):
        """Отправка события о закрытом задании"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "assignment_closed",
                    "assignment_id": event["assignment_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def metrics_event(self, event):
        """Отправка метрик дашборда"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "metrics",
                    "pending_submissions": event["pending_submissions"],
                    "ungraded_submissions": event["ungraded_submissions"],
                    "active_students": event["active_students"],
                    "total_assignments": event["total_assignments"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def ping(self, event):
        """Heartbeat ping"""
        self.pong_received = False
        await self.send(text_data=json.dumps({"type": "ping", "timestamp": event["timestamp"]}))

    # Helper methods

    def check_dashboard_access(self) -> bool:
        """Проверяет, есть ли у пользователя доступ к дашборду"""
        if not self.user.is_authenticated:
            return False

        # Учителя, тьюторы и админы имеют доступ
        return self.user.role in ["teacher", "tutor", "admin"]

    def is_metrics_broadcaster(self) -> bool:
        """Проверяет, должен ли этот consumer отправлять метрики"""
        # Только администраторы отправляют метрики всем
        # Но можно изменить на "первый подключившийся teacher"
        return self.user.role == "admin"

    async def send_welcome(self):
        """Отправляет приветственное сообщение с начальными данными"""
        metrics = await self.get_initial_metrics()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "welcome",
                    "user_id": self.user.id,
                    "user_email": self.user.email,
                    "user_role": self.user.role,
                    "metrics": metrics,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

    @database_sync_to_async
    def get_initial_metrics(self) -> dict:
        """Получает начальные метрики для пользователя"""
        from assignments.models import Assignment, AssignmentSubmission

        try:
            # Получаем задания, назначенные этому пользователю или его студентам
            if self.user.role == "teacher":
                # Учитель видит свои задания
                assignments = Assignment.objects.filter(author=self.user)
            elif self.user.role == "tutor":
                # Тьютор видит задания своих студентов
                try:
                    students = self.user.tutor_profile.students.all()
                    assignments = Assignment.objects.filter(assigned_to__in=students)
                except AttributeError:
                    logger.warning(
                        f"[DashboardConsumer] TutorProfile not found for tutor user {self.user.id}",
                        exc_info=True,
                    )
                    assignments = Assignment.objects.none()
            else:
                # Админ видит все
                assignments = Assignment.objects.all()

            # Подсчитываем метрики
            total_assignments = assignments.count()

            # Подсчитываем незавершенные сдачи
            pending_submissions = AssignmentSubmission.objects.filter(
                assignment__in=assignments, submitted_at__isnull=True
            ).count()

            # Подсчитываем необработанные оценки
            ungraded_submissions = AssignmentSubmission.objects.filter(
                assignment__in=assignments, submitted_at__isnull=False, grade__isnull=True
            ).count()

            # Подсчитываем активных студентов
            active_students = (
                AssignmentSubmission.objects.filter(assignment__in=assignments)
                .values("student_id")
                .distinct()
                .count()
            )

            return {
                "pending_submissions": pending_submissions,
                "ungraded_submissions": ungraded_submissions,
                "active_students": active_students,
                "total_assignments": total_assignments,
            }
        except Exception as e:
            logger.error(f"[DashboardConsumer] Error getting initial metrics: {e}")
            return {
                "pending_submissions": 0,
                "ungraded_submissions": 0,
                "active_students": 0,
                "total_assignments": 0,
            }

    async def heartbeat_loop(self):
        """Отправляет heartbeat каждые 30 секунд"""
        missed_pongs = 0
        self.pong_received = True

        try:
            while True:
                await asyncio.sleep(30)

                # Проверяем, получили ли pong на последний ping
                if not self.pong_received:
                    missed_pongs += 1
                    logger.warning(
                        f"[DashboardConsumer] User {self.user.id} missed pong #{missed_pongs}"
                    )

                    if missed_pongs >= 2:
                        logger.warning(
                            f"[DashboardConsumer] Closing connection for user {self.user.id} (missed 2 pongs)"
                        )
                        await self.close()
                        return
                else:
                    missed_pongs = 0

                # Отправляем ping
                await self.channel_layer.group_send(
                    self.user_dashboard_group,
                    {"type": "ping", "timestamp": datetime.now().isoformat()},
                )
        except Exception as e:
            logger.error(f"[DashboardConsumer] Error in heartbeat loop: {e}")

    async def metrics_broadcast_loop(self):
        """Отправляет метрики каждые 10 секунд (для админов)"""
        try:
            while True:
                await asyncio.sleep(10)

                metrics = await self.get_initial_metrics()

                await self.channel_layer.group_send(
                    self.metrics_group,
                    {
                        "type": "metrics_event",
                        "pending_submissions": metrics["pending_submissions"],
                        "ungraded_submissions": metrics["ungraded_submissions"],
                        "active_students": metrics["active_students"],
                        "total_assignments": metrics["total_assignments"],
                        "timestamp": datetime.now().isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"[DashboardConsumer] Error in metrics broadcast loop: {e}")
