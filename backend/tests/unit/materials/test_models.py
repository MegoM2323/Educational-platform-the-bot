"""
Unit tests for materials.models

Покрытие:
- Subject model
- TeacherSubject model
- SubjectEnrollment model
- Material model
- MaterialProgress model
- StudyPlan model
- StudyPlanFile model
"""
import pytest
from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from materials.models import (
    Subject, TeacherSubject, SubjectEnrollment, Material, MaterialProgress,
    MaterialComment, MaterialSubmission, MaterialFeedback, StudyPlan, StudyPlanFile,
    SubjectPayment, SubjectSubscription, validate_submission_file
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestSubjectModel:
    """Тесты модели Subject"""

    def test_create_subject(self):
        """Тест создания предмета"""
        subject = Subject.objects.create(
            name="Математика",
            description="Алгебра и геометрия",
            color="#FF5733"
        )

        assert subject.id is not None
        assert subject.name == "Математика"
        assert subject.description == "Алгебра и геометрия"
        assert subject.color == "#FF5733"

    def test_subject_str_method(self):
        """Тест строкового представления предмета"""
        subject = Subject.objects.create(name="Физика")
        assert str(subject) == "Физика"

    def test_subject_ordering(self):
        """Тест сортировки предметов по имени"""
        Subject.objects.create(name="Физика")
        Subject.objects.create(name="Математика")
        Subject.objects.create(name="Химия")

        subjects = list(Subject.objects.all())
        assert subjects[0].name == "Математика"
        assert subjects[1].name == "Физика"
        assert subjects[2].name == "Химия"

    def test_subject_default_color(self):
        """Тест цвета по умолчанию"""
        subject = Subject.objects.create(name="История")
        assert subject.color == "#3B82F6"


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherSubjectModel:
    """Тесты модели TeacherSubject"""

    def test_create_teacher_subject(self, teacher_user, subject):
        """Тест создания связи преподаватель-предмет"""
        ts = TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject,
            is_active=True
        )

        assert ts.id is not None
        assert ts.teacher == teacher_user
        assert ts.subject == subject
        assert ts.is_active is True
        assert ts.assigned_at is not None

    def test_teacher_subject_unique_together(self, teacher_user, subject):
        """Тест уникальности связи teacher-subject"""
        TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject
        )

        # Попытка создать дубликат должна вызвать ошибку
        with pytest.raises(Exception):
            TeacherSubject.objects.create(
                teacher=teacher_user,
                subject=subject
            )

    def test_teacher_subject_cascade_delete(self, teacher_user, subject):
        """Тест каскадного удаления при удалении teacher или subject"""
        ts = TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject
        )

        ts_id = ts.id
        subject.delete()

        # TeacherSubject должен быть удален вместе с subject
        assert not TeacherSubject.objects.filter(id=ts_id).exists()

    def test_teacher_subject_str_method(self, teacher_user, subject):
        """Тест строкового представления"""
        ts = TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject
        )
        expected = f"{teacher_user.get_full_name()} - {subject.name}"
        assert str(ts) == expected


