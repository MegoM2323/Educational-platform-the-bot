#!/usr/bin/env bash

#===============================================================================
# THE BOT PLATFORM - TEST ENVIRONMENT SETUP SCRIPT
#===============================================================================
# Полная автоматизация создания тестового окружения
# Версия: 1.0.0
#===============================================================================

set -euo pipefail

#===============================================================================
# КОНСТАНТЫ И ЦВЕТА
#===============================================================================

# Цвета для вывода
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Символы
readonly CHECK_MARK="✓"
readonly CROSS_MARK="✗"
readonly ARROW="→"
readonly BULLET="•"

# Пути
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/.venv"
LOG_FILE="$PROJECT_ROOT/setup.log"

# Статистика
declare -A STATS=(
    [users]=0
    [subjects]=0
    [enrollments]=0
    [materials]=0
    [assignments]=0
    [reports]=0
    [chat_rooms]=0
    [messages]=0
)

# Пароль для тестовых аккаунтов
readonly TEST_PASSWORD="TestPass123!"

#===============================================================================
# ФУНКЦИИ ВЫВОДА
#===============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  ████████╗██╗  ██╗███████╗    ██████╗  ██████╗ ████████╗             ║
║  ╚══██╔══╝██║  ██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝             ║
║     ██║   ███████║█████╗      ██████╔╝██║   ██║   ██║                ║
║     ██║   ██╔══██║██╔══╝      ██╔══██╗██║   ██║   ██║                ║
║     ██║   ██║  ██║███████╗    ██████╔╝╚██████╔╝   ██║                ║
║     ╚═╝   ╚═╝  ╚═╝╚══════╝    ╚═════╝  ╚═════╝    ╚═╝                ║
║                                                                       ║
║              TEST ENVIRONMENT SETUP AUTOMATION                       ║
║                        Version 1.0.0                                 ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK_MARK}${NC} $*"
    log "SUCCESS: $*"
}

print_error() {
    echo -e "${RED}${CROSS_MARK}${NC} $*" >&2
    log "ERROR: $*"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
    log "WARNING: $*"
}

print_info() {
    echo -e "${BLUE}${BULLET}${NC} $*"
    log "INFO: $*"
}

print_header() {
    echo ""
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${WHITE}$*${NC}"
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_subheader() {
    echo ""
    echo -e "${CYAN}${ARROW}${NC} ${WHITE}$*${NC}"
    echo -e "${CYAN}───────────────────────────────────────────────────────────────────────${NC}"
}

print_step() {
    echo -e "${MAGENTA}[$(date +'%H:%M:%S')]${NC} $*"
}

show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))

    printf "\r${CYAN}["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "]${NC} %3d%% - %s" "$percentage" "$message"

    if [ "$current" -eq "$total" ]; then
        echo ""
    fi
}

#===============================================================================
# ФУНКЦИИ ПРОВЕРКИ
#===============================================================================

check_prerequisites() {
    print_subheader "Проверка предварительных условий"

    # Проверка директории
    if [ ! -f "$BACKEND_DIR/manage.py" ]; then
        print_error "Файл manage.py не найден. Запустите скрипт из корня проекта."
        exit 1
    fi
    print_success "Проект найден: $PROJECT_ROOT"

    # Проверка Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 не установлен"
        exit 1
    fi
    print_success "Python: $(python3 --version)"

    # Проверка виртуального окружения
    if [ ! -d "$VENV_DIR" ]; then
        print_warning "Виртуальное окружение не найдено, создаем..."
        python3 -m venv "$VENV_DIR"
    fi
    print_success "Виртуальное окружение: $VENV_DIR"

    # Проверка сервера Django
    if ! curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
        print_warning "Django сервер не запущен на порту 8000"
        print_info "Пожалуйста, запустите сервер: ./start.sh"
        print_info "Или запустите вручную: cd backend && python manage.py runserver 8000"

        read -p "Хотите продолжить без проверки сервера? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "Django сервер доступен на http://localhost:8000"
    fi

    # Проверка базы данных
    print_step "Проверка подключения к базе данных..."
    if ! "$VENV_DIR/bin/python" "$BACKEND_DIR/manage.py" check --database default &> /dev/null; then
        print_error "Не удается подключиться к базе данных"
        print_info "Проверьте настройки в .env файле"
        exit 1
    fi
    print_success "База данных доступна"
}

