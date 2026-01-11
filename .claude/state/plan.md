# T015: Improve exception handling в consumers.py

## Проблема

Broad exception handlers маскируют реальные ошибки, затрудняют debugging и скрывают security issues.

**Найдено 11 мест с `except Exception`:**
1. Line 155: graceful_shutdown() - Exception catch-all
2. Line 180: receive() при отправке ошибки размера
3. Line 248: disconnect() cleanup
4. Line 404: _handle_message() при сохранении
5. Line 449: _handle_read()
6. Line 459: chat_message() broadcast
7. Line 473: chat_typing() broadcast
8. Line 481: chat_message_edited() broadcast
9. Line 492: chat_message_deleted() broadcast
10. Line 510: chat_message_deleted() broadcast
11. Line 572: _heartbeat_loop()
12. Line 607: _check_current_permissions()
13. Line 638: _send_error()
14. Line 664: _get_client_ip() IP parsing (хорошо, но можно точнее)
15. Line 749: _validate_token()
16. Line 766: _check_access()
17. Line 797: _save_message()
18. Line 812: _mark_as_read()
19. Line 828: _get_user_data()

## Решение

Catch specific exception types:
- `json.JSONDecodeError` для JSON parsing
- `ValidationError` для user input errors (INFO level)
- `ObjectDoesNotExist` для missing objects (INFO level)
- `DatabaseError` для DB problems (ERROR level)
- `PermissionError` для access denied (INFO level)
- `ValueError` для invalid values (WARNING level)
- `asyncio.TimeoutError` для timeouts (WARNING level)
- `asyncio.CancelledError` для task cancellation (DEBUG level)
- `Exception` как catch-all (ERROR level с exc_info=True)

## Файлы для изменения
1. `backend/chat/consumers.py` - добавить импорты и обновить 19 exception handlers

## Импорты для добавления
```python
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import DatabaseError
```

## Реализация по методам

### Async methods (с logger.error/warning)
1. **graceful_shutdown()** line 155
   - `asyncio.CancelledError` → DEBUG: skip (it's expected)
   - `Exception` → ERROR with exc_info

2. **receive()** line 180
   - `asyncio.CancelledError` → skip
   - `Exception` → ERROR with exc_info

3. **disconnect()** line 248
   - `RuntimeError` (group_discard) → WARNING
   - `Exception` → ERROR with exc_info

4. **_handle_message()** line 404
   - `ValidationError` → INFO
   - `ObjectDoesNotExist` → INFO
   - `DatabaseError` → ERROR
   - `PermissionError` → INFO
   - `asyncio.TimeoutError` → WARNING
   - `Exception` → ERROR

5. **_handle_read()** line 449
   - `ObjectDoesNotExist` → INFO
   - `DatabaseError` → ERROR
   - `Exception` → ERROR

6. **chat_message()** line 459
   - `json.JSONDecodeError` → WARNING
   - `asyncio.CancelledError` → DEBUG (skip)
   - `Exception` → ERROR

7. **chat_typing()** line 473 - same as chat_message

8. **chat_message_edited()** line 481 - same as chat_message

9. **chat_message_deleted()** line 492, 510 - same as chat_message

10. **_heartbeat_loop()** line 572
    - `asyncio.CancelledError` → DEBUG (skip)
    - `asyncio.TimeoutError` → WARNING
    - `DatabaseError` → ERROR
    - `Exception` → ERROR

### Sync DB methods (with @database_sync_to_async)
11. **_check_current_permissions()** line 607
    - `ObjectDoesNotExist` → INFO
    - `DatabaseError` → ERROR
    - `PermissionError` → WARNING
    - `Exception` → ERROR

12. **_send_error()** line 638
    - `json.JSONDecodeError` → ERROR (shouldn't happen in send())
    - `Exception` → ERROR (important: not exc_info to avoid recursion)

13. **_get_client_ip()** line 664
    - `UnicodeDecodeError` → DEBUG
    - `Exception` → DEBUG (not critical)

14. **_validate_token()** line 749
    - `TokenError` (jwt related) → INFO
    - `ObjectDoesNotExist` → INFO
    - `Exception` → DEBUG

15. **_check_access()** line 766
    - `ObjectDoesNotExist` → INFO
    - `DatabaseError` → ERROR
    - `PermissionError` → WARNING
    - `Exception` → ERROR

16. **_save_message()** line 797
    - `ValidationError` → WARNING
    - `ObjectDoesNotExist` → WARNING
    - `DatabaseError` → ERROR
    - `PermissionError` → WARNING
    - `Exception` → ERROR

17. **_mark_as_read()** line 812
    - `ObjectDoesNotExist` → INFO
    - `DatabaseError` → ERROR
    - `Exception` → ERROR

18. **_get_user_data()** line 828
    - `ObjectDoesNotExist` → WARNING
    - `Exception` → ERROR

## Статус
- [ ] Task 1: Обновить consumers.py с specific exception handlers
- [ ] Task 2: Запустить black formatter
- [ ] Task 3: Запустить mypy type checker
- [ ] Task 4: Обновить progress.json

## Прогресс
Ожидание: coder → reviewer → tester
