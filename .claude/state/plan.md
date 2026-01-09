# План: Исправление rsync-deploy-native.sh

## Обзор
Исправление 12 критических и высоких проблем в deployment скрипте, найденных reviewer.

## Файл
`/home/mego/Python Projects/THE_BOT_platform/scripts/deployment/rsync-deploy-native.sh`

## Задачи

### PHASE 1: Критические проблемы (исправляются в одной итерации)

1. **exit 0 перед PHASE 6-8 (линия ~590)**
   - Переместить `exit 0` в конец скрипта (после Phase 8)
   - Удалить преждевременный exit

2. **migrate --check перед migrate (линия ~473)**
   - Добавить `python manage.py migrate --check` ДО `python manage.py migrate`
   - В PHASE 5 Database Migrations

3. **Двойной exit в trap (линия ~259)**
   - Оставить только один `exit 1` в trap handler
   - Удалить exit из cleanup функции

4. **Hardcoded пути в heredoc (линии ~482, ~520)**
   - Экспортировать PROD_HOME, PROD_USER, BACKUP_DIR в SSH heredoc
   - Заменить hardcoded `/home/mg/backups` на `${BACKUP_DIR}`

5. **Database backup без chmod 600 (линия ~300+)**
   - Добавить `chmod 600 *.sql` после pg_dump, перед gzip
   - Защитить файлы с паролями

6. **Отсутствует проверка cd перед npm install (линия ~250+)**
   - Добавить `cd frontend || exit 1` с проверкой успеха
   - Логировать ошибку если cd упал

7. **LOCAL_PATH использует ${BASH_SOURCE[0]} неправильно (линия ~190+)**
   - Использовать: `LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"`
   - Или передать как параметр функции

8. **Health check маскирует ошибки через || true (линия ~673)**
   - Удалить `|| true` из curl
   - Логировать warning если health check упал
   - Не считать это ошибкой, но информировать

9. **Отсутствуют кавычки вокруг $PROD_HOME в SSH (линия ~283+)**
   - Заменить `${PROD_HOME}` на `"${PROD_HOME}"` везде в SSH блоках
   - Защитить от пробелов в пути

10. **Дублирование кода в PHASE 5 (линия ~320+)**
    - Объединить два блока (с условием SKIP_MIGRATIONS и без) в один
    - Использовать if/else для SKIP_MIGRATIONS

11. **Database backup failure логируется как warning (линия ~340+)**
    - Изменить на log_error
    - Добавить `exit 1` если pg_dump упал

12. **DEPLOY_LOG в /tmp может быть удален (линия ~175+)**
    - Перенести логирование в `$PROD_HOME/logs/` или в journalctl
    - Убедиться что директория существует и имеет права

## Verification
- `bash -n scripts/deployment/rsync-deploy-native.sh` - синтаксис проходит
- Все 12 проблем исправлены
- Логирование детальное
- Error handling на месте
