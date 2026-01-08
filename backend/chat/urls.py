from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter
from . import views


router = SimpleRouter()
router.register(r"", views.ChatRoomViewSet, basename="chat")

urlpatterns = [
    path("", include(router.urls)),
    # Message endpoints with path parameters
    path(
        "<int:room_id>/messages/<int:pk>/",
        views.MessageViewSet.as_view({"patch": "update", "delete": "destroy"}),
        name="message-detail",
    ),
    # Contacts endpoint
    path("contacts/", views.ChatContactsView.as_view(), name="chat-contacts"),
    # Custom action endpoints
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
]
