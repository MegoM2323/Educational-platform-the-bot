# CI/CD Quick Start - Чеклист первого запуска

## Шаг 1: GitHub Secrets (15-30 минут)

Перейдите в **Repository → Settings → Secrets and variables → Actions**

### Обязательные для тестов

- [ ] `CODECOV_TOKEN` - получите на https://codecov.io

### Для приложения (нужны для тестов)

- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `YOOKASSA_SHOP_ID`
- [ ] `YOOKASSA_SECRET_KEY`
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `TELEGRAM_PUBLIC_CHAT_ID`
- [ ] `TELEGRAM_LOG_CHAT_ID`

### Для deployment

- [ ] `STAGING_HOST` - например: `staging.the-bot.ru`
- [ ] `STAGING_USER` - например: `deploy`
- [ ] `STAGING_SSH_KEY` - приватный SSH ключ
- [ ] `STAGING_PATH` - например: `/home/deploy/the-bot-staging`
- [ ] `PRODUCTION_HOST` - например: `the-bot.ru`
- [ ] `PRODUCTION_USER` - например: `deploy`
- [ ] `PRODUCTION_SSH_KEY` - приватный SSH ключ
- [ ] `PRODUCTION_PATH` - например: `/home/deploy/the-bot-platform`

**Подробности:** [SECRETS_SETUP.md](./SECRETS_SETUP.md)

---

## Шаг 2: Codecov Setup (5 минут)

- [ ] Зарегистрируйтесь на https://codecov.io
- [ ] Подключите GitHub репозиторий
- [ ] Скопируйте Upload Token
- [ ] Добавьте в GitHub Secrets как `CODECOV_TOKEN`

---

## Шаг 3: Создание ветки develop (2 минуты)

```bash
git checkout -b develop
git push origin develop
```

---

## Шаг 4: Branch Protection (5 минут)

**Repository → Settings → Branches → Add rule**

### Для `main`:

- [ ] Branch name pattern: `main`
- [ ] Require a pull request before merging
  - [ ] Require approvals: **1**
  - [ ] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require status checks to pass before merging
  - [ ] Require branches to be up to date before merging
  - [ ] Status checks to require:
    - `Backend Unit Tests`
    - `Frontend Unit Tests`
    - `Integration Tests`
    - `Lint & Code Quality`
- [ ] Require conversation resolution before merging

### Для `develop`:

- [ ] То же самое, но можно убрать "Require approvals" для быстрой разработки

---

## Шаг 5: SSH ключи для deployment (10 минут)

### Создание ключей

```bash
# Staging
ssh-keygen -t ed25519 -C "github-staging" -f ~/.ssh/github_staging
# Production
ssh-keygen -t ed25519 -C "github-production" -f ~/.ssh/github_production
```

### Добавление на серверы

```bash
# Staging
ssh-copy-id -i ~/.ssh/github_staging.pub deploy@staging.the-bot.ru

# Production
ssh-copy-id -i ~/.ssh/github_production.pub deploy@the-bot.ru
```

### Добавление в GitHub Secrets

```bash
# Скопируйте ПРИВАТНЫЕ ключи (целиком с BEGIN/END)
cat ~/.ssh/github_staging      # → STAGING_SSH_KEY
cat ~/.ssh/github_production   # → PRODUCTION_SSH_KEY
```

---

## Шаг 6: Настройка серверов (10 минут)

### На Staging сервере:

```bash
ssh deploy@staging.the-bot.ru

# Sudo без пароля
sudo visudo
# Добавить:
# deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart the-bot-staging-*
# deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx

# Проверить services
sudo systemctl status the-bot-staging-daphne.service
sudo systemctl status the-bot-staging-celery-worker.service
```

### На Production сервере:

```bash
ssh deploy@the-bot.ru

# То же самое, но для production services
sudo visudo
# deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart the-bot-*
# deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx

# Проверить services
sudo systemctl status the-bot-daphne.service
sudo systemctl status the-bot-celery-worker.service
```

---

## Шаг 7: Первый тестовый запуск (5 минут)

```bash
# 1. Сделайте тестовое изменение
echo "# Testing CI/CD" >> README.md

# 2. Commit и push
git add README.md
git commit -m "test: verify CI/CD pipeline"
git push origin develop

# 3. Перейдите на GitHub
# Repository → Actions

# 4. Вы должны увидеть запущенные workflows:
# ✅ Backend Unit Tests
# ✅ Frontend Unit Tests
# ✅ Integration Tests
# ✅ E2E Tests
# ✅ Lint & Code Quality
# ✅ Code Coverage
```

---

## Шаг 8: Проверка результатов (10 минут)

### GitHub Actions

- [ ] Все workflows запустились
- [ ] Backend Unit Tests - **PASSED** ✅
- [ ] Frontend Unit Tests - **PASSED** ✅
- [ ] Integration Tests - **PASSED** ✅
- [ ] E2E Tests - **PASSED** ✅
- [ ] Lint & Code Quality - **PASSED** ✅

