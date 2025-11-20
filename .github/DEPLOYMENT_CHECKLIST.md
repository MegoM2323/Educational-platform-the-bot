# Deployment Checklist для THE BOT Platform

## Pre-Deployment Checklist

### 1. Код и тесты

- [ ] Все изменения закоммичены и запушены
- [ ] Unit тесты проходят локально (`make test-unit`)
- [ ] Integration тесты проходят локально (`make test-integration`)
- [ ] E2E тесты проходят локально (`make test-e2e`)
- [ ] Линтинг проходит без ошибок (`make lint`)
- [ ] Coverage >= 80% для critical paths
- [ ] Нет TODO или FIXME в продакшн коде

### 2. Код ревью

- [ ] Pull Request создан и прошел ревью
- [ ] Все комментарии ревьюеров обработаны
- [ ] CI/CD pipeline прошел успешно (все зеленые галочки)
- [ ] Нет merge conflicts
- [ ] Branch protection rules соблюдены

### 3. База данных

- [ ] Миграции созданы (`make makemigrations`)
- [ ] Миграции протестированы локально (`make migrate`)
- [ ] Миграции обратимы (есть reverse операции)
- [ ] Нет data loss операций без backup
- [ ] Schema changes не ломают старый код (backward compatible)

### 4. Frontend

- [ ] Production build успешен (`npm run build`)
- [ ] Нет console.log в production коде
- [ ] Env variables правильно настроены
- [ ] Assets оптимизированы
- [ ] Проверена работа в Chrome, Firefox, Safari

### 5. Backend

- [ ] Все зависимости в requirements.txt
- [ ] Нет DEBUG=True в production
- [ ] SECRET_KEY не захардкожен
- [ ] ALLOWED_HOSTS настроен правильно
- [ ] CORS настроен правильно

### 6. Безопасность

- [ ] Нет секретов в коде или .env файлах в репозитории
- [ ] Все sensitive данные в environment variables
- [ ] SQL injection защита активна
- [ ] XSS защита активна
- [ ] CSRF protection включен
- [ ] Security scan прошел (`security-scan.yml`)

### 7. Performance

- [ ] Database queries оптимизированы (select_related, prefetch_related)
- [ ] Нет N+1 queries
- [ ] Static files сжаты
- [ ] Images оптимизированы
- [ ] Caching настроен (Redis)

### 8. Monitoring

- [ ] Логирование настроено
- [ ] Error tracking работает
- [ ] Health check endpoint работает (`/api/health/`)
- [ ] Metrics собираются

## Staging Deployment Checklist

### Pre-Staging

- [ ] Все изменения в ветке `develop`
- [ ] Pull Request merged в `develop`
- [ ] CI/CD pipeline успешно прошел

### During Staging Deployment

- [ ] Push в `develop` сделан
- [ ] `deploy-staging.yml` workflow запустился
- [ ] Все тесты прошли
- [ ] Deployment на staging успешен
- [ ] Health check прошел

### Post-Staging

