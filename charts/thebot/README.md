# THE_BOT Helm Chart

Helm chart для развертывания THE_BOT - образовательной платформы на Kubernetes.

## Overview

THE_BOT - это полнофункциональная образовательная платформа с поддержкой:
- Django REST Framework backend
- React frontend
- PostgreSQL database
- Redis cache & message broker
- Celery для асинхронных задач

## Chart Structure

```
thebot/
├── Chart.yaml                    # Метаинформация чарта
├── values.yaml                   # Default значения
├── values-dev.yaml              # Development окружение
├── values-staging.yaml          # Staging окружение
├── values-prod.yaml             # Production окружение (шаблон)
├── values-prod-example.yaml     # Пример production конфигурации
├── README.md                    # Этот файл
└── templates/
    ├── _helpers.tpl             # Шаблонные функции
    ├── namespace.yaml           # Kubernetes namespace
    ├── configmap.yaml           # ConfigMap для конфигурации
    ├── secret.yaml              # Secret для чувствительных данных
    ├── serviceaccount.yaml      # ServiceAccount для RBAC
    ├── pvc.yaml                 # PersistentVolumeClaims
    ├── backend-deployment.yaml  # Backend deployment
    ├── backend-service.yaml     # Backend service
    ├── frontend-deployment.yaml # Frontend deployment
    ├── frontend-service.yaml    # Frontend service
    ├── celery-deployment.yaml   # Celery workers
    ├── celery-beat-deployment.yaml # Celery scheduler
    ├── postgresql-statefulset.yaml # PostgreSQL database
    ├── postgresql-service.yaml  # PostgreSQL service
    ├── redis-statefulset.yaml   # Redis cache
    ├── redis-service.yaml       # Redis service
    ├── ingress.yaml             # Ingress для публичного доступа
    ├── migration-job.yaml       # Job для DB миграций
    ├── collectstatic-job.yaml   # Job для сбора static файлов
    ├── hpa-backend.yaml         # Horizontal Pod Autoscaler
    ├── hpa-frontend.yaml        # Horizontal Pod Autoscaler
    ├── hpa-celery.yaml          # Horizontal Pod Autoscaler
    ├── network-policy.yaml      # NetworkPolicy для безопасности
    └── pdb-backend.yaml         # Pod Disruption Budget
```

## Quick Start

### 1. Development

```bash
# Установка в development режиме
helm install thebot ./charts/thebot \
  -f values-dev.yaml \
  --namespace thebot \
  --create-namespace

# Проверка статуса
kubectl get all -n thebot

# Просмотр логов
kubectl logs -n thebot deployment/thebot-backend -f
```

### 2. Staging

```bash
# Установка в staging режиме
helm install thebot ./charts/thebot \
  -f values-staging.yaml \
  --namespace thebot \
  --create-namespace

# Проверка статуса
helm status thebot -n thebot

# Просмотр значений
helm get values thebot -n thebot
```

### 3. Production

```bash
# ВАЖНО: Переопределить secrets перед deployment!

# Установка в production режиме с custom values
helm install thebot ./charts/thebot \
  -f values-prod.yaml \
  -f values-prod-custom.yaml \  # Используй свои значения!
  --namespace thebot \
  --create-namespace \
  --wait \
  --timeout 10m
```

## Configuration

### Default Values (values.yaml)

Основные параметры:
- **Environment**: development
- **Backend replicas**: 1
- **Frontend replicas**: 1
- **PostgreSQL storage**: 10Gi
- **Redis storage**: 5Gi

### Environment-Specific Values

#### Development (values-dev.yaml)
- Debug: True
- 1 replica per service
- Small resource limits
- Disabled autoscaling
- Local storage (standard)

#### Staging (values-staging.yaml)
- Debug: False
- 2-3 replicas per service
- Medium resource limits
- Autoscaling enabled (2-4 replicas)
- SSD storage
- Monitoring enabled
- Network policies enabled

#### Production (values-prod.yaml)
- Debug: False
- 3+ replicas per service
- Large resource limits
- Autoscaling enabled (3-10 replicas)
- Fast SSD storage
- Full monitoring & logging
- Network policies enabled
- Pod disruption budgets
- High availability setup

