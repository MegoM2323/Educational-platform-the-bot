"""
Демонстрация работы Telegram уведомлений для счетов.

Этот файл показывает как работают сигналы:

1. Создание счета со статусом SENT → родителю отправляется уведомление
2. Изменение статуса на PAID → родителю подтверждение + тьютору уведомление
3. Изменение любого статуса → обновление существующего сообщения

ТРЕБОВАНИЯ:
- parent.parent_profile.telegram_id должен быть заполнен
- tutor.tutor_profile.telegram_id должен быть заполнен
- TELEGRAM_BOT_TOKEN должен быть настроен в .env
- ENVIRONMENT != 'test' (в test режиме уведомления отключены)

ИСПОЛЬЗОВАНИЕ:
    from invoices.test_telegram_notifications import demo_telegram_flow
    demo_telegram_flow(tutor, student, parent)
"""

def demo_telegram_flow(tutor, student, parent):
    """
    Демонстрация полного цикла Telegram уведомлений.
    
    Args:
        tutor: User объект с ролью 'tutor'
        student: User объект с ролью 'student'
        parent: User объект с ролью 'parent'
    """
    from decimal import Decimal
    from django.utils import timezone
    from datetime import timedelta
    from invoices.models import Invoice
    
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ TELEGRAM УВЕДОМЛЕНИЙ")
    print("=" * 60)
    
    # Шаг 1: Создание счета со статусом SENT
    print("\n[1] Создание счета со статусом SENT...")
    invoice = Invoice.objects.create(
        tutor=tutor,
        student=student,
        parent=parent,
        amount=Decimal('5000.00'),
        description='Оплата за 4 занятия по математике',
        status=Invoice.Status.SENT,
        due_date=timezone.now().date() + timedelta(days=7)
    )
    print(f"✓ Счет #{invoice.id} создан")
    print(f"  → Родителю отправлено уведомление в Telegram")
    print(f"  → telegram_message_id: {invoice.telegram_message_id}")
    
    # Шаг 2: Изменение статуса на VIEWED
    print("\n[2] Родитель просмотрел счет...")
    invoice.status = Invoice.Status.VIEWED
    invoice.save()
    print(f"✓ Статус изменен на VIEWED")
    print(f"  → Сообщение в Telegram обновлено")
    
    # Шаг 3: Оплата счета
    print("\n[3] Родитель оплатил счет...")
    invoice.status = Invoice.Status.PAID
    invoice.save()
    print(f"✓ Статус изменен на PAID")
    print(f"  → Сообщение родителю обновлено")
    print(f"  → Родителю отправлено подтверждение оплаты")
    print(f"  → Тьютору отправлено уведомление об оплате")
    
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    
    return invoice


def check_telegram_setup(user):
    """
    Проверяет настройку Telegram для пользователя.
    
    Args:
        user: User объект
        
    Returns:
        bool: True если telegram_id настроен
    """
    profile = None
    
    if user.role == 'parent' and hasattr(user, 'parent_profile'):
        profile = user.parent_profile
    elif user.role == 'tutor' and hasattr(user, 'tutor_profile'):
        profile = user.tutor_profile
    
    if not profile:
        print(f"✗ У пользователя {user.email} нет профиля")
        return False
    
    telegram_id = getattr(profile, 'telegram_id', None)
    if not telegram_id:
        print(f"✗ У пользователя {user.email} не указан telegram_id")
        return False
    
    print(f"✓ Пользователь {user.email}: telegram_id = {telegram_id}")
    return True
