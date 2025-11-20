# Примеры использования CI/CD

## Сценарий 1: Новый Feature

### Описание
Разработчик создает новый feature для платформы (например, добавление нового типа отчетов).

### Шаги

1. **Создание feature branch:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/new-report-type
```

2. **Разработка:**
```bash
# Backend changes
cd backend
vim reports/models.py        # Добавить новую модель
vim reports/views.py         # Добавить views
vim reports/serializers.py   # Добавить serializers
python manage.py makemigrations

# Frontend changes
cd ../frontend/src
vim pages/dashboard/Reports.tsx  # UI для отчетов

# Tests
cd ../../backend/tests
vim test_reports.py  # Unit тесты
```

3. **Локальная проверка:**
```bash
# В корне проекта
make test-unit           # Быстрые unit тесты
make test-integration    # Более медленные integration тесты
make lint                # Проверка стиля кода

# Если что-то не так - исправить
make format              # Автоформатирование
```

4. **Commit и Push:**
```bash
git add .
git commit -m "feat: add new report type for teachers

- Add ReportTemplate model
- Add API endpoints for report generation
- Add UI for report creation
- Add tests for report functionality"

git push origin feature/new-report-type
```

5. **Создание Pull Request:**
- Перейдите на GitHub
- Нажмите "Compare & pull request"
- Заполните PR template:
  - ✅ Описание изменений
  - ✅ Тип изменений (New feature)
  - ✅ Связанные issues
  - ✅ Checklist выполнен
- Создайте PR в `develop`

6. **CI/CD автоматически:**
- ✅ Запустит Backend Unit Tests (2-3 минуты)
- ✅ Запустит Frontend Unit Tests (1-2 минуты)
- ✅ Запустит Integration Tests (3-5 минут)
- ✅ Запустит E2E Tests (5-10 минут)
- ✅ Запустит Lint checks (1 минута)
- ✅ Сгенерирует Coverage report
- ✅ Проверит PR title format
- ✅ Добавит auto-labels

7. **Code Review:**
- Reviewer проверяет код
- CI/CD статус виден в PR:
  ```
  ✅ Backend Unit Tests
  ✅ Frontend Unit Tests
  ✅ Integration Tests
  ✅ E2E Tests
  ✅ Lint & Code Quality
  ✅ Code Coverage (85%)
  ```
- Reviewer оставляет комментарии
- Разработчик вносит изменения (repeat steps 2-6)

8. **Merge в develop:**
- После approval, merge PR
- GitHub Actions автоматически:
  - ✅ Merge в develop
  - ✅ Запускает все тесты снова
  - ✅ **Автоматически деплоит на staging!**

9. **Проверка на staging:**
```bash
# Открыть staging
open https://staging.the-bot.ru

# Проверить новый функционал
# Если ок - готово к production
```

**Итого:** От commit до staging автоматически!

---

## Сценарий 2: Hotfix для Production

### Описание
На production обнаружен критический баг. Нужно срочно исправить.

### Шаги

1. **Создание hotfix branch от main:**
```bash
git checkout main
git pull origin main
git checkout -b hotfix/critical-payment-bug
```

2. **Исправление бага:**
```bash
cd backend/payments
vim views.py  # Исправить баг

# Добавить тест, который воспроизводит баг
cd ../tests
vim test_payments.py  # Regression test
```

3. **Локальная проверка:**
```bash
# Запустить ТОЛЬКО релевантные тесты (быстрее)
cd backend
pytest tests/test_payments.py -v

# Проверить что баг исправлен
make test-unit
```

4. **Commit и Push:**
```bash
git add .
git commit -m "fix: resolve critical payment processing bug

Payment webhook was failing due to incorrect status check.
This caused payments to not be reflected in user accounts.

Fixes #123"

git push origin hotfix/critical-payment-bug
```

5. **Создание PR в main:**
- Создайте PR в `main` (не develop!)
- Пометьте как "urgent" или "hotfix"
- Request review от team lead

6. **Fast-track Review:**
- Team lead быстро проверяет
- CI/CD проходит все тесты
- Approve и merge

7. **Manual Production Deployment:**
```bash
# На GitHub
Actions → Deploy to Production → Run workflow

# Input:
Reason: "Hotfix: Critical payment bug #123"

