"""
Tests for lesson scheduling module.
Covers: Lessons, Tutors, Parents, Students interactions.
"""
from datetime import time, timedelta, date
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User, StudentProfile
from scheduling.models import Lesson
from materials.models import Subject


class LessonModelValidationTests(TestCase):
    """Tests for Lesson model validation"""

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
            description="Math lessons",
        )

    def test_create_lesson_success(self):
        """Test successful lesson creation"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed",
        )

        self.assertIsNotNone(lesson.id)
        self.assertEqual(lesson.teacher, self.teacher)
        self.assertEqual(lesson.student, self.student)
        self.assertEqual(lesson.subject, self.subject)

    def test_create_lesson_default_status(self):
        """Test that default status is 'pending'"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        self.assertEqual(lesson.status, "pending")

    def test_lesson_with_description(self):
        """Test lesson with description"""
        description = "Advanced algebra concepts"
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            description=description,
        )

        self.assertEqual(lesson.description, description)

    def test_lesson_with_telemost_link(self):
        """Test lesson with Yandex Telemost link"""
        link = "https://telemost.yandex.ru/j/12345"
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            telemost_link=link,
        )

        self.assertEqual(lesson.telemost_link, link)

    def test_lesson_timestamps(self):
        """Test lesson timestamps"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        self.assertIsNotNone(lesson.created_at)
        self.assertIsNotNone(lesson.updated_at)

    def test_lesson_status_choices(self):
        """Test all status choices"""
        statuses = ["pending", "confirmed", "completed", "cancelled"]

        for status_choice in statuses:
            lesson = Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today(),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status=status_choice,
            )
            self.assertEqual(lesson.status, status_choice)


class LessonQueriesTests(TestCase):
    """Tests for common lesson queries"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math lessons",
        )

    def test_get_teacher_lessons(self):
        """Test getting lessons taught by a teacher"""
        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student2,
            subject=self.subject,
            date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

        teacher_lessons = self.teacher.taught_lessons.all()
        self.assertEqual(teacher_lessons.count(), 2)
        self.assertIn(lesson1, teacher_lessons)
        self.assertIn(lesson2, teacher_lessons)

    def test_get_student_lessons(self):
        """Test getting lessons for a student"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        student_lessons = self.student1.student_lessons.all()
        self.assertEqual(student_lessons.count(), 1)
        self.assertIn(lesson, student_lessons)

    def test_get_lessons_by_subject(self):
        """Test getting lessons by subject"""
        subject2 = Subject.objects.create(
            name="Physics",
            description="Physics lessons",
        )

        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student2,
            subject=subject2,
            date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

        math_lessons = self.subject.lessons.all()
        physics_lessons = subject2.lessons.all()

        self.assertEqual(math_lessons.count(), 1)
        self.assertEqual(physics_lessons.count(), 1)
        self.assertIn(lesson1, math_lessons)
        self.assertIn(lesson2, physics_lessons)

    def test_get_pending_lessons(self):
        """Test getting pending lessons"""
        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending",
        )
        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student2,
            subject=self.subject,
            date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
            status="confirmed",
        )

        pending = Lesson.objects.filter(status="pending")
        self.assertEqual(pending.count(), 1)
        self.assertIn(lesson1, pending)
        self.assertNotIn(lesson2, pending)

    def test_get_confirmed_lessons(self):
        """Test getting confirmed lessons"""
        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed",
        )
        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student2,
            subject=self.subject,
            date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
            status="cancelled",
        )

        confirmed = Lesson.objects.filter(status="confirmed")
        self.assertEqual(confirmed.count(), 1)
        self.assertIn(lesson1, confirmed)
        self.assertNotIn(lesson2, confirmed)


class TutorStudentLessonTests(TestCase):
    """Tests for tutor-student lesson interactions"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor",
            email="tutor@example.com",
            password="testpass123",
            role=User.Role.TUTOR,
        )
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
            description="Math lessons",
        )
        # Create student profile and link to tutor
        StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor,
            grade="10",
        )

    def test_tutor_can_see_tutored_students(self):
        """Test that tutor can see their tutored students"""
        tutored = self.tutor.tutored_students.all()
        self.assertIn(self.student, tutored)

    def test_student_knows_their_tutor(self):
        """Test that student knows their tutor"""
        profile = self.student.student_profile
        self.assertEqual(profile.tutor, self.tutor)

    def test_lesson_between_teacher_and_student(self):
        """Test creating lesson between teacher and student"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        self.assertEqual(lesson.teacher, self.teacher)
        self.assertEqual(lesson.student, self.student)


class ParentStudentLessonTests(TestCase):
    """Tests for parent-student lesson relationships"""

    def setUp(self):
        self.parent = User.objects.create_user(
            username="parent",
            email="parent@example.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
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
            description="Math lessons",
        )
        # Link student to parent
        StudentProfile.objects.create(
            user=self.student,
            parent=self.parent,
            grade="10",
        )

    def test_parent_can_see_children(self):
        """Test that parent can see their children"""
        children = self.parent.children_students.all()
        self.assertIn(self.student, children)

    def test_student_knows_their_parent(self):
        """Test that student knows their parent"""
        profile = self.student.student_profile
        self.assertEqual(profile.parent, self.parent)

    def test_parent_can_see_child_lessons(self):
        """Test that parent can see child's lessons"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed",
        )

        child = self.parent.children_students.first()
        child_lessons = child.student_lessons.all()

        self.assertIn(lesson, child_lessons)


class LessonDateTimeTests(TestCase):
    """Tests for lesson date and time handling"""

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
            description="Math lessons",
        )

    def test_lesson_date_in_future(self):
        """Test creating lesson in future"""
        future_date = date.today() + timedelta(days=7)
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        self.assertEqual(lesson.date, future_date)

    def test_lesson_time_duration(self):
        """Test lesson duration calculation"""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 30),
        )

        duration = timedelta(hours=1, minutes=30)
        calculated_duration = timedelta(
            hours=lesson.end_time.hour - lesson.start_time.hour,
            minutes=lesson.end_time.minute - lesson.start_time.minute,
        )

        self.assertEqual(calculated_duration, duration)

    def test_multiple_lessons_same_day(self):
        """Test multiple lessons on the same day"""
        today = date.today()
        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=today,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=today,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

        day_lessons = Lesson.objects.filter(date=today)
        self.assertEqual(day_lessons.count(), 2)
        self.assertIn(lesson1, day_lessons)
        self.assertIn(lesson2, day_lessons)
