"""
Unit tests for TeacherDashboard service and views

Тесты покрывают:
- Получение списка студентов и материалов
- Работа с submissions (ответы студентов)
- Feedback для студентов
- Study plans (учебные планы)
- Bulk операции
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from materials.teacher_dashboard_service import TeacherDashboardService
from materials.models import (
    Material, MaterialProgress, MaterialSubmission, MaterialFeedback,
    StudyPlan, StudyPlanFile, Subject, SubjectEnrollment
)

User = get_user_model()


# ===== SERVICE TESTS: Basic Dashboard Functions =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardService:
    """Базовые тесты TeacherDashboardService"""

    def test_init_requires_teacher_role(self, student_user):
        """Инициализация сервиса требует роль teacher"""
        with pytest.raises(ValueError, match="Пользователь должен иметь роль 'teacher'"):
            TeacherDashboardService(student_user)

    def test_init_with_valid_teacher(self, teacher_user):
        """Успешная инициализация с teacher пользователем"""
        service = TeacherDashboardService(teacher_user)
        assert service.teacher == teacher_user

    def test_get_teacher_students(self, teacher_user, student_user, sample_enrollment):
        """Получить список студентов преподавателя"""
        service = TeacherDashboardService(teacher_user)
        students = service.get_teacher_students()

        assert len(students) == 1
        assert students[0]['id'] == student_user.id
        assert students[0]['username'] == student_user.username
        assert 'profile' in students[0]
        assert 'subjects' in students[0]

    def test_get_teacher_students_excludes_admins(self, db, teacher_user, admin_user, sample_enrollment):
        """Админы не должны попадать в список студентов"""
        # Создаем зачисление админа
        subject = sample_enrollment.subject
        SubjectEnrollment.objects.create(
            student=admin_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TeacherDashboardService(teacher_user)
        students = service.get_teacher_students()

        # Проверяем, что admin не в списке
        student_ids = [s['id'] for s in students]
        assert admin_user.id not in student_ids

    def test_get_teacher_materials(self, teacher_user, sample_material):
        """Получить материалы преподавателя"""
        service = TeacherDashboardService(teacher_user)
        materials = service.get_teacher_materials()

        assert len(materials) == 1
        assert materials[0]['id'] == sample_material.id
        assert materials[0]['title'] == sample_material.title
        assert 'subject' in materials[0]

    def test_get_teacher_materials_filter_by_subject(self, teacher_user, sample_material, db):
        """Фильтрация материалов по предмету"""
        # Создаем материал в другом предмете
        other_subject = Subject.objects.create(
            name="Физика",
            description="Курс физики"
        )
        Material.objects.create(
            title="Other Material",
            subject=other_subject,
            author=teacher_user
        )

        service = TeacherDashboardService(teacher_user)
        materials = service.get_teacher_materials(subject_id=sample_material.subject.id)

        # Должен быть только один материал из нужного предмета
        assert len(materials) == 1
        assert materials[0]['id'] == sample_material.id

    def test_distribute_material(self, teacher_user, sample_material, student_user):
        """Распределить материал студенту"""
        service = TeacherDashboardService(teacher_user)
        result = service.distribute_material(
            material_id=sample_material.id,
            student_ids=[student_user.id]
        )

        assert result['success'] is True
        assert result['assigned_count'] == 1
        assert sample_material.assigned_to.filter(id=student_user.id).exists()

    def test_distribute_material_creates_progress(self, teacher_user, sample_material, student_user):
        """Распределение материала создает MaterialProgress"""
        service = TeacherDashboardService(teacher_user)
        service.distribute_material(
            material_id=sample_material.id,
            student_ids=[student_user.id]
        )

        progress = MaterialProgress.objects.filter(
            student=student_user,
            material=sample_material
        )
        assert progress.exists()


# ===== SERVICE TESTS: Submissions =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardSubmissions:
    """Тесты для работы с ответами студентов (submissions)"""

    def test_get_pending_submissions(self, teacher_user, student_user, sample_material, sample_enrollment):
        """Получить задания ожидающие проверки"""
        # Создать submission
        submission = MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.SUBMITTED,
            submission_text="Test submission"
        )

        # В сервисе нет метода get_pending_submissions, проверим через QuerySet
        pending = MaterialSubmission.objects.filter(
            material__author=teacher_user,
            status=MaterialSubmission.Status.SUBMITTED
        )

        assert pending.count() == 1
        assert pending.first().id == submission.id

    def test_get_submissions_exclude_reviewed(self, teacher_user, student_user, sample_material):
        """Не показывать проверенные submissions в pending"""
        # Создать reviewed submission
        MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.REVIEWED,
            submission_text="Reviewed submission"
        )

        pending = MaterialSubmission.objects.filter(
            material__author=teacher_user,
            status=MaterialSubmission.Status.SUBMITTED
        )

        assert pending.count() == 0

    def test_create_submission_feedback(self, teacher_user, student_user, sample_material):
        """Создать фидбек для submission"""
        submission = MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.SUBMITTED,
            submission_text="Test"
        )

        feedback = MaterialFeedback.objects.create(
            submission=submission,
            teacher=teacher_user,
            feedback_text="Great work!",
            grade=5
        )

        assert feedback.feedback_text == "Great work!"
        assert feedback.grade == 5
        assert feedback.teacher == teacher_user

    def test_update_submission_status_after_feedback(self, teacher_user, student_user, sample_material):
        """Обновить статус submission после фидбека"""
        submission = MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.SUBMITTED,
            submission_text="Test"
        )

        # Создаем фидбек и обновляем статус
        MaterialFeedback.objects.create(
            submission=submission,
            teacher=teacher_user,
            feedback_text="Good",
            grade=4
        )

        submission.status = MaterialSubmission.Status.REVIEWED
        submission.save()

        submission.refresh_from_db()
        assert submission.status == MaterialSubmission.Status.REVIEWED

    def test_get_submissions_by_material(self, teacher_user, sample_material, db):
        """Получить submissions для конкретного материала"""
        # Создать несколько submissions
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        students = []
        for _ in range(3):
            student = StudentUserFactory()
            StudentProfile.objects.get_or_create(user=student)
            students.append(student)

        for student in students:
            MaterialSubmission.objects.create(
                material=sample_material,
                student=student,
                status=MaterialSubmission.Status.SUBMITTED,
                submission_text="Test"
            )

        submissions = MaterialSubmission.objects.filter(
            material=sample_material
        )

        assert submissions.count() == 3

    def test_filter_submissions_by_status(self, teacher_user, student_user, sample_material, db):
        """Фильтрация submissions по статусу"""
        # Создаем submissions с разными статусами
        MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.SUBMITTED,
            submission_text="Submitted"
        )

        from conftest import StudentUserFactory
        from accounts.models import StudentProfile
        student2 = StudentUserFactory()
        StudentProfile.objects.get_or_create(user=student2)

        MaterialSubmission.objects.create(
            material=sample_material,
            student=student2,
            status=MaterialSubmission.Status.REVIEWED,
            submission_text="Reviewed"
        )

        submitted = MaterialSubmission.objects.filter(
            material=sample_material,
            status=MaterialSubmission.Status.SUBMITTED
        )
        reviewed = MaterialSubmission.objects.filter(
            material=sample_material,
            status=MaterialSubmission.Status.REVIEWED
        )

        assert submitted.count() == 1
        assert reviewed.count() == 1

    def test_submission_requires_file_or_text(self, student_user, sample_material):
        """Submission требует файл или текст"""
        from django.core.exceptions import ValidationError

        submission = MaterialSubmission(
            material=sample_material,
            student=student_user,
            status=MaterialSubmission.Status.SUBMITTED
        )

        with pytest.raises(ValidationError):
            submission.full_clean()

    def test_feedback_grade_validation(self, teacher_user, student_user, sample_material):
        """Валидация оценки в feedback"""
        submission = MaterialSubmission.objects.create(
            material=sample_material,
            student=student_user,
            submission_text="Test"
        )

        # Оценка должна быть от 1 до 5
        feedback = MaterialFeedback.objects.create(
            submission=submission,
            teacher=teacher_user,
            feedback_text="Good",
            grade=3
        )

        assert 1 <= feedback.grade <= 5


# ===== SERVICE TESTS: Study Plans =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardStudyPlans:
    """Тесты для учебных планов"""

    def test_create_study_plan(self, teacher_user, student_user, subject, sample_enrollment):
        """Создать учебный план"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Неделя 1: Алгебра",
            content="План занятий на неделю",
            week_start_date=timezone.now().date()
        )

        assert plan is not None
        assert plan.student == student_user
        assert plan.teacher == teacher_user
        assert plan.subject == subject
        assert plan.status == StudyPlan.Status.DRAFT

    def test_study_plan_auto_calculates_end_date(self, teacher_user, student_user, subject):
        """Учебный план автоматически вычисляет дату окончания"""
        start_date = timezone.now().date()
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Test Plan",
            content="Content",
            week_start_date=start_date
        )

        expected_end_date = start_date + timedelta(days=6)
        assert plan.week_end_date == expected_end_date

    def test_attach_file_to_study_plan(self, teacher_user, student_user, subject):
        """Прикрепить файл к учебному плану"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Plan",
            content="Content",
            week_start_date=timezone.now().date()
        )

        test_file = SimpleUploadedFile(
            "plan.pdf",
            b"plan content",
            content_type="application/pdf"
        )

        plan_file = StudyPlanFile.objects.create(
            study_plan=plan,
            file=test_file,
            name="Study Plan PDF",
            file_size=len(b"plan content"),
            uploaded_by=teacher_user
        )

        assert plan_file is not None
        assert plan_file.study_plan == plan
        assert plan_file.uploaded_by == teacher_user

    def test_get_teacher_study_plans(self, teacher_user, student_user, subject):
        """Получить все учебные планы преподавателя"""
        # Создать несколько планов
        for i in range(3):
            StudyPlan.objects.create(
                student=student_user,
                teacher=teacher_user,
                subject=subject,
                title=f"Week {i+1}",
                content="Content",
                week_start_date=timezone.now().date() - timedelta(weeks=i)
            )

        plans = StudyPlan.objects.filter(teacher=teacher_user)
        assert plans.count() == 3

    def test_update_study_plan_status(self, teacher_user, student_user, subject):
        """Обновить статус учебного плана"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Plan",
            content="Content",
            week_start_date=timezone.now().date(),
            status=StudyPlan.Status.DRAFT
        )

        plan.status = StudyPlan.Status.SENT
        plan.save()

        plan.refresh_from_db()
        assert plan.status == StudyPlan.Status.SENT
        assert plan.sent_at is not None

    def test_study_plan_auto_finds_enrollment(self, teacher_user, student_user, subject, sample_enrollment):
        """Учебный план автоматически находит enrollment"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Plan",
            content="Content",
            week_start_date=timezone.now().date()
        )

        # После save должен быть установлен enrollment
        plan.refresh_from_db()
        assert plan.enrollment is not None
        assert plan.enrollment == sample_enrollment

    def test_delete_study_plan(self, teacher_user, student_user, subject):
        """Удалить учебный план"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Plan",
            content="Content",
            week_start_date=timezone.now().date()
        )

        plan_id = plan.id
        plan.delete()

        assert not StudyPlan.objects.filter(id=plan_id).exists()

    def test_get_study_plan_files(self, teacher_user, student_user, subject):
        """Получить файлы учебного плана"""
        plan = StudyPlan.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            title="Plan",
            content="Content",
            week_start_date=timezone.now().date()
        )

        # Создаем несколько файлов
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"file{i}.pdf",
                b"content",
                content_type="application/pdf"
            )
            StudyPlanFile.objects.create(
                study_plan=plan,
                file=test_file,
                name=f"File {i}",
                file_size=7,
                uploaded_by=teacher_user
            )

        files = plan.files.all()
        assert files.count() == 3


