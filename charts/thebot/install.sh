#!/bin/bash

# THE_BOT Helm Chart - Installation Script
# Скрипт для установки/обновления Helm chart на Kubernetes

set -e

# Configuration
CHART_NAME="thebot"
CHART_PATH="./charts/thebot"
NAMESPACE="thebot"
ENVIRONMENT="${1:-dev}"
DRY_RUN="${2:-false}"

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Проверка предварительных условий..."

    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm не установлен"
        exit 1
    fi
    log_success "Helm установлен"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl не установлен"
        exit 1
    fi
    log_success "kubectl установлен"

    # Check chart exists
    if [ ! -f "$CHART_PATH/Chart.yaml" ]; then
        log_error "Chart не найден в $CHART_PATH"
        exit 1
    fi
    log_success "Chart найден"
}

# Lint chart
lint_chart() {
    log_info "Валидация chart..."

    if helm lint "$CHART_PATH"; then
        log_success "Chart валиден"
    else
        log_error "Chart содержит ошибки"
        exit 1
    fi
}

# Create namespace
create_namespace() {
    log_info "Создание namespace..."

    if kubectl create namespace "$NAMESPACE" 2>/dev/null; then
        log_success "Namespace $NAMESPACE создан"
    else
        log_warning "Namespace $NAMESPACE уже существует"
    fi
}

# Create values file
get_values_file() {
    case "$ENVIRONMENT" in
        dev)
            echo "$CHART_PATH/values-dev.yaml"
            ;;
        staging)
            echo "$CHART_PATH/values-staging.yaml"
            ;;
        prod)
            echo "$CHART_PATH/values-prod.yaml"
            ;;
        *)
            log_error "Неизвестное окружение: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

# Dry run
dry_run_install() {
    local values_file=$(get_values_file)

    log_info "Выполнение сухого запуска (dry-run)..."
    log_info "Используемые значения: $values_file"

    helm install "$CHART_NAME" "$CHART_PATH" \
        -f "$values_file" \
        --namespace "$NAMESPACE" \
        --dry-run \
        --debug

    log_success "Dry-run успешен"
}

# Install or upgrade
install_or_upgrade() {
    local values_file=$(get_values_file)

    log_info "Проверка текущей установки..."

    if helm list -n "$NAMESPACE" | grep -q "$CHART_NAME"; then
        log_info "Release $CHART_NAME найден, выполняется upgrade..."

        helm upgrade "$CHART_NAME" "$CHART_PATH" \
            -f "$values_file" \
            --namespace "$NAMESPACE" \
            --wait \
            --timeout 10m \
            ${HELM_EXTRA_ARGS:-}

        log_success "Release успешно обновлен"
    else
        log_info "Release $CHART_NAME не найден, выполняется install..."

        helm install "$CHART_NAME" "$CHART_PATH" \
            -f "$values_file" \
            --namespace "$NAMESPACE" \
            --wait \
            --timeout 10m \
            ${HELM_EXTRA_ARGS:-}

        log_success "Release успешно установлен"
    fi
}

# Show deployment status
show_status() {
    log_info "Статус развертывания..."

    kubectl get all -n "$NAMESPACE" -o wide

    log_info "Статус pods..."
    kubectl get pods -n "$NAMESPACE" -w &
    WATCH_PID=$!

    # Wait for pods to be ready (max 5 minutes)
    log_info "Ожидание готовности pods (timeout 5m)..."
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=thebot \
        -n "$NAMESPACE" \
        --timeout=300s || log_warning "Некоторые pods не готовы"

    kill $WATCH_PID 2>/dev/null || true
}

# Show access information
show_access_info() {
    log_info "======================================================"
    log_info "Информация о доступе к приложению"
    log_info "======================================================"

    case "$ENVIRONMENT" in
        dev)
            log_info "Frontend доступен по адресу: http://localhost:8080"
            log_info "Backend доступен по адресу: http://localhost:8000"
            log_info ""
            log_info "Port forwarding для frontend:"
            log_info "  kubectl port-forward -n $NAMESPACE service/thebot-frontend 8080:80"
            log_info ""
            log_info "Port forwarding для backend:"
            log_info "  kubectl port-forward -n $NAMESPACE service/thebot-backend 8000:8000"
            ;;
        staging)
            log_info "Frontend доступен по адресу: https://staging.thebot.com"
            log_info "Backend доступен по адресу: https://api.staging.thebot.com"
            ;;
        prod)
            log_info "Frontend доступен по адресу: https://thebot.com"
            log_info "Backend доступен по адресу: https://api.thebot.com"
            ;;
    esac

    log_info ""
    log_info "Просмотр логов:"
    log_info "  kubectl logs -n $NAMESPACE deployment/thebot-backend -f"
    log_info "  kubectl logs -n $NAMESPACE deployment/thebot-frontend -f"
    log_info ""
    log_info "Просмотр статуса release:"
    log_info "  helm status thebot -n $NAMESPACE"
    log_info ""
    log_info "Просмотр значений:"
    log_info "  helm get values thebot -n $NAMESPACE"
}

# Main
main() {
    log_info "======================================================"
    log_info "THE_BOT Helm Chart Installation"
    log_info "======================================================"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info ""

    check_prerequisites
    echo ""

    lint_chart
    echo ""

    create_namespace
    echo ""

    if [ "$DRY_RUN" = "true" ]; then
        dry_run_install
        echo ""
        log_info "Для реальной установки выполни:"
        log_info "  ./install.sh $ENVIRONMENT false"
    else
        install_or_upgrade
        echo ""

        show_status
        echo ""

        show_access_info
    fi

    log_info "======================================================"
    log_success "Установка завершена!"
    log_info "======================================================"
}

# Show usage
show_usage() {
    cat << EOF
Usage: ./install.sh [ENVIRONMENT] [DRY_RUN]

Arguments:
  ENVIRONMENT   Окружение для установки (dev, staging, prod)
                Default: dev
  DRY_RUN       Выполнить сухой запуск без реальной установки (true/false)
                Default: false

Examples:
  # Installation in development
  ./install.sh dev false

  # Dry-run for staging
  ./install.sh staging true

  # Installation in production
  ./install.sh prod false

EOF
}

# Parse arguments
if [ "$ENVIRONMENT" = "--help" ] || [ "$ENVIRONMENT" = "-h" ]; then
    show_usage
    exit 0
fi

# Run main
main