## Installation

### Prerequisites

- Kubernetes 1.20+
- Helm 3+
- kubectl configured

### Step-by-Step Installation

```bash
# 1. Добавить Helm repo (если используются внешние чарты)
# helm repo add bitnami https://charts.bitnami.com/bitnami
# helm repo update

# 2. Создать namespace
kubectl create namespace thebot

# 3. Создать файл с секретами (не добавлять в git!)
cat > values-prod-secrets.yaml <<EOF
secrets:
  data:
    SECRET_KEY: "your-secret-key-here"
    POSTGRES_PASSWORD: "your-postgres-password"
    DATABASE_URL: "postgresql://thebot_user:password@postgres:5432/thebot_prod"
    REDIS_URL: "redis://redis:6379/0"
    YOOKASSA_SHOP_ID: "your-shop-id"
    YOOKASSA_SECRET_KEY: "your-secret"
EOF

# 4. Установить chart
helm install thebot ./charts/thebot \
  -f values-prod.yaml \
  -f values-prod-secrets.yaml \
  -n thebot

# 5. Проверить статус
helm status thebot -n thebot
kubectl get all -n thebot
```

## Upgrade

```bash
# Обновить chart с новыми значениями
helm upgrade thebot ./charts/thebot \
  -f values-prod.yaml \
  -f values-prod-secrets.yaml \
  -n thebot \
  --wait

# Откатить на предыдущую версию если что-то пошло не так
helm rollback thebot -n thebot
```

## Validation

### Синтаксис чарта

```bash
# Проверить синтаксис
helm lint ./charts/thebot

# Отобразить шаблоны без установки
helm template thebot ./charts/thebot -f values-dev.yaml

# Сухой запуск (dry-run)
helm install thebot ./charts/thebot \
  -f values-dev.yaml \
  --dry-run \
  --debug
```

### Проверка ресурсов

```bash
# Проверить развернутые ресурсы
kubectl get all -n thebot

# Проверить состояние pods
kubectl get pods -n thebot -w

# Проверить логи
kubectl logs -n thebot deployment/thebot-backend -f
kubectl logs -n thebot statefulset/thebot-postgres -f

# Проверить events
kubectl get events -n thebot --sort-by='.lastTimestamp'
```

## Values Reference

### Backend

```yaml
backend:
  enabled: true
  replicaCount: 1
  image:
    repository: thebot/backend
    tag: latest
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

### Database (PostgreSQL)

```yaml
postgresql:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi
    storageClassName: "standard"
```

### Cache (Redis)

```yaml
redis:
  enabled: true
  persistence:
    enabled: true
    size: 5Gi
    storageClassName: "standard"
```

### Ingress

```yaml
ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: "thebot.local"
      paths:
        - path: /
          backend: frontend
        - path: /api
          backend: backend
```

## Secrets Management

**ВАЖНО**: Никогда не добавляй секреты в values файлы, которые добавляются в git!

### Option 1: External Secrets File

```bash
# Создать файл с секретами (add to .gitignore)
cat > values-prod-secrets.yaml <<EOF
secrets:
  data:
    SECRET_KEY: "change-me"
    POSTGRES_PASSWORD: "change-me"
    DATABASE_URL: "postgresql://..."
EOF

# Установить с секретами
helm install thebot ./charts/thebot \
  -f values-prod.yaml \
  -f values-prod-secrets.yaml
```

### Option 2: External Secrets Operator

```yaml
# Использовать external-secrets для управления секретами из AWS Secrets Manager / Vault
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: thebot-secrets
spec:
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: thebot-secrets
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: thebot/secret-key
```

### Option 3: Sealed Secrets

```bash
# Зашифровать секреты с помощью sealed-secrets
echo -n 'my-secret' | kubectl create secret generic thebot-secrets \
  --dry-run=client \
  --from-file=/dev/stdin \
  -o yaml | kubeseal -f - > sealed-secrets.yaml
```

## Troubleshooting

### Pods не запускаются

```bash
# Проверить логи pod
kubectl logs -n thebot <pod-name>

