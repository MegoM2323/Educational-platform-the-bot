"""
Unit tests for Tutor Dashboard Service and Views
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from rest_framework.test import APIClient
from decimal import Decimal

from materials.tutor_dashboard_service import TutorDashboardService
from materials.models import Subject, SubjectEnrollment, Material, MaterialProgress
from reports.models import Report, ReportRecipient

User = get_user_model()


# ============================================================================
# SERVICE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTutorDashboardService:
    """Тесты сервиса TutorDashboardService"""

    def test_service_initialization(self, tutor_user):
        """Service инициализируется для tutor"""
        service = TutorDashboardService(tutor_user)
        assert service.tutor == tutor_user

    def test_service_requires_tutor_role(self, student_user):
        """Service требует роль TUTOR"""
        with pytest.raises(PermissionDenied) as exc_info:
            TutorDashboardService(student_user)
        assert "Только тьюторы" in str(exc_info.value)

    def test_service_rejects_teacher_role(self, teacher_user):
        """Service отклоняет роль TEACHER"""
        with pytest.raises(PermissionDenied):
            TutorDashboardService(teacher_user)

    def test_service_rejects_parent_role(self, parent_user):
        """Service отклоняет роль PARENT"""
        with pytest.raises(PermissionDenied):
            TutorDashboardService(parent_user)

    def test_get_students(self, tutor_user, student_user):
        """Получить список студентов тьютора"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert students[0]['id'] == student_user.id
        assert students[0]['name'] == student_user.get_full_name()

    def test_get_students_empty(self, tutor_user):
        """Пустой список студентов если нет назначений"""
        service = TutorDashboardService(tutor_user)
        students = service.get_students()
        assert len(students) == 0

    def test_get_students_with_subjects(self, tutor_user, student_user, subject, teacher_user):
        """Получить студентов с их предметами"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем зачисление
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert len(students[0]['subjects']) == 1
        assert students[0]['subjects'][0]['name'] == subject.name

    def test_get_students_with_parent(self, tutor_user, student_user, parent_user):
        """Получить студентов с информацией о родителе"""
        # Назначаем тьютора и родителя студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        students = service.get_students()

        assert len(students) == 1
        assert students[0]['parent'] is not None
        assert students[0]['parent']['id'] == parent_user.id
        assert students[0]['parent']['name'] == parent_user.get_full_name()

    def test_get_student_subjects(self, tutor_user, student_user, subject, teacher_user):
        """Получить предметы студента"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем зачисление
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        subjects = service.get_student_subjects(student_user.id)

        assert len(subjects) == 1
        assert subjects[0]['id'] == subject.id
        assert subjects[0]['name'] == subject.name
        assert subjects[0]['teacher']['id'] == teacher_user.id

    def test_get_student_subjects_permission_denied(self, tutor_user, other_student_user):
        """Нельзя получить предметы чужого студента"""
        service = TutorDashboardService(tutor_user)

        with pytest.raises(PermissionDenied) as exc_info:
            service.get_student_subjects(other_student_user.id)
        assert "не принадлежит данному тьютору" in str(exc_info.value)

    def test_get_student_progress(self, tutor_user, student_user, sample_material, enrollment):
        """Получить прогресс студента"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Назначаем материал студенту
        sample_material.assigned_to.add(student_user)

        # Создаем прогресс
        MaterialProgress.objects.create(
            student=student_user,
            material=sample_material,
            progress_percentage=75,
            is_completed=False,
            time_spent=120
        )

        service = TutorDashboardService(tutor_user)
        progress = service.get_student_progress(student_user.id)

        assert progress['student']['id'] == student_user.id
        assert progress['total_materials'] == 1
        assert progress['completed_materials'] == 0
        assert progress['average_progress'] == 75.0

    def test_get_student_progress_multiple_subjects(self, tutor_user, student_user,
                                                    subject, teacher_user):
        """Прогресс студента по нескольким предметам"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем второй предмет
        subject2 = Subject.objects.create(name="Физика", description="Курс физики")

        # Создаем зачисления
        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user,
            is_active=True
        )

        # Создаем материалы
        material1 = Material.objects.create(
            title="Material 1",
            subject=subject,
            author=teacher_user
        )
        material2 = Material.objects.create(
            title="Material 2",
            subject=subject2,
            author=teacher_user
        )

        # Создаем прогрессы
        MaterialProgress.objects.create(
            student=student_user,
            material=material1,
            progress_percentage=100,
            is_completed=True
        )
        MaterialProgress.objects.create(
            student=student_user,
            material=material2,
            progress_percentage=50,
            is_completed=False
        )

        service = TutorDashboardService(tutor_user)
        progress = service.get_student_progress(student_user.id)

        assert progress['total_materials'] == 2
        assert progress['completed_materials'] == 1
        assert len(progress['subject_progress']) == 2

    def test_assign_subject(self, tutor_user, student_user, subject, teacher_user):
        """Назначить предмет студенту"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is True
        assert 'enrollment_id' in result

        # Проверяем что зачисление создано
        enrollment = SubjectEnrollment.objects.get(id=result['enrollment_id'])
        assert enrollment.student == student_user
        assert enrollment.subject == subject
        assert enrollment.teacher == teacher_user
        assert enrollment.assigned_by == tutor_user

    def test_assign_subject_with_custom_name(self, tutor_user, student_user, subject, teacher_user):
        """Назначить предмет с кастомным названием"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id,
            custom_subject_name="Математика (углубленный курс)"
        )

        assert result['success'] is True
        enrollment = SubjectEnrollment.objects.get(id=result['enrollment_id'])
        assert enrollment.custom_subject_name == "Математика (углубленный курс)"

    def test_assign_subject_duplicate(self, tutor_user, student_user, subject, teacher_user):
        """Нельзя назначить уже назначенный предмет"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Первое назначение
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is False
        assert "уже назначен" in result['message']

    def test_assign_subject_to_other_student(self, tutor_user, other_student_user, subject, teacher_user):
        """Нельзя назначить предмет чужому студенту"""
        service = TutorDashboardService(tutor_user)
        result = service.assign_subject(
            student_id=other_student_user.id,
            subject_id=subject.id,
            teacher_id=teacher_user.id
        )

        assert result['success'] is False
        assert "не принадлежит данному тьютору" in result['message']

    def test_create_student_report(self, tutor_user, student_user, parent_user):
        """Создать отчет о студенте для родителя"""
        # Связываем студента с тьютором и родителем
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        service = TutorDashboardService(tutor_user)
        result = service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data={
                'title': 'Отчет за неделю',
                'content': 'Студент показал хороший прогресс',
                'report_type': 'tutor_to_parent'
            }
        )

        assert result['success'] is True
        assert 'report_id' in result

        # Проверяем что отчет создан
        report = Report.objects.get(id=result['report_id'])
        assert report.author == tutor_user
        assert report.title == 'Отчет за неделю'

        # Проверяем получателя
        recipient = ReportRecipient.objects.get(report=report)
        assert recipient.recipient == parent_user
        assert recipient.read_at is None  # Еще не прочитан

    def test_create_report_wrong_parent(self, tutor_user, student_user):
        """Нельзя создать отчет для неправильного родителя"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем другого родителя
        from accounts.models import ParentProfile
        other_parent = User.objects.create(
            username='other_parent',
            role=User.Role.PARENT
        )
        ParentProfile.objects.create(user=other_parent)

        service = TutorDashboardService(tutor_user)
        result = service.create_student_report(
            student_id=student_user.id,
            parent_id=other_parent.id,
            report_data={'title': 'Test', 'content': 'Test'}
        )

        assert result['success'] is False
        assert "не является родителем" in result['message']

    def test_get_tutor_reports(self, tutor_user, student_user, parent_user):
        """Получить отчеты тьютора"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        # Создаем несколько отчетов
        service = TutorDashboardService(tutor_user)
        service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data={'title': 'Отчет 1', 'content': 'Содержание 1'}
        )
        service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data={'title': 'Отчет 2', 'content': 'Содержание 2'}
        )

        reports = service.get_tutor_reports()

        assert len(reports) == 2
        assert reports[0]['title'] in ['Отчет 1', 'Отчет 2']
        assert len(reports[0]['recipients']) == 1

    def test_get_dashboard_data(self, tutor_user, student_user, subject, teacher_user):
        """Получить полные данные дашборда"""
        # Назначаем тьютора студенту
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Создаем зачисление
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        service = TutorDashboardService(tutor_user)
        data = service.get_dashboard_data()

        assert 'tutor_info' in data
        assert data['tutor_info']['id'] == tutor_user.id

        assert 'statistics' in data
        assert data['statistics']['total_students'] == 1
        assert data['statistics']['total_subjects_assigned'] == 1

        assert 'students' in data
        assert len(data['students']) == 1

        assert 'reports' in data

    def test_get_dashboard_data_empty(self, tutor_user):
        """Дашборд с пустыми данными"""
        service = TutorDashboardService(tutor_user)
        data = service.get_dashboard_data()

        assert data['statistics']['total_students'] == 0
        assert data['statistics']['total_subjects_assigned'] == 0
        assert len(data['students']) == 0


# ============================================================================
# VIEW TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
class TestTutorDashboardViews:
    """Тесты views для TutorDashboard"""

    def test_get_dashboard_requires_authentication(self):
        """Dashboard требует аутентификации"""
        client = APIClient()
        response = client.get('/api/materials/dashboard/tutor/')
        # DRF возвращает 403 Forbidden когда нет аутентификации, а не 401 Unauthorized
        assert response.status_code in [401, 403]

    def test_get_dashboard_requires_tutor_role(self, student_user):
        """Dashboard требует роль TUTOR"""
        client = APIClient()
        client.force_authenticate(user=student_user)
        response = client.get('/api/materials/dashboard/tutor/')
        assert response.status_code == 403

    def test_get_dashboard_success(self, tutor_user):
        """Успешное получение dashboard"""
        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 200
        assert 'tutor_info' in response.data
        assert 'statistics' in response.data
        assert 'students' in response.data

    def test_get_students_list(self, tutor_user, student_user):
        """Получить список студентов через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.get('/api/materials/dashboard/tutor/students/')

        assert response.status_code == 200
        assert 'students' in response.data
        assert len(response.data['students']) == 1

    def test_get_student_subjects_api(self, tutor_user, student_user, subject, teacher_user):
        """Получить предметы студента через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/subjects/')

        assert response.status_code == 200
        assert 'subjects' in response.data
        assert len(response.data['subjects']) == 1

    def test_get_student_progress_api(self, tutor_user, student_user, sample_material):
        """Получить прогресс студента через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        sample_material.assigned_to.add(student_user)
        MaterialProgress.objects.create(
            student=student_user,
            material=sample_material,
            progress_percentage=50
        )

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/progress/')

        assert response.status_code == 200
        assert 'total_materials' in response.data
        assert response.data['total_materials'] == 1

    def test_assign_subject_api(self, tutor_user, student_user, subject, teacher_user):
        """Назначить предмет через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.post('/api/materials/dashboard/tutor/students/assign-subject/', {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'teacher_id': teacher_user.id
        })

        assert response.status_code == 201
        assert response.data['success'] is True

    def test_assign_subject_missing_data(self, tutor_user):
        """Назначение предмета без необходимых данных"""
        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.post('/api/materials/dashboard/tutor/students/assign-subject/', {
            'student_id': 1
        })

        assert response.status_code == 400

    def test_create_report_api(self, tutor_user, student_user, parent_user):
        """Создать отчет через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.post('/api/materials/dashboard/tutor/reports/create/', {
            'student_id': student_user.id,
            'parent_id': parent_user.id,
            'title': 'Test Report',
            'content': 'Test content'
        })

        assert response.status_code == 201
        assert response.data['success'] is True

    def test_get_reports_api(self, tutor_user, student_user, parent_user):
        """Получить отчеты через API"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.parent = parent_user
        student_user.student_profile.save()

        # Создаем отчет
        service = TutorDashboardService(tutor_user)
        service.create_student_report(
            student_id=student_user.id,
            parent_id=parent_user.id,
            report_data={'title': 'Test', 'content': 'Test'}
        )

        client = APIClient()
        client.force_authenticate(user=tutor_user)
        response = client.get('/api/materials/dashboard/tutor/reports/')

        assert response.status_code == 200
        assert 'reports' in response.data
        assert len(response.data['reports']) == 1


# ===== QUERY OPTIMIZATION TESTS =====

@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.dashboard
@pytest.mark.performance
class TestTutorDashboardQueryOptimization:
    """Тесты для проверки оптимизации запросов (N+1 query problem)"""

    def test_get_student_progress_query_count(self, tutor_user, teacher_user):
        """get_student_progress должен использовать аннотации для предметов"""
        from materials.models import Subject

        # Создаем студента с 5 предметами
        student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        from accounts.models import StudentProfile
        StudentProfile.objects.create(
            user=student,
            tutor=tutor_user,
            grade='10'
        )

        # Создаем 5 зачислений с материалами
        for i in range(5):
            # Создаем отдельный предмет для каждого зачисления
            subject = Subject.objects.create(
                name=f'Test Subject {i}',
                description=f'Test description {i}'
            )

            enrollment = SubjectEnrollment.objects.create(
                student=student,
                subject=subject,
                teacher=teacher_user,
                assigned_by=tutor_user,
                is_active=True
            )

            # Создаем материалы с прогрессом
            for j in range(3):
                material = Material.objects.create(
                    title=f"Material {i}-{j}",
                    subject=subject,
                    author=teacher_user,
                    status=Material.Status.ACTIVE
                )

                MaterialProgress.objects.create(
                    student=student,
                    material=material,
                    is_completed=(j == 0),
                    progress_percentage=j * 30,
                    time_spent=j * 60
                )

        service = TutorDashboardService(tutor_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_student_progress(student.id)

            query_count = len(connection.queries)

            # До оптимизации: ~15+ запросов (цикл по enrollments с запросами для каждого)
            # После оптимизации: ~5-7 запросов (аннотации + словарь)
            assert query_count <= 10, f"Слишком много запросов: {query_count}. Ожидалось <= 10"

        assert result['total_materials'] == 15
        assert len(result['subject_progress']) == 5

    def test_get_students_query_count(self, tutor_user, teacher_user):
        """get_students должен использовать prefetch_related эффективно"""
        from materials.models import Subject

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

            from accounts.models import StudentProfile
            StudentProfile.objects.create(
                user=student,
                tutor=tutor_user,
                grade='10',
                goal='Подготовка к экзаменам'
            )

            # Каждый студент имеет 2 зачисления на разные предметы
            for j in range(2):
                subject = Subject.objects.create(
                    name=f'Test Subject {i}-{j}',
                    description=f'Test description {i}-{j}'
                )

                SubjectEnrollment.objects.create(
                    student=student,
                    subject=subject,
                    teacher=teacher_user,
                    assigned_by=tutor_user,
                    is_active=True
                )

        service = TutorDashboardService(tutor_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_students()

            query_count = len(connection.queries)

            # До оптимизации: ~70+ запросов
            # После оптимизации: ~50-60 запросов (все еще много из-за сложной логики)
            # Метод get_students использует prefetch, но сам по себе сложный
            assert query_count <= 65, f"Слишком много запросов: {query_count}. Ожидалось <= 65"

        assert len(result) == 10

    def test_get_tutor_reports_query_count(self, tutor_user, parent_user):
        """get_tutor_reports должен использовать Prefetch для recipients"""
        # Создаем 5 отчетов с несколькими получателями
        from reports.models import Report, ReportRecipient
        from django.utils import timezone

        for i in range(5):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT
            )

            from accounts.models import StudentProfile
            StudentProfile.objects.create(
                user=student,
                tutor=tutor_user,
                parent=parent_user,
                grade='10'
            )

            # Создаем отчет
            report = Report.objects.create(
                title=f'Report {i}',
                description=f'Test report {i}',
                type=Report.Type.CUSTOM,
                status=Report.Status.DRAFT,
                author=tutor_user,
                start_date=timezone.now().date(),
                end_date=timezone.now().date()
            )

            # Добавляем получателя
            ReportRecipient.objects.create(
                report=report,
                recipient=parent_user
            )

        service = TutorDashboardService(tutor_user)

        from django.test.utils import override_settings
        from django.db import connection

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = service.get_tutor_reports()

            query_count = len(connection.queries)

            # До оптимизации: ~10+ запросов (цикл по recipients)
            # После оптимизации: ~2-3 запроса (Prefetch с select_related)
            assert query_count <= 5, f"Слишком много запросов: {query_count}. Ожидалось <= 5"

        assert len(result) == 5