@pytest.mark.unit
@pytest.mark.django_db
class TestSubjectEnrollmentModel:
    """Тесты модели SubjectEnrollment"""

    def test_create_enrollment(self, student_user, subject, teacher_user):
        """Тест создания зачисления"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        assert enrollment.id is not None
        assert enrollment.student == student_user
        assert enrollment.subject == subject
        assert enrollment.teacher == teacher_user
        assert enrollment.is_active is True
        assert enrollment.enrolled_at is not None

    def test_enrollment_unique_together(self, student_user, subject, teacher_user):
        """Тест уникальности комбинации student-subject-teacher"""
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        with pytest.raises(Exception):
            SubjectEnrollment.objects.create(
                student=student_user,
                subject=subject,
                teacher=teacher_user
            )

    def test_enrollment_custom_subject_name(self, student_user, subject, teacher_user):
        """Тест кастомного названия предмета"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            custom_subject_name="Продвинутая математика"
        )

        assert enrollment.get_subject_name() == "Продвинутая математика"

    def test_enrollment_get_subject_name_default(self, student_user, subject, teacher_user):
        """Тест получения стандартного названия предмета"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        assert enrollment.get_subject_name() == subject.name

    def test_enrollment_str_method(self, student_user, subject, teacher_user):
        """Тест строкового представления"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        expected = f"{student_user} - {subject.name} ({teacher_user})"
        assert str(enrollment) == expected


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialModel:
    """Тесты модели Material"""

    def test_create_material(self, teacher_user, subject):
        """Тест создания материала"""
        material = Material.objects.create(
            title="Введение в алгебру",
            description="Основы алгебры",
            content="Текст урока",
            author=teacher_user,
            subject=subject,
            type=Material.Type.LESSON,
            status=Material.Status.DRAFT
        )

        assert material.id is not None
        assert material.title == "Введение в алгебру"
        assert material.author == teacher_user
        assert material.subject == subject
        assert material.type == Material.Type.LESSON
        assert material.status == Material.Status.DRAFT

    def test_material_file_upload(self, teacher_user, subject):
        """Тест загрузки файла к материалу"""
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )

        material = Material.objects.create(
            title="Урок с файлом",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            file=test_file
        )

        assert material.file is not None
        assert material.file.name.endswith('.pdf')

    def test_material_published_at_auto_set(self, teacher_user, subject):
        """Тест автоматической установки published_at при активации"""
        material = Material.objects.create(
            title="Тест публикации",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.DRAFT
        )

        assert material.published_at is None

        material.status = Material.Status.ACTIVE
        material.save()

        assert material.published_at is not None

    def test_material_str_method(self, teacher_user, subject):
        """Тест строкового представления"""
        material = Material.objects.create(
            title="Тестовый урок",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        assert str(material) == "Тестовый урок"


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialProgressModel:
    """Тесты модели MaterialProgress"""

    def test_create_progress(self, student_user, teacher_user, subject):
        """Тест создания прогресса"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        progress = MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=50,
            time_spent=30
        )

        assert progress.id is not None
        assert progress.student == student_user
        assert progress.material == material
        assert progress.progress_percentage == 50
        assert progress.time_spent == 30
        assert progress.is_completed is False

    def test_progress_unique_together(self, student_user, teacher_user, subject):
        """Тест уникальности student-material"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        MaterialProgress.objects.create(
            student=student_user,
            material=material
        )

        with pytest.raises(Exception):
            MaterialProgress.objects.create(
                student=student_user,
                material=material
            )

    def test_progress_completion(self, student_user, teacher_user, subject):
        """Тест завершения материала"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        progress = MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=100,
            is_completed=True,
            completed_at=timezone.now()
        )

        assert progress.is_completed is True
        assert progress.completed_at is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestStudyPlanModel:
    """Тесты модели StudyPlan"""

    def test_create_study_plan(self, teacher_user, student_user, subject):
        """Тест создания плана занятий"""
        today = date.today()

        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План на неделю 1",
            content="Содержание плана",
            week_start_date=today,
            status=StudyPlan.Status.DRAFT
        )

        assert plan.id is not None
        assert plan.teacher == teacher_user
        assert plan.student == student_user
        assert plan.subject == subject
        assert plan.week_start_date == today
        # week_end_date должен быть автоматически установлен на +6 дней
        assert plan.week_end_date == today + timedelta(days=6)

    def test_study_plan_auto_week_end_date(self, teacher_user, student_user, subject):
        """Тест автоматического расчета week_end_date"""
        start_date = date.today()

        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=start_date
        )

        expected_end = start_date + timedelta(days=6)
        assert plan.week_end_date == expected_end

    def test_study_plan_sent_at_auto_set(self, teacher_user, student_user, subject):
        """Тест автоматической установки sent_at при отправке"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=date.today(),
            status=StudyPlan.Status.DRAFT
        )

        assert plan.sent_at is None

        plan.status = StudyPlan.Status.SENT
        plan.save()

        assert plan.sent_at is not None

    def test_study_plan_auto_enrollment_link(self, teacher_user, student_user, subject):
        """Тест автоматической связи с enrollment"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=date.today()
        )

        # enrollment должен быть автоматически установлен
        assert plan.enrollment == enrollment


@pytest.mark.unit
@pytest.mark.django_db
class TestStudyPlanFileModel:
    """Тесты модели StudyPlanFile"""

    def test_create_study_plan_file(self, teacher_user, student_user, subject):
        """Тест создания файла для плана занятий"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=date.today()
        )

        test_file = SimpleUploadedFile(
            "plan.pdf",
            b"file_content",
            content_type="application/pdf"
        )

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            name="План занятий.pdf",
            file_size=1024,
            uploaded_by=teacher_user
        )

        assert plan_file.id is not None
        assert plan_file.study_plan == plan
        assert plan_file.name == "План занятий.pdf"
        assert plan_file.file_size == 1024
        assert plan_file.uploaded_by == teacher_user

    def test_study_plan_file_auto_name(self, teacher_user, student_user, subject):
        """Тест автоматического заполнения имени файла"""
        plan = StudyPlan.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            title="План",
            content="Содержание",
            week_start_date=date.today()
        )

        test_file = SimpleUploadedFile("test.pdf", b"content")

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            file_size=100,
            uploaded_by=teacher_user
        )

        # name должно быть установлено из имени файла
        assert plan_file.name == "test.pdf"


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialSubmissionModel:
    """Тесты модели MaterialSubmission"""

    def test_create_submission(self, student_user, teacher_user, subject):
        """Тест создания ответа на материал"""
        material = Material.objects.create(
            title="Домашняя работа",
            content="Задание",
            author=teacher_user,
            subject=subject,
            type=Material.Type.HOMEWORK
        )

        submission = MaterialSubmission.objects.create(
            material=material,
            student=student_user,
            submission_text="Мой ответ на задание",
            status=MaterialSubmission.Status.SUBMITTED
        )

        assert submission.id is not None
        assert submission.material == material
        assert submission.student == student_user
        assert submission.submission_text == "Мой ответ на задание"

    def test_submission_file_validation(self):
        """Тест валидации размера файла"""
        # Файл размером > 10MB должен вызвать ошибку
        large_file = SimpleUploadedFile(
            "large.pdf",
            b"x" * (11 * 1024 * 1024)  # 11MB
        )

        with pytest.raises(ValidationError):
            validate_submission_file(large_file)

    def test_submission_requires_content(self, student_user, teacher_user, subject):
        """Тест требования наличия текста или файла"""
        material = Material.objects.create(
            title="Домашняя работа",
            content="Задание",
            author=teacher_user,
            subject=subject
        )

        submission = MaterialSubmission(
            material=material,
            student=student_user
        )

        with pytest.raises(ValidationError):
            submission.clean()


