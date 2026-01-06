"""
Tests for Knowledge Graph module.
Covers: Elements, Lessons, Student Progress.
"""
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from accounts.models import User
from knowledge_graph.models import Element, Lesson, StudentProgress, StudentElementProgress
from materials.models import Subject


class ElementModelTests(TestCase):
    """Tests for Element model"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

    def test_create_text_problem_element(self):
        """Test creating text problem element"""
        element = Element.objects.create(
            title="Algebra Problem",
            description="Solve for x",
            element_type="text_problem",
            content={"problem": "x + 5 = 10", "answer": "5"},
            created_by=self.teacher,
        )

        self.assertEqual(element.title, "Algebra Problem")
        self.assertEqual(element.element_type, "text_problem")
        self.assertFalse(element.is_public)

    def test_create_video_element(self):
        """Test creating video element"""
        element = Element.objects.create(
            title="Math Introduction",
            description="Video about basic math",
            element_type="video",
            content={"url": "https://example.com/video.mp4", "duration": 600},
            created_by=self.teacher,
        )

        self.assertEqual(element.element_type, "video")
        self.assertIn("url", element.content)

    def test_create_theory_element(self):
        """Test creating theory element"""
        element = Element.objects.create(
            title="Quadratic Equations",
            description="Theory about quadratic equations",
            element_type="theory",
            content={"text": "Formula ax^2 + bx + c = 0"},
            created_by=self.teacher,
        )

        self.assertEqual(element.element_type, "theory")

    def test_create_quick_question_element(self):
        """Test creating quick question element"""
        element = Element.objects.create(
            title="What is 2+2?",
            description="Basic arithmetic",
            element_type="quick_question",
            content={"question": "2 + 2 = ?", "options": ["3", "4", "5"]},
            created_by=self.teacher,
        )

        self.assertEqual(element.element_type, "quick_question")

    def test_element_difficulty_range(self):
        """Test difficulty parameter within range"""
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            difficulty=7,
            created_by=self.teacher,
        )

        self.assertEqual(element.difficulty, 7)

    def test_element_difficulty_min_max(self):
        """Test difficulty limits (1-10)"""
        # Min value
        element1 = Element.objects.create(
            title="Easy",
            description="Easy",
            element_type="text_problem",
            content={},
            difficulty=1,
            created_by=self.teacher,
        )
        self.assertEqual(element1.difficulty, 1)

        # Max value
        element2 = Element.objects.create(
            title="Hard",
            description="Hard",
            element_type="text_problem",
            content={},
            difficulty=10,
            created_by=self.teacher,
        )
        self.assertEqual(element2.difficulty, 10)

    def test_element_time_estimate(self):
        """Test estimated time in minutes"""
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            estimated_time_minutes=15,
            created_by=self.teacher,
        )

        self.assertEqual(element.estimated_time_minutes, 15)

    def test_element_max_score(self):
        """Test max score parameter"""
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            max_score=50,
            created_by=self.teacher,
        )

        self.assertEqual(element.max_score, 50)

    def test_element_tags(self):
        """Test element tags"""
        tags = ["algebra", "equations", "linear"]
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            tags=tags,
            created_by=self.teacher,
        )

        self.assertEqual(element.tags, tags)

    def test_element_public_flag(self):
        """Test public/private visibility"""
        private_element = Element.objects.create(
            title="Private",
            description="Private",
            element_type="text_problem",
            content={},
            is_public=False,
            created_by=self.teacher,
        )
        public_element = Element.objects.create(
            title="Public",
            description="Public",
            element_type="text_problem",
            content={},
            is_public=True,
            created_by=self.teacher,
        )

        self.assertFalse(private_element.is_public)
        self.assertTrue(public_element.is_public)

    def test_element_timestamps(self):
        """Test element timestamps"""
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            created_by=self.teacher,
        )

        self.assertIsNotNone(element.created_at)
        self.assertIsNotNone(element.updated_at)

    def test_element_author_relationship(self):
        """Test element creator relationship"""
        element = Element.objects.create(
            title="Test",
            description="Test",
            element_type="text_problem",
            content={},
            created_by=self.teacher,
        )

        self.assertEqual(element.created_by, self.teacher)
        self.assertIn(element, self.teacher.created_elements.all())


class LessonModelTests(TestCase):
    """Tests for Lesson model in knowledge graph"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math",
        )

    def test_create_lesson(self):
        """Test creating a lesson"""
        lesson = Lesson.objects.create(
            title="Quadratic Equations",
            description="Learn quadratic equations",
            subject=self.subject,
            created_by=self.teacher,
            order=1,
        )

        self.assertEqual(lesson.title, "Quadratic Equations")
        self.assertEqual(lesson.subject, self.subject)
        self.assertEqual(lesson.created_by, self.teacher)

    def test_lesson_order(self):
        """Test lesson ordering"""
        lesson1 = Lesson.objects.create(
            title="Lesson 1",
            description="",
            subject=self.subject,
            created_by=self.teacher,
            order=1,
        )
        lesson2 = Lesson.objects.create(
            title="Lesson 2",
            description="",
            subject=self.subject,
            created_by=self.teacher,
            order=2,
        )

        lessons = Lesson.objects.filter(subject=self.subject).order_by("order")
        self.assertEqual(list(lessons), [lesson1, lesson2])

    def test_add_elements_to_lesson(self):
        """Test adding elements to lesson"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        element = Element.objects.create(
            title="Element",
            description="",
            element_type="text_problem",
            content={},
            created_by=self.teacher,
        )

        lesson.elements.add(element)

        self.assertIn(element, lesson.elements.all())

    def test_lesson_timestamps(self):
        """Test lesson timestamps"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )

        self.assertIsNotNone(lesson.created_at)
        self.assertIsNotNone(lesson.updated_at)