# Проверить описание pod (events)
kubectl describe pod -n thebot <pod-name>

# Проверить статус
kubectl get pods -n thebot -o wide
```

### Недостаточно ресурсов

```bash
# Проверить наличие свободных ресурсов
kubectl top nodes

# Проверить распределение pod по нодам
kubectl get pods -n thebot -o wide

# Просмотреть requests/limits
kubectl describe node <node-name>
```

### Database подключение

```bash
# Проверить доступность PostgreSQL
kubectl exec -n thebot deployment/thebot-backend -- \
  pg_isready -h thebot-postgres -U thebot_user

# Проверить доступность Redis
kubectl exec -n thebot deployment/thebot-backend -- \
  redis-cli -h thebot-redis ping
```

### Миграции не выполнились

```bash
# Проверить логи job миграции
kubectl logs -n thebot job/thebot-migrate

# Запустить миграции вручную
kubectl exec -n thebot deployment/thebot-backend -- \
  python manage.py migrate
```

## Monitoring

### Prometheus (если enabled)

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
```

### Health Checks

```bash
# Backend health
kubectl exec -n thebot deployment/thebot-backend -- \
  curl http://localhost:8000/api/system/health/

# Frontend health
kubectl exec -n thebot deployment/thebot-frontend -- \
  curl http://localhost:80/

# Database health
kubectl exec -n thebot statefulset/thebot-postgres -- \
  pg_isready -U thebot_user
```

## Scaling

### Manual Scaling

```bash
# Scale backend to 5 replicas
kubectl scale deployment thebot-backend \
  -n thebot \
  --replicas=5

# Scale frontend to 3 replicas
kubectl scale deployment thebot-frontend \
  -n thebot \
  --replicas=3
```

### Autoscaling

Autoscaling можно включить в values файле:

```yaml
backend:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

## Backup & Restore

### Backup Database

```bash
# Создать backup PostgreSQL
kubectl exec -n thebot statefulset/thebot-postgres -- \
  pg_dump -U thebot_user thebot > thebot_backup.sql

# Или использовать PV snapshots
kubectl exec -n thebot statefulset/thebot-postgres -- \
  pg_dump -U thebot_user -Fc thebot > thebot_backup.dump
```

### Restore Database

```bash
# Восстановить из backup
kubectl exec -i -n thebot statefulset/thebot-postgres -- \
  psql -U thebot_user thebot < thebot_backup.sql
```

## Uninstall

```bash
# Удалить release
helm uninstall thebot -n thebot

# Удалить namespace (удалит все ресурсы)
kubectl delete namespace thebot

# Удалить PVC если нужно сохранить данные
kubectl get pvc -n thebot
```

## Development

### Lint Chart

```bash
helm lint ./charts/thebot
```

### Template Validation

```bash
helm template thebot ./charts/thebot -f values-dev.yaml | kubectl apply -f - --dry-run=client
```

### Update Dependencies

```bash
# Если используются зависимости
helm dependency update ./charts/thebot
```

## Advanced

### Custom Resource Definitions

Если нужны CRD для Prometheus, cert-manager и т.д.:

```bash
# Добавить зависимость в Chart.yaml
dependencies:
  - name: prometheus
    version: "15.x.x"
    repository: https://prometheus-community.github.io/helm-charts
    condition: prometheus.enabled

# Обновить dependencies
helm dependency update ./charts/thebot
```

### Multiple Releases

```bash
# Установить несколько версий одного приложения
helm install thebot-prod ./charts/thebot \
  -f values-prod.yaml \
  -n thebot-prod

helm install thebot-staging ./charts/thebot \
  -f values-staging.yaml \
  -n thebot-staging
```

## Support

Для проблем и вопросов:
1. Проверить логи: `kubectl logs -n thebot <pod-name>`
2. Проверить события: `kubectl get events -n thebot`
3. Проверить статус: `helm status thebot -n thebot`
4. Проверить values: `helm get values thebot -n thebot`

## License

[LICENSE]

## Contributing

[CONTRIBUTING]
