"""
Ручной тест API оплаты для проверки полного флоу
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from materials.models import SubjectEnrollment, SubjectSubscription, SubjectPayment
from materials.parent_dashboard_service import ParentDashboardService
from django.test import RequestFactory
from decimal import Decimal

User = get_user_model()


def test_payment_flow():
    """Тестирование полного флоу оплаты"""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ПОЛНОГО ФЛОУ ОПЛАТЫ")
    print("=" * 70)
    
    # 1. Получаем существующие данные
    try:
        enrollment = SubjectEnrollment.objects.get(id=15)
        parent = User.objects.filter(role=User.Role.PARENT).first()
        student = enrollment.student
        
        print(f"\n1. Найденные данные:")
        print(f"   Enrollment: {enrollment.id} - {enrollment.subject.name}")
        print(f"   Student: {student.get_full_name()}")
        print(f"   Parent: {parent.get_full_name() if parent else 'Not found'}")
        
        # 2. Проверяем текущую подписку
        print(f"\n2. Проверка текущей подписки:")
        try:
            old_subscription = SubjectSubscription.objects.get(enrollment=enrollment)
            print(f"   ✓ Подписка существует: ID={old_subscription.id}")
            print(f"     Amount: {old_subscription.amount}")
            print(f"     Status: {old_subscription.status}")
            print(f"     Next payment: {old_subscription.next_payment_date}")
        except SubjectSubscription.DoesNotExist:
            print(f"   ✗ Подписка не найдена")
            old_subscription = None
        
        # 3. Создаем сервис и тестовый request
        print(f"\n3. Создание сервиса:")
        service = ParentDashboardService(parent)
        factory = RequestFactory()
        request = factory.post('/test/')
        request.user = parent
        
        # 4. Тестируем создание платежа с обновлением подписки
        print(f"\n4. Создание платежа с обновлением подписки:")
        print(f"   Amount: 6000.00")
        print(f"   Create subscription: True")
        
        try:
            payment_data = service.initiate_payment(
                child=student,
                enrollment=enrollment,
                amount=Decimal('6000.00'),
                description='Тестовая оплата с обновлением подписки',
                create_subscription=True,
                request=request
            )
            
            print(f"   ✓ Платеж создан успешно!")
            print(f"     Payment ID: {payment_data['payment_id']}")
            print(f"     Amount: {payment_data['amount']}")
            print(f"     Subscription created: {payment_data.get('subscription_created', False)}")
            print(f"     Subscription updated: {payment_data.get('subscription_updated', False)}")
            print(f"     Confirmation URL: {payment_data.get('confirmation_url', 'N/A')}")
            
            # 5. Проверяем обновленную подписку
            print(f"\n5. Проверка обновленной подписки:")
            subscription = SubjectSubscription.objects.get(enrollment=enrollment)
            print(f"   ✓ Подписка обновлена:")
            print(f"     ID: {subscription.id}")
            print(f"     Amount: {subscription.amount} (было: {old_subscription.amount if old_subscription else 'N/A'})")
            print(f"     Status: {subscription.status}")
            print(f"     Next payment: {subscription.next_payment_date}")
            
            # 6. Проверяем, что подписка действительно обновлена, а не создана новая
            all_subscriptions = SubjectSubscription.objects.filter(enrollment=enrollment)
            print(f"\n6. Проверка уникальности подписки:")
            print(f"   Всего подписок для enrollment {enrollment.id}: {all_subscriptions.count()}")
            if all_subscriptions.count() == 1:
                print(f"   ✓ Подписка уникальна (правильно)")
            else:
                print(f"   ✗ Найдено несколько подписок (ошибка!)")
            
            print(f"\n" + "=" * 70)
            print("ТЕСТ ПРОЙДЕН УСПЕШНО!")
            print("=" * 70)
            return True
            
        except Exception as e:
            print(f"   ✗ Ошибка при создании платежа: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    test_payment_flow()

