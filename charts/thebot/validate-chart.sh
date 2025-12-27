#!/bin/bash

# THE_BOT Helm Chart - Basic Validation Script
# Скрипт для базовой валидации Helm chart без установки Helm

set -e

CHART_PATH="./charts/thebot"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test 1: Check chart structure
test_chart_structure() {
    log_info "Test 1: Проверка структуры chart"

    REQUIRED_FILES=("Chart.yaml" "values.yaml" "values-dev.yaml" "values-staging.yaml" "values-prod.yaml" "README.md")
    MISSING_FILES=0

    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$CHART_PATH/$file" ]; then
            log_success "Найден файл: $file"
        else
            log_error "Не найден файл: $file"
            MISSING_FILES=$((MISSING_FILES + 1))
        fi
    done

    if [ $MISSING_FILES -eq 0 ]; then
        log_success "Все необходимые файлы присутствуют"
        return 0
    else
        log_error "Отсутствуют некоторые файлы"
        return 1
    fi
}

# Test 2: Check templates directory
test_templates_directory() {
    log_info "Test 2: Проверка наличия шаблонов"

    if [ ! -d "$CHART_PATH/templates" ]; then
        log_error "Директория templates не найдена"
        return 1
    fi

    TEMPLATE_COUNT=$(find "$CHART_PATH/templates" -name "*.yaml" | wc -l)
    if [ $TEMPLATE_COUNT -gt 0 ]; then
        log_success "Найдено $TEMPLATE_COUNT шаблонов"
        return 0
    else
        log_error "Шаблоны не найдены"
        return 1
    fi
}

# Test 3: Check YAML syntax
test_yaml_syntax() {
    log_info "Test 3: Проверка синтаксиса YAML файлов"

    if ! command -v python3 &> /dev/null; then
        log_info "Python3 не установлен, пропуск теста"
        return 0
    fi

    python3 << 'PYTHON_EOF'
import yaml
import os
import sys

chart_path = "./charts/thebot"
yaml_files = []

for root, dirs, files in os.walk(chart_path):
    for file in files:
        if file.endswith(('.yaml', '.yml')):
            yaml_files.append(os.path.join(root, file))

errors = 0
for yaml_file in yaml_files:
    try:
        with open(yaml_file, 'r') as f:
            yaml.safe_load(f)
        print(f"[OK] {yaml_file}")
    except Exception as e:
        print(f"[ERROR] {yaml_file}: {str(e)}", file=sys.stderr)
        errors += 1

sys.exit(errors)
PYTHON_EOF

    if [ $? -eq 0 ]; then
        log_success "Все YAML файлы валидны"
        return 0
    else
        log_error "Некоторые YAML файлы содержат ошибки"
        return 1
    fi
}

