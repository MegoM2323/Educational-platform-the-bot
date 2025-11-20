import pytest
from django.contrib.auth import get_user_model

from accounts.tutor_service import StudentCreationService, SubjectAssignmentService
from materials.models import Subject, SubjectEnrollment


User = get_user_model()


@pytest.mark.django_db
def test_student_creation_service_creates_users_and_profiles():
    tutor = User.objects.create(username='tutor1', role=User.Role.TUTOR)

    student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
        tutor=tutor,
        student_first_name='Ivan',
        student_last_name='Petrov',
        grade='7',
        goal='Math improvement',
        parent_first_name='Olga',
        parent_last_name='Petrova',
        parent_email='olga@example.com',
        parent_phone='+79990000000',
    )

    assert student_user.role == User.Role.STUDENT
    assert parent_user.role == User.Role.PARENT
    assert student_user.student_profile.tutor_id == tutor.id
    assert student_user.student_profile.parent_id == parent_user.id
    assert student_user.username == student_creds.username
    assert parent_user.username == parent_creds.username
    # Пароли сгенерированы и сохранены в профиле
    assert student_user.student_profile.generated_username
    assert student_user.student_profile.generated_password


@pytest.mark.django_db
def test_subject_assignment_service_assign_and_unassign():
    tutor = User.objects.create(username='tutor1', role=User.Role.TUTOR)
    teacher = User.objects.create(username='teacher1', role=User.Role.TEACHER)
    student = User.objects.create(username='student1', role=User.Role.STUDENT)

    # Привяжем профиль студента к тьютору для валидации
    from accounts.models import StudentProfile
    StudentProfile.objects.create(user=student, grade='7', goal='', tutor=tutor)

    subject = Subject.objects.create(name='Mathematics', description='Algebra', color='#ff0000')

    enrollment = SubjectAssignmentService.assign_subject(
        tutor=tutor,
        student=student,
        subject=subject,
        teacher=teacher,
    )

    assert isinstance(enrollment, SubjectEnrollment)
    assert enrollment.teacher_id == teacher.id
    assert enrollment.assigned_by_id == tutor.id
    assert enrollment.is_active is True

    # Unassign
    SubjectAssignmentService.unassign_subject(tutor=tutor, student=student, subject=subject)
    enrollment.refresh_from_db()
    assert enrollment.is_active is False


