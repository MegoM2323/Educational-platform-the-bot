#!/usr/bin/env bash
set -euo pipefail

# ================== CONFIG ==================
DOMAIN="the-bot.ru"
WWW_DOMAIN="www.the-bot.ru"
ADMIN_EMAIL="admin@the-bot.ru"

# Абсолютные пути с учётом пробелов
# Автоопределение корня проекта по расположению скрипта
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$PROJECT_ROOT/.venv"

PYTHON_BIN="python3"      # для Ubuntu безопаснее явно python3
DJANGO_BIND_IP="127.0.0.1"
ASGI_PORT="8001"         # Daphne порт (HTTP+WS)
# На Ubuntu используется схема sites-available/sites-enabled
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/the-bot"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/the-bot"

# ================== HELPERS ==================
log() { echo -e "[$(date +'%H:%M:%S')] $*"; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Требуется команда: $1"; exit 1; }; }

# ================== PRE-CHECKS ==================
need_cmd sudo
need_cmd apt-get
need_cmd systemctl

if [ ! -d "$BACKEND_DIR" ] || [ ! -d "$FRONTEND_DIR" ]; then
  echo "Не найден проект по пути: $PROJECT_ROOT"
  exit 1
fi

# ================== ENV CONFIGURATION AUTO-SWITCH ==================
# Проверяем и переключаем .env с localhost на production конфигурацию
log "Проверяю конфигурацию .env..."

ENV_FILE="$PROJECT_ROOT/.env"
ENV_NEEDS_UPDATE=false

if [ -f "$ENV_FILE" ]; then
  # Проверяем на localhost-specific значения в .env
  if grep -q "VITE_DJANGO_API_URL.*localhost\|FRONTEND_URL.*localhost\|VITE_WS_URL.*localhost" "$ENV_FILE" 2>/dev/null; then
    log "⚠️  Обнаружена LOCALHOST конфигурация в .env"
    log "   Переключаю на PRODUCTION конфигурацию для сервера ($DOMAIN)..."

    # Создаём резервную копию
    cp "$ENV_FILE" "$ENV_FILE.backup.localhost"
    log "   (резервная копия: $ENV_FILE.backup.localhost)"

    # Заменяем localhost значения на production
    # Используем макрос для безопасной подстановки
    sed -i.tmp \
      -e "s|VITE_DJANGO_API_URL=.*localhost.*|VITE_DJANGO_API_URL=https://$DOMAIN/api|g" \
      -e "s|FRONTEND_URL=.*localhost.*|FRONTEND_URL=https://$DOMAIN|g" \
      -e "s|VITE_WS_URL=.*ws://localhost.*|VITE_WS_URL=wss://$DOMAIN/ws|g" \
      "$ENV_FILE"

    # Удаляем временный файл
    rm -f "$ENV_FILE.tmp"

    log "✅ .env переключён на production конфигурацию"
    log "   VITE_DJANGO_API_URL=https://$DOMAIN/api"
    log "   FRONTEND_URL=https://$DOMAIN"
    log "   VITE_WS_URL=wss://$DOMAIN/ws"
  else
    log "✅ .env уже настроена на production"
  fi
else
  log "⚠️  Файл .env не найден. Создаётся базовая конфигурация..."
  cat > "$ENV_FILE" <<EOF
# Production Configuration for the-bot.ru
VITE_DJANGO_API_URL=https://$DOMAIN/api
FRONTEND_URL=https://$DOMAIN
VITE_WS_URL=wss://$DOMAIN/ws

# Database
SUPABASE_DB_HOST=your_db_host
SUPABASE_DB_USER=your_db_user
SUPABASE_DB_PASSWORD=your_db_password
SUPABASE_DB_NAME=your_db_name
SUPABASE_DB_PORT=6543

# Payment
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
PAYMENT_TEST_MODE=False

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_PUBLIC_CHAT_ID=your_chat_id
TELEGRAM_LOG_CHAT_ID=your_log_chat_id

# Redis
USE_REDIS_CACHE=True
USE_REDIS_CHANNELS=True
REDIS_URL=redis://127.0.0.1:6379/0

# Debug
DEBUG=False
PAYMENT_DEVELOPMENT_MODE=False
EOF
  log "⚠️  Заполните переменные в .env файле перед запуском сервера"
  exit 1
fi

log "Проверяю ALLOWED_HOSTS в Django..."
if ! grep -Eiq "ALLOWED_HOSTS\s*=.*$DOMAIN" "$BACKEND_DIR/config/settings.py"; then
  log "ВНИМАНИЕ: В $BACKEND_DIR/config/settings.py должен быть добавлен домен в ALLOWED_HOSTS (например: ['$DOMAIN', '$WWW_DOMAIN']). Скрипт его не меняет."
fi

# Автодобавление доменов в ALLOWED_HOSTS при простой форме списка (опционально)
if grep -Eq "^ALLOWED_HOSTS\s*=\s*\[.*\]" "$BACKEND_DIR/config/settings.py" && \
   ! grep -Eiq "ALLOWED_HOSTS\s*=.*($DOMAIN|$WWW_DOMAIN)" "$BACKEND_DIR/config/settings.py"; then
  log "Добавляю домены в ALLOWED_HOSTS автоматически"
  "$VENV_DIR/bin/python" - <<PY
import re, pathlib
p = pathlib.Path(r"$BACKEND_DIR/config/settings.py")
s = p.read_text()
m = re.search(r"^ALLOWED_HOSTS\s*=\s*\[(.*?)\]", s, re.M|re.S)
if m:
    items = [x.strip() for x in m.group(1).split(',') if x.strip()]
    def norm(x):
        return x.strip(" ")
    hosts = [norm(x) for x in items]
    for h in ["'$DOMAIN'", "'$WWW_DOMAIN'"]:
        if h not in hosts:
            hosts.append(h)
    new_list = "[" + ", ".join(hosts) + "]"
    s = s[:m.start()] + f"ALLOWED_HOSTS = {new_list}" + s[m.end():]
    p.write_text(s)
PY
fi

# ================== PACKAGES ==================
log "Устанавливаю системные пакеты (nginx, certbot, python3, node, npm, lsof, coreutils, netcat)..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  nginx certbot python3-certbot-nginx python3 python3-venv nodejs npm lsof coreutils netcat-openbsd

# ================== PYTHON ENV + BACKEND ==================
log "Проверяю .venv и зависимости backend..."

# Проверяем, существует ли виртуальное окружение и работает ли оно
# Также проверяем, что пути в venv корректные (не содержат старые пути)
VENV_BROKEN=false
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/daphne" ]; then
  # Проверяем, что daphne ссылается на правильный python
  if ! head -1 "$VENV_DIR/bin/daphne" | grep -q "$VENV_DIR/bin/python"; then
    log "Обнаружены неправильные пути в виртуальном окружении, пересоздаю..."
    VENV_BROKEN=true
  fi
fi

if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python" ] || ! "$VENV_DIR/bin/python" -c "import django" >/dev/null 2>&1 || [ "$VENV_BROKEN" = true ]; then
  log "Создаю .venv и ставлю зависимости backend..."
  # Удаляем старое виртуальное окружение, если оно сломано
  if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
  fi
  
  # Пытаемся создать venv с установкой последних bundled pip/setuptools
  if ! "$PYTHON_BIN" -m venv --upgrade-deps "$VENV_DIR" 2>/dev/null; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
  
  # Гарантируем наличие pip внутри venv (иногда на Ubuntu он отсутствует)
  if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    "$VENV_DIR/bin/python" -m ensurepip --upgrade || true
  fi

  # Устанавливаем/обновляем pip, setuptools, wheel внутри venv и ставим зависимости
  "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
  "$VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
  
  # Дополнительно устанавливаем модули, которые могут отсутствовать
  "$VENV_DIR/bin/python" -m pip install django-filter Pillow
else
  log "Виртуальное окружение уже существует и работает, пропускаю создание"
fi

# Гарантируем наличие django-filter (модуль django_filters), если он не тянется зависимостями
if ! "$VENV_DIR/bin/python" - <<'PY'
import sys
try:
    import django_filters  # noqa: F401
except Exception:
    sys.exit(1)
else:
    sys.exit(0)
PY
then
  log "Устанавливаю отсутствующий пакет: django-filter"
  "$VENV_DIR/bin/python" -m pip install "django-filter"
fi

# Гарантируем наличие Pillow (для ImageField)
if ! "$VENV_DIR/bin/python" - <<'PY'
import sys
try:
    import PIL  # noqa: F401
except Exception:
    sys.exit(1)
else:
    sys.exit(0)
PY
then
  log "Устанавливаю отсутствующий пакет: Pillow"
  "$VENV_DIR/bin/python" -m pip install "Pillow"
fi

log "Проверяю Django настройки и применяю миграции..."
cd "$BACKEND_DIR"

# Проверяем Django настройки
if ! "$VENV_DIR/bin/python" manage.py check --deploy >/dev/null 2>&1; then
  log "Предупреждение: Django настройки имеют проблемы, но продолжаю..."
fi

# Сначала получаем параметры БД для сетевой проверки
log "Получаю параметры подключения к БД..."
DB_PARAMS=$("$VENV_DIR/bin/python" - <<PY
import os, sys
from dotenv import dotenv_values
from pathlib import Path
from urllib.parse import urlparse

# Загружаем .env из корня проекта
project_root = Path("$PROJECT_ROOT")
env_path = project_root / ".env"

if env_path.exists():
    env_vars = dotenv_values(env_path)
    for k, v in env_vars.items():
        if k and v is not None:
            os.environ[k] = str(v)
else:
    # Пробуем backend/.env
    backend_env = project_root / "backend" / ".env"
    if backend_env.exists():
        env_vars = dotenv_values(backend_env)
        for k, v in env_vars.items():
            if k and v is not None:
                os.environ[k] = str(v)

database_url = os.getenv('DATABASE_URL')
if database_url:
    parsed = urlparse(database_url)
    host = parsed.hostname
    port = str(parsed.port or '5432')
else:
    host = os.getenv('SUPABASE_DB_HOST')
    port = str(os.getenv('SUPABASE_DB_PORT', '6543'))

if host and port:
    print(f"{host}:{port}")
    sys.exit(0)
else:
    print("ERROR: Не удалось определить хост и порт БД", file=sys.stderr)
    sys.exit(1)
PY
)

if [ $? -eq 0 ] && [ -n "$DB_PARAMS" ]; then
  DB_HOST=$(echo "$DB_PARAMS" | cut -d: -f1)
  DB_PORT=$(echo "$DB_PARAMS" | cut -d: -f2)
  
  log "Проверяю сетевую доступность Supabase: $DB_HOST:$DB_PORT"
  
  # Проверка DNS резолюции
  if command -v host >/dev/null 2>&1 || command -v nslookup >/dev/null 2>&1; then
    if host "$DB_HOST" >/dev/null 2>&1 || nslookup "$DB_HOST" >/dev/null 2>&1; then
      log "✅ DNS резолюция успешна для $DB_HOST"
    else
      log "⚠️  Не удалось разрешить DNS для $DB_HOST"
    fi
  fi
  
  # Проверка доступности порта через nc (netcat) или telnet
  if command -v nc >/dev/null 2>&1; then
    log "Проверяю доступность порта через nc (таймаут 10 секунд)..."
    if timeout 10 nc -zv "$DB_HOST" "$DB_PORT" 2>&1 | grep -q "succeeded\|open"; then
      log "✅ Порт $DB_PORT доступен на $DB_HOST"
    else
      log "⚠️  Порт $DB_PORT недоступен или фильтруется на $DB_HOST"
      log "   Это может быть нормально, если используется SSL/TLS"
    fi
  elif command -v telnet >/dev/null 2>&1; then
    log "Проверяю доступность порта через telnet (таймаут 10 секунд)..."
    if timeout 10 telnet "$DB_HOST" "$DB_PORT" </dev/null 2>&1 | grep -q "Connected\|Open"; then
      log "✅ Порт $DB_PORT доступен на $DB_HOST"
    else
      log "⚠️  Порт $DB_PORT недоступен или фильтруется на $DB_HOST"
    fi
  else
    log "⚠️  Команды nc/telnet не найдены, пропускаю проверку порта"
  fi
else
  log "⚠️  Не удалось получить параметры БД для сетевой проверки"
fi

# Проверяем доступность БД через Django с увеличенным таймаутом для сервера
log "Проверяю подключение к БД через Django (таймаут 60 секунд)..."
export DB_CONNECT_TIMEOUT=60  # Увеличиваем таймаут для сервера

"$VENV_DIR/bin/python" - <<'PY'
import os, sys, signal, time, traceback

def timeout_handler(signum, frame):
    print("\n❌ Проверка БД превысила таймаут (60 секунд)")
    print("   Это указывает на проблему с сетевым подключением к Supabase")
    sys.exit(2)

# Устанавливаем обработчик таймаута
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60 секунд для сервера

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    # Устанавливаем увеличенный таймаут для сервера
    if 'DB_CONNECT_TIMEOUT' not in os.environ:
        os.environ['DB_CONNECT_TIMEOUT'] = '60'
    
    print("🔧 Инициализирую Django...")
    import django
    django.setup()
    
    from django.conf import settings
    from django.db import connection
    
    db = settings.DATABASES['default']
    required = ['ENGINE','NAME','USER','HOST']
    missing = [k for k in required if not db.get(k)]
    if missing:
        print(f"❌ Недостаточно параметров БД: {missing}")
        sys.exit(2)
    
    host = db['HOST']
    port = db.get('PORT', '5432')
    name = db['NAME']
    user = db['USER']
    
    print(f"✅ Параметры БД: {host}:{port} / {name}")
    print(f"   Пользователь: {user}")
    print(f"   Таймаут подключения: {os.environ.get('DB_CONNECT_TIMEOUT', '60')} секунд")
    
    # Пытаемся подключиться к БД с детальной диагностикой
    print("🔍 Пытаюсь подключиться к БД...")
    start_time = time.time()
    
    try:
        # Пробуем подключиться через psycopg2 напрямую для более детальной диагностики
        import psycopg2
        from psycopg2 import OperationalError, DatabaseError
        
        print("   Используя psycopg2 для подключения...")
        conn_params = {
            'host': host,
            'port': port,
            'database': name,
            'user': user,
            'password': db.get('PASSWORD', ''),
            'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', '60')),
        }
        
        # Добавляем SSL параметры если есть
        if 'OPTIONS' in db and 'sslmode' in db['OPTIONS']:
            conn_params['sslmode'] = db['OPTIONS']['sslmode']
            print(f"   SSL режим: {conn_params['sslmode']}")
        
        conn = psycopg2.connect(**conn_params)
        elapsed = time.time() - start_time
        print(f"✅ Подключение успешно! (заняло {elapsed:.2f} секунд)")
        
        # Проверяем версию PostgreSQL
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   PostgreSQL: {version[:60]}...")
        
        conn.close()
        signal.alarm(0)
        sys.exit(0)
        
    except OperationalError as e:
        elapsed = time.time() - start_time
        signal.alarm(0)
        print(f"\n❌ Ошибка операционного подключения (после {elapsed:.2f} секунд):")
        print(f"   {str(e)}")
        print("\n   Возможные причины:")
        print("   1. Хост/порт недоступен (проверьте файрвол)")
        print("   2. Неправильные учетные данные")
        print("   3. Проблемы с DNS резолюцией")
        print("   4. SSL/TLS проблемы")
        print("   5. Превышен лимит подключений в Supabase")
        sys.exit(2)
        
    except DatabaseError as e:
        elapsed = time.time() - start_time
        signal.alarm(0)
        print(f"\n❌ Ошибка базы данных (после {elapsed:.2f} секунд):")
        print(f"   {str(e)}")
        sys.exit(2)
        
    except Exception as e:
        elapsed = time.time() - start_time
        signal.alarm(0)
        print(f"\n❌ Неожиданная ошибка при подключении (после {elapsed:.2f} секунд):")
        print(f"   {type(e).__name__}: {str(e)}")
        print("\n   Детали:")
        traceback.print_exc()
        sys.exit(2)
    
