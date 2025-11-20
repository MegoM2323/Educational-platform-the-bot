# GitHub Secrets Setup Guide

## Как добавить secrets в GitHub

1. Откройте репозиторий на GitHub
2. Перейдите в **Settings** → **Secrets and variables** → **Actions**
3. Нажмите **New repository secret**
4. Введите **Name** и **Value**
5. Нажмите **Add secret**

## Обязательные Secrets

### Database Secrets

#### `DATABASE_URL` (для CI/CD тестов используется PostgreSQL в GitHub Actions)
```
postgres://user:password@host:port/database
```
**Пример:**
```
postgres://thebot_user:secure_password@db.example.com:5432/thebot_production
```

### Supabase Secrets

#### `SUPABASE_URL`
```
https://your-project-id.supabase.co
```
**Где найти:** Supabase Dashboard → Settings → API → Project URL

#### `SUPABASE_KEY`
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
**Где найти:** Supabase Dashboard → Settings → API → Project API keys → `anon` `public`

#### `SUPABASE_SERVICE_ROLE_KEY`
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
**Где найти:** Supabase Dashboard → Settings → API → Project API keys → `service_role` `secret`

⚠️ **ВАЖНО:** Service role key имеет полные права, храните его в секрете!

### Payment Secrets (YooKassa)

#### `YOOKASSA_SHOP_ID`
```
123456
```
**Где найти:** YooKassa Dashboard → Настройки → Shop ID

#### `YOOKASSA_SECRET_KEY`
```
live_secretkey_your_secret_key_here
```
**Где найти:** YooKassa Dashboard → Настройки → Secret key

⚠️ **ВАЖНО:** Используйте `test_` ключ для staging, `live_` для production!

### Telegram Secrets

#### `TELEGRAM_BOT_TOKEN`
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
```
**Где найти:**
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Используйте команду `/newbot`
3. BotFather даст вам токен

#### `TELEGRAM_PUBLIC_CHAT_ID`
```
-1001234567890
```
**Где найти:**
1. Добавьте бота в группу
2. Отправьте сообщение в группу
3. Перейдите: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Найдите `"chat":{"id":-1001234567890,...}`

#### `TELEGRAM_LOG_CHAT_ID`
```
-1001234567890
```
**Для логов и уведомлений (может быть отдельная группа или та же)**

### Code Coverage

#### `CODECOV_TOKEN`
```
abc123-def456-ghi789-jkl012
```
**Где найти:**
1. Зарегистрируйтесь на https://codecov.io
2. Подключите GitHub репозиторий
3. Settings → копируйте Repository Upload Token

### Deployment Secrets - Staging

#### `STAGING_HOST`
```
staging.the-bot.ru
```
**IP адрес или domain staging сервера**

#### `STAGING_USER`
```
deploy
```
**Username для SSH подключения**

#### `STAGING_SSH_KEY`
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
-----END OPENSSH PRIVATE KEY-----
```

**Как создать:**
```bash
# На локальной машине
ssh-keygen -t ed25519 -C "github-actions-staging" -f ~/.ssh/github_staging_deploy

# Скопируйте ПРИВАТНЫЙ ключ целиком (включая BEGIN и END строки)
cat ~/.ssh/github_staging_deploy

# Добавьте ПУБЛИЧНЫЙ ключ на staging сервер
ssh-copy-id -i ~/.ssh/github_staging_deploy.pub deploy@staging.the-bot.ru

# Или вручную на сервере:
# cat ~/.ssh/github_staging_deploy.pub >> ~/.ssh/authorized_keys
```

#### `STAGING_PATH`
```
/home/deploy/the-bot-staging
```
**Полный путь к проекту на staging сервере**

### Deployment Secrets - Production

#### `PRODUCTION_HOST`
```
the-bot.ru
```
**IP адрес или domain production сервера**

#### `PRODUCTION_USER`
```
deploy
```
**Username для SSH подключения**

#### `PRODUCTION_SSH_KEY`
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
-----END OPENSSH PRIVATE KEY-----
```

**Как создать:**
```bash
# На локальной машине
ssh-keygen -t ed25519 -C "github-actions-production" -f ~/.ssh/github_production_deploy

# Скопируйте ПРИВАТНЫЙ ключ целиком
cat ~/.ssh/github_production_deploy