# Test 4: Check required Kubernetes resource kinds
test_resource_kinds() {
    log_info "Test 4: Проверка типов Kubernetes ресурсов"

    REQUIRED_KINDS=("Deployment" "StatefulSet" "Service" "Ingress" "ConfigMap" "Secret" "Namespace")
    FOUND_KINDS=0

    for kind in "${REQUIRED_KINDS[@]}"; do
        if grep -r "kind: $kind" "$CHART_PATH/templates/" > /dev/null; then
            log_success "Найден ресурс: $kind"
            ((FOUND_KINDS++))
        else
            log_error "Не найден ресурс: $kind"
        fi
    done

    if [ $FOUND_KINDS -eq ${#REQUIRED_KINDS[@]} ]; then
        return 0
    else
        return 1
    fi
}

# Test 5: Check values files
test_values_files() {
    log_info "Test 5: Проверка values файлов"

    REQUIRED_KEYS=("backend" "frontend" "postgresql" "redis" "ingress")
    ERRORS=0

    for values_file in values.yaml values-dev.yaml values-staging.yaml values-prod.yaml; do
        log_info "Проверка $values_file..."

        for key in "${REQUIRED_KEYS[@]}"; do
            if grep -q "^$key:" "$CHART_PATH/$values_file"; then
                log_success "  Найден ключ: $key"
            else
                log_error "  Не найден ключ: $key"
                ERRORS=$((ERRORS + 1))
            fi
        done
    done

    if [ $ERRORS -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Test 6: Check for required environment variables
test_environment_variables() {
    log_info "Test 6: Проверка переменных окружения в templates"

    REQUIRED_VARS=("DEBUG" "ENVIRONMENT" "DATABASE_HOST" "REDIS_HOST")
    FOUND_VARS=0

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -r "name: $var" "$CHART_PATH/templates/" > /dev/null; then
            log_success "Найдена переменная окружения: $var"
            ((FOUND_VARS++))
        fi
    done

    if [ $FOUND_VARS -ge $((${#REQUIRED_VARS[@]} - 1)) ]; then
        return 0
    else
        return 1
    fi
}

# Test 7: Check helpers template
test_helpers_template() {
    log_info "Test 7: Проверка helpers шаблона"

    if [ -f "$CHART_PATH/templates/_helpers.tpl" ]; then
        HELPER_COUNT=$(grep -c "^{{-" "$CHART_PATH/templates/_helpers.tpl")
        if [ $HELPER_COUNT -gt 0 ]; then
            log_success "Найдено $HELPER_COUNT вспомогательных функций"
            return 0
        else
            log_error "Вспомогательные функции не найдены"
            return 1
        fi
    else
        log_error "Файл _helpers.tpl не найден"
        return 1
    fi
}

# Test 8: Check for probes configuration
test_probes_configuration() {
    log_info "Test 8: Проверка конфигурации probes (health checks)"

    PROBE_TYPES=("livenessProbe" "readinessProbe")
    FOUND_PROBES=0

    for probe_type in "${PROBE_TYPES[@]}"; do
        if grep -r "$probe_type" "$CHART_PATH/templates/" > /dev/null; then
            log_success "Найдена конфигурация: $probe_type"
            ((FOUND_PROBES++))
        else
            log_error "Не найдена конфигурация: $probe_type"
        fi
    done

    if [ $FOUND_PROBES -eq ${#PROBE_TYPES[@]} ]; then
        return 0
    else
        return 1
    fi
}

# Test 9: Check for resource limits
test_resource_limits() {
    log_info "Test 9: Проверка ограничений ресурсов"

    if grep -r "requests:" "$CHART_PATH/templates/" > /dev/null && \
       grep -r "limits:" "$CHART_PATH/templates/" > /dev/null; then
        log_success "Найдены конфигурации requests и limits"
        return 0
    else
        log_error "Конфигурации requests/limits не найдены"
        return 1
    fi
}

# Test 10: Check for security context
test_security_context() {
    log_info "Test 10: Проверка конфигурации безопасности (securityContext)"

    if grep -r "securityContext:" "$CHART_PATH/templates/" > /dev/null; then
        log_success "Найдена конфигурация securityContext"
        return 0
    else
        log_error "Конфигурация securityContext не найдена"
        return 1
    fi
}

# Run all tests
run_all_tests() {
    log_info "======================================================"
    log_info "THE_BOT Helm Chart - Basic Validation"
    log_info "======================================================"
    echo ""

    PASSED=0
    FAILED=0

    tests=(
        test_chart_structure
        test_templates_directory
        test_yaml_syntax
        test_resource_kinds
        test_values_files
        test_environment_variables
        test_helpers_template
        test_probes_configuration
        test_resource_limits
        test_security_context
    )

    for test in "${tests[@]}"; do
        if $test; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
        echo ""
    done

    # Summary
    log_info "======================================================"
    log_info "VALIDATION SUMMARY"
    log_info "======================================================"
    echo -e "${GREEN}Tests passed: $PASSED${NC}"
    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}Tests failed: $FAILED${NC}"
        return 1
    else
        echo -e "${GREEN}All validation checks passed!${NC}"
        return 0
    fi
}

# Main
run_all_tests
exit $?
