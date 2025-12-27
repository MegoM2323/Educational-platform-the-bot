#!/usr/bin/env python
"""
Create test data for quick_question E2E tests (T104)

This script sets up:
1. Test student account (student@test.com)
2. Test subject and teacher
3. Test lesson with mixed elements:
   - quick_question (for retry testing)
   - theory (to verify unchanged behavior)
   - text_problem (to verify unchanged behavior)
4. Knowledge graph with student enrolled

Usage:
    python scripts/testing/create_quick_question_test_data.py

Environment:
    ENVIRONMENT=development (uses local SQLite)
"""

import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

# Configure Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ.setdefault('ENVIRONMENT', 'development')

django.setup()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, TeacherProfile
from materials.models import Subject
from knowledge_graph.models import Element, Lesson, LessonElement, KnowledgeGraph, GraphLesson

User = get_user_model()


def create_test_student():
    """Create or get test student account"""
    try:
        student = User.objects.get(email='student@test.com')
        print(f"✓ Student already exists: {student.email}")
    except User.DoesNotExist:
        student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='TestPass123!',
            role='student',
            first_name='Test',
            last_name='Student'
        )
        StudentProfile.objects.create(user=student)
        print(f"✓ Created test student: {student.email}")

    return student


def create_test_teacher():
    """Create or get test teacher account"""
    try:
        teacher = User.objects.get(email='teacher@test.com')
        print(f"✓ Teacher already exists: {teacher.email}")
    except User.DoesNotExist:
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher',
            first_name='Test',
            last_name='Teacher'
        )
        TeacherProfile.objects.create(user=teacher)
        print(f"✓ Created test teacher: {teacher.email}")

    return teacher


def create_test_subject(teacher):
    """Create or get test subject"""
    subject, created = Subject.objects.get_or_create(
        name='Тестовая Математика',
        defaults={'description': 'Предмет для E2E тестирования'}
    )

    if created:
        print(f"✓ Created test subject: {subject.name}")
    else:
        print(f"✓ Subject already exists: {subject.name}")

    return subject


def create_quick_question_element(teacher):
    """Create quick_question element for retry testing"""
    try:
        element = Element.objects.get(title='Быстрый вопрос')
        print(f"✓ Quick question element already exists")
    except Element.DoesNotExist:
        element = Element.objects.create(
            title='Быстрый вопрос',
            description='Выберите правильный ответ на простой вопрос',
            element_type='quick_question',
            content={
                'question': 'Сколько будет 2 + 2?',
                'choices': ['3', '4', '5'],
                'correct_answer': 1  # Index 1 = '4'
            },
            difficulty=1,
            estimated_time_minutes=1,
            max_score=10,
            created_by=teacher
        )
        print(f"✓ Created quick_question element: {element.title}")

    return element


def create_theory_element(teacher):
    """Create theory element to verify unchanged behavior"""
    try:
        element = Element.objects.get(title='Теория: Основы математики')
        print(f"✓ Theory element already exists")
    except Element.DoesNotExist:
        element = Element.objects.create(
            title='Теория: Основы математики',
            description='Читайте теоретический материал',
            element_type='theory',
            content={
                'text': 'Основные операции в математике: сложение, вычитание, умножение, деление.',
                'sections': [
                    {
                        'title': 'Сложение',
                        'content': 'Сложение - это операция объединения двух чисел.'
                    }
                ]
            },
            difficulty=1,
            estimated_time_minutes=5,
            max_score=0,
            created_by=teacher
        )
        print(f"✓ Created theory element: {element.title}")

    return element


def create_text_problem_element(teacher):
    """Create text_problem element to verify unchanged behavior"""
    try:
        element = Element.objects.get(title='Текстовая задача')
        print(f"✓ Text problem element already exists")
    except Element.DoesNotExist:
        element = Element.objects.create(
            title='Текстовая задача',
            description='Решите текстовую задачу',
            element_type='text_problem',
            content={
                'problem_text': 'В классе 25 учеников. 15 занимаются спортом. Сколько учеников не занимаются спортом?',
                'hints': [
                    'Подумайте о разности',
                    'Используйте вычитание'
                ]
            },
            difficulty=2,
            estimated_time_minutes=10,
            max_score=10,
            created_by=teacher
        )
        print(f"✓ Created text_problem element: {element.title}")

    return element


