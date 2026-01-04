#!/bin/bash

set -e

DOMAIN="the-bot.ru"
IP="5.129.249.206"
BASE_URL="https://${DOMAIN}"
TIMEOUT=10

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

declare -A USERS=(
    [admin]="admin123"
    [student1]="student123"
    [teacher1]="teacher123"
    [tutor1]="tutor123"
    [parent1]="parent123"
)

declare -A ROLES=(
    [admin]="admin"
    [student1]="student"
    [teacher1]="teacher"
    [tutor1]="tutor"
    [parent1]="parent"
)

declare -A RESULTS

setup_hosts() {
    echo "Проверка /etc/hosts..."
    if grep -q "$IP $DOMAIN" /etc/hosts 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Запись уже в /etc/hosts"
    else
        echo -e "${YELLOW}→${NC} Попытка добавить $IP $DOMAIN в /etc/hosts"
        if echo "$IP $DOMAIN" | sudo tee -a /etc/hosts > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Запись добавлена"
        else
            echo -e "${YELLOW}⚠${NC} Не удалось добавить в /etc/hosts (требуется sudo с паролем)"
            echo -e "${YELLOW}⚠${NC} Тестирование продолжается, но может не работать"
        fi
    fi
}

test_login() {
    local username=$1
    local password=$2
    local expected_role=$3

    local login_response
    login_response=$(curl -s -k -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
        --max-time "$TIMEOUT" \
        "$BASE_URL/api/auth/login/" 2>/dev/null || echo "{\"error\":\"timeout\"}")

    local access_token
    access_token=$(echo "$login_response" | jq -r '.access' 2>/dev/null || echo "")

    if [ -z "$access_token" ] || [ "$access_token" = "null" ]; then
        RESULTS[$username]="FAILED"
        return 1
    fi

    local profile_response
    profile_response=$(curl -s -k -X GET \
        -H "Authorization: Bearer $access_token" \
        --max-time "$TIMEOUT" \
        "$BASE_URL/api/auth/profile/" 2>/dev/null || echo "{\"error\":\"timeout\"}")

    local profile_username
    local profile_role
    profile_username=$(echo "$profile_response" | jq -r '.username' 2>/dev/null || echo "")
    profile_role=$(echo "$profile_response" | jq -r '.role' 2>/dev/null || echo "")

    if [ "$profile_username" != "$username" ] || [ "$profile_role" != "$expected_role" ]; then
        RESULTS[$username]="FAILED"
        return 1
    fi

    RESULTS[$username]="OK"
    return 0
}

print_results() {
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "              РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ"
    echo "═══════════════════════════════════════════════════"
    echo ""
    printf "%-15s %-15s %-10s\n" "Role" "Username" "Status"
    echo "───────────────────────────────────────────────────"

    local passed=0
    local failed=0

    for username in "${!USERS[@]}"; do
        local role=${ROLES[$username]}
        local status=${RESULTS[$username]:-UNKNOWN}

        if [ "$status" = "OK" ]; then
            printf "%-15s %-15s ${GREEN}✓ %s${NC}\n" "$role" "$username" "$status"
            ((passed++))
        else
            printf "%-15s %-15s ${RED}✗ %s${NC}\n" "$role" "$username" "$status"
            ((failed++))
        fi
    done

    echo "───────────────────────────────────────────────────"
    echo ""
    echo -n "Итого: "
    echo -ne "${GREEN}✓ $passed${NC} | "
    if [ $failed -gt 0 ]; then
        echo -e "${RED}✗ $failed${NC}"
    else
        echo -e "${RED}✗ 0${NC}"
    fi
    echo "═══════════════════════════════════════════════════"
    echo ""

    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}Все тесты пройдены успешно!${NC}"
        return 0
    else
        echo -e "${RED}Некоторые тесты не пройдены.${NC}"
        return 1
    fi
}

main() {
    echo "╔════════════════════════════════════════════════════╗"
    echo "║  Smoke тестирование THE_BOT на $DOMAIN║"
    echo "╚════════════════════════════════════════════════════╝"
    echo ""

    setup_hosts
    echo ""

    echo "Запуск параллельного тестирования 5 ролей..."
    echo "(Это может занять до 10 сек на роль)"
    echo ""

    local pids=()

    for username in "${!USERS[@]}"; do
        local password=${USERS[$username]}
        local expected_role=${ROLES[$username]}

        {
            echo -e "→ Тестирую $username..."
            if test_login "$username" "$password" "$expected_role"; then
                echo -e "${GREEN}✓${NC} $username успешно залогинился"
            else
                echo -e "${RED}✗${NC} $username ошибка при логине"
            fi
        } &
        pids+=($!)
    done

    echo ""
    echo "Ожидание завершения всех тестов..."
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done

    print_results
}

main "$@"
