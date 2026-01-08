from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter
from . import views


router = SimpleRouter(trailing_slash=False)
router.register(r"", views.ChatRoomViewSet, basename="chat")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<int:room_id>/messages/<int:pk>/",
        views.MessageViewSet.as_view({"patch": "update", "delete": "destroy"}),
        name="message-detail",
    ),
    path("contacts/", views.ChatContactsView.as_view(), name="chat-contacts"),
]