# Confirm
```

8. **Deployment процесс:**
- ✅ Все тесты проходят
- ✅ Создается backup БД и media
- ✅ Deploy на production
- ✅ Миграции (если есть)
- ✅ Restart services
- ✅ Health check
- ✅ Telegram notification

9. **Verification:**
```bash
# Проверить что production работает
curl https://the-bot.ru/api/health/

# Проверить логи
ssh user@the-bot.ru
sudo journalctl -u the-bot-daphne.service -n 50

# Проверить что баг исправлен
# (попробовать воспроизвести баг)
```

10. **Backport в develop:**
```bash
# Создать PR из hotfix/critical-payment-bug в develop
# Или cherry-pick:
git checkout develop
git cherry-pick <hotfix_commit_hash>
git push origin develop
```

**Итого:** От обнаружения бага до production fix ~ 30-60 минут

---

## Сценарий 3: Release Cycle

### Описание
Команда готова к release новой версии с накопленными features.

### Шаги

1. **Проверка staging:**
```bash
# Убедитесь что все features работают на staging
open https://staging.the-bot.ru

# Smoke testing:
# - Авторизация
# - Основные user flows
# - Все роли (student, teacher, tutor, parent)
# - Payments
# - Chat
```

2. **Создание Release PR:**
```bash
# Создайте PR из develop в main
git checkout develop
git pull origin develop

# На GitHub:
# Create Pull Request: develop → main
# Title: "Release v1.2.0"
```

3. **Release Checklist:**

В PR описании:
```markdown
## Release v1.2.0

### Features
- [ ] New report type for teachers
- [ ] Enhanced dashboard for parents
- [ ] Improved chat UI
- [ ] Payment history page

### Bug Fixes
- [ ] Fixed payment webhook issue
- [ ] Resolved chat connection drops
- [ ] Fixed mobile responsive issues

### Testing
- [ ] All CI/CD tests pass
- [ ] Staging fully tested
- [ ] Security scan passed
- [ ] Performance acceptable

### Documentation
- [ ] CHANGELOG updated
- [ ] API docs updated (if needed)
- [ ] User-facing docs updated (if needed)

### Deployment Plan
- [ ] Backup strategy confirmed
- [ ] Rollback plan prepared
- [ ] Team notified
- [ ] Monitoring prepared
```

4. **Review и Approval:**
- Team lead reviews
- Product owner approves
- All CI/CD checks pass
- Merge PR

5. **Create GitHub Release:**
```bash
# На GitHub
Releases → Create a new release

Tag: v1.2.0
Title: Release v1.2.0
Description:
```

```markdown
# Release v1.2.0 - 2025-11-20

## New Features
- **Reports**: Added new report type for teachers with customizable templates
- **Dashboard**: Enhanced parent dashboard with better child progress visualization
- **Chat**: Improved chat UI with message reactions and file preview
- **Payments**: Added payment history page with detailed transaction info

## Improvements
- Performance: Optimized database queries (30% faster dashboard load)
- UX: Better mobile responsive design for all dashboards
- Security: Enhanced payment webhook validation

