#!/usr/bin/env python
"""Создание TeacherProfile для test_teacher"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User, TeacherProfile
from materials.models import Subject

u = User.objects.get(email='test_teacher@example.com')
tp, created = TeacherProfile.objects.get_or_create(
    user=u,
    defaults={
        'subject': 'Математика',
        'bio': 'Тестовый учитель',
        'experience_years': 5
    }
)

if created:
    print(f'Created TeacherProfile: {tp}')
else:
    print(f'TeacherProfile already exists: {tp}')

print(f'Profile ID: {tp.id}')

# У TeacherProfile subject - это CharField, а не ManyToManyField
print(f'Teacher subject: {tp.subject}')

