from django.test import TestCase
from django.contrib.auth import get_user_model

from materials.models import Subject, SubjectEnrollment
from backend.reports.student_report_service import StudentReportService, CreateStudentReportInput
from backend.reports.models import StudentReport


class StudentReportServiceTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create(username='teacher1', role='teacher', first_name='T', last_name='One')
        self.student = User.objects.create(username='student1', role='student', first_name='S', last_name='One')
        self.subject = Subject.objects.create(name='Math')
        SubjectEnrollment.objects.create(student=self.student, subject=self.subject, teacher=self.teacher)

    def test_get_teacher_students(self):
        students = StudentReportService.get_teacher_students(self.teacher)
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]['id'], self.student.id)

    def test_create_student_report(self):
        data = CreateStudentReportInput(
            teacher=self.teacher,
            student=self.student,
            title='Progress Jan',
            period_start='2024-01-01',
            period_end='2024-01-31',
            content={'summary': 'Good progress'},
        )
        report = StudentReportService.create_student_report(data)
        self.assertIsInstance(report, StudentReport)
        self.assertEqual(report.teacher, self.teacher)
        self.assertEqual(report.student, self.student)

    def test_create_student_report_forbidden_if_not_student_of_teacher(self):
        User = get_user_model()
        other_student = User.objects.create(username='student2', role='student')
        data = CreateStudentReportInput(
            teacher=self.teacher,
            student=other_student,
            title='Forbidden',
            period_start='2024-01-01',
            period_end='2024-01-31',
            content={},
        )
        with self.assertRaises(ValueError):
            StudentReportService.create_student_report(data)