except SystemExit as e:
    signal.alarm(0)
    sys.exit(e.code)
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Критическая ошибка: {e}")
    traceback.print_exc()
    sys.exit(2)
PY

DB_CHECK_EXIT_CODE=$?
if [ $DB_CHECK_EXIT_CODE -ne 0 ]; then
  log ""
  log "════════════════════════════════════════════════════════════"
  log "ОШИБКА: Не удалось подключиться к БД Supabase"
  log "════════════════════════════════════════════════════════════"
  log ""
  log "Рекомендации по диагностике:"
  log ""
  log "1. Проверьте доступность Supabase с сервера:"
  if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    log "   nc -zv $DB_HOST $DB_PORT"
    log "   или"
    log "   telnet $DB_HOST $DB_PORT"
  fi
  log ""
  log "2. Проверьте правильность параметров в .env:"
  log "   - DATABASE_URL или SUPABASE_DB_* параметры"
  log "   - DB_CONNECT_TIMEOUT (попробуйте увеличить до 120)"
  log ""
  log "3. Проверьте настройки файрвола на сервере:"
  log "   sudo ufw status"
  log "   sudo iptables -L -n"
  log ""
  log "4. Проверьте логи Supabase на наличие блокировок"
  log ""
  log "5. Попробуйте подключиться вручную:"
  log "   cd $BACKEND_DIR"
  log "   source $VENV_DIR/bin/activate"
  log "   python backend/test_db_connection.py"
  log ""
  log "6. Если проблема сохраняется, проверьте:"
  log "   - Правильность хостнейма Supabase (pooler.supabase.com)"
  log "   - Доступность порта 6543 (connection pooler) или 5432 (прямое)"
  log "   - SSL/TLS сертификаты"
  log ""
  exit 1
