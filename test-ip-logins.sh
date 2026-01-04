#!/bin/bash
# Smoke-тестирование логинов THE_BOT через IP адрес
# Использование: ./test-ip-logins.sh [server_ip:port]
# Пример: ./test-ip-logins.sh 5.129.249.206:8000
#         ./test-ip-logins.sh localhost:8000 (по умолчанию)

SERVER_IP="${1:-localhost:8000}"
BASE_URL="http://$SERVER_IP"

# Тестовые учетные данные (5 ролей)
declare -A USERS=(
  ["admin"]="admin:test123"
  ["student"]="student:test123"
  ["teacher"]="teacher:test123"
  ["tutor"]="tutor:test123"
  ["parent"]="parent:test123"
)

echo "╔═══════════════════════════════════════════════════╗"
echo "║ Smoke-тестирование THE_BOT: $SERVER_IP ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

# Инициализировать cookies для сессии (получение CSRF токена через OPTIONS)
echo "Initializing session..."
curl -s -c /tmp/cookies.txt -X OPTIONS "$BASE_URL/api/auth/login/" > /dev/null 2>&1

# Извлечь CSRF токен из Cookie
csrf_token=$(grep csrftoken /tmp/cookies.txt 2>/dev/null | awk '{print $NF}' || echo "")

# Тестировать каждую роль
for role in "${!USERS[@]}"; do
  creds="${USERS[$role]}"
  username="${creds%:*}"
  password="${creds#*:}"

  echo -n "Testing $role ($username)... "

  # POST логин с cookies и CSRF токеном
  response=$(curl -s -X POST "$BASE_URL/api/auth/login/" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $csrf_token" \
    -b /tmp/cookies.txt \
    -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
    --max-time 10 2>/dev/null)

  # Проверить успешный логин
  if echo "$response" | jq -e '.success' > /dev/null 2>&1; then
    success=$(echo "$response" | jq -r '.success')

    if [ "$success" = "true" ]; then
      echo -e "${GREEN}✓ OK${NC}"
      ((passed++))
    else
      error=$(echo "$response" | jq -r '.error // "Unknown error"')
      echo -e "${RED}✗ $error${NC}"
      ((failed++))
    fi
  else
    # Может быть HTML ошибка (403, 500 и т.д.)
    if echo "$response" | grep -q "<!doctype\|<html"; then
      http_code=$(echo "$response" | grep -oP '(?<=<title>)\d+' | head -1)
      if [ -n "$http_code" ]; then
        echo -e "${RED}✗ HTTP $http_code${NC}"
      else
        echo -e "${RED}✗ HTML Response (check CSRF)${NC}"
      fi
    else
      echo -e "${RED}✗ No JSON response${NC}"
    fi
    ((failed++))
  fi
done

echo ""
echo "═══════════════════════════════════════════════════"
echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}"
echo "═══════════════════════════════════════════════════"

# Дополнительная информация для отладки
if [ $failed -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}Troubleshooting:${NC}"
  echo "1. Убедись что сервер запущен: curl -s $BASE_URL/"
  echo "2. Проверь Redis: redis-cli ping"
  echo "3. Проверь БД: python manage.py dbshell"
  echo "4. Проверь логи: tail -100 /tmp/django.log"
  echo ""
fi

# Выход с кодом ошибки если есть падения
[ $failed -eq 0 ] && exit 0 || exit 1
