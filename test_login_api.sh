#!/bin/bash
# Скрипт для проверки API входа для всех ролей

cd "$(dirname "$0")/backend"

echo "============================================================"
echo "Проверка API входа для всех ролей"
echo "============================================================"

python manage.py shell << 'EOF'
from accounts.views import login_view
from rest_framework.test import APIRequestFactory
from django.test import RequestFactory

factory = APIRequestFactory()
test_accounts = [
    ('student@test.com', 'TestPass123!', 'Студент'),
    ('teacher@test.com', 'TestPass123!', 'Преподаватель'),
    ('tutor@test.com', 'TestPass123!', 'Тьютор'),
    ('parent@test.com', 'TestPass123!', 'Родитель'),
    ('admin@test.com', 'TestPass123!', 'Администратор'),
]

print('\nТестирование входа через API:')
print('=' * 60)

all_passed = True
for email, password, role_name in test_accounts:
    request = factory.post('/api/accounts/login/', {'email': email, 'password': password}, format='json')
    request.META['HTTP_HOST'] = 'localhost'
    response = login_view(request)
    
    status = response.status_code
    success = response.data.get('success') if hasattr(response, 'data') else False
    user_role = response.data.get('data', {}).get('user', {}).get('role') if success else None
    
    if status == 200 and success:
        print(f'✅ {role_name:15} | {email:25} | Status: {status} | Role: {user_role}')
    else:
        print(f'❌ {role_name:15} | {email:25} | Status: {status} | Success: {success}')
        all_passed = False

print('=' * 60)
if all_passed:
    print('✅ Все тесты пройдены успешно!')
    exit(0)
else:
    print('❌ Некоторые тесты не прошли')
    exit(1)
EOF