@pytest.mark.unit
@pytest.mark.django_db
class TestSubjectPaymentModel:
    """Тесты модели SubjectPayment"""

    def test_create_subject_payment(self, enrollment, payment):
        """Тест создания платежа по предмету"""
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PENDING
        )

        assert subject_payment.id is not None
        assert subject_payment.enrollment == enrollment
        assert subject_payment.payment == payment
        assert subject_payment.amount == Decimal('100.00')
        assert subject_payment.due_date is not None

    def test_subject_payment_unique_enrollment_payment(self, enrollment, payment):
        """Тест уникальности enrollment-payment"""
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('100.00')
        )

        with pytest.raises(Exception):
            SubjectPayment.objects.create(
                enrollment=enrollment,
                payment=payment,
                amount=Decimal('100.00')
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestSubjectSubscriptionModel:
    """Тесты модели SubjectSubscription"""

    def test_create_subscription(self, enrollment):
        """Тест создания подписки"""
        subscription = SubjectSubscription.objects.create(
            enrollment=enrollment,
            amount=Decimal('100.00'),
            status=SubjectSubscription.Status.ACTIVE,
            next_payment_date=timezone.now() + timedelta(days=7),
            payment_interval_weeks=1
        )

        assert subscription.id is not None
        assert subscription.enrollment == enrollment
        assert subscription.amount == Decimal('100.00')
        assert subscription.status == SubjectSubscription.Status.ACTIVE

    def test_subscription_schedule_next_payment(self, enrollment, settings):
        """Тест планирования следующего платежа"""
        subscription = SubjectSubscription.objects.create(
            enrollment=enrollment,
            amount=Decimal('100.00'),
            status=SubjectSubscription.Status.ACTIVE,
            next_payment_date=timezone.now(),
            payment_interval_weeks=1
        )

        old_date = subscription.next_payment_date
        subscription.schedule_next_payment()

        # next_payment_date должен быть обновлен
        assert subscription.next_payment_date > old_date