# Добавьте ПУБЛИЧНЫЙ ключ на production сервер
ssh-copy-id -i ~/.ssh/github_production_deploy.pub deploy@the-bot.ru
```

⚠️ **ВАЖНО:** Используйте отдельные SSH ключи для staging и production!

#### `PRODUCTION_PATH`
```
/home/deploy/the-bot-platform
```
**Полный путь к проекту на production сервере**

## Environments (опционально, для дополнительной защиты)

Вы можете создать отдельные environments для staging и production с дополнительными правилами:

### Создание Environment

1. Settings → Environments → New environment
2. Введите имя: `staging` или `production`

### Protection Rules для Production

- **Required reviewers:** Укажите кто должен одобрить деплой (1-6 человек)
- **Wait timer:** Задержка перед деплоем (0-43200 минут)
- **Deployment branches:** Ограничьте деплой только с определенных веток (например, только `main`)

### Environment Secrets

После создания environment можно добавить специфичные для него секреты:
- Settings → Environments → [environment name] → Add secret

Это удобно если у вас разные credentials для staging и production.

## Проверка Secrets

После добавления всех secrets:

1. Перейдите в Actions → любой workflow
2. Запустите workflow вручную или сделайте push
3. Проверьте что secrets корректно подставляются (они будут скрыты как `***`)

## Security Best Practices

### DO ✅

- ✅ Используйте минимально необходимые permissions
- ✅ Регулярно ротируйте секреты (раз в 3-6 месяцев)
- ✅ Используйте разные credentials для staging и production
- ✅ Используйте отдельные SSH ключи для каждого environment
- ✅ Используйте test credentials для тестов в CI/CD
- ✅ Ограничьте доступ к secrets только необходимым людям
- ✅ Audit log проверяйте регулярно
- ✅ Используйте environments с required reviewers для production

### DON'T ❌

- ❌ Не коммитьте secrets в git
- ❌ Не используйте production credentials в staging/development
- ❌ Не расшаривайте SSH ключи между разными сервисами
- ❌ Не используйте простые пароли
- ❌ Не логируйте secrets в console
- ❌ Не используйте одинаковые credentials для разных сервисов

## Troubleshooting

### Secret не работает

1. **Проверьте имя secret** - точное совпадение с `${{ secrets.SECRET_NAME }}`
2. **Проверьте значение** - нет лишних пробелов/переносов строк в начале/конце
3. **Проверьте scope** - secret добавлен на уровне repository, не organization
4. **Проверьте permissions** - workflow имеет доступ к secrets

### SSH key не работает

```bash
# Проверьте формат ключа
cat ~/.ssh/your_key
# Должен начинаться с: -----BEGIN OPENSSH PRIVATE KEY-----
# И заканчиваться: -----END OPENSSH PRIVATE KEY-----

# Проверьте права на ключ локально
chmod 600 ~/.ssh/your_key

# Проверьте что публичный ключ добавлен на сервер
ssh -i ~/.ssh/your_key user@server

# Проверьте права на сервере
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### Database connection fails

```bash
# Проверьте формат DATABASE_URL
# Правильно: postgres://user:pass@host:5432/db
# Неправильно: postgresql://... (для psycopg2)

# Проверьте что хост доступен из GitHub Actions
# (может потребоваться whitelist IP GitHub Actions в firewall)
```

## Шаблон для копирования

Используйте этот шаблон для быстрой настройки secrets:

```bash
# Database
DATABASE_URL=postgres://user:pass@host:5432/db

# Supabase
SUPABASE_URL=https://project.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Payments
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=live_secret...

# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_PUBLIC_CHAT_ID=-1001234567890
TELEGRAM_LOG_CHAT_ID=-1001234567890

# Codecov
CODECOV_TOKEN=abc123...

# Staging
STAGING_HOST=staging.the-bot.ru
STAGING_USER=deploy
STAGING_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
STAGING_PATH=/home/deploy/the-bot-staging

# Production
PRODUCTION_HOST=the-bot.ru
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
PRODUCTION_PATH=/home/deploy/the-bot-platform
```

## Quick Setup Script

Скрипт для добавления всех secrets через GitHub CLI:

```bash
#!/bin/bash
# setup_github_secrets.sh

# Требуется: GitHub CLI (https://cli.github.com/)
# Установка: brew install gh (macOS) или apt install gh (Ubuntu)

# Login
gh auth login

# Database
gh secret set DATABASE_URL

# Supabase
gh secret set SUPABASE_URL
gh secret set SUPABASE_KEY
gh secret set SUPABASE_SERVICE_ROLE_KEY

# Payments
gh secret set YOOKASSA_SHOP_ID
gh secret set YOOKASSA_SECRET_KEY

# Telegram
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_PUBLIC_CHAT_ID
gh secret set TELEGRAM_LOG_CHAT_ID

# Codecov
gh secret set CODECOV_TOKEN

# Staging
gh secret set STAGING_HOST
gh secret set STAGING_USER
gh secret set STAGING_SSH_KEY < ~/.ssh/github_staging_deploy
gh secret set STAGING_PATH

# Production
gh secret set PRODUCTION_HOST
gh secret set PRODUCTION_USER
gh secret set PRODUCTION_SSH_KEY < ~/.ssh/github_production_deploy
gh secret set PRODUCTION_PATH

echo "All secrets set successfully!"
```

Использование:
```bash
chmod +x setup_github_secrets.sh
./setup_github_secrets.sh
```

## Support

Если возникли проблемы:
1. Проверьте [GitHub Actions documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
2. Проверьте логи workflow в Actions
3. Создайте issue в репозитории
