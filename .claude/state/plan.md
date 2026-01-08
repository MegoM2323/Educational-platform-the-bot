# План: Группа 4 - WebSocket безопасность (T014-T015)

## Обзор
Исправление критических уязвимостей WebSocket в `backend/chat/consumers.py`:
- T014: Rate limiting на уровне пользователя (защита от multi-connection bypass)
- T015: Защита от перебора чатов через WebSocket

## Текущая проблема
- Строки 103-120 в consumers.py: Rate limiting на level per-connection (`self.message_timestamps`)
- Можно обойти, открыв несколько WebSocket соединений и отправляя сообщения параллельно
- Нет защиты от попыток подключиться к разным чатам для enum/brute-force

## Независимые задачи (PARALLEL GROUP 1)

### Task T014: Rate limiting на уровне пользователя
- **Файл**: `/backend/chat/consumers.py` строки 103-120
- **Зависимостей**: нет
- **Действия**:
  1. Добавить импорт: `import redis` (или использовать django.core.cache)
  2. Заменить per-connection (`self.message_timestamps`) на per-user rate limiting с Redis
  3. Ключ Redis: `chat_rate_limit:{user_id}` с expiration 60 сек
  4. При каждом сообщении:
     - Проверить счётчик в Redis за последнюю минуту
     - Если >= 10 → отправить error с кодом RATE_LIMIT_EXCEEDED
     - Иначе: INCR счётчик в Redis (с TTL 60 сек при первом INCR)
  5. Удалить `self.message_timestamps` из `__init__` и `_handle_message`

### Task T015: Защита от перебора чатов
- **Файл**: `/backend/chat/consumers.py` в методе `connect()`
- **Зависимостей**: нет (выполняется параллельно с T014)
- **Действия**:
  1. Добавить rate limiting на попытки подключиться к разным чатам
  2. Ключ Redis: `chat_rooms_limit:{user_id}` с expiration 60 сек
  3. В методе `connect()` (после аутентификации):
     - Проверить количество разных чатов в Redis за последнюю минуту
     - Если > 5 → закрыть соединение с кодом 4029 (Too Many Requests)
     - Иначе: INCR счётчик в Redis с TTL 60 сек
  4. Хранить лишь count чатов, не сами комнаты (для эффективности)

## Детали реализации

### Redis подключение
- Использовать `django.core.cache.cache` (уже настроено в settings.py)
- Или `redis.StrictRedis(host='localhost', port=6379, db=4)` для прямого доступа
- Рекомендуется: `django.core.cache.cache` для consistency с остальным проектом

### Константы
```python
CHAT_RATE_LIMIT = 10  # max messages per minute per user
CHAT_RATE_WINDOW = 60  # seconds
CHAT_ROOMS_LIMIT = 5  # max different rooms per minute per user
```

### Error codes
- 4001: Unauthorized (уже используется для auth timeout)
- 4003: Forbidden (уже используется для access denied)
- 4029: Too Many Requests (новый код для rate limit/room limit)

### Тестирование
- Проверить что за одной connection нельзя отправить >10 сообщений в минуту
- Проверить что с несколькими connections можно обойти лимит (ДО T014) → ДОЛЖНО РАБОТАТЬ ПОСЛЕ T014
- Проверить что нельзя подключиться к >5 разным чатам в минуту
- Проверить что TTL работает корректно (счётчик обнуляется через 60 сек)

## Success Criteria
- [ ] T014: Rate limiting moved to Redis per-user level
- [ ] T014: Multiple WebSocket connections throttled at user level
- [ ] T015: Connection attempts to different rooms rate-limited
- [ ] Both: Error codes 4029 returned on rate limit
- [ ] Both: Redis keys expire correctly (TTL=60)
- [ ] Both: No per-connection state used (self.message_timestamps removed)
- [ ] No syntax errors or import issues
- [ ] Code formatted with black

## Estimated Time
- T014: 20 minutes (move to Redis)
- T015: 15 minutes (room enumeration protection)
- Total: 35 minutes (parallel execution)