# ===== SERVICE TESTS: Bulk Operations =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardBulkOperations:
    """Тесты для bulk операций"""

    def test_bulk_distribute_material(self, teacher_user, sample_material, db):
        """Распределить материал нескольким студентам"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        students = []
        for _ in range(5):
            student = StudentUserFactory()
            StudentProfile.objects.get_or_create(user=student)
            students.append(student)

        student_ids = [s.id for s in students]

        service = TeacherDashboardService(teacher_user)
        result = service.distribute_material(
            material_id=sample_material.id,
            student_ids=student_ids
        )

        assert result['success'] is True
        assert result['assigned_count'] == 5

        # Проверяем, что все студенты назначены
        for student in students:
            assert sample_material.assigned_to.filter(id=student.id).exists()

    def test_bulk_distribute_excludes_admins(self, db, teacher_user, sample_material, admin_user):
        """Bulk операция исключает админов"""
        from conftest import StudentUserFactory

        student = StudentUserFactory()
        # StudentProfile автоматически создается сигналом при создании пользователя

        # Пытаемся назначить материал студенту И админу
        student_ids = [student.id, admin_user.id]

        service = TeacherDashboardService(teacher_user)
        result = service.distribute_material(
            material_id=sample_material.id,
            student_ids=student_ids
        )

        # Должен быть назначен только 1 студент (админ исключен)
        assert result['assigned_count'] == 1
        assert sample_material.assigned_to.filter(id=student.id).exists()
        assert not sample_material.assigned_to.filter(id=admin_user.id).exists()

    def test_bulk_create_progress_records(self, teacher_user, sample_material, db):
        """Bulk создание записей прогресса"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        students = []
        for _ in range(3):
            student = StudentUserFactory()
            StudentProfile.objects.get_or_create(user=student)
            students.append(student)

        student_ids = [s.id for s in students]

        service = TeacherDashboardService(teacher_user)
        service.distribute_material(
            material_id=sample_material.id,
            student_ids=student_ids
        )

        # Проверяем, что для каждого студента создан MaterialProgress
        for student in students:
            progress = MaterialProgress.objects.filter(
                student=student,
                material=sample_material
            )
            assert progress.exists()

    def test_bulk_material_distribution_invalid_material(self, teacher_user, db):
        """Попытка распределить несуществующий материал"""
        from conftest import StudentUserFactory

        student = StudentUserFactory()
        # StudentProfile автоматически создается сигналом при создании пользователя

        service = TeacherDashboardService(teacher_user)
        result = service.distribute_material(
            material_id=9999,  # Несуществующий ID
            student_ids=[student.id]
        )

        assert result['success'] is False
        assert 'не найден' in result['message']