## Bug Fixes
- Fixed payment webhook status check (#123)
- Resolved chat connection drops on slow networks (#145)
- Fixed mobile menu overlap on small screens (#156)

## Technical
- Updated Django to 5.2.1
- Updated React to 18.3.1
- Added new database indexes for better performance

## Breaking Changes
None

## Migration Notes
- Run migrations: `python manage.py migrate`
- No manual intervention required

## Contributors
@developer1, @developer2, @developer3

---

**Full Changelog**: https://github.com/USER/THE_BOT_platform/compare/v1.1.0...v1.2.0
```

6. **Automatic Deployment:**
- GitHub Actions автоматически запускает `deploy-production.yml`
- Весь процесс виден в Actions tab

7. **Monitoring (first hour):**
```bash
# Watch logs
ssh user@the-bot.ru
sudo journalctl -u the-bot-daphne.service -f

# Monitor errors
sudo tail -f /var/log/nginx/the-bot-error.log

# Check metrics (если настроены)
# - Response times
# - Error rates
# - Resource usage
```

8. **Announcement:**
```markdown
# В Telegram PUBLIC chat

🎉 THE BOT Platform v1.2.0 Released!

Новые возможности:
✨ Новые типы отчетов для преподавателей
📊 Улучшенный дашборд для родителей
💬 Обновленный интерфейс чата
💳 История платежей

Улучшения производительности и множество исправлений!

Подробности: https://github.com/USER/THE_BOT_platform/releases/tag/v1.2.0
```

**Итого:** Полный release цикл с автоматическим deployment

---

## Сценарий 4: Rollback после Failed Deployment

### Описание
Production deployment прошел, но через 10 минут обнаружена критическая проблема.

### Шаги

1. **Обнаружение проблемы:**
```bash
# Пользователи сообщают о проблеме
# Или мониторинг показывает ошибки

# Проверка логов
ssh user@the-bot.ru
sudo journalctl -u the-bot-daphne.service -n 100

# Видим:
# ERROR: Database connection timeout
# ERROR: Migration 0015 failed
```

2. **Быстрое решение: Rollback:**

**Option A: Automatic Rollback (если health check failed)**
- Workflow автоматически откатился к предыдущей версии

**Option B: Manual Rollback**
```bash
# SSH на production
ssh user@the-bot.ru
cd /home/deploy/the-bot-platform

# Откат кода
git log --oneline -5
git reset --hard HEAD~1  # Откат к предыдущему коммиту

# Откат миграций (если нужно)
cd backend
source ../.venv/bin/activate
python manage.py migrate materials 0014  # Откат к предыдущей миграции

# Restart services
sudo systemctl restart the-bot-daphne.service
sudo systemctl restart the-bot-celery-worker.service
sudo systemctl restart the-bot-celery-beat.service

# Verify
curl https://the-bot.ru/api/health/
```

3. **Verification:**
```bash
# Проверить основные функции
curl https://the-bot.ru/api/auth/me/
curl https://the-bot.ru/api/materials/

# Проверить логи
sudo journalctl -u the-bot-daphne.service -n 50
# Ошибок нет, все работает
```

4. **Communication:**
```markdown
# Telegram LOG chat

⚠️ Production Rollback Executed

Время: 14:30 UTC
Причина: Database migration failure
Действие: Rollback к v1.1.0
Статус: ✅ Успешно, сервис восстановлен

Downtime: ~5 минут

Анализ проблемы в процессе.
```

5. **Post-mortem:**
```bash
# Создать issue на GitHub
Title: "Post-mortem: Failed deployment v1.2.0"

Content:
- Что пошло не так
- Почему не поймали в staging/CI
- Как предотвратить в будущем
- Action items
```

6. **Исправление и повторный deploy:**
```bash
# Исправить проблему в develop
git checkout develop
# ... fix migration issue ...
git commit -m "fix: resolve migration conflict in materials app"

# Test on staging
git push origin develop
# Automatic deploy to staging

# Test thoroughly on staging
# ...

# When ready, repeat release process
```

**Итого:** От обнаружения до rollback ~ 5-10 минут

---

## Сценарий 5: Dependency Update (Dependabot)

### Описание
Dependabot создал PR для обновления зависимостей.

### Шаги

1. **Dependabot создает PR:**
```
Title: "Bump django from 5.2.0 to 5.2.1"

Description:
Bumps django from 5.2.0 to 5.2.1.

Release notes: ...
Changelog: ...
Commits: ...
```

2. **Автоматические проверки:**
- ✅ CI/CD запускается автоматически
- ✅ Все тесты проходят
- ✅ Lint checks pass
- ✅ Security scan pass

3. **Review:**
```bash
# Проверить changelog Django 5.2.1
# Убедиться что нет breaking changes

# Если minor update и тесты проходят - safe to merge
# Если major update - более тщательная проверка
```

4. **Merge:**
- Approve and merge PR
- Dependabot автоматически обновит другие PRs (rebase)

5. **Deploy flow:**
- Merge в develop → auto deploy to staging
- Проверить на staging
- Release в main → production

**Итого:** Автоматическое обновление зависимостей с минимальным усилием

---

## Сценарий 6: Security Vulnerability

### Описание
Security scan обнаружил уязвимость в зависимости.

### Шаги

1. **Security Alert:**
```
GitHub Security Alert:

High severity vulnerability in package 'requests'
CVE-2024-XXXXX: Request smuggling vulnerability
Affected versions: < 2.32.0
Fix: Update to >= 2.32.0
```

2. **Automatic PR from Dependabot:**
- Dependabot автоматически создает PR
- Title: "Bump requests from 2.31.0 to 2.32.0 (security)"

3. **CI/CD проверка:**
- All tests run automatically
- Security scan re-run

4. **Fast-track:**
```bash
# Если тесты проходят - немедленно merge
# Security updates имеют приоритет
```

5. **Hotfix deployment:**
```bash
# Deploy через hotfix process (Сценарий 2)
# Не ждать обычного release цикла
```

**Итого:** От обнаружения уязвимости до production fix ~ 1-2 часа

---

## Сценарий 7: Adding E2E Test

### Описание
Разработчик добавляет новый E2E тест для критического user flow.

### Шаги

1. **Создание теста:**
```typescript
// tests/e2e/payment-flow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Payment Flow', () => {
  test('parent can pay for subject subscription', async ({ page }) => {
    // Login as parent
    await page.goto('http://localhost:8080');
    await page.getByLabel('Email').fill('parent@test.com');
    await page.getByLabel('Password').fill('password123');
    await page.getByRole('button', { name: 'Войти' }).click();

    // Navigate to children
    await expect(page.getByRole('heading', { name: 'Мои дети' })).toBeVisible();

    // Select child
    await page.getByRole('button', { name: 'Иван Иванов' }).click();

    // Click pay button
    await page.getByRole('button', { name: 'Оплатить предмет' }).click();

    // Verify payment page
    await expect(page.getByText('Оплата подписки')).toBeVisible();
    await expect(page.getByText('5000 ₽')).toBeVisible();

    // In test mode, verify test amount
    await expect(page.getByText('1 ₽')).toBeVisible(); // Test mode

    // Complete payment
    await page.getByRole('button', { name: 'Оплатить' }).click();

    // Wait for redirect
    await page.waitForURL('**/payment-success');

    // Verify success
    await expect(page.getByText('Оплата успешна')).toBeVisible();
  });
});
```

2. **Локальный запуск:**
```bash
# Start services
./start.sh

# In another terminal
npx playwright test tests/e2e/payment-flow.spec.ts

# Debug if needed
npx playwright test --debug
```

3. **Commit:**
```bash
git add tests/e2e/payment-flow.spec.ts
git commit -m "test: add E2E test for payment flow"
git push
```

4. **CI/CD автоматически:**
- E2E workflow запустится
- Тест выполнится на 3 браузерах (chromium, firefox, webkit)
- Если failed - artifacts (screenshots, videos) загрузятся

5. **Review:**
- Reviewer видит что E2E test добавлен
- CI/CD показывает что тест проходит
- Merge

**Итого:** E2E тест автоматически выполняется в CI/CD на всех PR

---

## Полезные команды

### Локальная разработка

```bash
# Быстрая проверка перед push
make test-unit && make lint

# Полная проверка (как в CI)
make test && make lint && make test-e2e

# Только backend
cd backend && pytest -m unit

# Только frontend
cd frontend && npm test

# Specific test
cd backend && pytest tests/test_payments.py::TestPaymentWebhook::test_payment_succeeded
```

### Мониторинг CI/CD

```bash
# Статус текущих workflows
gh run list --limit 10

# Логи конкретного workflow
gh run view <run-id> --log

# Watch workflow
gh run watch <run-id>
```

### Debugging failed CI

```bash
# Download artifacts
gh run download <run-id>

# View failed test logs
cat pytest-report.html

# View Playwright report
npx playwright show-report playwright-report/
```

## Tips & Tricks

### Пропуск CI для trivial changes

```bash
# Добавьте [skip ci] в commit message
git commit -m "docs: fix typo [skip ci]"

# CI не запустится
```

### Re-run failed jobs

```bash
# На GitHub
Actions → Select failed workflow → Re-run failed jobs
```

### Local CI simulation

```bash
# Используйте act для локального запуска GitHub Actions
brew install act  # macOS
apt install act   # Linux

# Run workflow locally
act -W .github/workflows/backend-unit-tests.yml
```

### Conditional workflows

```yaml
# В workflow file
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

Эти примеры покрывают основные сценарии использования CI/CD pipeline для THE BOT Platform.
