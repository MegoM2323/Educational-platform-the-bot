# CI/CD Pipeline Setup Guide

## Обзор

Этот документ описывает настройку и использование CI/CD pipeline для THE BOT Platform на базе GitHub Actions.

## Структура Pipeline

### 1. Backend Unit Tests (`backend-unit-tests.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:** Запускает unit тесты backend
- **Сервисы:** PostgreSQL 15, Redis 7
- **Timeout:** 10 минут

### 2. Frontend Unit Tests (`frontend-unit-tests.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:** Запускает unit тесты frontend с coverage
- **Timeout:** 10 минут

### 3. Integration Tests (`integration-tests.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:** Запускает интеграционные тесты backend
- **Сервисы:** PostgreSQL 15, Redis 7
- **Timeout:** 15 минут

### 4. E2E Tests (`e2e-tests.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:** Запускает E2E тесты на Playwright (3 браузера)
- **Сервисы:** PostgreSQL 15, Redis 7
- **Timeout:** 30 минут
- **Matrix:** chromium, firefox, webkit

### 5. Lint & Code Quality (`lint.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:**
  - Backend: flake8, black, isort, mypy
  - Frontend: eslint, prettier
- **Timeout:** 5 минут

### 6. Code Coverage (`codecov.yml`)
- **Триггеры:** Push и PR на main/develop
- **Что делает:** Генерирует и загружает coverage reports
- **Интеграция:** Codecov
- **Timeout:** 15 минут

### 7. Deploy to Staging (`deploy-staging.yml`)
- **Триггеры:** Push на develop
- **Условие:** Все тесты прошли успешно
- **Что делает:**
  - Запускает все тесты
  - Деплоит на staging сервер
  - Health check
  - Уведомления в Telegram
- **Timeout:** 15 минут

### 8. Deploy to Production (`deploy-production.yml`)
- **Триггеры:**
  - Manual dispatch (workflow_dispatch)
  - Release created
- **Условие:** Все тесты прошли, manual approval
- **Что делает:**
  - Запускает все тесты
  - Создает backup БД и media
  - Деплоит на production
  - Health check
  - Rollback при failure
  - Уведомления в Telegram
- **Timeout:** 20 минут

### 9. PR Checks (`pr-checks.yml`)
- **Триггеры:** Pull Request
- **Что делает:**
  - Проверка формата заголовка PR
  - Автоматические лейблы
  - Проверка на merge conflicts

## Настройка GitHub Secrets

### Обязательные секреты

#### Database
```bash
DATABASE_URL=postgres://user:pass@host:port/db
```

#### Supabase
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

#### YooKassa (Payments)
```bash
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

#### Telegram
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_PUBLIC_CHAT_ID=chat_id_for_announcements
TELEGRAM_LOG_CHAT_ID=chat_id_for_logs
```

#### Codecov
```bash
CODECOV_TOKEN=your_codecov_token
```

#### Staging Server (для deploy-staging.yml)
```bash
STAGING_HOST=staging.the-bot.ru
STAGING_USER=deploy_user
STAGING_SSH_KEY=<private_ssh_key>
STAGING_PATH=/path/to/project
```

#### Production Server (для deploy-production.yml)
```bash
PRODUCTION_HOST=the-bot.ru
PRODUCTION_USER=deploy_user
PRODUCTION_SSH_KEY=<private_ssh_key>
PRODUCTION_PATH=/path/to/project
```

### Как добавить секреты

1. Перейдите в репозиторий на GitHub
2. Settings → Secrets and variables → Actions
3. Нажмите "New repository secret"
4. Введите имя и значение секрета
5. Сохраните

## Настройка серверов для деплоя

### SSH ключи

1. Создайте SSH ключ для деплоя:
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy
```

2. Добавьте публичный ключ на сервер:
```bash
# На сервере
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA..." >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

3. Добавьте приватный ключ в GitHub Secrets как `STAGING_SSH_KEY` и `PRODUCTION_SSH_KEY`

### Настройка sudo без пароля

На сервере для пользователя деплоя:

```bash
sudo visudo
```

Добавьте:
```
deploy_user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart the-bot-*
deploy_user ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
```

### Systemd сервисы

Убедитесь что на серверах настроены сервисы:

**Staging:**
- `the-bot-staging-daphne.service`
- `the-bot-staging-celery-worker.service`
- `the-bot-staging-celery-beat.service`

**Production:**
- `the-bot-daphne.service`
- `the-bot-celery-worker.service`
- `the-bot-celery-beat.service`

## Настройка Codecov

1. Зарегистрируйтесь на https://codecov.io
2. Подключите GitHub репозиторий
3. Скопируйте токен
4. Добавьте в GitHub Secrets как `CODECOV_TOKEN`

## Использование Makefile

Локальная разработка с использованием Makefile:

```bash
# Установка зависимостей
make install

# Запуск тестов
make test
make test-unit
make test-integration
make test-e2e

# Coverage
make coverage

# Линтинг
make lint
make format

# Разработка
make start
make stop
make migrate

# Очистка
make clean
```

