"""
Прямой тест создания студента через Django ORM
"""
import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, ParentProfile
from accounts.tutor_service import StudentCreationService

User = get_user_model()


def main():
    print("=== Тест создания ученика и родителя ===\n")
    
    # Получаем или создаем тьютора
    tutor = User.objects.filter(role=User.Role.TUTOR).first()
    if not tutor:
        tutor = User.objects.create_user(
            username='test_tutor_direct',
            email='test_tutor_direct@example.com',
            password='testpass123',
            role=User.Role.TUTOR,
            first_name='Тест',
            last_name='Тьютор'
        )
        print(f"✓ Создан тьютор: {tutor.get_full_name()}")
    else:
        print(f"✓ Используется существующий тьютор: {tutor.get_full_name()}")
    
    try:
        # Создаем ученика и родителя
        print("\n--- Создание ученика и родителя ---")
        student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
            tutor=tutor,
            student_first_name='Дмитрий',
            student_last_name='Синицын',
            grade='8Б',
            goal='Подготовка к олимпиаде по математике',
            parent_first_name='Ирина',
            parent_last_name='Синицына',
            parent_email='irina@example.com',
            parent_phone='+79991234567'
        )
        
        print(f"✓ Создан ученик: {student_user.get_full_name()}")
        print(f"✓ Создан родитель: {parent_user.get_full_name()}")
        
        # Проверяем профили
        print("\n--- Проверка профилей ---")
        student_profile = StudentProfile.objects.get(user=student_user)
        print(f"✓ Профиль ученика: класс {student_profile.grade}, цель: {student_profile.goal}")
        
        parent_profile = ParentProfile.objects.get(user=parent_user)
        print(f"✓ Профиль родителя создан")
        
        # Проверяем связи
        print("\n--- Проверка связей ---")
        assert student_profile.tutor == tutor, "Связь с тьютором не создана"
        print("✓ Связь ученик-тьютор создана")
        
        assert student_profile.parent == parent_user, "Связь с родителем не создана"
        print("✓ Связь ученик-родитель создана")
        
        assert student_user in parent_profile.children.all(), "Связь родитель-ученик не создана"
        print("✓ Связь родитель-ученик создана")
        
        # Проверяем учетные данные
        print("\n--- Учетные данные ---")
        print(f"Ученик: username={student_creds.username}, password={student_creds.password}")
        print(f"Родитель: username={parent_creds.username}, password={parent_creds.password}")
        
        assert student_profile.generated_username == student_creds.username
        assert student_profile.generated_password == student_creds.password
        print("✓ Учетные данные сохранены в профиле")
        
        print("\n=== Все проверки пройдены успешно! ===")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

