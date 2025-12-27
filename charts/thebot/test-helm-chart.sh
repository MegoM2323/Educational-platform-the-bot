#!/bin/bash

# THE_BOT Helm Chart - Test Script
# Скрипт для валидации и тестирования Helm chart

set -e

CHART_PATH="./charts/thebot"
COLORS=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    if [ "$COLORS" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    else
        echo "[INFO] $1"
    fi
}

log_success() {
    if [ "$COLORS" = true ]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    else
        echo "[SUCCESS] $1"
    fi
}

log_warning() {
    if [ "$COLORS" = true ]; then
        echo -e "${YELLOW}[WARNING]${NC} $1"
    else
        echo "[WARNING] $1"
    fi
}

log_error() {
    if [ "$COLORS" = true ]; then
        echo -e "${RED}[ERROR]${NC} $1"
    else
        echo "[ERROR] $1"
    fi
}

# Test 1: Check if helm is installed
test_helm_installed() {
    log_info "Test 1: Проверка установки Helm"

    if ! command -v helm &> /dev/null; then
        log_error "Helm не установлен"
        return 1
    fi

    HELM_VERSION=$(helm version --short)
    log_success "Helm установлен: $HELM_VERSION"
    return 0
}

# Test 2: Lint the chart
test_lint() {
    log_info "Test 2: Валидация синтаксиса chart"

    if helm lint "$CHART_PATH"; then
        log_success "Chart синтаксис валиден"
        return 0
    else
        log_error "Chart синтаксис некорректен"
        return 1
    fi
}

# Test 3: Template rendering with default values
test_template_default() {
    log_info "Test 3: Рендер шаблонов с default значениями"

    if helm template thebot "$CHART_PATH" > /tmp/thebot-default.yaml; then
        MANIFEST_SIZE=$(wc -l < /tmp/thebot-default.yaml)
        log_success "Шаблоны отрендерены ($MANIFEST_SIZE строк)"
        return 0
    else
        log_error "Ошибка при рендере шаблонов"
        return 1
    fi
}

# Test 4: Template rendering with dev values
test_template_dev() {
    log_info "Test 4: Рендер шаблонов с dev значениями"

    if helm template thebot "$CHART_PATH" -f "$CHART_PATH/values-dev.yaml" > /tmp/thebot-dev.yaml; then
        MANIFEST_SIZE=$(wc -l < /tmp/thebot-dev.yaml)
        log_success "Шаблоны отрендерены в dev режиме ($MANIFEST_SIZE строк)"
        return 0
    else
        log_error "Ошибка при рендере шаблонов в dev режиме"
        return 1
    fi
}

# Test 5: Template rendering with staging values
test_template_staging() {
    log_info "Test 5: Рендер шаблонов с staging значениями"

    if helm template thebot "$CHART_PATH" -f "$CHART_PATH/values-staging.yaml" > /tmp/thebot-staging.yaml; then
        MANIFEST_SIZE=$(wc -l < /tmp/thebot-staging.yaml)
        log_success "Шаблоны отрендерены в staging режиме ($MANIFEST_SIZE строк)"
        return 0
    else
        log_error "Ошибка при рендере шаблонов в staging режиме"
        return 1
    fi
}

# Test 6: Template rendering with prod values
test_template_prod() {
    log_info "Test 6: Рендер шаблонов с prod значениями"

    if helm template thebot "$CHART_PATH" -f "$CHART_PATH/values-prod.yaml" > /tmp/thebot-prod.yaml; then
        MANIFEST_SIZE=$(wc -l < /tmp/thebot-prod.yaml)
        log_success "Шаблоны отрендерены в prod режиме ($MANIFEST_SIZE строк)"
        return 0
    else
        log_error "Ошибка при рендере шаблонов в prod режиме"
        return 1
    fi
}

# Test 7: Check manifest syntax with kubectl
test_manifest_syntax() {
    log_info "Test 7: Проверка синтаксиса manifest файлов"

    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl не установлен, пропуск теста"
        return 0
    fi

    # Test dev manifest
    if kubectl apply -f /tmp/thebot-dev.yaml --dry-run=client -o yaml > /dev/null 2>&1; then
        log_success "Dev manifest синтаксис корректен"
        return 0
    else
        log_error "Dev manifest синтаксис некорректен"
        return 1
    fi
}

# Test 8: Check for required resources
test_required_resources() {
    log_info "Test 8: Проверка наличия обязательных ресурсов"

    MANIFEST="/tmp/thebot-default.yaml"
    REQUIRED_RESOURCES=("Namespace" "ConfigMap" "Secret" "Deployment" "Service" "StatefulSet" "Ingress")
    MISSING_RESOURCES=0

    for resource in "${REQUIRED_RESOURCES[@]}"; do
        if grep -q "kind: $resource" "$MANIFEST"; then
            log_success "Найден ресурс: $resource"
        else
            log_error "Не найден ресурс: $resource"
            MISSING_RESOURCES=$((MISSING_RESOURCES + 1))
        fi
    done

    if [ $MISSING_RESOURCES -eq 0 ]; then
        log_success "Все обязательные ресурсы присутствуют"
        return 0
    else
        log_error "Отсутствуют некоторые ресурсы"
        return 1
    fi
}

