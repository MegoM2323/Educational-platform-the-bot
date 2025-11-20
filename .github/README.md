# CI/CD для THE BOT Platform

Полноценный CI/CD pipeline на базе GitHub Actions для автоматизированного тестирования, линтинга и деплоя.

## Быстрый старт

### 1. Настройка Secrets

Следуйте инструкциям в [SECRETS_SETUP.md](./SECRETS_SETUP.md) для добавления всех необходимых secrets.

**Минимально необходимые для тестов:**
- `CODECOV_TOKEN` (опционально, для coverage)

**Для деплоя:**
- Все secrets из staging/production секций

### 2. Первый запуск

```bash
# Убедитесь что у вас есть ветка develop
git checkout -b develop
git push origin develop

# Настройте branch protection для main и develop
# Repository → Settings → Branches → Add rule
```

### 3. Проверка работы

После push в `main` или `develop`:

1. Перейдите в **Actions** tab на GitHub
2. Вы должны увидеть запущенные workflows:
   - ✅ Backend Unit Tests
   - ✅ Frontend Unit Tests
   - ✅ Integration Tests
   - ✅ E2E Tests
   - ✅ Lint & Code Quality
   - ✅ Code Coverage

## Workflows

### Тестирование

| Workflow | Триггер | Описание | Timeout |
|----------|---------|----------|---------|
| [backend-unit-tests.yml](./workflows/backend-unit-tests.yml) | Push/PR | Unit тесты backend | 10 мин |
| [frontend-unit-tests.yml](./workflows/frontend-unit-tests.yml) | Push/PR | Unit тесты frontend | 10 мин |
| [integration-tests.yml](./workflows/integration-tests.yml) | Push/PR | Интеграционные тесты | 15 мин |
| [e2e-tests.yml](./workflows/e2e-tests.yml) | Push/PR | E2E тесты (Playwright) | 30 мин |

### Качество кода

| Workflow | Триггер | Описание | Timeout |
|----------|---------|----------|---------|
| [lint.yml](./workflows/lint.yml) | Push/PR | Линтинг backend + frontend | 5 мин |
| [codecov.yml](./workflows/codecov.yml) | Push/PR | Coverage reports | 15 мин |
| [security-scan.yml](./workflows/security-scan.yml) | Push/PR/Weekly | Сканирование безопасности | 10 мин |

### Деплой

| Workflow | Триггер | Описание | Timeout |
|----------|---------|----------|---------|
| [deploy-staging.yml](./workflows/deploy-staging.yml) | Push в develop | Деплой на staging | 15 мин |
| [deploy-production.yml](./workflows/deploy-production.yml) | Manual/Release | Деплой на production | 20 мин |

### Утилиты

| Workflow | Триггер | Описание |
|----------|---------|----------|
| [pr-checks.yml](./workflows/pr-checks.yml) | Pull Request | Проверка PR формата, лейблы |
| [dependabot.yml](../dependabot.yml) | Weekly | Автообновление зависимостей |

## Структура

```
.github/
├── workflows/
│   ├── backend-unit-tests.yml      # Backend unit тесты
│   ├── frontend-unit-tests.yml     # Frontend unit тесты
│   ├── integration-tests.yml       # Интеграционные тесты
│   ├── e2e-tests.yml               # E2E тесты (Playwright)
│   ├── lint.yml                    # Линтинг
│   ├── codecov.yml                 # Coverage reporting
│   ├── security-scan.yml           # Security scanning
│   ├── deploy-staging.yml          # Staging deployment
│   ├── deploy-production.yml       # Production deployment
│   └── pr-checks.yml               # PR validation
├── dependabot.yml                  # Dependabot configuration
├── labeler.yml                     # Auto-labeling configuration
├── PULL_REQUEST_TEMPLATE.md        # PR template
├── CI_CD_SETUP.md                  # Детальная настройка CI/CD
├── SECRETS_SETUP.md                # Настройка GitHub Secrets
├── DEPLOYMENT_CHECKLIST.md         # Чеклист для деплоя
└── README.md                       # Этот файл
```

## Использование

### Разработка нового feature

```bash
# 1. Создайте feature branch от develop
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# 2. Разработка
# ... make changes ...

# 3. Локальная проверка
make test
make lint

# 4. Push и создание PR
git push origin feature/my-feature
# Создайте PR в develop на GitHub

# 5. CI/CD автоматически запустит:
# - Unit tests (backend + frontend)
# - Integration tests
# - E2E tests
# - Lint checks
# - Coverage reports

# 6. После approve и merge в develop:
# - Автоматически запустится deploy на staging
```

### Deploy на Production