Если что-то failed ❌:
1. Нажмите на failed workflow
2. Посмотрите логи
3. Исправьте проблему
4. Push снова

### Codecov

- [ ] Перейдите на https://codecov.io/gh/YOUR_USERNAME/THE_BOT_platform
- [ ] Coverage report загружен
- [ ] Coverage >= 80% (или близко к этому)

---

## Шаг 9: Тестовый PR (10 минут)

```bash
# 1. Создайте feature branch
git checkout -b feature/test-ci-cd

# 2. Сделайте изменение
echo "CI/CD is working!" >> README.md
git add README.md
git commit -m "feat: test PR workflow"
git push origin feature/test-ci-cd

# 3. На GitHub создайте Pull Request
# feature/test-ci-cd → develop

# 4. Проверьте что:
# ✅ Все workflows запустились
# ✅ Auto-labels добавлены
# ✅ PR checks passed
# ✅ Codecov comment появился (если настроен)
# ✅ PR можно merge (если branch protection настроен)

# 5. Merge PR
# ✅ После merge в develop должен запуститься deploy-staging workflow
```

---

## Шаг 10: Проверка Staging Deployment (опционально, 15 минут)

Если настроили staging secrets:

- [ ] После merge в develop, `deploy-staging` workflow запустился
- [ ] Deployment прошел успешно
- [ ] Health check прошел
- [ ] Staging сервер доступен: `https://staging.the-bot.ru`
- [ ] Telegram notification пришло

Если failed:
1. Проверьте логи workflow
2. SSH на staging сервер и проверьте логи services
3. Исправьте проблему

---

## Шаг 11: Documentation (5 минут)

Прочитайте:

- [ ] `.github/README.md` - основная документация
- [ ] `.github/CI_CD_SETUP.md` - детальная настройка
- [ ] `.github/EXAMPLES.md` - примеры использования
- [ ] `Makefile` - локальные команды

---

## Шаг 12: Команде (5 минут)

- [ ] Поделитесь документацией с командой
- [ ] Объясните процесс PR
- [ ] Покажите как смотреть логи в Actions
- [ ] Расскажите про branch protection rules

---

## Итоговый чеклист

### Must Have (критично для работы)

- [x] GitHub Secrets добавлены (минимум для тестов)
- [x] Codecov настроен
- [x] Ветка develop создана
- [x] Branch protection для main настроен
- [x] Первый тестовый запуск прошел успешно

### Should Have (важно, но не критично)

- [ ] SSH ключи для deployment настроены
- [ ] Серверы подготовлены для deployment
- [ ] Branch protection для develop настроен
- [ ] Staging deployment протестирован
- [ ] Документация прочитана командой

### Nice to Have (можно сделать позже)

- [ ] Production deployment протестирован
- [ ] Telegram notifications настроены
- [ ] Security scan проверен
- [ ] Dependabot PRs просмотрены
- [ ] Team onboarding проведен

---

## Troubleshooting

### Тесты падают в CI

**Причина:** Обычно environment variables или версии Python/Node.js

**Решение:**
1. Проверьте логи в Actions
2. Убедитесь что все secrets добавлены
3. Проверьте что версии совпадают:
   - Python 3.11
   - Node.js 18

### Deployment fails

**Причина:** SSH ключи, sudo права, или services не работают

**Решение:**
1. Проверьте SSH ключ (правильный формат с BEGIN/END)
2. Проверьте sudo права на сервере
3. Проверьте что services running: `sudo systemctl status ...`

### Coverage не загружается

**Причина:** CODECOV_TOKEN неправильный или отсутствует

**Решение:**
1. Проверьте токен на https://codecov.io
2. Убедитесь что он добавлен в GitHub Secrets
3. Re-run workflow

---

## Быстрые команды

```bash
# Проверка локально перед push
make test-unit && make lint

# Полная проверка
make test && make lint

# Coverage
make coverage

# Форматирование
make format

# Проверка статуса workflows (требует GitHub CLI)
gh run list --limit 10

# Watch workflow
gh run watch
```

---

## Контакты и поддержка

**Документация:**
- `.github/README.md`
- `.github/CI_CD_SETUP.md`
- `.github/SECRETS_SETUP.md`
- `.github/EXAMPLES.md`

**Issues:**
- Создайте issue на GitHub с тегом `ci/cd`

**Вопросы:**
- Проверьте документацию
- Проверьте Examples.md для конкретных сценариев

---

## Время выполнения

- **Минимальная настройка:** ~1 час (без deployment)
- **Полная настройка:** ~2 часа (с deployment)
- **С тестированием:** ~3 часа

---

**Готово!** 🎉

После выполнения этого чеклиста ваш CI/CD pipeline полностью настроен и готов к работе.

**Следующий шаг:** Начните использовать workflow в повседневной разработке. См. [EXAMPLES.md](./EXAMPLES.md) для конкретных сценариев.