## Checklist для первого запуска CI/CD

### 1. Подготовка репозитория

- [ ] Создана ветка `develop`
- [ ] Установлены branch protection rules для `main` и `develop`
- [ ] Добавлены все обязательные GitHub Secrets
- [ ] Установлен Codecov

### 2. Настройка серверов

- [ ] SSH ключи созданы и добавлены
- [ ] Sudo права настроены для пользователя деплоя
- [ ] Systemd сервисы работают
- [ ] Nginx правильно настроен
- [ ] Redis установлен и запущен

### 3. Проверка workflows

- [ ] Backend unit tests проходят
- [ ] Frontend unit tests проходят
- [ ] Integration tests проходят
- [ ] E2E tests проходят (может потребоваться настройка)
- [ ] Lint проходит без ошибок
- [ ] Coverage reports загружаются в Codecov

### 4. Тестовый деплой

- [ ] Staging деплой работает (push в develop)
- [ ] Health check проходит на staging
- [ ] Telegram уведомления приходят
- [ ] Production деплой работает (manual dispatch)
- [ ] Rollback работает при failure

### 5. Дополнительно

- [ ] Dependabot настроен (автоматические PR для обновлений)
- [ ] PR template используется
- [ ] Auto-labeling работает
- [ ] Команда знакома с процессом

## Процесс разработки

### Работа с feature branches

1. Создайте feature branch от `develop`:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
```

2. Разработка и коммиты:
```bash
# Локальные тесты
make test
make lint

# Коммит
git add .
git commit -m "feat: add new feature"
```

3. Создайте Pull Request в `develop`:
```bash
git push origin feature/my-feature
```

4. PR автоматически запустит:
   - Unit tests
   - Integration tests
   - E2E tests
   - Lint checks
   - Coverage checks

5. После review и merge в `develop`:
   - Автоматически запустится деплой на staging

### Release в production

1. Создайте PR из `develop` в `main`
2. После merge в `main`:
   - Создайте release на GitHub
   - Или запустите manual deployment через Actions

3. Manual deployment:
   - Перейдите в Actions → Deploy to Production
   - Нажмите "Run workflow"
   - Введите причину деплоя
   - Подтвердите

## Мониторинг и отладка

### Просмотр логов workflows

```bash
# В GitHub UI
Repository → Actions → Select workflow run → View logs
```

### Просмотр логов на сервере

```bash
# Daphne logs
sudo journalctl -u the-bot-daphne.service -f

# Celery logs
sudo journalctl -u the-bot-celery-worker.service -f
sudo tail -f /var/log/celery/worker.log

# Nginx logs
sudo tail -f /var/log/nginx/the-bot-error.log
```

### Отладка failed deployments

1. Проверьте логи workflow в GitHub Actions
2. SSH на сервер и проверьте:
```bash
# Статус сервисов
sudo systemctl status the-bot-daphne.service
sudo systemctl status the-bot-celery-worker.service

# Git статус
cd /path/to/project
git log -1
git status

# Проверка приложения
curl -I https://the-bot.ru/api/health/
```

3. При необходимости rollback:
```bash
git reset --hard HEAD~1
sudo systemctl restart the-bot-daphne.service
```

## Оптимизация CI/CD

### Ускорение тестов

1. **Кэширование зависимостей:**
   - Уже настроено в workflows (pip cache, npm cache)

2. **Параллельные тесты:**
```bash
# Backend
pytest -n auto  # использует pytest-xdist

# Frontend
vitest --threads
```

3. **Запуск только измененных тестов:**
```bash
pytest --testmon  # только измененные тесты
```

### Сокращение времени деплоя

1. **Предварительная сборка:**
   - Frontend собирается локально или в CI
   - На сервер копируется уже собранный bundle

2. **Rolling deployment:**
   - Поочередный перезапуск сервисов
   - Zero downtime deployment

## Troubleshooting

### Проблема: Тесты падают в CI, но работают локально

**Решение:**
1. Проверьте версии Python и Node.js
2. Проверьте environment variables
3. Убедитесь что БД и Redis доступны

### Проблема: Деплой не запускается

**Решение:**
1. Проверьте что все secrets добавлены
2. Проверьте SSH ключи
3. Проверьте branch protection rules

### Проблема: Health check fails после деплоя

**Решение:**
1. Увеличьте timeout для health check
2. Проверьте логи сервисов на сервере
3. Проверьте что миграции прошли успешно

### Проблема: Coverage не загружается в Codecov

**Решение:**
1. Проверьте CODECOV_TOKEN
2. Убедитесь что coverage files генерируются
3. Проверьте формат coverage files

## Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.io/)
- [Playwright Documentation](https://playwright.dev/)
- [pytest Documentation](https://docs.pytest.org/)

## Поддержка

При возникновении проблем:
1. Проверьте логи в GitHub Actions
2. Проверьте логи на сервере
3. Обратитесь к этой документации
4. Создайте issue в репозитории
