from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import forum_views
from . import admin_views

router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='room')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ChatParticipantViewSet, basename='participant')
router.register(r'threads', views.MessageThreadViewSet, basename='thread')
router.register(r'general', views.GeneralChatViewSet, basename='general-chat')
router.register(r'forum', forum_views.ForumChatViewSet, basename='forum-chat')

urlpatterns = [
    path('', include(router.urls)),
    path('notifications/', views.ChatRoomViewSet.as_view({'get': 'stats'}), name='chat-notifications'),

    # Admin endpoints (read-only)
    path('admin/rooms/', admin_views.AdminChatRoomListView.as_view(), name='admin-chat-rooms'),
    path('admin/rooms/<int:room_id>/', admin_views.AdminChatRoomDetailView.as_view(), name='admin-chat-room-detail'),
    path('admin/rooms/<int:room_id>/messages/', admin_views.AdminChatRoomMessagesView.as_view(), name='admin-chat-room-messages'),
    path('admin/stats/', admin_views.AdminChatStatsView.as_view(), name='admin-chat-stats'),
]