fi

# Применяем миграции с увеличенным таймаутом для сервера
log "Применяю миграции..."
# Устанавливаем увеличенный таймаут подключения для сервера (60 секунд, как при проверке)
export DB_CONNECT_TIMEOUT=60

# Проверяем наличие конфликтующих миграций
log "Проверяю наличие конфликтующих миграций..."
MIGRATION_CHECK=$("$VENV_DIR/bin/python" manage.py showmigrations --plan 2>&1)
if echo "$MIGRATION_CHECK" | grep -q "Conflicting migrations\|multiple leaf nodes"; then
  log "⚠️  Обнаружены конфликтующие миграции"
  log "Проверяю, существует ли merge-миграция..."
  # Проверяем, есть ли уже merge-миграция для materials
  if [ -f "$BACKEND_DIR/materials/migrations/0010_merge_0004_0009.py" ]; then
    log "✅ Merge-миграция уже существует, применяю миграции..."
  else
    log "⚠️  Merge-миграция не найдена, но она должна быть создана вручную"
    log "Продолжаю с применением миграций..."
  fi
fi

# Проверяем наличие команды timeout, если есть - используем её
if command -v timeout >/dev/null 2>&1; then
  log "Запускаю миграции с таймаутом 5 минут..."
  if timeout 300 "$VENV_DIR/bin/python" manage.py migrate --noinput; then
    log "✅ Миграции применены успешно"
  else
    MIGRATION_EXIT_CODE=$?
    if [ $MIGRATION_EXIT_CODE -eq 124 ]; then
      log "❌ Миграции превысили таймаут (5 минут)"
      log "Возможные причины:"
      log "  1. Медленное подключение к Supabase БД"
      log "  2. Большой объем данных для миграции"
      log "  3. Блокировки в БД"
      log "  4. Проблемы с сетью между сервером и Supabase"
      log ""
      log "Рекомендации:"
      log "  1. Проверьте скорость подключения к Supabase:"
      log "     nc -zv \$(grep SUPABASE_DB_HOST .env | cut -d= -f2) \$(grep SUPABASE_DB_PORT .env | cut -d= -f2)"
      log "  2. Увеличьте DB_CONNECT_TIMEOUT в .env (например, до 60)"
      log "  3. Запустите миграции вручную для диагностики:"
      log "     cd $BACKEND_DIR && $VENV_DIR/bin/python manage.py migrate --verbosity 2"
      exit 1
    elif [ $MIGRATION_EXIT_CODE -eq 1 ]; then
      # Ошибка миграций (например, конфликт)
      log "❌ Ошибка при применении миграций (код выхода: $MIGRATION_EXIT_CODE)"
      log ""
      log "Попытка разрешить конфликт миграций автоматически..."
      if timeout 60 "$VENV_DIR/bin/python" manage.py makemigrations --merge --noinput 2>&1 | tee /tmp/makemigrations.log; then
        log "✅ Merge-миграция создана, повторяю применение миграций..."
        if timeout 300 "$VENV_DIR/bin/python" manage.py migrate --noinput; then
          log "✅ Миграции применены успешно после разрешения конфликта"
        else
          log "❌ Ошибка после создания merge-миграции"
          log "Проверьте логи выше для деталей"
          exit 1
        fi
      else
        log "❌ Не удалось автоматически разрешить конфликт миграций"
        log "Необходимо разрешить конфликт вручную:"
        log "  1. cd $BACKEND_DIR"
        log "  2. source $VENV_DIR/bin/activate"
        log "  3. python manage.py makemigrations --merge"
        log "  4. Выберите нужные миграции для merge"
        log "  5. python manage.py migrate"
        exit 1
      fi
    else
      log "❌ Ошибка при применении миграций (код выхода: $MIGRATION_EXIT_CODE)"
      log "Проверьте логи выше для деталей"
      exit 1
    fi
  fi
