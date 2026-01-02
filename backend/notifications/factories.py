import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from .models import (
    Notification,
    NotificationTemplate,
    NotificationSettings,
    NotificationQueue,
    Broadcast,
    BroadcastRecipient,
    NotificationClick,
    PushDeliveryLog,
    NotificationUnsubscribe,
)
from accounts.factories import UserFactory


class NotificationFactory(DjangoModelFactory):
    class Meta:
        model = Notification

    title = factory.Sequence(lambda n: f"Notification {n}")
    message = "Test notification message"
    recipient = factory.SubFactory(UserFactory)
    type = Notification.Type.SYSTEM
    priority = Notification.Priority.NORMAL
    scope = Notification.Scope.USER
    is_read = False
    is_sent = False
    related_object_type = "assignment"
    related_object_id = 1
    data = {}
    is_archived = False


class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = NotificationTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    description = "Test template"
    type = Notification.Type.SYSTEM
    title_template = "Test Title"
    message_template = "Test Message"
    is_active = True


class NotificationSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NotificationSettings

    user = factory.SubFactory(UserFactory)
    assignment_notifications = True
    material_notifications = True
    message_notifications = True
    report_notifications = True
    payment_notifications = True
    invoice_notifications = True
    system_notifications = True
    email_notifications = True
    push_notifications = True
    sms_notifications = False
    in_app_notifications = True
    quiet_hours_enabled = False
    timezone = "UTC"


class NotificationQueueFactory(DjangoModelFactory):
    class Meta:
        model = NotificationQueue

    notification = factory.SubFactory(NotificationFactory)
    status = NotificationQueue.Status.PENDING
    channel = "email"
    scheduled_at = None
    attempts = 0
    max_attempts = 3
    error_message = ""


class BroadcastFactory(DjangoModelFactory):
    class Meta:
        model = Broadcast

    created_by = factory.SubFactory(UserFactory)
    target_group = Broadcast.TargetGroup.ALL_STUDENTS
    target_filter = {}
    message = "Broadcast message"
    recipient_count = 0
    sent_count = 0
    failed_count = 0
    status = Broadcast.Status.DRAFT


class BroadcastRecipientFactory(DjangoModelFactory):
    class Meta:
        model = BroadcastRecipient

    broadcast = factory.SubFactory(BroadcastFactory)
    recipient = factory.SubFactory(UserFactory)
    telegram_sent = False


class NotificationClickFactory(DjangoModelFactory):
    class Meta:
        model = NotificationClick

    notification = factory.SubFactory(NotificationFactory)
    user = factory.SubFactory(UserFactory)
    action_type = "link_click"
    action_url = "https://example.com"
    action_data = {}
    user_agent = ""
    ip_address = None


class PushDeliveryLogFactory(DjangoModelFactory):
    class Meta:
        model = PushDeliveryLog

    notification = factory.SubFactory(NotificationFactory)
    user = factory.SubFactory(UserFactory)
    device_token = None
    status = PushDeliveryLog.DeliveryStatus.PENDING
    attempt_number = 1
    max_attempts = 3
    success = False
    error_message = ""
    error_code = ""
    fcm_message_id = ""
    device_type = "android"
    payload_size = 1024
    delivered_at = None
    retry_at = None


class NotificationUnsubscribeFactory(DjangoModelFactory):
    class Meta:
        model = NotificationUnsubscribe

    user = factory.SubFactory(UserFactory)
    notification_types = ["assignments", "materials"]
    channel = NotificationUnsubscribe.Channel.EMAIL
    ip_address = None
    user_agent = ""
    token_used = False
    reason = ""
    resubscribed_at = None
