# План: T005 - Backend JWT Header Support

## Обзор
Обновление TokenAuthMiddleware для поддержки JWT в Authorization header с сохранением backward compatibility для query string метода.

## Текущее состояние
- TokenAuthMiddleware: парсит JWT только из query_string (?token=<token>)
- Нужно добавить поддержку Authorization header: `Authorization: Bearer <token>`
- Оба метода должны работать (для backward compatibility)

## Задача T005: TokenAuthMiddleware JWT Header Support

Файл: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/middleware.py`

**Что обновить:**

1. Логика извлечения токена (приоритет):
   - **Приоритет 1:** Authorization header: `Authorization: Bearer <token>`
   - **Приоритет 2:** Query string: `?token=<token>` (legacy, deprecated)

2. Обновить `__call__` метод:
   ```
   - Получить headers из scope
   - Проверить Authorization header (ищем "Bearer <token>")
   - Если нет - fallback на query string
   - Валидировать токен и добавить user в scope
   - Логировать какой способ был использован
   ```

3. Добавить новый приватный метод:
   ```python
   def _extract_token_from_headers(self, headers: dict) -> str | None:
       """Extract token from Authorization header"""
       auth_header = headers.get(b"authorization", b"").decode()
       if auth_header.startswith("Bearer "):
           return auth_header[7:]
       return None
   ```

4. Обновить docstring класса:
   ```
   Поддержка двух методов:
   1. Authorization header: Authorization: Bearer <token>
   2. Query string: ?token=<token> (deprecated, для backward compatibility)
   ```

5. Логирование:
   - При извлечении из header: `[TokenAuthMiddleware] Token extracted from Authorization header: user_id={user_id}`
   - При извлечении из query: `[TokenAuthMiddleware] Token extracted from query string (legacy): user_id={user_id}`
   - При отсутствии токена: `[TokenAuthMiddleware] No token provided in either header or query`

## Verification
- Authorization header парсится корректно
- Query string fallback работает
- Оба способа логируются правильно
- AnonymousUser используется при отсутствии валидного токена
- Все исключения обрабатываются gracefully
- Black formatter проходит
- Syntax проверяется

