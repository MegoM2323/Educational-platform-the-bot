#!/usr/bin/env python
"""
Создание тестовых предметов и связей преподавателей с предметами
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment, TeacherSubject

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает тестовые предметы и назначает их преподавателям'

    def handle(self, *args, **options):
        # Создаем предметы
        subjects_data = [
            {'name': 'Математика', 'description': 'Алгебра и геометрия', 'color': '#3B82F6'},
            {'name': 'Физика', 'description': 'Механика, оптика, электричество', 'color': '#10B981'},
            {'name': 'Химия', 'description': 'Органическая и неорганическая химия', 'color': '#F59E0B'},
            {'name': 'Биология', 'description': 'Анатомия, ботаника, зоология', 'color': '#06B6D4'},
            {'name': 'История', 'description': 'История России и мира', 'color': '#8B5CF6'},
            {'name': 'География', 'description': 'Физическая и экономическая география', 'color': '#14B8A6'},
            {'name': 'Литература', 'description': 'Русская и зарубежная литература', 'color': '#EC4899'},
            {'name': 'Русский язык', 'description': 'Грамматика и правописание', 'color': '#EF4444'},
            {'name': 'Английский язык', 'description': 'Grammar, reading, writing', 'color': '#F97316'},
            {'name': 'Информатика', 'description': 'Программирование и информационные технологии', 'color': '#6366F1'},
        ]

        self.stdout.write('\n=== Создание предметов ===')
        subjects = {}
        
        for subj_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subj_data['name'],
                defaults={
                    'description': subj_data['description'],
                    'color': subj_data['color']
                }
            )
            subjects[subj_data['name']] = subject
            status = 'создан' if created else 'уже существует'
            self.stdout.write(f'  {subject.name} - {status}')

        # Получаем или создаем преподавателей
        self.stdout.write('\n=== Работа с преподавателями ===')
        
        teacher_subjects = {
            'Математика': ['Математика'],
            'Физика': ['Физика'],
            'Химия': ['Химия'],
            'Биология': ['Биология'],
            'История': ['История'],
            'География': ['География'],
            'Литература': ['Литература', 'Русский язык'],
            'Русский язык': ['Русский язык', 'Литература'],
            'Английский язык': ['Английский язык'],
            'Информатика': ['Информатика'],
        }

        for subject_name, teacher_subjects_list in teacher_subjects.items():
            # Создаем преподавателя для каждого предмета
            teacher_email = f'teacher_{subject_name.lower().replace(" ", "_")}@example.com'
            teacher_username = f'teacher_{subject_name.lower().replace(" ", "_")}'
            
            teacher, created = User.objects.get_or_create(
                email=teacher_email,
                defaults={
                    'username': teacher_username,
                    'first_name': f'Преподаватель',
                    'last_name': subject_name,
                    'role': User.Role.TEACHER,
                    'is_verified': True
                }
            )
            
            if created:
                teacher.set_password('testpass123')
                teacher.save()
                self.stdout.write(f'  Создан преподаватель: {teacher.get_full_name()}')
            else:
                self.stdout.write(f'  Преподаватель уже существует: {teacher.get_full_name()}')
            
            # Связываем преподавателя с предметами через модель TeacherSubject
            for subj_name in teacher_subjects_list:
                if subj_name in subjects:
                    # Создаем связь преподаватель-предмет
                    teacher_subject, created = TeacherSubject.objects.get_or_create(
                        teacher=teacher,
                        subject=subjects[subj_name],
                        defaults={'is_active': True}
                    )
                    
                    if created:
                        self.stdout.write(f'    Назначен предмет "{subj_name}" преподавателю {teacher.get_full_name()}')
                    else:
                        self.stdout.write(f'    Предмет "{subj_name}" уже назначен преподавателю {teacher.get_full_name()}')

        self.stdout.write('\n=== Предметы готовы к назначению ===')
        self.stdout.write('Теперь можно назначать эти предметы студентам!')