else
  # Если команды timeout нет, запускаем без неё (таймаут будет через DB_CONNECT_TIMEOUT)
  log "Команда timeout не найдена, запускаю миграции без внешнего таймаута..."
  log "Таймаут подключения к БД: $DB_CONNECT_TIMEOUT секунд"
  if "$VENV_DIR/bin/python" manage.py migrate --noinput; then
    log "✅ Миграции применены успешно"
  else
    MIGRATION_EXIT_CODE=$?
    if [ $MIGRATION_EXIT_CODE -eq 1 ]; then
      log "❌ Ошибка при применении миграций (возможно, конфликт)"
      log "Попытка разрешить конфликт..."
      if "$VENV_DIR/bin/python" manage.py makemigrations --merge --noinput; then
        log "✅ Merge-миграция создана, повторяю применение миграций..."
        if "$VENV_DIR/bin/python" manage.py migrate --noinput; then
          log "✅ Миграции применены успешно после разрешения конфликта"
        else
          log "❌ Ошибка после создания merge-миграции"
          exit 1
        fi
      else
        log "❌ Не удалось автоматически разрешить конфликт"
        log "Разрешите конфликт вручную: python manage.py makemigrations --merge"
        exit 1
      fi
    else
      log "❌ Ошибка при применении миграций (код выхода: $MIGRATION_EXIT_CODE)"
      log "Проверьте логи выше для деталей"
      log "Если миграции зависают, установите пакет coreutils для команды timeout"
      exit 1
    fi
  fi