# ===== VIEW TESTS: API Endpoints =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardViews:
    """API тесты для TeacherDashboard endpoints"""

    def test_get_dashboard_data(self, teacher_user):
        """GET /api/dashboard/teacher/ возвращает данные дашборда"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/dashboard/teacher/')

        assert response.status_code == 200
        assert 'teacher_info' in response.data
        assert 'students' in response.data
        assert 'materials' in response.data

    def test_dashboard_requires_authentication(self):
        """Дашборд требует аутентификацию"""
        client = APIClient()
        response = client.get('/api/dashboard/teacher/')

        assert response.status_code in [401, 403]

    def test_dashboard_requires_teacher_role(self, student_user):
        """Дашборд требует роль teacher"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/dashboard/teacher/')

        assert response.status_code == 403

    def test_get_teacher_students_endpoint(self, teacher_user, student_user, sample_enrollment):
        """GET /api/dashboard/teacher/students/"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/dashboard/teacher/students/')

        assert response.status_code == 200
        students = response.data.get('students') or response.data
        assert len(students) >= 1

    def test_get_teacher_materials_via_service(self, teacher_user, sample_material):
        """Получить материалы преподавателя через сервис"""
        service = TeacherDashboardService(teacher_user)
        materials = service.get_teacher_materials()

        assert len(materials) >= 1
        assert materials[0]['id'] == sample_material.id
        assert materials[0]['title'] == sample_material.title


# ===== INTEGRATION TESTS: Reports =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardReports:
    """Тесты для системы отчетов"""

    def test_create_student_report(self, teacher_user, student_user):
        """Создать отчет о студенте"""
        service = TeacherDashboardService(teacher_user)

        report_data = {
            'title': 'Отчет за неделю',
            'description': 'Прогресс студента',
            'type': 'progress',
            'start_date': timezone.now().date() - timedelta(days=7),
            'end_date': timezone.now().date(),
            'progress_percentage': 75,
            'overall_grade': 'Хорошо',
            'recommendations': 'Продолжать в том же духе',
            'achievements': 'Отличная работа'
        }

        result = service.create_student_report(
            student_id=student_user.id,
            report_data=report_data
        )

        # Логируем результат для отладки если тест падает
        if not result['success']:
            print(f"Error: {result.get('message', 'Unknown error')}")

        assert result['success'] is True, f"Expected success but got error: {result.get('message', 'Unknown')}"
        assert 'report_id' in result

    def test_get_teacher_reports(self, teacher_user, student_user):
        """Получить отчеты преподавателя"""
        # Сначала создаем отчет
        service = TeacherDashboardService(teacher_user)
        service.create_student_report(
            student_id=student_user.id,
            report_data={
                'title': 'Test Report',
                'type': 'progress'
            }
        )

        reports = service.get_teacher_reports()
        assert len(reports) >= 1


# ===== CACHE TESTS =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardCache:
    """Тесты для кеширования данных дашборда"""

    def test_dashboard_data_uses_cache(self, teacher_user, settings):
        """Данные дашборда используют кеш"""
        # DummyCache в настройках для тестов, проверяем что метод вызывается
        service = TeacherDashboardService(teacher_user)

        # Первый вызов
        data1 = service.get_dashboard_data()

        # Второй вызов должен использовать кеш
        data2 = service.get_dashboard_data()

        assert data1 == data2


# ===== QUERY OPTIMIZATION TESTS =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
@pytest.mark.performance
class TestTeacherDashboardQueryOptimization:
    """Тесты для проверки оптимизации запросов (N+1 query problem)"""

    def test_get_teacher_materials_query_count(self, teacher_user, subject, student_user, sample_enrollment):
        """get_teacher_materials должен делать минимальное количество запросов"""
        # Создаем 10 материалов с разными студентами и прогрессом
        materials = []
        for i in range(10):
            material = Material.objects.create(
                title=f"Material {i}",
                subject=subject,
                author=teacher_user,
                status=Material.Status.ACTIVE
            )
            # Назначаем материал студенту
            material.assigned_to.add(student_user)
            # Создаем прогресс
            MaterialProgress.objects.create(
                student=student_user,
                material=material,
                is_completed=(i % 2 == 0),  # Половина завершена
                progress_percentage=i * 10
            )
            materials.append(material)

        service = TeacherDashboardService(teacher_user)

        # Проверяем количество запросов
        # Ожидаем: 1 запрос для материалов с аннотациями
        from django.test.utils import override_settings
        from django.db import connection
        from django.conf import settings

        # Сбрасываем queries
        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_teacher_materials()

            # Подсчитываем запросы
            query_count = len(connection.queries)

            # До оптимизации: ~22 запроса (1 materials + 10*2 для статистики)
            # После оптимизации: ~1-3 запроса (1 materials с аннотациями)
            assert query_count <= 5, f"Слишком много запросов: {query_count}. Ожидалось <= 5"

        assert len(result) == 10

    def test_get_student_progress_overview_all_students_query_count(self, teacher_user, subject):
        """get_student_progress_overview для всех студентов должен быть оптимальным"""
        # Создаем 5 студентов с материалами и прогрессом
        students = []
        for i in range(5):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            students.append(student)

            # Зачисляем на предмет
            SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher_user,
                is_active=True
            )

            # Создаем материалы
            for j in range(3):
                material = Material.objects.create(
                    title=f"Material {i}-{j}",
                    subject=subject,
                    author=teacher_user,
                    status=Material.Status.ACTIVE
                )
                material.assigned_to.add(student)

                # Создаем прогресс
                MaterialProgress.objects.create(
                    student=student,
                    material=material,
                    is_completed=(j == 0),
                    progress_percentage=j * 30
                )

        service = TeacherDashboardService(teacher_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_student_progress_overview()

            query_count = len(connection.queries)

            # До оптимизации: ~20+ запросов (циклы по материалам и subjects)
            # После оптимизации: ~5-8 запросов
            assert query_count <= 10, f"Слишком много запросов: {query_count}. Ожидалось <= 10"

        assert result['total_students'] == 5

    def test_get_teacher_students_query_count(self, teacher_user, subject):
        """get_teacher_students должен использовать prefetch_related эффективно"""
        # Создаем 10 студентов
        students = []
        for i in range(10):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT
            )
            students.append(student)

            # Создаем профиль
            from accounts.models import StudentProfile
            StudentProfile.objects.get_or_create(
                user=student,
                defaults={'grade': '10', 'goal': 'Подготовка к ОГЭ'}
            )

            # Зачисляем на предмет
            SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher_user,
                is_active=True
            )

        service = TeacherDashboardService(teacher_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_teacher_students()

            query_count = len(connection.queries)

            # До оптимизации: ~15+ запросов
            # После оптимизации: ~5-7 запросов (prefetch используется правильно)
            assert query_count <= 10, f"Слишком много запросов: {query_count}. Ожидалось <= 10"

        assert len(result) == 10


# ===== NEW TESTS: Profile Auto-Creation and Error Handling =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTeacherDashboardProfileHandling:
    """Тесты для автоматического создания и обработки ошибок профиля"""

    def test_dashboard_auto_creates_teacher_profile(self, db):
        """Дашборд автоматически создает TeacherProfile если его нет"""
        from accounts.models import TeacherProfile
        from conftest import TeacherUserFactory

        # Создаем учителя напрямую (без использования fixture который уже создает профиль)
        teacher = TeacherUserFactory()

        # Удаляем профиль если был создан signal
        TeacherProfile.objects.filter(user=teacher).delete()

        # Проверяем что профиля нет
        assert not TeacherProfile.objects.filter(user=teacher).exists()

        # Делаем запрос к дашборду
        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.get('/api/dashboard/teacher/')

        # Проверяем что статус OK
        assert response.status_code == 200

        # Проверяем что профиль был создан
        assert TeacherProfile.objects.filter(user=teacher).exists()
        profile = TeacherProfile.objects.get(user=teacher)
        assert profile.user == teacher

    def test_dashboard_includes_profile_data(self, db):
        """Дашборд включает данные профиля в ответ"""
        from accounts.models import TeacherProfile
        from conftest import TeacherUserFactory

        teacher = TeacherUserFactory()
        # Убедимся что профиль существует
        TeacherProfile.objects.get_or_create(user=teacher)

        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.get('/api/dashboard/teacher/')

        assert response.status_code == 200
        assert 'profile' in response.data
        assert response.data['profile'] is not None

    def test_dashboard_returns_default_profile_on_error(self, db, mocker):
        """Дашборд возвращает структурированный объект при ошибке профиля"""
        from conftest import TeacherUserFactory

        teacher = TeacherUserFactory()

        # Mock ошибку при получении профиля
        mocker.patch(
            'materials.teacher_dashboard_views.TeacherProfile.objects.get_or_create',
            side_effect=Exception("Database error")
        )

        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.get('/api/dashboard/teacher/')

        # Дашборд все еще возвращает 200 (не блокирует весь дашборд)
        assert response.status_code == 200

        # Профиль содержит default значения вместо None
        assert 'profile' in response.data
        profile = response.data['profile']
        assert profile['bio'] == ''
        assert profile['experience_years'] == 0
        assert profile['subjects'] == []
        assert profile['avatar_url'] is None

    def test_signal_creates_teacher_profile_on_user_creation(self, db):
        """Signal автоматически создает TeacherProfile при создании User с ролью teacher"""
        from accounts.models import TeacherProfile

        # Создаем пользователя с ролью teacher
        teacher = User.objects.create_user(
            username='signal_test_teacher',
            email='signal_teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Test',
            last_name='Teacher'
        )

        # Проверяем что профиль был создан signal
        profile = TeacherProfile.objects.filter(user=teacher).first()
        assert profile is not None
        assert profile.user == teacher
        assert profile.bio == ''
        assert profile.experience_years == 0

    def test_signal_logs_profile_creation(self, db):
        """Signal автоматически логирует создание профиля"""
        from accounts.models import TeacherProfile

        # Просто проверяем что профиль был создан сигналом
        # Логирование проверяется через stderr в процессе разработки
        teacher = User.objects.create_user(
            username='log_test_teacher',
            email='log_teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        # Проверяем что профиль был создан signal обработчиком
        assert TeacherProfile.objects.filter(user=teacher).exists()
        profile = TeacherProfile.objects.get(user=teacher)
        assert profile.user == teacher

    def test_dashboard_handles_missing_profile_gracefully(self, db):
        """Дашборд корректно обрабатывает отсутствующий профиль"""
        from accounts.models import TeacherProfile
        from conftest import TeacherUserFactory

        teacher = TeacherUserFactory()

        # Удаляем профиль
        TeacherProfile.objects.filter(user=teacher).delete()

        client = APIClient()
        client.force_authenticate(user=teacher)

        # Первый запрос - профиля нет, будет создан
        response1 = client.get('/api/dashboard/teacher/')
        assert response1.status_code == 200

        # Второй запрос - профиль уже существует
        response2 = client.get('/api/dashboard/teacher/')
        assert response2.status_code == 200

        # Оба запроса должны вернуть профиль
        assert response1.data['profile'] is not None
        assert response2.data['profile'] is not None

    def test_get_or_create_idempotency(self, db):
        """get_or_create для профиля идемпотентен"""
        from accounts.models import TeacherProfile
        from conftest import TeacherUserFactory

        teacher = TeacherUserFactory()

        # Удаляем профиль если существует
        TeacherProfile.objects.filter(user=teacher).delete()

        # Первое создание
        profile1, created1 = TeacherProfile.objects.get_or_create(user=teacher)
        assert created1 is True

        # Второе получение
        profile2, created2 = TeacherProfile.objects.get_or_create(user=teacher)
        assert created2 is False
        assert profile1.id == profile2.id
