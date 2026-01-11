"""
Создает тестовые данные для проверки Chat API
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment
from accounts.models import StudentProfile

User = get_user_model()

# Удалить старые тестовые пользователи
User.objects.filter(username__startswith='test_').delete()

print("=" * 60)
print("CREATING TEST DATA FOR CHAT API")
print("=" * 60)

# 1. Создать Subject
subject, _ = Subject.objects.get_or_create(
    name='Mathematics',
    defaults={'name': 'Mathematics'}
)
print(f"\n✓ Subject created: {subject.name} (ID: {subject.id})")

# 2. Создать учителя
teacher, created = User.objects.get_or_create(
    username='test_teacher_001',
    defaults={
        'email': 'teacher@test.com',
        'first_name': 'John',
        'last_name': 'Teacher',
        'role': 'teacher',
        'is_active': True,
    }
)
print(f"✓ Teacher created: {teacher.username} (ID: {teacher.id})")

# 3. Создать студента
student, created = User.objects.get_or_create(
    username='test_student_001',
    defaults={
        'email': 'student@test.com',
        'first_name': 'Jane',
        'last_name': 'Student',
        'role': 'student',
        'is_active': True,
    }
)
print(f"✓ Student created: {student.username} (ID: {student.id})")

# 4. Создать SubjectEnrollment (связь между студентом и учителем)
enrollment, created = SubjectEnrollment.objects.get_or_create(
    student=student,
    teacher=teacher,
    subject=subject,
    defaults={'status': 'active'}
)
print(f"✓ SubjectEnrollment created: {student.username} -> {teacher.username} for {subject.name}")
print(f"  Status: {enrollment.status}")

# 5. Создать другого учителя
teacher2, created = User.objects.get_or_create(
    username='test_teacher_002',
    defaults={
        'email': 'teacher2@test.com',
        'first_name': 'Bob',
        'last_name': 'Tutor',
        'role': 'teacher',
        'is_active': True,
    }
)
print(f"✓ Second teacher created: {teacher2.username} (ID: {teacher2.id})")

# 6. Создать второго студента
student2, created = User.objects.get_or_create(
    username='test_student_002',
    defaults={
        'email': 'student2@test.com',
        'first_name': 'Mike',
        'last_name': 'Johnson',
        'role': 'student',
        'is_active': True,
    }
)
print(f"✓ Second student created: {student2.username} (ID: {student2.id})")

# 7. Создать второе SubjectEnrollment
enrollment2, created = SubjectEnrollment.objects.get_or_create(
    student=student2,
    teacher=teacher2,
    subject=subject,
    defaults={'status': 'active'}
)
print(f"✓ Second SubjectEnrollment created")

# 8. Создать тьютора
tutor, created = User.objects.get_or_create(
    username='test_tutor_001',
    defaults={
        'email': 'tutor@test.com',
        'first_name': 'Alex',
        'last_name': 'Tutor',
        'role': 'tutor',
        'is_active': True,
    }
)
print(f"✓ Tutor created: {tutor.username} (ID: {tutor.id})")

# 9. Привязать студента к тьютору
student_profile, _ = StudentProfile.objects.get_or_create(
    user=student,
    defaults={'tutor': tutor}
)
print(f"✓ Student {student.username} assigned to tutor {tutor.username}")

print("\n" + "=" * 60)
print("TEST DATA CREATED SUCCESSFULLY")
print("=" * 60)
print("\nYou can now test:")
print(f"1. Chat between student ({student.id}) and teacher ({teacher.id})")
print(f"2. Chat between student ({student2.id}) and teacher ({teacher2.id})")
print(f"3. Chat between student ({student.id}) and tutor ({tutor.id})")
