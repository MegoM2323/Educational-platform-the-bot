# План: Исправить 5 MEDIUM проблем с логированием и проверками

## Summary
Исправить 5 проблем с логированием (потеря stack trace), проверками null, дублированием кода и пустыми значениями в 4 файлах backend.

## Independent Tasks (all 5 can run in parallel)

### Task 1: backend/reports/consumers.py:225-230
**File:** backend/reports/consumers.py
**Lines:** 225-230
**Issue:** AttributeError логирование без exc_info=True теряет stack trace
**Solution:** Добавить exc_info=True в logger.warning

### Task 2: backend/invoices/signals.py:250
**File:** backend/invoices/signals.py
**Lines:** 250
**Issue:** invoice.parent может быть None, используется без проверки
**Solution:** Добавить None check перед использованием invoice.parent

### Task 3: backend/invoices/signals.py:243
**File:** backend/invoices/signals.py
**Lines:** 243
**Issue:** Дата форматируется в пустую строку когда paid_at is None
**Solution:** Добавить информативное сообщение вместо пустой строки (например "Дата оплаты не установлена")

### Task 4: backend/config/asgi.py:44-55
**File:** backend/config/asgi.py
**Lines:** 44-55
**Issue:** Дублирование инициализации logger и import logging в try/except блоках
**Solution:** Инициализировать logger один раз перед try/except, использовать его в обоих местах

### Task 5: backend/chat/middleware.py:91-95
**File:** backend/chat/middleware.py
**Lines:** 91-95
**Issue:** Exception логирование без exc_info=True теряет traceback
**Solution:** Добавить exc_info=True в logger.error

## Execution Order
All 5 tasks are independent → parallel execution

## Success Criteria
- exc_info=True добавлен в logger.warning/error (tasks 1, 5)
- None checks добавлены перед использованием (task 2)
- Информативные сообщения вместо пустых строк (task 3)
- Дублирование logger удалено (task 4)
- Code style consistency с существующим кодом
- No syntax errors
- Type hints where appropriate
