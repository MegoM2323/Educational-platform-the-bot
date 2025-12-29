#!/usr/bin/env python
"""
Создание тестовых учебных материалов для студентов
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from materials.models import Subject, Material

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает тестовые учебные материалы и назначает их студентам'

    def handle(self, *args, **options):
        self.stdout.write('\n=== Создание тестовых материалов ===')

        # Получаем тестовых пользователей
        teacher = User.objects.filter(email='teacher@test.com').first()
        student = User.objects.filter(email='student@test.com').first()

        if not teacher:
            self.stdout.write(self.style.ERROR('ERROR: teacher@test.com не найден!'))
            return

        if not student:
            self.stdout.write(self.style.ERROR('ERROR: student@test.com не найден!'))
            return

        # Получаем или создаем предметы
        subjects_data = [
            {'name': 'Математика', 'description': 'Алгебра и геометрия', 'color': '#3B82F6'},
            {'name': 'Физика', 'description': 'Механика, оптика, электричество', 'color': '#10B981'},
            {'name': 'Русский язык', 'description': 'Грамматика и правописание', 'color': '#EF4444'},
        ]

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
            status = 'создан' if created else 'существует'
            self.stdout.write(f'  ✓ {subject.name} - {status}')

        # Создаем тестовые материалы
        materials_data = [
            {
                'title': 'Введение в алгебру',
                'description': 'Основные понятия алгебры для начинающих',
                'content': 'Алгебра - это раздел математики, изучающий общие свойства операций...',
                'subject': 'Математика',
                'type': Material.Type.LESSON,
                'difficulty_level': 1,
                'tags': 'алгебра,основы,математика'
            },
            {
                'title': 'Уравнения первой степени',
                'description': 'Решение линейных уравнений',
                'content': 'Линейное уравнение имеет вид ax + b = 0, где a ≠ 0...',
                'subject': 'Математика',
                'type': Material.Type.LESSON,
                'difficulty_level': 2,
                'tags': 'уравнения,алгебра'
            },
            {
                'title': 'Тест по алгебре',
                'description': 'Проверка знаний по основам алгебры',
                'content': 'Тестовое задание для проверки усвоения материала',
                'subject': 'Математика',
                'type': Material.Type.TEST,
                'difficulty_level': 2,
                'tags': 'тест,проверка'
            },
            {
                'title': 'Основы физики',
                'description': 'Введение в мир физики',
                'content': 'Физика - наука о природе и её явлениях...',
                'subject': 'Физика',
                'type': Material.Type.PRESENTATION,
                'difficulty_level': 1,
                'tags': 'физика,основы'
            },
            {
                'title': 'Русский язык: Морфология',
                'description': 'Части речи и их грамматические признаки',
                'content': 'Морфология - раздел грамматики, изучающий части речи...',
                'subject': 'Русский язык',
                'type': Material.Type.DOCUMENT,
                'difficulty_level': 2,
                'tags': 'русский,морфология'
            },
        ]

        created_materials = []
        self.stdout.write('\n=== Создание материалов ===')

        for mat_data in materials_data:
            subject = subjects.get(mat_data['subject'])
            if not subject:
                self.stdout.write(self.style.WARNING(f'  ⚠ Предмет "{mat_data["subject"]}" не найден, пропускаем'))
                continue

            material, created = Material.objects.get_or_create(
                title=mat_data['title'],
                defaults={
                    'description': mat_data['description'],
                    'content': mat_data['content'],
                    'author': teacher,
                    'subject': subject,
                    'type': mat_data['type'],
                    'status': Material.Status.ACTIVE,
                    'difficulty_level': mat_data['difficulty_level'],
                    'tags': mat_data['tags'],
                    'is_public': False,
                }
            )

            if created:
                material.published_at = timezone.now()
                material.save()
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Создан: "{material.title}" ({material.get_type_display()})')
                )
                created_materials.append(material)
            else:
                self.stdout.write(f'  ♻ Существует: "{material.title}"')

        # Назначаем материалы студенту
        self.stdout.write('\n=== Назначение материалов студентам ===')
        assigned_count = 0

        for material in created_materials:
            if student not in material.assigned_to.all():
                material.assigned_to.add(student)
                assigned_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Материал "{material.title}" назначен студенту {student.email}'
                    )
                )

        # Итоговый отчет
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('✅ ТЕСТОВЫЕ МАТЕРИАЛЫ СОЗДАНЫ!'))
        self.stdout.write('='*80)
        self.stdout.write(f'  • Создано материалов: {len(created_materials)}')
        self.stdout.write(f'  • Назначено студентам: {assigned_count}')
        self.stdout.write(f'  • Студент: {student.get_full_name()} ({student.email})')
        self.stdout.write('='*80 + '\n')