fi

# Создаем суперпользователя для админки, если не существует
log "Проверяю суперпользователя для админки..."
"$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@the-bot.ru').exists():
    User.objects.create_superuser(
        username='admin@the-bot.ru',
        email='admin@the-bot.ru',
        password='admin123',
        first_name='Admin',
        last_name='User',
        role='teacher'
    )
    print('✅ Суперпользователь создан: admin@the-bot.ru / admin123')
else:
    print('✅ Суперпользователь уже существует')
"

# collectstatic с проверкой STATIC_ROOT; если не задан, используем $BACKEND_DIR/staticfiles
if ! "$VENV_DIR/bin/python" - <<'PY'
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django import setup
setup()
from django.conf import settings
sys.exit(0 if getattr(settings, 'STATIC_ROOT', None) else 1)
PY
then
  log "STATIC_ROOT не задан — временно использую $BACKEND_DIR/staticfiles для collectstatic"
  "$VENV_DIR/bin/python" - <<PY
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django import setup
setup()
from django.conf import settings
from django.core.management import call_command
settings.STATIC_ROOT = "$BACKEND_DIR/staticfiles"
os.makedirs(settings.STATIC_ROOT, exist_ok=True)
call_command('collectstatic', '--noinput')
PY
else
  "$VENV_DIR/bin/python" manage.py collectstatic --noinput
fi

# Публикуем статику Django в /var/www/the-bot-static с корректными правами
DJANGO_STATIC_PUBLISH="/var/www/the-bot-static"
sudo mkdir -p "$DJANGO_STATIC_PUBLISH"
if [ -d "$BACKEND_DIR/staticfiles" ]; then
  sudo rsync -a --delete "$BACKEND_DIR/staticfiles/" "$DJANGO_STATIC_PUBLISH/"
fi
sudo chown -R www-data:www-data "$DJANGO_STATIC_PUBLISH"
sudo find "$DJANGO_STATIC_PUBLISH" -type d -exec chmod 755 {} +
sudo find "$DJANGO_STATIC_PUBLISH" -type f -exec chmod 644 {} +

# ================== FRONTEND BUILD ==================
log "Собираю frontend (Vite)..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
  npm ci || npm install
fi
# Пробрасываем URL-ы бекенда и вебсокетов в билд
export VITE_DJANGO_API_URL="https://$DOMAIN/api"
export VITE_WS_URL="wss://$DOMAIN/ws"
npm run build