def create_video_element(teacher):
    """Create video element"""
    try:
        element = Element.objects.get(title='Видео: Введение в математику')
        print(f"✓ Video element already exists")
    except Element.DoesNotExist:
        element = Element.objects.create(
            title='Видео: Введение в математику',
            description='Смотрите видеоурок',
            element_type='video',
            content={
                'url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
                'title': 'Введение в математику',
                'description': 'Базовые концепции',
                'duration_seconds': 600
            },
            difficulty=1,
            estimated_time_minutes=10,
            max_score=0,
            created_by=teacher
        )
        print(f"✓ Created video element: {element.title}")

    return element


def create_test_lesson(teacher, subject, quick_question, theory, text_problem, video):
    """Create lesson with all element types"""
    try:
        lesson = Lesson.objects.get(title='Урок для E2E тестирования')
        print(f"✓ Lesson already exists: {lesson.title}")
    except Lesson.DoesNotExist:
        lesson = Lesson.objects.create(
            title='Урок для E2E тестирования',
            description='Комплексный урок для тестирования всех типов элементов',
            subject=subject,
            created_by=teacher
        )
        print(f"✓ Created lesson: {lesson.title}")

    # Add elements to lesson in order
    elements_to_add = [
        (theory, 1),
        (quick_question, 2),
        (text_problem, 3),
        (video, 4),
    ]

    for element, order in elements_to_add:
        lesson_element, created = LessonElement.objects.get_or_create(
            lesson=lesson,
            element=element,
            defaults={'order': order}
        )
        if created:
            print(f"  ✓ Added {element.element_type} ({order}) to lesson")
        else:
            print(f"  ✓ {element.element_type} already in lesson")

    return lesson


def create_knowledge_graph(student, teacher, subject, lesson):
    """Create knowledge graph with student enrolled"""
    try:
        graph = KnowledgeGraph.objects.get(
            student=student,
            subject=subject
        )
        print(f"✓ Knowledge graph already exists for {student.email}")
    except KnowledgeGraph.DoesNotExist:
        graph = KnowledgeGraph.objects.create(
            student=student,
            subject=subject,
            created_by=teacher
        )
        print(f"✓ Created knowledge graph for {student.email}")

    # Add lesson to graph
    graph_lesson, created = GraphLesson.objects.get_or_create(
        knowledge_graph=graph,
        lesson=lesson,
        defaults={'order': 1}
    )
    if created:
        print(f"  ✓ Added lesson to graph: {lesson.title}")
    else:
        print(f"  ✓ Lesson already in graph")

    return graph


def main():
    print("\n" + "="*70)
    print("CREATING TEST DATA FOR QUICK_QUESTION E2E TESTS (T104)")
    print("="*70 + "\n")

    try:
        # Create accounts
        print("Step 1: Creating test accounts...")
        student = create_test_student()
        teacher = create_test_teacher()

        # Create subject
        print("\nStep 2: Creating test subject...")
        subject = create_test_subject(teacher)

        # Create elements
        print("\nStep 3: Creating lesson elements...")
        quick_question = create_quick_question_element(teacher)
        theory = create_theory_element(teacher)
        text_problem = create_text_problem_element(teacher)
        video = create_video_element(teacher)

        # Create lesson
        print("\nStep 4: Creating test lesson...")
        lesson = create_test_lesson(
            teacher, subject,
            quick_question, theory, text_problem, video
        )

        # Create knowledge graph
        print("\nStep 5: Creating knowledge graph...")
        graph = create_knowledge_graph(student, teacher, subject, lesson)

        print("\n" + "="*70)
        print("✓ TEST DATA CREATED SUCCESSFULLY")
        print("="*70)
        print("\nYou can now run E2E tests:")
        print("  cd frontend")
        print("  npx playwright test tests/e2e/student/quick-question-retry.spec.ts --headed")
        print("\nTest Credentials:")
        print(f"  Email: {student.email}")
        print(f"  Password: TestPass123!")
        print("\nLesson Details:")
        print(f"  Title: {lesson.title}")
        print(f"  Elements: 4 (Theory, Quick Question, Text Problem, Video)")
        print("\n")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
