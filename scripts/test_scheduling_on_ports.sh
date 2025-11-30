#!/bin/bash

"""
Скрипт для запуска тестов системы бронирования на разных портах.
Позволяет избежать конфликтов портов при параллельном тестировании.
"""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация портов
BACKEND_PORT=${BACKEND_PORT:-8010}
FRONTEND_PORT=${FRONTEND_PORT:-3001}

# Пути
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Функция для вывода заголовков
print_header() {
    echo -e "\n${BLUE}===================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================${NC}\n"
}

# Функция для вывода успеха
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Функция для вывода ошибки
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Функция для вывода предупреждения
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Функция для проверки свободности порта
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

# Функция для остановки процесса на порту
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Функция для запуска backend
start_backend() {
    local port=$1
    print_header "Запуск Backend на порту $port"

    # Проверяем порт
    if ! check_port $port; then
        print_warning "Порт $port занят, освобождаем..."
        kill_port $port
    fi

    # Активируем виртуальное окружение
    cd "$BACKEND_DIR"
    source "$PROJECT_ROOT/.venv/bin/activate" 2>/dev/null || {
        print_error "Не найдено виртуальное окружение"
        return 1
    }

    # Запускаем сервер в фоне
    ENVIRONMENT=test python manage.py runserver 127.0.0.1:$port > /tmp/backend_$port.log 2>&1 &
    BACKEND_PID=$!

    # Ждем запуска
    sleep 3

    # Проверяем что сервер запустился
    if curl -s http://127.0.0.1:$port/api/health/ > /dev/null 2>&1; then
        print_success "Backend запущен на порту $port (PID: $BACKEND_PID)"
        return 0
    else
        print_error "Не удалось запустить Backend на порту $port"
        return 1
    fi
}

# Функция для запуска frontend
start_frontend() {
    local port=$1
    local backend_port=$2
    print_header "Запуск Frontend на порту $port"

    # Проверяем порт
    if ! check_port $port; then
        print_warning "Порт $port занят, освобождаем..."
        kill_port $port
    fi

    cd "$FRONTEND_DIR"

    # Устанавливаем переменные окружения
    export VITE_DJANGO_API_URL="http://127.0.0.1:$backend_port/api"
    export PORT=$port

    # Запускаем dev server в фоне
    npm run dev -- --port $port > /tmp/frontend_$port.log 2>&1 &
    FRONTEND_PID=$!

    # Ждем запуска
    sleep 5

    # Проверяем что сервер запустился
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        print_success "Frontend запущен на порту $port (PID: $FRONTEND_PID)"
        return 0
    else
        print_error "Не удалось запустить Frontend на порту $port"
        return 1
    fi
}

# Функция для запуска backend тестов
run_backend_tests() {
    print_header "Запуск Backend тестов"

    cd "$BACKEND_DIR"
    source "$PROJECT_ROOT/.venv/bin/activate"

    # Unit тесты
    echo -e "\n${YELLOW}Unit тесты scheduling:${NC}"
    ENVIRONMENT=test pytest tests/unit/scheduling/ -v --tb=short || return 1
    print_success "Unit тесты пройдены"

    # Integration тесты
    echo -e "\n${YELLOW}Integration тесты:${NC}"
    ENVIRONMENT=test pytest tests/integration/scheduling/ -v --tb=short || return 1
    print_success "Integration тесты пройдены"

    # Coverage
    echo -e "\n${YELLOW}Проверка покрытия:${NC}"
    ENVIRONMENT=test pytest tests/unit/scheduling/ tests/integration/scheduling/ \
        --cov=scheduling --cov-report=term-missing --cov-report=html

    return 0
}

# Функция для запуска frontend unit тестов
run_frontend_unit_tests() {
    print_header "Запуск Frontend Unit тестов"

    cd "$FRONTEND_DIR"

    # Unit тесты хуков и компонентов
    npm test -- --run scheduling || return 1
    print_success "Frontend unit тесты пройдены"

    return 0
}

# Функция для запуска E2E тестов
run_e2e_tests() {
    local frontend_port=$1
    local backend_port=$2

    print_header "Запуск E2E тестов"

    cd "$FRONTEND_DIR"

    # Устанавливаем переменные для Playwright
    export PLAYWRIGHT_TEST_BASE_URL="http://localhost:$frontend_port"
    export PLAYWRIGHT_TEST_API_URL="http://127.0.0.1:$backend_port/api"

    # Запускаем E2E тесты
    npx playwright test tests/e2e/scheduling/ --reporter=list || return 1
    print_success "E2E тесты пройдены"

    return 0
}

# Функция для остановки серверов
cleanup() {
    print_header "Остановка серверов"

    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        print_success "Backend остановлен"
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        print_success "Frontend остановлен"
    fi

    # Очищаем порты на всякий случай
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
}

# Главная функция
main() {
    print_header "Тестирование системы бронирования"
    echo "Backend порт: $BACKEND_PORT"
    echo "Frontend порт: $FRONTEND_PORT"

    # Устанавливаем trap для очистки при выходе
    trap cleanup EXIT INT TERM

    # 1. Backend тесты (не требуют запущенных серверов)
    if ! run_backend_tests; then
        print_error "Backend тесты провалены"
        exit 1
    fi

    # 2. Frontend unit тесты (не требуют запущенных серверов)
    if ! run_frontend_unit_tests; then
        print_error "Frontend unit тесты провалены"
        exit 1
    fi

    # 3. Запускаем серверы для E2E
    if ! start_backend $BACKEND_PORT; then
        print_error "Не удалось запустить Backend"
        exit 1
    fi

    if ! start_frontend $FRONTEND_PORT $BACKEND_PORT; then
        print_error "Не удалось запустить Frontend"
        exit 1
    fi

    # 4. E2E тесты
    if ! run_e2e_tests $FRONTEND_PORT $BACKEND_PORT; then
        print_error "E2E тесты провалены"

        # Выводим логи для отладки
        echo -e "\n${YELLOW}Backend логи:${NC}"
        tail -n 20 /tmp/backend_$BACKEND_PORT.log

        echo -e "\n${YELLOW}Frontend логи:${NC}"
        tail -n 20 /tmp/frontend_$FRONTEND_PORT.log

        exit 1
    fi

    print_header "Все тесты успешно пройдены!"

    # Выводим итоговую статистику
    echo -e "\n${GREEN}Результаты тестирования:${NC}"
    echo "✓ Backend unit тесты: PASSED"
    echo "✓ Backend integration тесты: PASSED"
    echo "✓ Frontend unit тесты: PASSED"
    echo "✓ E2E тесты: PASSED"

    # Открываем отчет о покрытии
    if [ -f "$BACKEND_DIR/htmlcov/index.html" ]; then
        echo -e "\n${YELLOW}Отчет о покрытии: $BACKEND_DIR/htmlcov/index.html${NC}"
    fi
}

# Обработка аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --help)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --backend-port PORT   Порт для backend (по умолчанию: 8010)"
            echo "  --frontend-port PORT  Порт для frontend (по умолчанию: 3001)"
            echo "  --help               Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0"
            echo "  $0 --backend-port 8020 --frontend-port 3002"
            exit 0
            ;;
        *)
            echo "Неизвестный аргумент: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Запуск
main