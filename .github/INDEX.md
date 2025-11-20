# CI/CD Pipeline - Навигация

## Быстрый старт

Вы здесь впервые? Начните отсюда:

1. 🚀 **[QUICK_START.md](./QUICK_START.md)** - Пошаговый checklist первого запуска (12 шагов, ~2 часа)

2. 📖 **[README.md](./README.md)** - Основная документация CI/CD

3. 🔐 **[SECRETS_SETUP.md](./SECRETS_SETUP.md)** - Настройка GitHub Secrets

---

## По задачам

### Я хочу настроить CI/CD с нуля

1. **[QUICK_START.md](./QUICK_START.md)** - Следуйте этому чеклисту шаг за шагом
2. **[SECRETS_SETUP.md](./SECRETS_SETUP.md)** - Настройте все secrets
3. **[CI_CD_SETUP.md](./CI_CD_SETUP.md)** - Детальная техническая документация

**Время:** 2-3 часа

---

### Я хочу сделать деплой

#### На Staging
1. Просто сделайте push в ветку `develop`
2. CI/CD автоматически запустит deploy
3. Проверьте статус в **Actions** tab

#### На Production
1. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Пройдите весь checklist
2. Создайте Release на GitHub или используйте manual dispatch
3. Следите за процессом в **Actions** tab

**Важно:** Всегда проверяйте на staging перед production!

---

### Я хочу понять как работает CI/CD

1. **[README.md](./README.md)** - Обзор всех workflows
2. **[EXAMPLES.md](./EXAMPLES.md)** - 7 реальных сценариев использования
3. **[CI_CD_SETUP.md](./CI_CD_SETUP.md)** - Техническая документация

---

### Мне нужны примеры использования

**[EXAMPLES.md](./EXAMPLES.md)** содержит 7 детальных сценариев:

1. **Новый Feature** - От разработки до staging
2. **Hotfix для Production** - Быстрое исправление критического бага
3. **Release Cycle** - Полный цикл релиза
4. **Rollback** - Откат после неудачного деплоя
5. **Dependency Update** - Работа с Dependabot
6. **Security Vulnerability** - Исправление уязвимости
7. **Adding E2E Test** - Добавление нового E2E теста

---

### У меня проблема с CI/CD

#### Быстрая помощь
1. **[CI_CD_SETUP.md](./CI_CD_SETUP.md)** → Секция "Troubleshooting"
2. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** → "Common Issues & Solutions"
3. **[QUICK_START.md](./QUICK_START.md)** → Секция "Troubleshooting"

#### Частые проблемы

**Тесты падают в CI:**
- Проверьте версии Python (3.11) и Node.js (18)
- Проверьте environment variables
- См. логи в Actions → Failed workflow

**Deployment fails:**
- Проверьте GitHub Secrets
- Проверьте SSH ключи
- Проверьте что services работают на сервере

**Coverage не загружается:**
- Проверьте `CODECOV_TOKEN`
- Убедитесь что coverage files генерируются

---

### Я хочу добавить новый workflow

1. Посмотрите существующие workflows в `workflows/`
2. Используйте их как template
3. Следуйте best practices из **[CI_CD_SETUP.md](./CI_CD_SETUP.md)**

Примеры:
- `backend-unit-tests.yml` - для тестов
- `deploy-staging.yml` - для deployment
- `lint.yml` - для проверок качества

---

### Мне нужна информация о конкретном workflow

