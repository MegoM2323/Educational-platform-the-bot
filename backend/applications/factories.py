import factory
import uuid
from factory.django import DjangoModelFactory
from django.utils import timezone
from .models import Application
from accounts.factories import UserFactory


class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = Application

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    phone = "+1234567890"
    telegram_id = factory.Sequence(lambda n: str(n))
    applicant_type = Application.ApplicantType.STUDENT
    status = Application.Status.PENDING
    tracking_token = factory.LazyFunction(uuid.uuid4)
    grade = "10"
    subject = ""
    experience = ""
    motivation = "I want to learn"
    parent_first_name = ""
    parent_last_name = ""
    parent_email = ""
    parent_phone = ""
    parent_telegram_id = ""
    generated_username = factory.Sequence(lambda n: f"user_{n}")
    parent_username = ""
    notes = ""
