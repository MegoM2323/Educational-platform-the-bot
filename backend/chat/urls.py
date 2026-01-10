from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter
from . import views


router = SimpleRouter()
router.register(r"", views.ChatRoomViewSet, basename="chat")

urlpatterns = [
    # Static endpoints (must come before router to avoid id parameter capture)
    path("notifications/", views.ChatNotificationsView.as_view(), name="chat-notifications"),
    path("contacts/", views.ChatContactsView.as_view(), name="chat-contacts"),

    # Message endpoints with path parameters
    path(
        "<int:room_id>/messages/<int:pk>/",
        views.MessageViewSet.as_view({"patch": "update", "delete": "destroy"}),
        name="message-detail",
    ),

    # Custom action endpoints (must come before router to avoid id parameter capture)
    path(
        "<int:pk>/send_message/",
        views.ChatRoomViewSet.as_view({"post": "send_message"}),
        name="send-message",
    ),
    path(
        "<int:pk>/messages/",
        views.ChatRoomViewSet.as_view({"get": "messages"}),
        name="chat-messages",
    ),
    path(
        "<int:pk>/mark_as_read/",
        views.ChatRoomViewSet.as_view({"post": "mark_as_read"}),
        name="mark-as-read",
    ),

    # Router with empty pattern (must come last to avoid matching before custom routes)
    path("", include(router.urls)),
]
