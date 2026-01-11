from django.urls import path
from chat.views import (
    ChatListCreateView,
    ChatDetailDeleteView,
    MessageListCreateView,
    MessageDetailView,
    MarkAsReadView,
    ContactsListView,
)

app_name = "chat"

urlpatterns = [
    # Contacts endpoints (must be first to avoid <int:pk> matching "contacts")
    path("contacts/", ContactsListView.as_view(), name="contacts-list"),
    # Chat endpoints
    path("", ChatListCreateView.as_view(), name="chat-list-create"),
    path("<int:pk>/", ChatDetailDeleteView.as_view(), name="chat-detail-delete"),
    # Message endpoints
    path("<int:room_id>/messages/", MessageListCreateView.as_view(), name="message-list-create"),
    path("<int:room_id>/messages/<int:message_id>/", MessageDetailView.as_view(), name="message-detail"),
    path("<int:room_id>/send_message/", MessageListCreateView.as_view(), name="send-message"),
    path("<int:room_id>/mark_as_read/", MarkAsReadView.as_view(), name="mark-as-read"),
]