class StudentProgressTests(TestCase):
    """Tests for student progress tracking"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math",
        )

    def test_create_student_progress(self):
        """Test creating student progress record"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        progress = StudentProgress.objects.create(
            student=self.student,
            lesson=lesson,
            status="in_progress",
        )

        self.assertEqual(progress.student, self.student)
        self.assertEqual(progress.lesson, lesson)
        self.assertEqual(progress.status, "in_progress")

    def test_student_progress_statuses(self):
        """Test different progress statuses"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )

        statuses = ["not_started", "in_progress", "completed"]
        for status in statuses:
            progress = StudentProgress.objects.create(
                student=self.student,
                lesson=lesson,
                status=status,
            )
            self.assertEqual(progress.status, status)

    def test_student_progress_completion_percentage(self):
        """Test completion percentage tracking"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        progress = StudentProgress.objects.create(
            student=self.student,
            lesson=lesson,
            status="in_progress",
            completion_percentage=50,
        )

        self.assertEqual(progress.completion_percentage, 50)

    def test_student_element_progress(self):
        """Test student element progress"""
        element = Element.objects.create(
            title="Element",
            description="",
            element_type="text_problem",
            content={},
            max_score=100,
            created_by=self.teacher,
        )
        elem_progress = StudentElementProgress.objects.create(
            student=self.student,
            element=element,
            score=75,
            is_completed=True,
        )

        self.assertEqual(elem_progress.score, 75)
        self.assertTrue(elem_progress.is_completed)

    def test_get_student_lessons(self):
        """Test getting all lessons for a student"""
        lesson1 = Lesson.objects.create(
            title="Lesson 1",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        lesson2 = Lesson.objects.create(
            title="Lesson 2",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )

        StudentProgress.objects.create(
            student=self.student,
            lesson=lesson1,
            status="in_progress",
        )
        StudentProgress.objects.create(
            student=self.student,
            lesson=lesson2,
            status="completed",
        )

        student_lessons = StudentProgress.objects.filter(student=self.student)
        self.assertEqual(student_lessons.count(), 2)

    def test_get_completed_lessons(self):
        """Test getting completed lessons"""
        lesson1 = Lesson.objects.create(
            title="Lesson 1",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        lesson2 = Lesson.objects.create(
            title="Lesson 2",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )

        StudentProgress.objects.create(
            student=self.student,
            lesson=lesson1,
            status="completed",
        )
        StudentProgress.objects.create(
            student=self.student,
            lesson=lesson2,
            status="in_progress",
        )

        completed = StudentProgress.objects.filter(
            student=self.student,
            status="completed",
        )
        self.assertEqual(completed.count(), 1)

    def test_lesson_element_relationships(self):
        """Test relationships between lessons and elements"""
        lesson = Lesson.objects.create(
            title="Lesson",
            description="",
            subject=self.subject,
            created_by=self.teacher,
        )
        elem1 = Element.objects.create(
            title="Element 1",
            description="",
            element_type="text_problem",
            content={},
            created_by=self.teacher,
        )
        elem2 = Element.objects.create(
            title="Element 2",
            description="",
            element_type="theory",
            content={},
            created_by=self.teacher,
        )

        lesson.elements.add(elem1, elem2)

        self.assertEqual(lesson.elements.count(), 2)
        self.assertIn(elem1, lesson.elements.all())
        self.assertIn(elem2, lesson.elements.all())

    def test_student_attempts(self):
        """Test tracking student attempts"""
        element = Element.objects.create(
            title="Element",
            description="",
            element_type="text_problem",
            content={},
            max_score=100,
            created_by=self.teacher,
        )

        # First attempt
        progress1 = StudentElementProgress.objects.create(
            student=self.student,
            element=element,
            score=50,
            is_completed=False,
            attempt_number=1,
        )

        # Second attempt
        progress2 = StudentElementProgress.objects.create(
            student=self.student,
            element=element,
            score=75,
            is_completed=True,
            attempt_number=2,
        )

        all_attempts = StudentElementProgress.objects.filter(
            student=self.student,
            element=element,
        )
        self.assertEqual(all_attempts.count(), 2)
