# Scripts Directory

Организованные скрипты для управления проектом THE BOT Platform.

## Структура

### `dev/` - Разработка
- **`cleanup_db.sh`** - Очистка базы данных
- **`cleanup_all.sh`** - Полная очистка (БД + кэш)
- **`cleanup_preview.sh`** - Очистка preview-данных
- **`check_redis.sh`** - Проверка подключения к Redis

### `deployment/` - Продакшн
- **`deploy_server_config.sh`** - Настройка nginx, Celery, Redis на сервере

### `testing/` - Тестирование
- **`setup_test_environment.sh`** - Автоматизация создания тестового окружения

## Главные скрипты (в корне проекта)

- **`start.sh`** - Запуск локальной разработки (backend + frontend)
- **`start_server.sh`** - Продакшн развертывание на сервере

## Использование

```bash
# Локальная разработка
./start.sh

# Очистка БД
./scripts/dev/cleanup_db.sh

# Настройка тестового окружения
./scripts/testing/setup_test_environment.sh

# Продакшн развертывание
./start_server.sh
```
