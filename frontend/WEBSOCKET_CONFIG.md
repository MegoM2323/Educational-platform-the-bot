# WebSocket Configuration

## Обзор

Frontend использует WebSocket для real-time коммуникации (чат, уведомления, статусы платежей).

## Конфигурация URL

Приложение определяет WebSocket URL в следующем порядке приоритета:

1. **Environment Variable** (`.env.development` / `.env.production`)
   ```bash
   VITE_WEBSOCKET_URL=ws://localhost:8080/ws
   ```

2. **Auto-detection** (на основе `window.location`)
   - Development: `ws://localhost:8080/ws` (через Vite proxy)
   - Production: `wss://yourdomain.com/ws` (прямое подключение)

3. **Fallback** (SSR/build-time only)
   - `ws://localhost:8000/ws`

## Development режим

В development режиме Vite dev server работает на порту **8080** и проксирует WebSocket запросы на backend (**8000**).

### Vite Proxy Configuration

```javascript
// vite.config.ts
proxy: {
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true,
  }
}
```

### Правильный URL для development

```bash
# .env.development
VITE_WEBSOCKET_URL=ws://localhost:8080/ws
```

**НЕ используйте** `ws://localhost:8000/ws` в браузере - это минует Vite proxy и может вызвать CORS ошибки.

## Production режим

В production используйте прямое подключение к WebSocket:

```bash
# .env.production
VITE_WEBSOCKET_URL=wss://yourdomain.com/ws
```

## Исправление "Connection lost" проблемы

Если WebSocket показывает "Connection lost", проверьте:

1. **Правильный порт** в `.env.development`:
   - ✅ Correct: `ws://localhost:8080/ws`
   - ❌ Wrong: `ws://localhost:8000/ws`

2. **Backend запущен** на порту 8000:
   ```bash
   cd backend && python manage.py runserver 8000
   ```

3. **Vite dev server запущен** на порту 8080:
   ```bash
   cd frontend && npm run dev
   ```

4. **Токен авторизации** присутствует в localStorage:
   - Откройте DevTools → Application → Local Storage
   - Проверьте наличие `auth_token`

## Логирование

WebSocket сервис логирует все подключения и ошибки:

```javascript
// В браузере DevTools → Console
[WebSocket Config] Using base URL from VITE_WEBSOCKET_URL env var: ws://localhost:8080/ws
[ChatWebSocket] Connecting to room: { roomId: 1, hasToken: true }
```

## Архитектура WebSocket

```
Browser (localhost:8080)
    ↓ WebSocket request to /ws
Vite Dev Server (proxy)
    ↓ Forwards to ws://localhost:8000
Django Backend WebSocket
    ↓ Channels / Daphne
Real-time updates
```

## Сервисы WebSocket

Все сервисы используют единую функцию `getWebSocketBaseUrl()`:

1. **chatWebSocketService** - сообщения в чате
2. **notificationWebSocketService** - уведомления
3. **invoiceWebSocketService** - статусы платежей

## Troubleshooting

### Проблема: WebSocket соединяется к 8080 вместо 8000

**Решение**: Это правильное поведение в development! Vite проксирует запросы.

### Проблема: 401 Unauthorized

**Решение**: Токен авторизации отсутствует или истёк. Перелогиньтесь.

### Проблема: Connection refused

**Решение**: Backend не запущен или не слушает на порту 8000.

## Дополнительно

См. также:
- `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/websocketService.ts`
- `/home/mego/Python Projects/THE_BOT_platform/frontend/vite.config.ts`
