#!/usr/bin/env python
"""
Скрипт для автоматического исправления ошибок в create_full_test_dataset.py
"""

# Читаем файл
with open('core/management/commands/create_full_test_dataset.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ИСПРАВЛЕНИЕ 1: SubjectEnrollment - заменяем .student_profile на прямое использование User
content = content.replace(
    'student=student1.student_profile,',
    'student=student1,'
)
content = content.replace(
    'student=student2.student_profile,',
    'student=student2,'
)
content = content.replace(
    'teacher=teacher1.teacher_profile,',
    'teacher=teacher1,'
)
content = content.replace(
    'teacher=teacher2.teacher_profile,',
    'teacher=teacher2,'
)

# Заменяем TeacherSubject
content = content.replace(
    'teacher=teacher1.teacher_profile,',
    'teacher=teacher1,'
)
content = content.replace(
    'teacher=teacher2.teacher_profile,',
    'teacher=teacher2,'
)

# ИСПРАВЛЕНИЕ 2: ChatRoom - добавляем created_by
content = content.replace(
    'room = ChatRoom.objects.create()',
    'room = ChatRoom.objects.create(created_by=user1, name=f"Chat: {user1.get_full_name()} - {user2.get_full_name()}", type="direct")'
)

# ИСПРАВЛЕНИЕ 3: Notification - меняем user на recipient
content = content.replace(
    'user=user,',
    'recipient=user,'
)

# ИСПРАВЛЕНИЕ 4: Notification - меняем notification_type на type
content = content.replace(
    'notification_type=notif_type,',
    'type=notif_type,'
)

# ИСПРАВЛЕНИЕ 5: Message - убираем timestamp, используем created_at
content = content.replace(
    'timestamp=timezone.now()',
    'created_at=timezone.now()'
)

# Сохраняем
with open('core/management/commands/create_full_test_dataset.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Файл успешно исправлен!")
print("Применены исправления:")
print("  1. SubjectEnrollment: student/teacher теперь User объекты")
print("  2. ChatRoom: добавлен created_by")
print("  3. Notification: user → recipient")
print("  4. Notification: notification_type → type")
print("  5. Message: timestamp → created_at")