| Workflow | Описание | Документация |
|----------|----------|--------------|
| **backend-unit-tests.yml** | Backend unit тесты | [README.md](./README.md#workflows) |
| **frontend-unit-tests.yml** | Frontend unit тесты | [README.md](./README.md#workflows) |
| **integration-tests.yml** | Integration тесты | [README.md](./README.md#workflows) |
| **e2e-tests.yml** | E2E тесты (Playwright) | [README.md](./README.md#workflows) |
| **lint.yml** | Линтинг и форматирование | [README.md](./README.md#workflows) |
| **codecov.yml** | Coverage reporting | [README.md](./README.md#workflows) |
| **deploy-staging.yml** | Staging deployment | [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) |
| **deploy-production.yml** | Production deployment | [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) |
| **security-scan.yml** | Security scanning | [README.md](./README.md#workflows) |
| **pr-checks.yml** | PR validation | [README.md](./README.md#workflows) |

---

## Полная документация

### Основные документы

| Документ | Назначение | Время чтения |
|----------|-----------|--------------|
| **[README.md](./README.md)** | Главная документация | 15 мин |
| **[QUICK_START.md](./QUICK_START.md)** | Быстрый старт | 10 мин |
| **[EXAMPLES.md](./EXAMPLES.md)** | Примеры использования | 20 мин |
| **[CI_CD_SETUP.md](./CI_CD_SETUP.md)** | Детальная настройка | 30 мин |
| **[SECRETS_SETUP.md](./SECRETS_SETUP.md)** | Настройка secrets | 15 мин |
| **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** | Checklist деплоя | 20 мин |

### Справочники

| Документ | Назначение |
|----------|-----------|
| **[FILES_LIST.md](./FILES_LIST.md)** | Список всех файлов |
| **[PULL_REQUEST_TEMPLATE.md](./PULL_REQUEST_TEMPLATE.md)** | Шаблон PR |
| **[dependabot.yml](./dependabot.yml)** | Конфигурация Dependabot |
| **[labeler.yml](./labeler.yml)** | Конфигурация auto-labeling |
| **[../.codecov.yml](../.codecov.yml)** | Конфигурация Codecov |

### Корневые файлы

| Файл | Назначение |
|------|-----------|
| **[../Makefile](../Makefile)** | Локальные команды для разработки |
| **[../CI_CD_SUMMARY.md](../CI_CD_SUMMARY.md)** | Резюме всей установки |

---

## Рабочие процессы

### Процесс разработки feature

```
1. Создать feature branch от develop
2. Разработка + локальные тесты (make test)
3. Push → Автоматические тесты в CI
4. Создать PR в develop
5. Code review + автоматические проверки
6. Merge → Автоматический deploy на staging
7. Тестирование на staging
```

**Детали:** [EXAMPLES.md](./EXAMPLES.md) → Сценарий 1

---

### Процесс release

```
1. Все features протестированы на staging
2. Создать PR из develop в main
3. Review и approval
4. Merge в main
5. Создать Release на GitHub
6. Автоматический deploy на production
7. Мониторинг first hour
```

**Детали:** [EXAMPLES.md](./EXAMPLES.md) → Сценарий 3

---

### Процесс hotfix

```
1. Создать hotfix branch от main
2. Исправить баг + тест
3. Fast-track review
4. Merge в main
5. Manual production deployment
6. Verification
7. Backport в develop
```

**Детали:** [EXAMPLES.md](./EXAMPLES.md) → Сценарий 2

---

## Команды

### Локальная разработка

```bash
# Тестирование
make test              # Все тесты
make test-unit         # Unit тесты
make test-integration  # Integration тесты
make test-e2e          # E2E тесты
make coverage          # Coverage reports

# Качество кода
make lint              # Линтинг
make format            # Автоформатирование

# Разработка
make install           # Установка зависимостей
make start             # Старт серверов
make migrate           # Миграции
make clean             # Очистка
```

**Детали:** [../Makefile](../Makefile)

### GitHub CLI

```bash
# Статус workflows
gh run list --limit 10

# Watch workflow
gh run watch

# View logs
gh run view <run-id> --log
```

---

## GitHub Secrets

### Обязательные для тестов

- `CODECOV_TOKEN`
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PUBLIC_CHAT_ID`, `TELEGRAM_LOG_CHAT_ID`

### Для deployment

- `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`, `STAGING_PATH`
- `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_SSH_KEY`, `PRODUCTION_PATH`

**Детальная инструкция:** [SECRETS_SETUP.md](./SECRETS_SETUP.md)

---

## Структура директорий

```
.github/
├── workflows/          # GitHub Actions workflows (10 файлов)
├── README.md           # Главная документация
├── INDEX.md            # Этот файл (навигация)
├── QUICK_START.md      # Быстрый старт
├── EXAMPLES.md         # Примеры использования
├── CI_CD_SETUP.md      # Детальная настройка
├── SECRETS_SETUP.md    # Настройка secrets
├── DEPLOYMENT_CHECKLIST.md  # Checklist деплоя
├── FILES_LIST.md       # Список файлов
├── PULL_REQUEST_TEMPLATE.md # Шаблон PR
├── dependabot.yml      # Dependabot config
└── labeler.yml         # Auto-labeling config
```

---

## Полезные ссылки

### Внешние

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Codecov](https://codecov.io)
- [Playwright](https://playwright.dev)
- [Dependabot](https://docs.github.com/en/code-security/dependabot)

### Внутренние

- [Repository](https://github.com/YOUR_USERNAME/THE_BOT_platform)
- [Actions Tab](https://github.com/YOUR_USERNAME/THE_BOT_platform/actions)
- [Releases](https://github.com/YOUR_USERNAME/THE_BOT_platform/releases)
- [Issues](https://github.com/YOUR_USERNAME/THE_BOT_platform/issues)

---

## Поддержка

### Возникли вопросы?

1. Проверьте документацию (см. выше)
2. Проверьте [EXAMPLES.md](./EXAMPLES.md) для конкретных сценариев
3. Проверьте секцию Troubleshooting в:
   - [CI_CD_SETUP.md](./CI_CD_SETUP.md)
   - [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
   - [QUICK_START.md](./QUICK_START.md)

### Нашли баг или хотите улучшение?

Создайте issue на GitHub с тегом `ci/cd`

---

## Статус

✅ Pipeline настроен и готов к использованию
✅ Документация полная
✅ Примеры есть
✅ Troubleshooting guides есть

⚠️ **Action Required:** Настройте GitHub Secrets ([SECRETS_SETUP.md](./SECRETS_SETUP.md))

---

**Следующий шаг:** [QUICK_START.md](./QUICK_START.md) → Начните настройку!
