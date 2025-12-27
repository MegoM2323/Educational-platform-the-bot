from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chat/general/$', consumers.GeneralChatConsumer.as_asgi()),  # General chat
    re_path(r'^ws/chat/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),  # Private room
    re_path(r'^ws/notifications/(?P<user_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),  # User notifications
    re_path(r'^ws/dashboard/(?P<user_id>\w+)/$', consumers.DashboardConsumer.as_asgi()),  # Dashboard updates
]
