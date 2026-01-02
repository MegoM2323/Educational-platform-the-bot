"""
Materials factories for test data generation
"""
import factory
from factory.django import DjangoModelFactory
from materials.models import Subject


class SubjectFactory(DjangoModelFactory):
    """Factory for creating Subject instances"""

    class Meta:
        model = Subject

    name = factory.Sequence(lambda n: f"Subject {n}")
    description = "Test subject description"
    color = "#4F46E5"
