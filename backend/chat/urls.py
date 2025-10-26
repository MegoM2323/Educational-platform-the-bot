from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='room')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ChatParticipantViewSet, basename='participant')
router.register(r'threads', views.MessageThreadViewSet, basename='thread')
router.register(r'general', views.GeneralChatViewSet, basename='general-chat')

urlpatterns = [
    path('', include(router.urls)),
    path('notifications/', views.ChatRoomViewSet.as_view({'get': 'stats'}), name='chat-notifications'),
]