# Публикуем фронтенд в /var/www/the-bot с корректными правами для nginx
FRONTEND_PUBLISH="/var/www/the-bot"
sudo mkdir -p "$FRONTEND_PUBLISH"
sudo rsync -a --delete "$FRONTEND_DIR/dist/" "$FRONTEND_PUBLISH/"
sudo chown -R www-data:www-data "$FRONTEND_PUBLISH"
sudo find "$FRONTEND_PUBLISH" -type d -exec chmod 755 {} +
sudo find "$FRONTEND_PUBLISH" -type f -exec chmod 644 {} +

# ================== SYSTEMD: CELERY ==================
log "Проверяю Celery и Redis..."
cd "$BACKEND_DIR"

# Проверяем Redis
if ! redis-cli ping >/dev/null 2>&1; then
  log "⚠️  Redis недоступен. Устанавливаю Redis..."
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y redis-server
  sudo systemctl enable redis-server
  sudo systemctl start redis-server
  sleep 2
  
  if ! redis-cli ping >/dev/null 2>&1; then
    log "❌ Не удалось запустить Redis. Celery не будет работать."
  else
    log "✅ Redis установлен и запущен"
  fi
else
  log "✅ Redis доступен"
fi

# Проверяем Celery
if ! "$VENV_DIR/bin/python" -c "from core.celery import app; print('Celery инициализирован')" >/dev/null 2>&1; then
  log "❌ ОШИБКА: Celery приложение не загружается. Проверьте настройки."
else
  log "✅ Celery приложение проверено успешно"
fi

# Останавливаем и удаляем старые сервисы Celery (если есть)
if systemctl list-units --full -all | grep -q "the-bot-celery-worker.service"; then
  log "Останавливаю старый Celery Worker сервис..."
  sudo systemctl stop the-bot-celery-worker.service 2>/dev/null || true
  sudo systemctl disable the-bot-celery-worker.service 2>/dev/null || true
fi

if systemctl list-units --full -all | grep -q "the-bot-celery-beat.service"; then
  log "Останавливаю старый Celery Beat сервис..."
  sudo systemctl stop the-bot-celery-beat.service 2>/dev/null || true
  sudo systemctl disable the-bot-celery-beat.service 2>/dev/null || true
fi

# Создаем директорию для логов Celery
sudo mkdir -p /var/log/celery
sudo chown $(whoami):$(id -gn) /var/log/celery

# Создаем systemd unit для Celery Worker
log "Создаю systemd unit для Celery Worker..."
CELERY_WORKER_UNIT="[Unit]
Description=THE_BOT Celery Worker
After=network.target redis-server.service redis.service

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONPATH=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/celery -A core worker --loglevel=info --concurrency=4 --logfile=/var/log/celery/worker.log
Restart=always
RestartSec=10s
User=$(whoami)
Group=$(id -gn)
StandardOutput=journal
StandardError=journal

# Увеличенные таймауты для запуска
TimeoutStartSec=120s
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
"
echo "$CELERY_WORKER_UNIT" | sudo tee /etc/systemd/system/the-bot-celery-worker.service >/dev/null

# Создаем systemd unit для Celery Beat
log "Создаю systemd unit для Celery Beat (планировщик)..."
CELERY_BEAT_UNIT="[Unit]
Description=THE_BOT Celery Beat (Scheduler)
After=network.target redis-server.service redis.service the-bot-celery-worker.service

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONPATH=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/celery -A core beat --loglevel=info --logfile=/var/log/celery/beat.log
Restart=always
RestartSec=10s
User=$(whoami)
Group=$(id -gn)
StandardOutput=journal
StandardError=journal

# Увеличенные таймауты
TimeoutStartSec=60s
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
"
echo "$CELERY_BEAT_UNIT" | sudo tee /etc/systemd/system/the-bot-celery-beat.service >/dev/null

# Запускаем Celery сервисы
log "Перезагружаю конфигурацию systemd..."
sudo systemctl daemon-reload
sleep 2

log "Включаю автозапуск Celery сервисов..."
sudo systemctl enable the-bot-celery-worker.service
sudo systemctl enable the-bot-celery-beat.service

log "Запускаю Celery Worker..."
sudo systemctl restart the-bot-celery-worker.service
sleep 3

log "Запускаю Celery Beat..."
sudo systemctl restart the-bot-celery-beat.service
sleep 2

# Проверяем статус Celery Worker
if ! systemctl is-active --quiet the-bot-celery-worker.service; then
  log "⚠️  Ошибка запуска Celery Worker. Проверяю логи..."
  journalctl -u the-bot-celery-worker.service -n 30 --no-pager | sed 's/^/[celery-worker] /'
else
  log "✅ Celery Worker запущен"
fi

# Проверяем статус Celery Beat
if ! systemctl is-active --quiet the-bot-celery-beat.service; then
  log "⚠️  Ошибка запуска Celery Beat. Проверяю логи..."
  journalctl -u the-bot-celery-beat.service -n 30 --no-pager | sed 's/^/[celery-beat] /'
else
  log "✅ Celery Beat запущен (рекуррентные задачи активны)"
fi

# ================== SYSTEMD: DAPHNE (ASGI) ==================
log "Проверяю ASGI приложение перед созданием systemd сервиса..."
cd "$BACKEND_DIR"
if ! "$VENV_DIR/bin/python" -c "import config.asgi; print('ASGI приложение загружается успешно')" >/dev/null 2>&1; then
  log "ОШИБКА: ASGI приложение не загружается. Проверьте настройки Django."
  exit 1
