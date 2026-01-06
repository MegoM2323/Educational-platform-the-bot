"""
Materials factories for test data generation
"""
import factory
from factory.django import DjangoModelFactory


def _get_subject_model():
    from materials.models import Subject

    return Subject


def _get_subject_enrollment_model():
    from materials.models import SubjectEnrollment

    return SubjectEnrollment


class SubjectFactory(DjangoModelFactory):
    """Factory for creating Subject instances"""

    class Meta:
        model = _get_subject_model()

    name = factory.Sequence(lambda n: f"Subject {n}")
    description = "Test subject description"
    color = "#4F46E5"


class SubjectEnrollmentFactory(DjangoModelFactory):
    """Factory for creating SubjectEnrollment instances"""

    class Meta:
        model = _get_subject_enrollment_model()

    student = factory.LazyFunction(
        lambda: __import__(
            "accounts.factories", fromlist=["StudentFactory"]
        ).StudentFactory()
    )
    teacher = factory.LazyFunction(
        lambda: __import__(
            "accounts.factories", fromlist=["TeacherFactory"]
        ).TeacherFactory()
    )
    subject = factory.SubFactory(SubjectFactory)
    is_active = True
    assigned_by = None
