import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from .models import (
    Element,
    ElementFile,
    Lesson,
    LessonElement,
    KnowledgeGraph,
    GraphLesson,
    LessonDependency,
    ElementProgress,
    LessonProgress,
)
from accounts.factories import UserFactory
from materials.factories import SubjectFactory


class ElementFactory(DjangoModelFactory):
    class Meta:
        model = Element

    title = factory.Sequence(lambda n: f"Element {n}")
    description = "Test element"
    element_type = "theory"
    content = {"text": "Test content"}
    difficulty = 5
    estimated_time_minutes = 10
    max_score = 100
    tags = ["math", "algebra"]
    created_by = factory.SubFactory(UserFactory)
    is_public = False


class ElementFileFactory(DjangoModelFactory):
    class Meta:
        model = ElementFile

    element = factory.SubFactory(ElementFactory)
    file = factory.django.FileField(filename="test.pdf")
    original_filename = "test.pdf"
    file_size = 1024
    uploaded_by = factory.SubFactory(UserFactory)


class KGLessonFactory(DjangoModelFactory):
    class Meta:
        model = Lesson

    title = factory.Sequence(lambda n: f"Lesson {n}")
    description = "Test lesson"
    subject = factory.SubFactory(SubjectFactory)
    created_by = factory.SubFactory(UserFactory)
    is_public = False
    total_duration_minutes = 60
    total_max_score = 500


class LessonElementFactory(DjangoModelFactory):
    class Meta:
        model = LessonElement

    lesson = factory.SubFactory(KGLessonFactory)
    element = factory.SubFactory(ElementFactory)
    order = factory.Sequence(lambda n: n)
    is_optional = False
    custom_instructions = ""


class KnowledgeGraphFactory(DjangoModelFactory):
    class Meta:
        model = KnowledgeGraph

    student = factory.SubFactory(UserFactory)
    subject = factory.SubFactory(SubjectFactory)
    created_by = factory.SubFactory(UserFactory)
    is_active = True
    allow_skip = False


class GraphLessonFactory(DjangoModelFactory):
    class Meta:
        model = GraphLesson

    graph = factory.SubFactory(KnowledgeGraphFactory)
    lesson = factory.SubFactory(KGLessonFactory)
    position_x = 0.0
    position_y = 0.0
    is_unlocked = False
    node_color = "#4F46E5"
    node_size = 50


class LessonDependencyFactory(DjangoModelFactory):
    class Meta:
        model = LessonDependency

    graph = factory.SubFactory(KnowledgeGraphFactory)
    from_lesson = factory.SubFactory(GraphLessonFactory)
    to_lesson = factory.SubFactory(GraphLessonFactory)
    dependency_type = "required"
    min_score_percent = 70


class ElementProgressFactory(DjangoModelFactory):
    class Meta:
        model = ElementProgress

    student = factory.SubFactory(UserFactory)
    element = factory.SubFactory(ElementFactory)
    graph_lesson = factory.SubFactory(GraphLessonFactory)
    answer = {}
    score = None
    max_score = 100
    status = "not_started"
    time_spent_seconds = 0
    attempts = 0


class LessonProgressFactory(DjangoModelFactory):
    class Meta:
        model = LessonProgress

    student = factory.SubFactory(UserFactory)
    graph_lesson = factory.SubFactory(GraphLessonFactory)
    status = "not_started"
    completed_elements = 0
    total_elements = 5
    completion_percent = 0
    total_score = 0
    max_possible_score = 500
    total_time_spent_seconds = 0
