# План: Исправить 41 failure в Backend API тестах T016-T027

## Summary
Исправить недостающие fields и endpoints в Parent API для прохождения тестов.

## Параллельные Task Группы

### Группа 1: ParentDashboard & ParentChildren (materials app)

#### Task T001: Добавить payments_summary и upcoming_classes в ParentDashboard
**Files:** backend/materials/parent_dashboard_service.py
**Changes:**
- В методе get_dashboard_data() строка 979-1004, добавить после ключа "total_children":
  - "payments_summary": {totals по статусам, последние 3 платежа}
  - "upcoming_classes": {array с ближайшими классами}
**Success:** Тест test_dashboard_response_has_required_fields PASS

#### Task T002: Исправить /api/parent/children/ endpoint
**Files:** backend/materials/parent_dashboard_views.py, urls.py
**Changes:**
- ParentChildrenView уже реализован (строка 164), но URL может быть не зарегистрирован
- Проверить urlpatterns регистрацию
- Response должен быть list или dict с 'results' (текущее: вернет dict с 'children' и 'pagination')
**Success:** Тесты test_get_children_* PASS

### Группа 2: ParentPayments, ParentInvoices, ParentReports, ParentChat (разные apps)

#### Task T003: Добавить /api/dashboard/parent/payments/ endpoint
**Files:** backend/materials/parent_dashboard_views.py, urls.py
**Changes:**
- Endpoint parent_payments() уже есть (строка 432)
- Возвращает get_parent_payments() из service
- Убедиться в авторизации IsAuthenticated
- URL должен быть зарегистрирован

#### Task T004: Добавить /api/invoices/parent/ endpoint
**Files:** backend/invoices/views.py, urls.py
**Changes:**
- Создать ParentInvoicesView (ListAPIView)
- Фильтровать по parent_id текущего пользователя
- Support pagination
- Support filter по status
- Authorization: IsAuthenticated, IsParent

#### Task T005: Добавить /api/reports/weekly-reports/ endpoint
**Files:** backend/reports/views.py, urls.py
**Changes:**
- Создать ParentReportsView (ListAPIView)
- Фильтровать отчеты по parent_id
- Support filters: child_id, date_from, date_to
- Support pagination
- Support export PDF

#### Task T006: Исправить /api/chat/conversations/ endpoint
**Files:** backend/chat/views.py, urls.py
**Changes:**
- Создать ParentChatView (ListAPIView)
- Фильтровать conversations по parent_id
- Поддерживать pagination и filters
- POST для отправки сообщения

#### Task T007: Добавить PATCH метод в /api/profile/parent/
**Files:** backend/accounts/views.py, urls.py
**Changes:**
- ParentProfileView должна иметь PATCH метод
- Обновлять поля: first_name, last_name, phone, avatar
- НЕ позволять менять email
- Возвращать обновленный profile
- Authorization: IsAuthenticated

## Success Criteria
- Все 41 failing test должны быть PASSED
- Все 88 backend тестов должны быть PASSED
- Без создания новых failures

## Test Files (для запуска)
```bash
pytest backend/materials/tests/test_get_parent_dashboard_api.py \
        backend/materials/tests/test_get_parent_children_api.py \
        backend/materials/tests/test_initiate_payment_api.py \
        backend/materials/tests/test_cancel_subscription_api.py \
        backend/invoices/tests/test_get_parent_invoices_api.py \
        backend/reports/tests/test_parent_reports_api.py \
        backend/chat/tests/test_parent_chat_api.py \
        backend/accounts/tests/test_parent_profile_api.py \
        -v
```
