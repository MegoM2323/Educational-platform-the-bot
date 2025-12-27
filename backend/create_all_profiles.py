#!/usr/bin/env python
"""Создание профилей для всех тестовых пользователей"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User, TeacherProfile, TutorProfile, ParentProfile, StudentProfile
from materials.models import Subject

# Teacher profile
print("\n=== Creating Teacher Profile ===")
teacher_user = User.objects.get(email='test_teacher@example.com')
tp, created = TeacherProfile.objects.get_or_create(
    user=teacher_user,
    defaults={
        'subject': 'Математика',
        'bio': 'Тестовый учитель',
        'experience_years': 5
    }
)
print(f'Teacher Profile: {"Created" if created else "Already exists"} - ID: {tp.id}')

# Tutor profile
print("\n=== Creating Tutor Profile ===")
tutor_user = User.objects.get(email='test_tutor@example.com')
tutor_profile, created = TutorProfile.objects.get_or_create(
    user=tutor_user,
    defaults={
        'bio': 'Тестовый тьютор'
    }
)
print(f'Tutor Profile: {"Created" if created else "Already exists"} - ID: {tutor_profile.id}')

# Parent profile
print("\n=== Creating Parent Profile ===")
parent_user = User.objects.get(email='test_parent@example.com')
parent_profile, created = ParentProfile.objects.get_or_create(
    user=parent_user,
    defaults={}
)
print(f'Parent Profile: {"Created" if created else "Already exists"} - ID: {parent_profile.id}')

# Student profile (должен уже существовать, но проверим)
print("\n=== Checking Student Profile ===")
student_user = User.objects.get(email='test_student@example.com')
if hasattr(student_user, 'student_profile'):
    print(f'Student Profile: Already exists - ID: {student_user.student_profile.id}')
    print(f'Student tutor: {student_user.student_profile.tutor}')
else:
    # Создадим профиль студента с тьютором
    sp = StudentProfile.objects.create(
        user=student_user,
        grade='7',
        goal='Тестовая цель',
        tutor=tutor_profile
    )
    print(f'Student Profile: Created - ID: {sp.id}')
    print(f'Student tutor: {sp.tutor}')

print("\n=== All Profiles Created/Verified ===")