**Метод 1: Manual Deployment**
```bash
# 1. На GitHub
Actions → Deploy to Production → Run workflow

# 2. Укажите причину деплоя
Reason: "Release v1.2.3 with new features"

# 3. Подтвердите
```

**Метод 2: Release**
```bash
# 1. Создайте release на GitHub
# Releases → Create a new release

# 2. Заполните:
# Tag: v1.2.3
# Title: Release v1.2.3
# Description: Release notes...

# 3. Publish release
# Deployment автоматически запустится
```

### Rollback

Если что-то пошло не так:

**Automatic Rollback:**
- Срабатывает автоматически при failed health check в workflow

**Manual Rollback:**
```bash
# SSH на сервер
ssh user@the-bot.ru

# Откат к предыдущему коммиту
cd /path/to/project
git reset --hard HEAD~1

# Restart services
sudo systemctl restart the-bot-daphne.service
sudo systemctl restart the-bot-celery-worker.service
sudo systemctl restart the-bot-celery-beat.service
```

## Makefile Commands

Локальная разработка упрощена с помощью Makefile:

```bash
make help              # Показать все доступные команды

# Тестирование
make test              # Все тесты
make test-unit         # Unit тесты
make test-integration  # Интеграционные
make test-e2e          # E2E тесты
make coverage          # Coverage reports

# Качество кода
make lint              # Линтинг (backend + frontend)
make format            # Автоформатирование

# Разработка
make install           # Установка зависимостей
make start             # Старт dev серверов
make migrate           # Миграции БД
make clean             # Очистка
```

## Мониторинг

### GitHub Actions

Все workflows видны в **Actions** tab:
- Зеленая галочка ✅ = успешно
- Красный крестик ❌ = failed
- Желтый кружок 🟡 = в процессе

### Codecov

Coverage reports доступны на:
- https://codecov.io/gh/YOUR_USERNAME/THE_BOT_platform

### Telegram Notifications

Deployment уведомления приходят в:
- `TELEGRAM_PUBLIC_CHAT_ID` - успешные production deploys
- `TELEGRAM_LOG_CHAT_ID` - все логи и errors

## Branch Protection Rules

Рекомендуемые настройки для `main` и `develop`:

**Settings → Branches → Add rule:**

- ✅ Require a pull request before merging
  - ✅ Require approvals (1 минимум)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - Status checks to require:
    - Backend Unit Tests
    - Frontend Unit Tests
    - Integration Tests
    - Lint & Code Quality
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

## Troubleshooting

### Tests fail in CI but pass locally

**Возможные причины:**
1. Разные версии Python/Node.js
2. Разные environment variables
3. Database state differences

**Решение:**
```bash
# Проверьте версии
python --version  # Должно быть 3.11
node --version    # Должно быть 18.x

# Проверьте env vars
cat .env
```

### Deployment fails

**Проверьте:**
1. Все secrets добавлены
2. SSH ключи правильные
3. Сервер доступен
4. Services running

**Логи на сервере:**
```bash
sudo journalctl -u the-bot-daphne.service -n 50
sudo tail -f /var/log/nginx/the-bot-error.log
```

### Coverage not uploading to Codecov

**Проверьте:**
1. `CODECOV_TOKEN` добавлен в secrets
2. Coverage files генерируются
3. Codecov integration активна

## Best Practices

### Commits

Используйте conventional commits:
```
feat: add new feature
fix: resolve bug
docs: update documentation
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance tasks
```

### Pull Requests

- Используйте PR template
- Добавляйте описание изменений
- Link связанные issues
- Заполняйте checklist
- Запрашивайте review

### Testing

- Пишите тесты для всех новых features
- Стремитесь к coverage >= 80%
- Запускайте тесты локально перед push
- Проверяйте E2E тесты для UI изменений

### Deployment

- Всегда тестируйте на staging перед production
- Используйте deployment checklist
- Делайте backup перед production deploy
- Мониторьте приложение после deploy
- Будьте готовы к rollback

## Документация

- [CI_CD_SETUP.md](./CI_CD_SETUP.md) - Детальная настройка CI/CD
- [SECRETS_SETUP.md](./SECRETS_SETUP.md) - Настройка GitHub Secrets
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Чеклист для деплоя
- [PULL_REQUEST_TEMPLATE.md](./PULL_REQUEST_TEMPLATE.md) - Шаблон PR

## Support

Возникли проблемы?
1. Проверьте документацию выше
2. Проверьте логи workflows в Actions
3. Проверьте логи на сервере
4. Создайте issue в репозитории

---

**Создано для THE BOT Platform**
Версия: 1.0
Дата: 2025-11-20
