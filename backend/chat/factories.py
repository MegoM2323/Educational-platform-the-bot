import factory
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, Message, MessageThread, ChatParticipant, MessageRead

User = get_user_model()


class ChatRoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatRoom

    name = factory.Sequence(lambda n: f"Chat Room {n}")
    description = "Test room"
    type = ChatRoom.Type.DIRECT
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
    is_active = True
    auto_delete_days = 7


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    room = factory.SubFactory(ChatRoomFactory)
    sender = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
    content = "Test message"
    message_type = Message.Type.TEXT
    is_deleted = False
    deleted_by = None


class MessageThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageThread

    room = factory.SubFactory(ChatRoomFactory)
    title = factory.Sequence(lambda n: f"Thread {n}")
    created_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
    is_pinned = False
    is_locked = False


class ChatParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatParticipant

    room = factory.SubFactory(ChatRoomFactory)
    user = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
    is_muted = False
    is_admin = False


class MessageReadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageRead

    message = factory.SubFactory(MessageFactory)
    user = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).last()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
