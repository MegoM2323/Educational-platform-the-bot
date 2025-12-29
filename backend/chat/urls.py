from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from . import views
from . import forum_views
from . import admin_views


class OptionalSlashRouter(DefaultRouter):
    """
    Custom router that accepts URLs both with and without trailing slashes.
    This fixes 404 errors when frontend calls endpoints without trailing slash.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep trailing_slash=True for default behavior
        self.trailing_slash = '/?'  # Make trailing slash optional


router = OptionalSlashRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='room')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ChatParticipantViewSet, basename='participant')
router.register(r'threads', views.MessageThreadViewSet, basename='thread')
router.register(r'general', views.GeneralChatViewSet, basename='general-chat')
router.register(r'forum', forum_views.ForumChatViewSet, basename='forum-chat')

urlpatterns = [
    path('', include(router.urls)),

    # Notifications - support both with and without trailing slash
    re_path(r'^notifications/?$', views.ChatRoomViewSet.as_view({'get': 'stats'}), name='chat-notifications'),

    # Forum endpoints - support both with and without trailing slash
    re_path(r'^available-contacts/?$', forum_views.AvailableContactsView.as_view(), name='available-contacts'),
    re_path(r'^initiate-chat/?$', forum_views.InitiateChatView.as_view(), name='initiate-chat'),

    # Admin endpoints (read-only) - support both with and without trailing slash
    re_path(r'^admin/rooms/?$', admin_views.AdminChatRoomListView.as_view(), name='admin-chat-rooms'),
    re_path(r'^admin/rooms/(?P<room_id>\d+)/?$', admin_views.AdminChatRoomDetailView.as_view(), name='admin-chat-room-detail'),
    re_path(r'^admin/rooms/(?P<room_id>\d+)/messages/?$', admin_views.AdminChatRoomMessagesView.as_view(), name='admin-chat-room-messages'),
    re_path(r'^admin/stats/?$', admin_views.AdminChatStatsView.as_view(), name='admin-chat-stats'),
]
