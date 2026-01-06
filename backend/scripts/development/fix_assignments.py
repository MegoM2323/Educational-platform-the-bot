#!/usr/bin/env python
"""
Скрипт для исправления метода create_assignments в create_full_test_dataset.py
"""

# Читаем файл
with open('core/management/commands/create_full_test_dataset.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим и заменяем весь метод create_assignments
old_method_start = "    def create_assignments(self, enrollments):"
old_method_end = "        self.stdout.write(f'    ✓ Создано {len(assignments)} заданий')"

# Новая реализация метода
new_method = '''    def create_assignments(self, enrollments):
        """Создание заданий от преподавателей (через enrollment)"""
        from assignments.models import Assignment
        from django.utils import timezone
        from datetime import timedelta
        import random
        from decimal import Decimal

        assignments = []
        assignment_titles = [
            "Домашнее задание №1",
            "Контрольная работа",
            "Практическая работа",
            "Эссе по теме",
            "Итоговый тест",
        ]

        assignment_types = [
            Assignment.Type.HOMEWORK,
            Assignment.Type.TEST,
            Assignment.Type.PROJECT,
            Assignment.Type.ESSAY,
        ]

        for enrollment in enrollments:
            # Преподаватель - автор задания
            teacher = enrollment.teacher
            student = enrollment.student

            # Создаем 2 задания на каждый enrollment
            for i in range(2):
                title = random.choice(assignment_titles)
                assignment_type = random.choice(assignment_types)

                # Дата начала - неделю назад
                start_date = timezone.now() - timedelta(days=7)
                # Срок сдачи - через неделю
                due_date = timezone.now() + timedelta(days=7)

                try:
                    assignment = Assignment.objects.create(
                        author=teacher,  # ✅ Преподаватель - автор
                        title=f"{title} - {enrollment.subject.name}",
                        description=f"Описание задания '{title}' по предмету {enrollment.subject.name}",
                        instructions=f"Инструкции для выполнения задания",
                        type=assignment_type,
                        status=Assignment.Status.PUBLISHED,
                        max_score=100,
                        start_date=start_date,
                        due_date=due_date,  # ✅ Правильное поле
                        difficulty_level=random.randint(1, 3),
                    )

                    # Назначаем задание студенту через M2M
                    assignment.assigned_to.add(student)

                    assignments.append(assignment)

                    if self.verbosity >= 2:
                        self.stdout.write(f'      Задание: {assignment.title} → {student.get_full_name()}')

                except Exception as e:
                    if self.verbosity >= 1:
                        self.stderr.write(f'    ✗ Assignment error: {str(e)}')

        self.stdout.write(f'    ✓ Создано {len(assignments)} заданий')'''

# Находим начало и конец старого метода
start_idx = content.find(old_method_start)
if start_idx == -1:
    print("❌ Не найден метод create_assignments!")
    exit(1)

# Находим конец метода (следующий метод или конец класса)
end_marker = "        self.stdout.write(f'    ✓ Создано {len(assignments)} заданий')"
end_idx = content.find(end_marker, start_idx)

if end_idx == -1:
    print("❌ Не найден конец метода!")
    exit(1)

# Находим конец строки
end_idx = content.find('\n', end_idx) + 1

# Заменяем метод
new_content = content[:start_idx] + new_method + '\n' + content[end_idx:]

# Сохраняем
with open('core/management/commands/create_full_test_dataset.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Метод create_assignments исправлен!")
print("Применены изменения:")
print("  1. author=teacher (вместо teacher=)")
print("  2. due_date (вместо deadline)")
print("  3. assigned_to.add(student) для назначения студенту")
print("  4. Добавлены start_date и instructions")