check_redis() {
    print_step "Проверка Redis..."
    if redis-cli ping > /dev/null 2>&1; then
        print_success "Redis доступен"
        return 0
    else
        print_warning "Redis недоступен (опционально для тестирования)"
        return 1
    fi
}

#===============================================================================
# ФУНКЦИИ ОЧИСТКИ
#===============================================================================

cleanup_database() {
    print_subheader "Очистка базы данных"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: База данных не будет очищена"
        return 0
    fi

    print_step "Удаление тестовых пользователей и данных..."

    # Используем существующую команду cleanup_database
    cd "$BACKEND_DIR"
    if "$VENV_DIR/bin/python" manage.py cleanup_database \
        --all \
        --days 0 \
        --force >> "$LOG_FILE" 2>&1; then
        print_success "База данных очищена"
    else
        print_warning "Частичная очистка базы данных (некоторые данные могут остаться)"
    fi

    cd "$PROJECT_ROOT"
}

full_reset_database() {
    print_subheader "Полный сброс базы данных"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: Полный сброс не будет выполнен"
        return 0
    fi

    print_warning "ВНИМАНИЕ: Все данные будут удалены!"

    if [ "$FORCE" = false ]; then
        read -p "Вы уверены? Введите 'yes' для подтверждения: " -r
        if [[ ! $REPLY == "yes" ]]; then
            print_info "Отменено пользователем"
            exit 0
        fi
    fi

    print_step "Сброс базы данных к тестовому набору..."

    cd "$BACKEND_DIR"
    if "$VENV_DIR/bin/python" manage.py reset_to_known_test_dataset >> "$LOG_FILE" 2>&1; then
        print_success "База данных полностью сброшена"
        STATS[users]=4
    else
        print_error "Ошибка при сбросе базы данных"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

#===============================================================================
# ФУНКЦИИ СОЗДАНИЯ ДАННЫХ
#===============================================================================

create_test_users() {
    print_subheader "Создание тестовых пользователей"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: Пользователи не будут созданы"
        print_info "Будет создано:"
        print_info "  - student@test.com (Студент)"
        print_info "  - parent@test.com (Родитель)"
        print_info "  - teacher@test.com (Преподаватель)"
        print_info "  - tutor@test.com (Тьютор)"
        print_info "  - student2@test.com (Студент 2)"
        print_info "  - teacher2@test.com (Преподаватель 2)"
        print_info "  - admin@test.com (Администратор)"
        STATS[users]=7
        return 0
    fi

    print_step "Создание пользователей с единым паролем..."

    cd "$BACKEND_DIR"
    local output
    output=$("$VENV_DIR/bin/python" manage.py create_test_users_all 2>&1)

    if [ $? -eq 0 ]; then
        # Парсим количество созданных пользователей из вывода
        local user_count=$(echo "$output" | grep -E "(🆕|♻️)" | wc -l)
        STATS[users]=$user_count
        print_success "Создано/обновлено пользователей: $user_count"
        echo "$output" >> "$LOG_FILE"
    else
        print_error "Ошибка при создании пользователей"
        echo "$output" >> "$LOG_FILE"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

create_test_subjects() {
    print_subheader "Создание предметов и преподавателей"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: Предметы не будут созданы"
        print_info "Будет создано 10 предметов:"
        print_info "  - Математика, Физика, Химия, Биология, История"
        print_info "  - География, Литература, Русский язык, Английский язык, Информатика"
        STATS[subjects]=10
        return 0
    fi

    print_step "Создание предметов и назначение преподавателей..."

    cd "$BACKEND_DIR"
    local output
    output=$("$VENV_DIR/bin/python" manage.py create_test_subjects 2>&1)

    if [ $? -eq 0 ]; then
        # Парсим количество предметов
        local subject_count=$(echo "$output" | grep -E "(создан|уже существует)" | grep -v "Преподаватель" | wc -l)
        STATS[subjects]=$subject_count
        print_success "Создано предметов: $subject_count"
        echo "$output" >> "$LOG_FILE"
    else
        print_error "Ошибка при создании предметов"
        echo "$output" >> "$LOG_FILE"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

create_full_dataset() {
    print_subheader "Создание comprehensive dataset"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: Расширенный dataset не будет создан"
        print_info "Будет создано:"
        print_info "  - 5 enrollments (записи студентов на предметы)"
        print_info "  - 35 материалов для обучения"
        print_info "  - 15 заданий"
        print_info "  - 8 отчетов"
        print_info "  - 12 чат-комнат"
        print_info "  - 150 сообщений"
        STATS[enrollments]=5
        STATS[materials]=35
        STATS[assignments]=15
        STATS[reports]=8
        STATS[chat_rooms]=12
        STATS[messages]=150
        return 0
    fi

    print_step "Генерация тестовых данных (материалы, задания, отчеты, чаты)..."

    # Создаем временный Python скрипт для генерации данных
    local temp_script="$BACKEND_DIR/temp_generate_data.py"

    cat > "$temp_script" << 'PYTHON_SCRIPT'
import os
import sys
import django
from datetime import datetime, timedelta
from random import choice, randint, sample

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment, Material, MaterialSubmission, TeacherSubject
from assignments.models import Assignment, AssignmentSubmission
from reports.models import Report
from chat.models import ChatRoom, Message
from django.db import transaction

User = get_user_model()

stats = {
    'enrollments': 0,
    'materials': 0,
    'assignments': 0,
    'reports': 0,
    'chat_rooms': 0,
    'messages': 0,
}

try:
    with transaction.atomic():
        # Получаем пользователей
        students = list(User.objects.filter(role='student'))
        teachers = list(User.objects.filter(role='teacher'))
        tutors = list(User.objects.filter(role='tutor'))
        parents = list(User.objects.filter(role='parent'))

        if not students or not teachers:
            print("ERROR: Необходимы студенты и преподаватели")
            sys.exit(1)

        subjects = list(Subject.objects.all())
        if not subjects:
            print("ERROR: Необходимы предметы")
            sys.exit(1)

        # Создаем enrollments (записи на предметы)
        print("Creating enrollments...")
        for student in students[:2]:  # Первые 2 студента
            for subject in sample(subjects, min(3, len(subjects))):  # По 3 предмета
                # Находим преподавателя для этого предмета
                teacher_subject = TeacherSubject.objects.filter(subject=subject, is_active=True).first()
                if teacher_subject:
                    enrollment, created = SubjectEnrollment.objects.get_or_create(
                        student=student,
                        subject=subject,
                        teacher=teacher_subject.teacher,
                        defaults={
                            'tutor': tutors[0] if tutors else None,
                            'is_active': True
                        }
                    )
                    if created:
                        stats['enrollments'] += 1

        # Создаем материалы
        print("Creating materials...")
        material_types = ['video', 'document', 'presentation', 'link']
        for subject in subjects:
            teacher_subject = TeacherSubject.objects.filter(subject=subject, is_active=True).first()
            if teacher_subject:
                for i in range(3):  # По 3 материала на предмет
                    material = Material.objects.create(
                        title=f"{subject.name} - Урок {i+1}",
                        description=f"Учебный материал по теме '{subject.name}', урок номер {i+1}",
                        subject=subject,
                        teacher=teacher_subject.teacher,
                        material_type=choice(material_types),
                        status='published',
                        content=f"Содержание урока {i+1} по предмету {subject.name}"
                    )
                    stats['materials'] += 1

        # Создаем задания
        print("Creating assignments...")
        materials = list(Material.objects.filter(status='published'))
        for material in sample(materials, min(15, len(materials))):
            assignment = Assignment.objects.create(
                title=f"Задание: {material.title}",
                description=f"Выполните задание по материалу '{material.title}'",
                material=material,
                teacher=material.teacher,
                subject=material.subject,
                due_date=datetime.now() + timedelta(days=randint(1, 30)),
                max_score=randint(50, 100),
                status='published'
            )
            stats['assignments'] += 1

            # Создаем submissions для некоторых заданий
            if stats['assignments'] % 3 == 0:  # Каждое 3-е задание
                for student in students[:1]:
                    AssignmentSubmission.objects.create(
                        assignment=assignment,
                        student=student,
                        content="Тестовое выполнение задания",
                        status='submitted',
                        score=randint(30, assignment.max_score)
                    )

        # Создаем отчеты
        print("Creating reports...")
        if students and teachers:
            for i in range(8):
                Report.objects.create(
                    title=f"Отчет о прогрессе {i+1}",
                    content=f"Тестовый отчет о прогрессе студента. Отчет номер {i+1}",
                    student=choice(students),
                    teacher=choice(teachers),
                    report_type='progress',
                    status='sent',
                    period_start=datetime.now() - timedelta(days=14),
                    period_end=datetime.now()
                )
                stats['reports'] += 1

        # Создаем чат-комнаты и сообщения
        print("Creating chat rooms and messages...")
        if students and teachers:
            # Чаты студент-преподаватель
            for student in students:
                for teacher in sample(teachers, min(2, len(teachers))):
                    room = ChatRoom.objects.create(
                        name=f"Чат: {student.get_full_name()} - {teacher.get_full_name()}"
                    )
                    room.participants.add(student, teacher)
                    stats['chat_rooms'] += 1

                    # Создаем сообщения
                    for j in range(randint(5, 15)):
                        sender = choice([student, teacher])
                        Message.objects.create(
                            room=room,
                            sender=sender,
                            content=f"Тестовое сообщение {j+1} от {sender.get_full_name()}",
                            message_type='text'
                        )
                        stats['messages'] += 1

        # Чаты тьютор-родитель
        if tutors and parents:
            for tutor in tutors:
                for parent in parents:
                    room = ChatRoom.objects.create(
                        name=f"Чат: {tutor.get_full_name()} - {parent.get_full_name()}"
                    )
                    room.participants.add(tutor, parent)
                    stats['chat_rooms'] += 1

                    for j in range(randint(3, 8)):
                        sender = choice([tutor, parent])
                        Message.objects.create(
                            room=room,
                            sender=sender,
                            content=f"Обсуждение прогресса: сообщение {j+1}",
                            message_type='text'
                        )
                        stats['messages'] += 1

        # Выводим статистику
        for key, value in stats.items():
            print(f"STAT:{key}:{value}")

        print("SUCCESS: All data created")

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

    cd "$BACKEND_DIR"
    local output
    output=$("$VENV_DIR/bin/python" "$temp_script" 2>&1)
    local exit_code=$?

    # Удаляем временный скрипт
    rm -f "$temp_script"

    if [ $exit_code -eq 0 ]; then
        # Парсим статистику из вывода
        while IFS=':' read -r prefix key value; do
            if [ "$prefix" = "STAT" ]; then
                STATS[$key]=$value
            fi
        done <<< "$output"

        print_success "Comprehensive dataset создан"
        echo "$output" >> "$LOG_FILE"
    else
        print_error "Ошибка при создании dataset"
        echo "$output" >> "$LOG_FILE"
        print_warning "Продолжаем выполнение..."
    fi

    cd "$PROJECT_ROOT"
}

#===============================================================================
# ФУНКЦИИ ПРОВЕРКИ И СТАТИСТИКИ
#===============================================================================

verify_data() {
    print_subheader "Проверка созданных данных"

    print_step "Подсчет записей в базе данных..."

    cd "$BACKEND_DIR"

    # Создаем временный скрипт для проверки
    local temp_script="$BACKEND_DIR/temp_verify.py"

    cat > "$temp_script" << 'PYTHON_VERIFY'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from materials.models import Subject, SubjectEnrollment, Material
from assignments.models import Assignment
from reports.models import Report
from chat.models import ChatRoom, Message

User = get_user_model()

print(f"users:{User.objects.filter(is_superuser=False).count()}")
print(f"subjects:{Subject.objects.count()}")
print(f"enrollments:{SubjectEnrollment.objects.count()}")
print(f"materials:{Material.objects.count()}")
print(f"assignments:{Assignment.objects.count()}")
print(f"reports:{Report.objects.count()}")
print(f"chat_rooms:{ChatRoom.objects.count()}")
print(f"messages:{Message.objects.count()}")
PYTHON_VERIFY

    local output
    output=$("$VENV_DIR/bin/python" "$temp_script" 2>&1)

    # Удаляем временный скрипт
    rm -f "$temp_script"

    # Обновляем статистику из реальных данных БД
    while IFS=':' read -r key value; do
        if [ -n "$key" ] && [ -n "$value" ]; then
            STATS[$key]=$value
        fi
    done <<< "$output"

    print_success "Данные проверены"

    cd "$PROJECT_ROOT"
}

show_statistics() {
    print_header "ИТОГОВАЯ СТАТИСТИКА"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА - ДАННЫЕ НЕ БЫЛИ СОЗДАНЫ"
        echo ""
    fi

    echo -e "${WHITE}════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${CHECK_MARK} TEST ENVIRONMENT SETUP COMPLETE${NC}"
    echo -e "${WHITE}════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}📊 СТАТИСТИКА:${NC}"
    echo -e "${WHITE}────────────────────────────────────────────────────────────────────────${NC}"
    printf "%-20s %s\n" "Users:" "${STATS[users]} created"
    printf "%-20s %s\n" "Subjects:" "${STATS[subjects]} created"
    printf "%-20s %s\n" "Enrollments:" "${STATS[enrollments]} created"
    printf "%-20s %s\n" "Materials:" "${STATS[materials]} created"
    printf "%-20s %s\n" "Assignments:" "${STATS[assignments]} created"
    printf "%-20s %s\n" "Reports:" "${STATS[reports]} created"
    printf "%-20s %s\n" "Chat Rooms:" "${STATS[chat_rooms]} created"
    printf "%-20s %s\n" "Messages:" "${STATS[messages]} created"
    echo -e "${WHITE}────────────────────────────────────────────────────────────────────────${NC}"

    local total=$((STATS[users] + STATS[subjects] + STATS[enrollments] + STATS[materials] + STATS[assignments] + STATS[reports] + STATS[chat_rooms] + STATS[messages]))
    echo -e "${WHITE}Total records:${NC} ${GREEN}$total${NC}"
    echo ""

    echo -e "${CYAN}🔐 TEST CREDENTIALS:${NC}"
    echo -e "${WHITE}────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "Student:      ${YELLOW}student@test.com${NC}  / ${YELLOW}$TEST_PASSWORD${NC}"
    echo -e "Teacher:      ${YELLOW}teacher@test.com${NC}  / ${YELLOW}$TEST_PASSWORD${NC}"
    echo -e "Tutor:        ${YELLOW}tutor@test.com${NC}    / ${YELLOW}$TEST_PASSWORD${NC}"
    echo -e "Parent:       ${YELLOW}parent@test.com${NC}   / ${YELLOW}$TEST_PASSWORD${NC}"
    echo -e "Admin:        ${YELLOW}admin@test.com${NC}    / ${YELLOW}$TEST_PASSWORD${NC}"
    echo -e "${WHITE}────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    echo -e "${CYAN}🚀 NEXT STEPS:${NC}"
    echo -e "${WHITE}────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${BULLET} Open ${YELLOW}http://localhost:8080${NC} in browser"
    echo -e "${BULLET} Login with any test account"
    echo -e "${BULLET} Admin panel: ${YELLOW}http://localhost:8000/admin${NC}"
    echo -e "${BULLET} API docs: ${YELLOW}http://localhost:8000/api/${NC}"
    if [ "$RUN_E2E" = true ]; then
        echo -e "${BULLET} E2E tests: ${YELLOW}npm run test:e2e${NC}"
    fi
    echo -e "${WHITE}════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    print_success "Setup completed successfully!"
    echo ""
}

#===============================================================================
# E2E ТЕСТЫ
#===============================================================================

run_e2e_tests() {
    print_header "E2E ТЕСТИРОВАНИЕ"

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА: E2E тесты не будут запущены"
        return 0
    fi

    print_step "Запуск End-to-End тестов..."

    cd "$PROJECT_ROOT/frontend"

    if [ ! -d "node_modules" ]; then
        print_step "Установка npm зависимостей..."
        npm install >> "$LOG_FILE" 2>&1
    fi

    if [ -f "package.json" ] && grep -q "test:e2e" package.json; then
        print_step "Выполнение E2E тестов..."
        if npm run test:e2e >> "$LOG_FILE" 2>&1; then
            print_success "E2E тесты пройдены"
        else
            print_error "E2E тесты провалились"
            print_info "Проверьте лог: $LOG_FILE"
        fi
    else
        print_warning "E2E тесты не настроены в package.json"
    fi

    cd "$PROJECT_ROOT"
}

#===============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
#===============================================================================

show_usage() {
    cat << EOF
Использование: $0 [OPTIONS]

Опции:
    --full-reset        Полная очистка и пересоздание всего
    --clean-only        Только очистка (без создания данных)
    --seed-only         Только создание данных (без очистки)
    --preview           Показать что будет сделано (dry-run)
    --with-e2e          Запустить E2E тесты после setup
    --force             Без запроса подтверждения
    --help              Показать эту справку

Примеры:
    # Полная пересборка
    $0 --full-reset

    # Только добавить данные
    $0 --seed-only

    # Пересборка + E2E тесты
    $0 --full-reset --with-e2e

    # Посмотреть что будет сделано
    $0 --preview

    # Только очистка
    $0 --clean-only --force

EOF
}

main() {
    # Инициализация переменных
    local FULL_RESET=false
    local CLEAN_ONLY=false
    local SEED_ONLY=false
    DRY_RUN=false
    RUN_E2E=false
    FORCE=false

    # Парсинг аргументов
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full-reset)
                FULL_RESET=true
                shift
                ;;
            --clean-only)
                CLEAN_ONLY=true
                shift
                ;;
            --seed-only)
                SEED_ONLY=true
                shift
                ;;
            --preview)
                DRY_RUN=true
                shift
                ;;
            --with-e2e)
                RUN_E2E=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Неизвестная опция: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Проверка конфликтующих опций
    if [ "$CLEAN_ONLY" = true ] && [ "$SEED_ONLY" = true ]; then
        print_error "Опции --clean-only и --seed-only не могут использоваться вместе"
        exit 1
    fi

    # Инициализация лог-файла
    echo "=== THE BOT Platform - Test Environment Setup ===" > "$LOG_FILE"
    echo "Started at: $(date)" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Показываем баннер
    print_banner

    if [ "$DRY_RUN" = true ]; then
        print_warning "РЕЖИМ ПРОСМОТРА (DRY-RUN) - ИЗМЕНЕНИЯ НЕ БУДУТ ПРИМЕНЕНЫ"
        echo ""
    fi

    # Проверка предварительных условий
    check_prerequisites
    check_redis

    # Выполнение действий в зависимости от режима
    if [ "$FULL_RESET" = true ]; then
        print_header "РЕЖИМ: ПОЛНЫЙ СБРОС И ПЕРЕСОЗДАНИЕ"
        full_reset_database
        create_test_subjects
        create_full_dataset

    elif [ "$CLEAN_ONLY" = true ]; then
        print_header "РЕЖИМ: ТОЛЬКО ОЧИСТКА"
        cleanup_database

    elif [ "$SEED_ONLY" = true ]; then
        print_header "РЕЖИМ: ТОЛЬКО СОЗДАНИЕ ДАННЫХ"
        create_test_users
        create_test_subjects
        create_full_dataset

    else
        # По умолчанию: cleanup + seed
        print_header "РЕЖИМ: СТАНДАРТНЫЙ (ОЧИСТКА + СОЗДАНИЕ)"
        cleanup_database
        create_test_users
        create_test_subjects
        create_full_dataset
    fi

    # Проверка данных (если не режим только очистки)
    if [ "$CLEAN_ONLY" = false ]; then
        verify_data
    fi

    # Показываем статистику
    show_statistics

    # E2E тесты (если запрошено)
    if [ "$RUN_E2E" = true ] && [ "$CLEAN_ONLY" = false ]; then
        run_e2e_tests
    fi

    # Финальное сообщение
    echo "Log file: $LOG_FILE"
    echo ""

    log "Setup completed at: $(date)"
}

# Обработка ошибок
trap 'print_error "Скрипт прерван"; exit 130' INT
trap 'print_error "Произошла ошибка на строке $LINENO"; exit 1' ERR

# Запуск
main "$@"
