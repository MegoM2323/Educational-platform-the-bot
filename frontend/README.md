# THE BOT Platform - Frontend

## Описание

Frontend часть образовательной платформы THE BOT, построенная на React, TypeScript и Vite.

## Технологии

- **React 18** — UI библиотека
- **TypeScript** — типизированный JavaScript
- **Vite** — современный сборщик
- **React Router** — маршрутизация
- **TanStack Query** — управление состоянием сервера
- **shadcn/ui + Radix UI** — компоненты интерфейса
- **Tailwind CSS** — стилизация
- **React Hook Form + Zod** — формы и валидация

## Установка

```bash
npm install
```

## Запуск

### Режим разработки

```bash
npm run dev
```

Сервер запустится на `http://localhost:5173` (или на другом порту, если 5173 занят).

### Сборка для продакшена

```bash
npm run build
```

Собранные файлы будут в папке `dist/`.

### Предпросмотр продакшен сборки

```bash
npm run preview
```

## Структура проекта

```
frontend/
├── src/
│   ├── components/     # React компоненты
│   ├── pages/          # Страницы приложения
│   ├── hooks/          # React хуки
│   ├── services/        # API сервисы
│   ├── utils/           # Утилиты
│   └── types/           # TypeScript типы
├── public/              # Статические файлы
└── package.json         # Зависимости
```

## Конфигурация

Переменные окружения должны быть настроены в корневом `.env` файле:

```env
VITE_DJANGO_API_URL=http://localhost:8000/api
```

## Линтинг

```bash
npm run lint
```
