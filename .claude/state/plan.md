# План: Исправить 3 HIGH проблемы с проверками user

## Parallel Group 1 (независимые исправления)

### Task 1: backend/chat/consumers.py:100-114
**Проблема:** `user.is_authenticated` может вызвать AttributeError если user=None
**Решение:** Проверить что user существует перед проверкой is_authenticated
**Код:**
```python
user = self.scope.get("user")
if not user or not user.is_authenticated:
    await self.close(code=4001)
    return
```

### Task 2: backend/chat/consumers.py:1876/1974 (NotificationConsumer)
**Проблема:** NotificationConsumer проверяет auth но затем обращается к `scope['user'].id` без гарантии
**Решение:** После проверки убедись что user.id не None перед использованием

### Task 3: backend/invoices/signals.py:225-235
**Проблема:** Доступ к `invoice.tutor.tutor_profile` без hasattr проверки
**Решение:** Добавь hasattr проверку или используй getattr с default:
```python
if hasattr(invoice.tutor, 'tutor_profile'):
    telegram_id = invoice.tutor.tutor_profile.telegram_id
```

## Tasks

- [ ] task_1_consumer_auth: Исправить ChatConsumer auth проверку (coder)
- [ ] task_2_notification_auth: Исправить NotificationConsumer auth (coder)
- [ ] task_3_invoice_profile: Исправить доступ к tutor_profile (coder)

## Success Criteria
- Все 3 исправления применены
- No new None/AttributeError
- Reviewer LGTM
- Tests pass
