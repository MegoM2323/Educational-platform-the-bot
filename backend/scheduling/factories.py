import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from scheduling.models import Lesson, LessonHistory

User = get_user_model()


class LessonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lesson

    teacher = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True, role="teacher").first()
        or User.objects.create_user(
            username=f"teacher_{id(object())}",
            email=f"teacher_{id(object())}@test.com",
            role="teacher",
        )
    )
    student = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True, role="student").first()
        or User.objects.create_user(
            username=f"student_{id(object())}",
            email=f"student_{id(object())}@test.com",
            role="student",
        )
    )
    subject = factory.LazyFunction(
        lambda: __import__(
            "materials.models", fromlist=["Subject"]
        ).Subject.objects.first()
    )
    date = factory.LazyFunction(lambda: (timezone.now() + timedelta(days=7)).date())
    start_time = factory.LazyFunction(lambda: timezone.now().time())
    end_time = factory.LazyFunction(
        lambda: (timezone.now() + timedelta(hours=1)).time()
    )
    description = "Test lesson"
    telemost_link = ""
    status = Lesson.Status.PENDING


class LessonHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LessonHistory

    lesson = factory.SubFactory(LessonFactory)
    action = "created"
    performed_by = factory.LazyFunction(
        lambda: User.objects.filter(is_active=True).first()
        or User.objects.create_user(
            username=f"user_{id(object())}", email=f"user_{id(object())}@test.com"
        )
    )
    old_values = None
    new_values = None