fi
log "ASGI приложение проверено успешно"

log "Создаю systemd unit для Daphne (ASGI)..."
DAPHNE_UNIT_CONTENT="[Unit]
Description=THE_BOT ASGI (Daphne)
After=network.target

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONPATH=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/daphne -b $DJANGO_BIND_IP -p $ASGI_PORT config.asgi:application
Restart=always
User=$(whoami)
Group=$(id -gn)
# Убедись, что User имеет права читать проект

[Install]
WantedBy=multi-user.target
"
echo "$DAPHNE_UNIT_CONTENT" | sudo tee /etc/systemd/system/the-bot-daphne.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable the-bot-daphne.service
sudo systemctl restart the-bot-daphne.service

sleep 3
if ! systemctl is-active --quiet the-bot-daphne.service; then
  log "Ошибка запуска Daphne. Проверяю логи..."
  journalctl -u the-bot-daphne.service -n 50 --no-pager | sed 's/^/[daphne] /'
  
  # Дополнительная проверка - тестируем daphne напрямую
  log "Тестирую daphne напрямую..."
  cd "$BACKEND_DIR"
  if timeout 10s "$VENV_DIR/bin/daphne" -b 127.0.0.1 -p 8002 config.asgi:application >/dev/null 2>&1; then
    log "Daphne работает при прямом запуске, проблема в systemd конфигурации"
  else
    log "Daphne не работает даже при прямом запуске, проблема в ASGI приложении"
  fi
  
  echo "Ошибка запуска Daphne."
  exit 1
fi
log "Daphne запущен на $DJANGO_BIND_IP:$ASGI_PORT"

# ================== NGINX CONFIG ==================
log "Генерирую конфиг Nginx для домена $DOMAIN ..."
FRONTEND_DIST="/var/www/the-bot"
DJANGO_STATIC="/var/www/the-bot-static"