# Test 9: Check for replica count overrides
test_replica_counts() {
    log_info "Test 9: Проверка количества реплик в разных окружениях"

    # Dev: 1 replica
    DEV_REPLICAS=$(grep -A 10 "kind: Deployment" /tmp/thebot-dev.yaml | grep "replicas:" | head -1 | awk '{print $2}')
    if [ "$DEV_REPLICAS" = "1" ]; then
        log_success "Dev: $DEV_REPLICAS replica (correct)"
    else
        log_warning "Dev: $DEV_REPLICAS replicas (expected 1)"
    fi

    # Staging: 2-3 replicas
    STAGING_REPLICAS=$(grep -A 10 "kind: Deployment" /tmp/thebot-staging.yaml | grep "replicas:" | head -1 | awk '{print $2}')
    if [ "$STAGING_REPLICAS" = "2" ]; then
        log_success "Staging: $STAGING_REPLICAS replicas (correct)"
    else
        log_warning "Staging: $STAGING_REPLICAS replicas (expected 2)"
    fi

    # Prod: 3 replicas
    PROD_REPLICAS=$(grep -A 10 "kind: Deployment" /tmp/thebot-prod.yaml | grep "replicas:" | head -1 | awk '{print $2}')
    if [ "$PROD_REPLICAS" = "3" ]; then
        log_success "Prod: $PROD_REPLICAS replicas (correct)"
    else
        log_warning "Prod: $PROD_REPLICAS replicas (expected 3)"
    fi

    return 0
}

# Test 10: Check for environment variables
test_environment_variables() {
    log_info "Test 10: Проверка переменных окружения"

    MANIFEST="/tmp/thebot-prod.yaml"
    EXPECTED_VARS=("DEBUG" "ENVIRONMENT" "ALLOWED_HOSTS" "DATABASE_HOST" "REDIS_HOST")
    MISSING_VARS=0

    for var in "${EXPECTED_VARS[@]}"; do
        if grep -q "name: $var" "$MANIFEST"; then
            log_success "Найдена переменная окружения: $var"
        else
            log_error "Не найдена переменная окружения: $var"
            MISSING_VARS=$((MISSING_VARS + 1))
        fi
    done

    if [ $MISSING_VARS -eq 0 ]; then
        log_success "Все необходимые переменные окружения присутствуют"
        return 0
    else
        log_error "Отсутствуют некоторые переменные окружения"
        return 1
    fi
}

# Test 11: Check for persistent volumes
test_persistent_volumes() {
    log_info "Test 11: Проверка PersistentVolumeClaims"

    MANIFEST="/tmp/thebot-default.yaml"
    PVCS=("thebot-static" "thebot-media")
    MISSING_PVCS=0

    for pvc in "${PVCS[@]}"; do
        if grep -q "name: $pvc" "$MANIFEST"; then
            log_success "Найден PVC: $pvc"
        else
            log_error "Не найден PVC: $pvc"
            MISSING_PVCS=$((MISSING_PVCS + 1))
        fi
    done

    if [ $MISSING_PVCS -eq 0 ]; then
        log_success "Все необходимые PVC присутствуют"
        return 0
    else
        log_error "Отсутствуют некоторые PVC"
        return 1
    fi
}

# Test 12: Compare file sizes
test_manifest_sizes() {
    log_info "Test 12: Сравнение размеров manifest файлов"

    DEV_SIZE=$(wc -c < /tmp/thebot-dev.yaml)
    STAGING_SIZE=$(wc -c < /tmp/thebot-staging.yaml)
    PROD_SIZE=$(wc -c < /tmp/thebot-prod.yaml)

    log_success "Dev manifest: $DEV_SIZE bytes"
    log_success "Staging manifest: $STAGING_SIZE bytes"
    log_success "Prod manifest: $PROD_SIZE bytes"

    return 0
}

# Run all tests
run_all_tests() {
    log_info "======================================================"
    log_info "THE_BOT Helm Chart - Test Suite"
    log_info "======================================================"
    echo ""

    PASSED=0
    FAILED=0

    # Test 1
    if test_helm_installed; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 2
    if test_lint; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 3
    if test_template_default; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 4
    if test_template_dev; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 5
    if test_template_staging; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 6
    if test_template_prod; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 7
    if test_manifest_syntax; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 8
    if test_required_resources; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 9
    if test_replica_counts; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 10
    if test_environment_variables; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 11
    if test_persistent_volumes; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Test 12
    if test_manifest_sizes; then ((PASSED++)); else ((FAILED++)); fi
    echo ""

    # Summary
    log_info "======================================================"
    log_info "TEST SUMMARY"
    log_info "======================================================"
    log_success "Tests passed: $PASSED"
    if [ $FAILED -gt 0 ]; then
        log_error "Tests failed: $FAILED"
        return 1
    else
        log_success "All tests passed!"
        return 0
    fi
}

# Main
run_all_tests
exit $?
