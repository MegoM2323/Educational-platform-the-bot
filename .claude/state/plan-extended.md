# ПОЛНЫЙ ПЛАН ИСПРАВЛЕНИЯ: Все HTTP 500 ошибки + Production Deployment

## ФАЗА 1: КРИТИЧЕСКИЕ 500 ОШИБКИ (Параллельные группы)

### Parallel Group 1A: WebSocket Consumers (ВЫСОКИЙ ПРИОРИТЕТ)

#### T1A1: Исправить backend/chat/consumers.py - KeyError в url_route
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
**Строки:** 87, 1927

**Проблема:**
```python
# НЕПРАВИЛЬНО (строка 87):
self.room_id = self.scope["url_route"]["kwargs"].get("room_id")

# НЕПРАВИЛЬНО (строка 1927 в NotificationConsumer):
self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
```

**Решение:**
```python
# ПРАВИЛЬНО:
try:
    self.room_id = self.scope.get("url_route", {}).get("kwargs", {}).get("room_id")
    if not self.room_id:
        logger.error("[ChatConsumer] room_id not found in URL route")
        await self.close(code=4000)
        return
except Exception as e:
    logger.error(f"[ChatConsumer] Error extracting room_id: {e}")
    await self.close(code=4000)
    return
```

**Строки для изменения:**
- 87: `self.room_id = self.scope["url_route"]["kwargs"].get("room_id")`
- 1927: `self.user_id = self.scope["url_route"]["kwargs"]["user_id"]`
- 2026: `self.user_id = self.scope["url_route"]["kwargs"]["user_id"]` (DashboardConsumer)

---

#### T1A2: Исправить backend/chat/consumers.py - AnonymousUser обработка
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
**Строки:** 176, 180, 513, 661, 1609-1612, 1940

**Проблема:**
```python
# НЕПРАВИЛЬНО:
user = self.scope["user"]
user_id = user.id  # ← AnonymousUser.id = None → 500 при обращении к БД
role = user.role  # ← AnonymousUser не имеет role → AttributeError

# НЕПРАВИЛЬНО (в serialize):
"id": self.scope["user"].id,  # ← None для AnonymousUser
"username": self.scope["user"].username,  # ← '' для AnonymousUser
```

**Решение - везде перед использованием user проверять:**
```python
# ПРАВИЛЬНО:
user = self.scope["user"]
if not user.is_authenticated:
    logger.warning("[ChatConsumer] Unauthenticated user attempting connection")
    await self.close(code=4001)
    return

# Теперь безопасно:
user_id = user.id
role = getattr(user, "role", "unknown")
```

**Строки для изменения:**
- 104-105: Add is_authenticated check before close(code=4003)
- 140-176: Add is_authenticated check before any user attribute access
- 513: Add is_authenticated check before sending message
- 661: Add is_authenticated check in delete_message
- 1609-1612: Add is_authenticated check before serializing user
- 1940: Add is_authenticated check before string comparison

---

### Parallel Group 1B: Attribute Errors (ВЫСОКИЙ ПРИОРИТЕТ)

#### T1B1: Исправить backend/reports/consumers.py - tutor_profile AttributeError
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/reports/consumers.py`
**Строка:** 198

**Проблема:**
```python
# НЕПРАВИЛЬНО:
elif self.user.role == 'tutor':
    students = self.user.tutor_profile.students.all()  # ← 500 если нет TutorProfile
```

**Решение:**
```python
# ПРАВИЛЬНО:
elif self.user.role == 'tutor':
    try:
        tutor_profile = self.user.tutor_profile
        students = tutor_profile.students.all()
    except AttributeError:
        logger.warning(f"[ReportsConsumer] TutorProfile not found for user {self.user.id}")
        students = []
```

---

#### T1B2: Исправить backend/invoices/signals.py - tutor_profile & profile access
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/invoices/signals.py`
**Строки:** 203, 122-123

**Проблема:**
```python
# НЕПРАВИЛЬНО (строка 203):
profile = user.tutor_profile  # ← AttributeError если нет профиля

# НЕПРАВИЛЬНО (строка 122-123):
if _has_telegram_id(invoice.parent):  # ← Может быть parent=None
    ...
```

**Решение:**
```python
# ПРАВИЛЬНО:
try:
    profile = user.tutor_profile
except AttributeError:
    logger.warning(f"[InvoiceSignal] TutorProfile not found for user {user.id}")
    return

# ПРАВИЛЬНО:
if invoice.parent and hasattr(invoice.parent, 'telegram_id'):
    if invoice.parent.telegram_id:
        ...
```

---

#### T1B3: Исправить backend/accounts/views.py - tutor_profile access
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/views.py`
**Строки:** 447, 498, 652

**Проблема:**
```python
# НЕПРАВИЛЬНО:
tutor_profile = user.tutor_profile  # ← Может быть AttributeError
return tutor_profile.specialization  # ← 500 если нет профиля
```

**Решение:**
```python
# ПРАВИЛЬНО:
try:
    tutor_profile = user.tutor_profile
    return tutor_profile.specialization or ""