NGINX_CONF="server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN $WWW_DOMAIN;

    # Статика фронтенда
    root $FRONTEND_DIST;
    index index.html;

    # Проксируем API и админку в ASGI (Daphne)
    location ~ ^/(api|admin)/ {
        proxy_pass http://$DJANGO_BIND_IP:$ASGI_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket (например, /ws/)
    location /ws/ {
        proxy_pass http://$DJANGO_BIND_IP:$ASGI_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Django static (после collectstatic)
    location /static/ {
        alias $DJANGO_STATIC/;
        access_log off;
        expires 30d;
    }

    # Медиа, если используются
    location /media/ {
        alias $BACKEND_DIR/media/;
        access_log off;
        expires 30d;
    }

    # Отдаём SPA index.html для остальных путей (роутинг на фронте)
    location / {
        try_files \$uri /index.html;
    }

    # Безопасность/заголовки по минимуму
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header Referrer-Policy no-referrer-when-downgrade;
}
"
echo "$NGINX_CONF" | sudo tee "$NGINX_SITE_AVAILABLE" >/dev/null

# Активируем сайт через sites-enabled и отключаем дефолтный, если он есть
if [ ! -e "$NGINX_SITE_ENABLED" ]; then
  sudo ln -s "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
fi
if [ -e "/etc/nginx/sites-enabled/default" ]; then
  sudo rm -f "/etc/nginx/sites-enabled/default"
fi

# Отключаем возможные конфликты server_name для $DOMAIN / $WWW_DOMAIN в других конфигах
for path in \
  /etc/nginx/conf.d/*.conf \
  /etc/nginx/sites-enabled/* \
  /etc/nginx/sites-available/*; do
  [ -e "$path" ] || continue
  
  # Пропускаем уже отключенные файлы (.disabled)
  if echo "$path" | grep -q "\.disabled"; then
    continue
  fi
  
  # Пропускаем наш основной файл
  if [ "$path" = "$NGINX_SITE_AVAILABLE" ] || [ "$path" = "$NGINX_SITE_ENABLED" ]; then
    continue
  fi
  
  if grep -Eiq "server_name[^\n]*\b($DOMAIN|$WWW_DOMAIN)\b" "$path" 2>/dev/null; then
    log "Найден потенциальный конфликт Nginx: $path — отключаю"
    # Если это симлинк в sites-enabled — удаляем линк
    if [ -L "$path" ] && echo "$path" | grep -q "/sites-enabled/"; then
      sudo rm -f "$path"
    # Если это файл в conf.d или sites-available — переименуем в .disabled
    else
      # Если файл уже имеет .disabled, пропускаем
      if echo "$path" | grep -q "\.disabled"; then
        continue
      fi
      sudo mv -f "$path" "$path.disabled" 2>/dev/null || true
    fi
  fi
done

# Явно удалим устаревший конфиг из conf.d, если вдруг остался
if [ -f "/etc/nginx/conf.d/the-bot.conf" ]; then
  log "Удаляю устаревший конфиг: /etc/nginx/conf.d/the-bot.conf"
  sudo rm -f "/etc/nginx/conf.d/the-bot.conf"
fi

log "Проверяю конфиг Nginx и перезапускаю..."
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# ================== LET'S ENCRYPT (HTTPS) ==================
log "Запрашиваю/обновляю сертификаты Let's Encrypt..."
if sudo certbot --nginx -d "$DOMAIN" -d "$WWW_DOMAIN" --non-interactive --agree-tos -m "$ADMIN_EMAIL" 2>&1 | tee /tmp/certbot-output.log; then
  log "SSL сертификат успешно установлен"
else
  CERTBOT_ERROR=$(cat /tmp/certbot-output.log 2>/dev/null || echo "")
  if echo "$CERTBOT_ERROR" | grep -q "does not match any trusted origins\|does not resolve\|No such host\|IP address"; then
    log "ВНИМАНИЕ: Certbot не смог выдать сертификат. Возможные причины:"
    log "  1. DNS записи для $DOMAIN и $WWW_DOMAIN не указывают на IP сервера"
    log "  2. Домен недоступен с внешнего интернета"
    log "  3. Порт 80 закрыт фаерволом"
    log "Сайт будет работать по HTTP. Для HTTPS настройте DNS и запустите скрипт снова."
  else
    log "Предупреждение: certbot завершился с ошибкой. Проверь логи выше."
  fi
fi

log "Включаю автоматическое продление сертификатов..."
# На Ubuntu пакетный certbot обычно использует certbot.timer, иногда certbot-renew.timer
sudo systemctl enable --now certbot.timer || sudo systemctl enable --now certbot-renew.timer || true

# ================== FIREWALL (UFW) ==================
log "Настраиваю UFW (фаервол): OpenSSH и HTTP/HTTPS..."
if ! command -v ufw >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ufw
fi

# Разрешаем SSH, HTTP и HTTPS. Профиль 'Nginx Full' включает 80 и 443.
sudo ufw allow OpenSSH || true
if sudo ufw app list 2>/dev/null | grep -q "Nginx Full"; then
  sudo ufw allow "Nginx Full" || true
else
  sudo ufw allow 80/tcp || true
  sudo ufw allow 443/tcp || true
fi

# Включаем UFW, если он не активен
if sudo ufw status | grep -qi inactive; then
  echo y | sudo ufw enable || true
fi

# ================== FINISH ==================
log "Готово! Проверяйте сайт: https://$DOMAIN"
if [ -n "$WWW_DOMAIN" ]; then
  log "Также доступен: https://$WWW_DOMAIN"
fi
log "Daphne: $DJANGO_BIND_IP:$ASGI_PORT, Nginx сайт: $NGINX_SITE_AVAILABLE"

# ================== DIAGNOSTICS ==================
log "Проверяю статус сервисов..."

# Проверка Celery Worker
if systemctl is-active --quiet the-bot-celery-worker.service; then
  log "✓ Celery Worker активен"
else
  log "✗ Celery Worker неактивен"
  journalctl -u the-bot-celery-worker.service -n 20 --no-pager | sed 's/^/[celery-worker] /'
fi

# Проверка Celery Beat
if systemctl is-active --quiet the-bot-celery-beat.service; then
  log "✓ Celery Beat активен (рекуррентные платежи)"
else
  log "✗ Celery Beat неактивен"
  journalctl -u the-bot-celery-beat.service -n 20 --no-pager | sed 's/^/[celery-beat] /'
fi

# Проверка Redis
if systemctl is-active --quiet redis-server.service || systemctl is-active --quiet redis.service; then
  log "✓ Redis активен"
else
  log "✗ Redis неактивен"
fi

# Проверка Daphne
if systemctl is-active --quiet the-bot-daphne.service; then
  log "✓ Daphne активен"
else
  log "✗ Daphne неактивен"
  journalctl -u the-bot-daphne.service -n 20 --no-pager | sed 's/^/[daphne] /'
fi

# Проверка порта 8001
if lsof -i :$ASGI_PORT >/dev/null 2>&1; then
  log "✓ Порт $ASGI_PORT открыт"
else
  log "✗ Порт $ASGI_PORT закрыт"
fi

# Тест HTTP-запроса к Daphne
if curl -s -o /dev/null -w "%{http_code}" "http://$DJANGO_BIND_IP:$ASGI_PORT/" | grep -q "200\|404\|500"; then
  log "✓ Daphne отвечает на HTTP-запросы"
else
  log "✗ Daphne не отвечает на HTTP-запросы"
fi

# Проверка Nginx
if systemctl is-active --quiet nginx; then
  log "✓ Nginx активен"
else
  log "✗ Nginx неактивен"
fi

# Тест конфига Nginx
if sudo nginx -t >/dev/null 2>&1; then
  log "✓ Конфиг Nginx корректен"
else
  log "✗ Ошибка в конфиге Nginx"
  sudo nginx -t
fi

# Проверка активных сайтов
log "Активные сайты Nginx:"
ls -la /etc/nginx/sites-enabled/ | sed 's/^/[nginx] /'

log "Диагностика завершена. Если проблемы остаются, проверьте логи:"
log "  sudo journalctl -u the-bot-daphne.service -f"
log "  sudo journalctl -u the-bot-celery-worker.service -f"
log "  sudo journalctl -u the-bot-celery-beat.service -f"
log "  sudo tail -f /var/log/nginx/error.log"
log "  sudo tail -f /var/log/celery/worker.log"
log "  sudo tail -f /var/log/celery/beat.log"