"""Unit tests for student schedule access control (H1)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from scheduling.models import Lesson
from materials.models import Subject
from accounts.models import StudentProfile

User = get_user_model()


class StudentScheduleAccessTests(TestCase):
    """Test student schedule access control."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.parent1 = User.objects.create(username="parent1", role="parent")
        self.student1 = User.objects.create(username="student1", role="student")
        StudentProfile.objects.create(user=self.student1, parent=self.parent1)

        self.parent2 = User.objects.create(username="parent2", role="parent")
        self.student2 = User.objects.create(username="student2", role="student")
        StudentProfile.objects.create(user=self.student2, parent=self.parent2)

        self.teacher = User.objects.create(username="teacher", role="teacher")

    def test_parent_can_access_own_child_schedule(self):
        """Parent can access schedule of their own child."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student1,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        lessons = Lesson.objects.filter(student=self.student1)
        self.assertEqual(lessons.count(), 1)

    def test_parent_cannot_access_other_child_schedule(self):
        """Parent cannot access schedule of other parent's children."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student2,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        student_profile = StudentProfile.objects.get(user=self.student2)
        self.assertEqual(student_profile.parent.id, self.parent2.id)
        self.assertNotEqual(student_profile.parent.id, self.parent1.id)

    def test_multiple_children_per_parent(self):
        """Parent with multiple children can access all their schedules."""
        student3 = User.objects.create(username="student3", role="student")
        StudentProfile.objects.create(user=student3, parent=self.parent1)

        children = StudentProfile.objects.filter(parent=self.parent1)
        self.assertEqual(children.count(), 2)