except AttributeError:
    return ""
```

**Строки для изменения:**
- 447: Wrap tutor_profile access in try/except
- 498: Wrap tutor_profile access in try/except
- 652: Wrap tutor_profile access in try/except

---

### Parallel Group 1C: Import & Routing Errors (ВЫСОКИЙ ПРИОРИТЕТ)

#### T1C1: Исправить backend/config/asgi.py - Import error handling
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/config/asgi.py`
**Строки:** 17-20, 44-55

**Проблема:**
```python
# НЕПРАВИЛЬНО:
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from invoices.routing import websocket_urlpatterns as invoice_websocket_urlpatterns
# ← Если любой импорт падает → весь ASGI падает
```

**Решение:**
```python
# ПРАВИЛЬНО:
websocket_urlpatterns = []

try:
    from chat.routing import websocket_urlpatterns as chat_patterns
    websocket_urlpatterns.extend(chat_patterns)
except ImportError as e:
    logger.error(f"[ASGI] Failed to import chat routing: {e}")

try:
    from invoices.routing import websocket_urlpatterns as invoice_patterns
    websocket_urlpatterns.extend(invoice_patterns)
except ImportError as e:
    logger.error(f"[ASGI] Failed to import invoices routing: {e}")

try:
    from reports.routing import websocket_urlpatterns as reports_patterns
    websocket_urlpatterns.extend(reports_patterns)
except ImportError as e:
    logger.error(f"[ASGI] Failed to import reports routing: {e}")

try:
    from notifications.routing import websocket_urlpatterns as notifications_patterns
    websocket_urlpatterns.extend(notifications_patterns)
except ImportError as e:
    logger.error(f"[ASGI] Failed to import notifications routing: {e}")
```

---

### Parallel Group 1D: Middleware & Channel Layer (СРЕДНИЙ ПРИОРИТЕТ)

#### T1D1: Исправить backend/chat/middleware.py - TokenAuthMiddleware exception handling
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/chat/middleware.py`
**Строки:** 35-45

**Проблема:**
```python
# НЕПРАВИЛЬНО:
async def __call__(self, scope, receive, send):
    if scope["type"] == "websocket":
        token = self.get_token_from_scope(scope)
        if token:
            user = await self.get_user_from_token(token)  # ← Может выбросить
            if user:
                scope['user'] = user
```

**Решение:**
```python
# ПРАВИЛЬНО:
async def __call__(self, scope, receive, send):
    if scope["type"] == "websocket":
        try:
            token = self.get_token_from_scope(scope)
            if token:
                user = await self.get_user_from_token(token)
                if user:
                    scope['user'] = user
                else:
                    logger.warning(f"[TokenAuthMiddleware] Invalid token in scope")
        except Exception as e:
            logger.error(f"[TokenAuthMiddleware] Error in __call__: {e}", exc_info=True)
            # Продолжить с AnonymousUser, не падать
```

---

### Parallel Group 1E: Channel Layer Verification

#### T1E1: Исправить backend/invoices/services.py - Channel layer safety
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/invoices/services.py`
**Строки:** 86-115

**Проблема:**
```python
# МОЖЕТ БЫТЬ ПРОБЛЕМА:
channel_layer = get_channel_layer()
if not channel_layer:
    return
async_to_sync(channel_layer.group_send)(...)  # ← OK, но может быть timeout
```

**Решение - добавить timeout и error handling:**
```python
@staticmethod
def broadcast_invoice_created(invoice: Invoice) -> None:
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("[InvoiceService] Channel layer not configured")
            return

        try:
            async_to_sync(channel_layer.group_send)(
                f"invoice_{invoice.id}",
                {
                    "type": "invoice.message",
                    "message": "Invoice created",
                }
            )
        except Exception as e:
            logger.error(f"[InvoiceService] Failed to broadcast invoice: {e}")
            # Не падать, просто залогировать
    except Exception as e:
        logger.error(f"[InvoiceService] Unexpected error in broadcast_invoice_created: {e}")
```

---

## ФАЗА 2: Database & Authentication (последовательно после ФАЗЫ 1)

### T2A: Исправить migration CheckConstraint syntax
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/invoices/migrations/0001_initial.py`
**Строка:** 302-304

**Проблема:** CheckConstraint использует неправильный синтаксис
**Решение:** Проверить Django 4.2.7 API и исправить параметры

### T2B: Исправить JWT Token Authentication
**Файл:** `/home/mego/Python Projects/THE_BOT_platform/backend/config/settings.py`

**Добавить SIMPLE_JWT settings и проверить REST_FRAMEWORK config**

---

## ФАЗА 3: Testing & Review (после ФАЗЫ 2)

### T3A: Integration Testing
- Test все 9 критических мест на AttributeError/KeyError
- Test WebSocket с AnonymousUser
- Test с отсутствующими profiles
- Test с поломанными imports

### T3B: Code Review
- Проверить все try/except блоки
- Verify error logging адекватен
- Check scope safety во всех consumers

---

## ФАЗА 4: Production Deployment

### T4A: Pre-deployment verification
1. Run all migrations locally: `python manage.py migrate`
2. Run tests: `pytest backend/tests/`
3. Check logs for any import errors

### T4B: Production deployment
```bash
./safe-deploy-native.sh
```

### T4C: Post-deployment verification
1. Check service status: `systemctl status thebot-*.service`
2. Monitor logs: `journalctl -u thebot-backend.service -f`
3. Test WebSocket: `curl wss://the-bot.ru/ws/notifications/`
4. Test API: `curl -H "Authorization: Bearer ..." https://the-bot.ru/api/chat/rooms/`

