# Unified API Client

Объединенный API клиент для THE_BOT_platform, который заменяет все существующие API клиенты и обеспечивает единообразное взаимодействие с бэкендом.

## Особенности

- **Единый интерфейс**: Все API вызовы проходят через один клиент
- **Автоматическое обновление токенов**: Поддержка refresh token для автоматического обновления сессии
- **Retry логика**: Автоматические повторы запросов при сетевых ошибках с экспоненциальной задержкой
- **Обработка ошибок**: Классификация и пользовательские сообщения об ошибках
- **Очередь запросов**: Предотвращение дублирования идентичных запросов
- **TypeScript поддержка**: Полная типизация для всех методов и интерфейсов

## Использование

### Базовое использование

```typescript
import { unifiedAPI } from './integrations/api/unifiedClient';

// Аутентификация
const loginResult = await unifiedAPI.login({
  email: 'user@example.com',
  password: 'password123'
});

if (loginResult.success) {
  console.log('Пользователь:', loginResult.data?.user);
}

// Получение данных дашборда
const dashboardResult = await unifiedAPI.getStudentDashboard();
if (dashboardResult.success) {
  console.log('Данные дашборда:', dashboardResult.data);
}
```

### Обратная совместимость

Для плавной миграции старый API клиент продолжает работать:

```typescript
import { apiClient } from './integrations/api/client';

// Старый способ (теперь использует unifiedAPI внутри)
const result = await apiClient.request('/some-endpoint');
```

## API Методы

### Аутентификация

- `login(credentials: LoginRequest): Promise<ApiResponse<LoginResponse>>`
- `logout(): Promise<ApiResponse>`
- `getProfile(): Promise<ApiResponse<{ user: User; profile?: any }>>`
- `updateProfile(profileData: Partial<User>): Promise<ApiResponse<User>>`
- `changePassword(passwordData: PasswordChangeData): Promise<ApiResponse>`

### Дашборды

- `getStudentDashboard(): Promise<ApiResponse<StudentDashboard>>`
- `getTeacherDashboard(): Promise<ApiResponse<TeacherDashboard>>`
- `getParentDashboard(): Promise<ApiResponse<ParentDashboard>>`

### Чат

- `getGeneralChat(): Promise<ApiResponse<ChatRoom>>`
- `getGeneralMessages(page?: number, pageSize?: number): Promise<ApiResponse<PaginatedMessages>>`
- `sendMessage(data: SendMessageRequest): Promise<ApiResponse<ChatMessage>>`

### Платежи

- `createPayment(data: CreatePaymentRequest): Promise<ApiResponse<Payment>>`
- `getPayment(id: string): Promise<ApiResponse<Payment>>`
- `getPayments(): Promise<ApiResponse<Payment[]>>`
- `getPaymentStatus(id: string): Promise<ApiResponse<Payment>>`

### Заявки

- `createApplication(data: CreateApplicationRequest): Promise<ApiResponse<Application>>`
- `getApplications(): Promise<ApiResponse<Application[]>>`
- `getApplication(id: number): Promise<ApiResponse<Application>>`
- `updateApplicationStatus(id: number, status: string, notes?: string): Promise<ApiResponse<Application>>`

### Утилиты

- `setToken(token: string): void`
- `getToken(): string | null`
- `isAuthenticated(): boolean`
- `healthCheck(): Promise<ApiResponse<{ status: string }>>`
- `connectWebSocket(): WebSocket | null`

## Конфигурация

### Переменные окружения

```env
VITE_DJANGO_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### Кастомная конфигурация

```typescript
import { UnifiedAPIClient } from './integrations/api/unifiedClient';

const customClient = new UnifiedAPIClient(
  'https://api.example.com/api',  // API URL
  'wss://api.example.com/ws',     // WebSocket URL
  {
    maxRetries: 5,                // Максимальное количество повторов
    baseDelay: 1000,              // Базовая задержка (мс)
    maxDelay: 10000,              // Максимальная задержка (мс)
    backoffMultiplier: 2,         // Множитель для экспоненциальной задержки
  }
);
```

## Обработка ошибок

### Типы ошибок

- **Network**: Сетевые ошибки, таймауты
- **Auth**: Ошибки аутентификации (401)
- **Validation**: Ошибки валидации (400)
- **Server**: Серверные ошибки (5xx)

### Пример обработки

```typescript
const result = await unifiedAPI.getStudentDashboard();

if (!result.success) {
  switch (result.error) {
    case 'Network error: Unable to connect to server':
      // Показать сообщение о проблемах с сетью
      break;
    case 'Authentication required or token expired':
      // Перенаправить на страницу входа
      break;
    default:
      // Показать общее сообщение об ошибке
      break;
  }
}
```

## Retry логика

Клиент автоматически повторяет запросы при:

- Сетевых ошибках (до 3 раз с экспоненциальной задержкой)
- Серверных ошибках (1 раз с задержкой 1 секунда)
- Ошибках аутентификации (с попыткой обновления токена)

## WebSocket поддержка

```typescript
const ws = unifiedAPI.connectWebSocket();

if (ws) {
  ws.onopen = () => console.log('WebSocket connected');
  ws.onmessage = (event) => console.log('Message:', event.data);
  ws.onclose = () => console.log('WebSocket disconnected');
}
```

## Тестирование

Запуск тестов:

```bash
npm test -- unifiedClient
npm test -- migration
npm test -- errorHandling
```

Тесты покрывают:
- Все API методы
- Обработку ошибок
- Retry логику
- Управление токенами
- Обратную совместимость

## Миграция

### Шаг 1: Обновить импорты

```typescript
// Старый способ
import { apiClient } from './integrations/api/client';

// Новый способ
import { unifiedAPI } from './integrations/api/unifiedClient';
```

### Шаг 2: Обновить вызовы методов

```typescript
// Старый способ
const response = await apiClient.request('/dashboard/student/');

// Новый способ
const response = await unifiedAPI.getStudentDashboard();
```

### Шаг 3: Обновить обработку ответов

```typescript
// Старый способ
if (response.data) {
  // обработка данных
}

// Новый способ
if (response.success && response.data) {
  // обработка данных
}
```

## Производительность

- **Очередь запросов**: Предотвращает дублирование идентичных запросов
- **Кэширование токенов**: Токены сохраняются в localStorage
- **Параллельные запросы**: Поддержка одновременных запросов
- **Оптимизированные повторы**: Умная логика повторов с задержками