- [ ] Staging сервер доступен (https://staging.the-bot.ru)
- [ ] Основные функции работают:
  - [ ] Авторизация
  - [ ] Дашборды всех ролей
  - [ ] Создание и редактирование материалов
  - [ ] Чат работает
  - [ ] Payments (в тестовом режиме)
  - [ ] File uploads
  - [ ] Reports
- [ ] Нет критических ошибок в логах
- [ ] Нет memory leaks
- [ ] Response time приемлемый
- [ ] WebSocket подключения работают

### Staging Testing

- [ ] Manual smoke testing выполнен
- [ ] Critical user flows протестированы
- [ ] Edge cases проверены
- [ ] Mobile responsive проверен
- [ ] Нет broken links
- [ ] Email notifications работают (если есть)
- [ ] Telegram notifications работают

## Production Deployment Checklist

### Pre-Production

- [ ] Все тесты на staging прошли успешно
- [ ] Stakeholders одобрили release
- [ ] Release notes подготовлены
- [ ] Rollback plan подготовлен
- [ ] Backup plan подготовлен
- [ ] Maintenance window запланирован (если нужен)

### Backup Creation

- [ ] Database backup создан автоматически (в workflow)
- [ ] Media files backup создан
- [ ] Backup проверен и доступен
- [ ] Backup retention policy настроена

### Production Deployment

**Метод 1: Manual Dispatch**
- [ ] Открыт Actions → Deploy to Production
- [ ] Нажат "Run workflow"
- [ ] Указана причина деплоя
- [ ] Workflow запущен

**Метод 2: Release**
- [ ] Release создан на GitHub
- [ ] Release notes заполнены
- [ ] Tag создан (semver: v1.2.3)
- [ ] Workflow автоматически запустился

### During Production Deployment

- [ ] Workflow `deploy-production.yml` запустился
- [ ] Все тесты прошли
- [ ] Backup создан
- [ ] Deployment на production начался
- [ ] Миграции прошли успешно
- [ ] Services перезапустились
- [ ] Health check прошел

### Post-Production

Immediate checks (first 5 minutes):
- [ ] Production сервер доступен (https://the-bot.ru)
- [ ] Health check endpoint отвечает
- [ ] Нет 5xx errors в логах
- [ ] Services запущены и стабильны
  ```bash
  sudo systemctl status the-bot-daphne.service
  sudo systemctl status the-bot-celery-worker.service
  sudo systemctl status the-bot-celery-beat.service
  ```

Critical functionality (first 15 minutes):
- [ ] Авторизация работает
- [ ] Главная страница загружается
- [ ] API endpoints отвечают
- [ ] WebSocket подключения работают
- [ ] Celery tasks выполняются
- [ ] Database queries работают
- [ ] Redis доступен

Full smoke test (first 30 minutes):
- [ ] Все основные user flows работают:
  - [ ] Student: просмотр материалов, отправка заданий
  - [ ] Teacher: создание материалов, проверка заданий
  - [ ] Tutor: управление студентами, назначение предметов
  - [ ] Parent: просмотр детей, оплата подписок
- [ ] File uploads работают
- [ ] Payments работают (создание подписки)
- [ ] Recurring payments обрабатываются (Celery)
- [ ] Chat работает
- [ ] Reports отправляются и получаются
- [ ] Telegram notifications приходят

Monitoring (first hour):
- [ ] Error rate нормальный
- [ ] Response times приемлемые
- [ ] Memory usage стабильный
- [ ] CPU usage нормальный
- [ ] Disk usage в пределах нормы
- [ ] Database connections в норме
- [ ] Нет memory leaks

### Rollback (if needed)

Если что-то пошло не так:

1. **Automatic rollback (в workflow)**
   - Срабатывает автоматически при failed health check
   - Git reset к предыдущему коммиту
   - Services перезапускаются

2. **Manual rollback**
   ```bash
   # SSH на сервер
   ssh user@the-bot.ru

   # Переход к предыдущей версии
   cd /path/to/project
   git log --oneline -5  # посмотреть последние коммиты
   git reset --hard <previous_commit_hash>

   # Restart services
   sudo systemctl restart the-bot-daphne.service
   sudo systemctl restart the-bot-celery-worker.service
   sudo systemctl restart the-bot-celery-beat.service

   # Verify
   curl https://the-bot.ru/api/health/
   ```

3. **Database rollback (if migrations failed)**
   ```bash
   cd backend
   python manage.py migrate <app_name> <previous_migration_number>
   ```

4. **Restore from backup (extreme case)**
   ```bash
   # Restore database
   python manage.py loaddata backup.json

   # Restore media files
   tar -xzf media_backup.tar.gz -C media/
   ```

### Post-Deployment Communication

- [ ] Telegram notification отправлено (автоматически)
- [ ] Stakeholders уведомлены
- [ ] Documentation обновлена (если нужно)
- [ ] Release notes опубликованы
- [ ] Known issues задокументированы (если есть)

## Monitoring (first 24 hours)

- [ ] Error logs проверяются каждые 2 часа
- [ ] Performance metrics мониторятся
- [ ] User feedback собирается
- [ ] Hotfix готов при необходимости

## Week 1 Post-Deployment

- [ ] No critical bugs reported
- [ ] Performance stable
- [ ] User feedback positive
- [ ] Metrics within expected range

## Emergency Contacts

- **DevOps:** [contact info]
- **Backend Lead:** [contact info]
- **Frontend Lead:** [contact info]
- **Product Owner:** [contact info]

## Common Issues & Solutions

### Issue: Health check fails

**Solution:**
```bash
# Check services
sudo systemctl status the-bot-daphne.service
sudo journalctl -u the-bot-daphne.service -n 50

# Check nginx
sudo nginx -t
sudo systemctl status nginx

# Check logs
sudo tail -f /var/log/nginx/the-bot-error.log
```

### Issue: Database connection timeout

**Solution:**
```bash
# Increase timeout in .env
DB_CONNECT_TIMEOUT=60

# Restart services
sudo systemctl restart the-bot-daphne.service
```

### Issue: Celery tasks not running

**Solution:**
```bash
# Check Redis
redis-cli ping

# Check Celery worker
sudo systemctl status the-bot-celery-worker.service
sudo journalctl -u the-bot-celery-worker.service -f

# Restart Celery
sudo systemctl restart the-bot-celery-worker.service
sudo systemctl restart the-bot-celery-beat.service
```

### Issue: Frontend assets not loading

**Solution:**
```bash
# Check nginx config
sudo nginx -t

# Rebuild frontend
cd frontend
npm run build

# Collect static
cd ../backend
python manage.py collectstatic --noinput

# Reload nginx
sudo systemctl reload nginx
```

### Issue: WebSocket connections failing

**Solution:**
```bash
# Check Daphne is running
sudo systemctl status the-bot-daphne.service

# Check Redis channel layer
redis-cli
> KEYS *

# Check nginx WebSocket config
sudo nano /etc/nginx/sites-available/the-bot
# Look for:
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";
```

## Notes

- Всегда имейте план B
- Никогда не деплойте в пятницу вечером
- Всегда проверяйте backup перед деплоем
- Rollback лучше чем broken production
- Communication is key - держите команду в курсе

## Sign-off

Deployment completed by: ________________
Date: ________________
Time: ________________
Version: ________________
Status: ☐ Success ☐ Partial ☐ Rollback