---

## КРИТИЧЕСКИЕ ФАЙЛЫ ДЛЯ ИСПРАВЛЕНИЯ

### ВЫСОКИЙ ПРИОРИТЕТ (БЛОКИРУЮЩИЕ 500 ОШИБКИ)
1. `backend/chat/consumers.py` - lines 87, 104-105, 140-180, 513, 661, 1609-1612, 1927, 2026, 1940 (9 мест)
2. `backend/reports/consumers.py` - line 198 (1 место)
3. `backend/invoices/signals.py` - lines 203, 122-123 (2 места)
4. `backend/accounts/views.py` - lines 447, 498, 652 (3 места)
5. `backend/config/asgi.py` - lines 17-20 (1 место)
6. `backend/chat/middleware.py` - lines 35-45 (1 место)

### СРЕДНИЙ ПРИОРИТЕТ
7. `backend/invoices/services.py` - lines 86-115 (error handling improvement)
8. `backend/invoices/migrations/0001_initial.py` - line 302 (syntax fix)
9. `backend/config/settings.py` - SIMPLE_JWT config (JWT fix)

---

## ИТОГО: 22 МЕСТА ТРЕБУЮТ ИСПРАВЛЕНИЯ

| Тип | Количество | Файлы |
|-----|-----------|-------|
| KeyError в url_route | 3 | chat/consumers.py (3 места) |
| AnonymousUser/AttributeError | 9 | chat/consumers.py (6), chat/middleware.py (1), reports/consumers.py (1), invoices/signals.py (1) |
| Missing profile attributes | 5 | invoices/signals.py (2), accounts/views.py (3) |
| Import errors | 1 | config/asgi.py (1) |
| Migration syntax | 1 | invoices/migrations/0001_initial.py (1) |
| JWT configuration | 1 | config/settings.py (1) |
| Channel layer safety | 1 | invoices/services.py (1) |

---

## ПАРАЛЛЕЛЬНОЕ ИСПОЛНЕНИЕ

**Group 1 (Все независимые):**
- T1A1: Исправить KeyError в url_route (chat/consumers.py)
- T1A2: Исправить AnonymousUser issues (chat/consumers.py)
- T1B1: Исправить tutor_profile в reports/consumers.py
- T1B2: Исправить tutor_profile в invoices/signals.py
- T1B3: Исправить tutor_profile в accounts/views.py
- T1C1: Исправить ASGI imports
- T1D1: Исправить middleware exception handling
- T1E1: Улучшить channel layer safety

**Group 2 (Зависит от Group 1):**
- T2A: Migration CheckConstraint
- T2B: JWT Authentication

**Group 3 (Зависит от Group 2):**
- T3A: Integration Testing
- T3B: Code Review

**Group 4 (Зависит от Group 3):**
- T4A-C: Production Deployment

---

## DEPLOYMENT STEPS ДЛЯ PRODUCTION

### Шаг 1: Backup
```bash
ssh mg@5.129.249.206 'pg_dump -U thebot_user -h 127.0.0.1 thebot_db > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql'
```

### Шаг 2: Deploy код
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
./safe-deploy-native.sh
```

### Шаг 3: Verify services
```bash
ssh mg@5.129.249.206 'systemctl status thebot-backend.service thebot-daphne.service'
```

### Шаг 4: Check logs
```bash
ssh mg@5.129.249.206 'journalctl -u thebot-backend.service -n 50'
ssh mg@5.129.249.206 'journalctl -u thebot-daphne.service -n 50'
```

### Шаг 5: Test endpoints
```bash
curl https://the-bot.ru/api/accounts/profile/
curl wss://the-bot.ru/ws/notifications/
```

### Шаг 6: Monitor для 500 errors
```bash
ssh mg@5.129.249.206 'tail -f /home/mg/THE_BOT_platform/backend/logs/*.log | grep -i "500\|error"'
```

---

## ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После всех исправлений:
- ✅ Нет KeyError при отсутствии url_route
- ✅ Нет AttributeError при missing profiles
- ✅ Нет 500 errors от AnonymousUser
- ✅ ASGI не падает при broken imports
- ✅ WebSocket connections безопасны
- ✅ API authentication работает
- ✅ Все логи записываются, но система не падает
- ✅ Production стабилен под нагрузкой
