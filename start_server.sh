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
log "Устанавливаю системные пакеты (nginx, certbot, python3, node, npm, lsof)..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  nginx certbot python3-certbot-nginx python3 python3-venv nodejs npm lsof

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

"$VENV_DIR/bin/python" manage.py migrate --noinput

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
log "  sudo tail -f /var/log/nginx/error.log"