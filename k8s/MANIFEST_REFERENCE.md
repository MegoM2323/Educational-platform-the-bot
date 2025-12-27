# Kubernetes Manifests Reference

Complete reference for all Kubernetes manifests in THE_BOT Platform.

## Base Manifests (k8s/base/)

### 00-namespace.yaml
Namespace and network policies for the thebot namespace.

**Resources:**
- Namespace `thebot`
- ResourceQuota (limits resource consumption)
- NetworkPolicy (default deny-all ingress)
- NetworkPolicy (allow DNS egress)
- NetworkPolicy (inter-service communication)

**Key Config:**
- Namespace: `thebot`
- Resource limits: 20 CPUs, 40Gi memory, 100 pods max

---

### 01-configmap.yaml
Application configuration and Nginx configuration.

**ConfigMaps:**
1. `django-config` - Django/backend settings
   - ENVIRONMENT, DEBUG, LOG_LEVEL
   - Database host/port
   - Redis configuration
   - Celery broker/backend URLs
   - WebSocket configuration
   - External service URLs

2. `frontend-config` - Frontend/React settings
   - API URL, WebSocket URL
   - Application name

3. `nginx-config` - Nginx server configuration
   - SSL/TLS setup
   - Proxy configuration
   - CORS settings
   - Security headers
   - Gzip compression
   - Upstream backend configuration

4. `prometheus-config` - Prometheus monitoring configuration
   - Scrape configs for backend, postgres, redis
   - Alert configurations

---

### 02-secrets.yaml
Sensitive configuration and credentials.

**Secrets:**
1. `django-secrets` - Backend API keys and passwords
   - SECRET_KEY (Django)
   - Database credentials
   - Redis password
   - YooKassa API credentials
   - Email credentials
   - JWT secrets
   - Telegram bot token
   - External API keys

2. `postgres-credentials` - Database credentials
3. `redis-credentials` - Cache password
4. `docker-registry-credentials` - Container registry auth
5. `tls-certificate` - HTTPS certificate and key
6. `ssh-keys` - Git SSH keys (optional)

**Note:** In production, use external secret management (sealed-secrets, Vault, external-secrets-operator)

---

### 03-pvc.yaml
Persistent volume claims for stateful data.

**PersistentVolumeClaims:**
1. `postgres-pvc` - Database storage
   - Size: 100Gi (production)
   - Access mode: ReadWriteOnce
   - Storage class: standard-fast

2. `redis-pvc` - Cache storage
   - Size: 20Gi
   - Access mode: ReadWriteOnce

3. `backend-static-pvc` - Static files
   - Size: 10Gi
   - Access mode: ReadWriteMany

4. `backend-media-pvc` - User uploads
   - Size: 50Gi
   - Access mode: ReadWriteMany

5. `backend-logs-pvc` - Application logs
   - Size: 10Gi
   - Access mode: ReadWriteMany

6. `frontend-logs-pvc` - Nginx logs
   - Size: 5Gi
   - Access mode: ReadWriteMany

7. `backup-pvc` - Backup storage
   - Size: 200Gi
   - Access mode: ReadWriteOnce

**StorageClasses:**
- `standard-fast` - AWS EBS (gp3) for fast storage
- `standard-shared` - NFS for shared storage (ReadWriteMany)

---

### 04-postgres-statefulset.yaml
PostgreSQL database server.

**Resources:**
1. StatefulSet `postgres`
   - Service name: postgres (headless)
   - Replicas: 1 (primary only)
   - Pod anti-affinity enabled
   - Image: postgres:15-alpine

2. Service `postgres` (headless, clusterIP: None)
3. Service `postgres-lb` (LoadBalancer for external access)
4. ConfigMap `postgres-config` (postgresql.conf, pg_hba.conf)

**Containers:**
- `postgres` - PostgreSQL server
  - Port: 5432
  - Probes: Liveness (pg_isready), Readiness
  - Resources: 500m CPU, 512Mi memory (request); 1000m CPU, 1Gi (limit)

- `postgres-exporter` - Prometheus exporter
  - Port: 9187
  - Scrapes PostgreSQL metrics

**Health Checks:**
- Liveness: pg_isready -U postgres
- Readiness: pg_isready -U postgres

**Volumes:**
- postgres-data (StatefulSet volumeClaimTemplate)
- postgres-config (ConfigMap)
- postgres-backups (PVC)

---

### 05-redis-statefulset.yaml
Redis cache and session store.

**Resources:**
1. StatefulSet `redis`
   - Service name: redis (headless)
   - Replicas: 1
   - Image: redis:7-alpine

2. Service `redis` (headless)
3. Service `redis-svc` (ClusterIP)
4. ConfigMap `redis-config` (redis.conf)

**Containers:**
- `redis` - Redis server
  - Port: 6379
  - Command: redis-server with requirepass and appendonly
  - Resources: 250m CPU, 256Mi memory (request); 500m CPU, 512Mi (limit)

- `redis-exporter` - Prometheus exporter
  - Port: 9121

**Health Checks:**
- Liveness: redis-cli ping
- Readiness: redis-cli ping

**Configuration:**
- maxmemory: 512mb
- maxmemory-policy: allkeys-lru
- appendonly: yes (AOF persistence)

---

### 06-backend-deployment.yaml
Django REST Framework API server.

**Resources:**
1. Deployment `backend`
   - Replicas: 3
   - Image: thebot/backend:latest
   - Strategy: RollingUpdate (maxSurge: 1, maxUnavailable: 0)

2. Service `backend` (ClusterIP)
3. Service `backend-internal` (headless)
4. ServiceAccount `backend`
5. Role `backend` (read secrets/configmaps)
6. RoleBinding `backend`
7. HorizontalPodAutoscaler `backend-hpa`
   - Min replicas: 3, Max replicas: 10
   - CPU: 70%, Memory: 80%
8. PodDisruptionBudget `backend-pdb` (minAvailable: 2)

**Containers:**
- `backend` - Gunicorn WSGI server
  - Port: 8000
  - Command: gunicorn with 4 workers
  - Resources: 500m CPU, 512Mi memory (request); 1000m CPU, 1Gi (limit)
  - Probes: Liveness (/api/system/health/), Readiness (/api/system/readiness/)
  - Env: EnvFrom configmaps/secrets, PYTHONUNBUFFERED=1

**Init Containers:**
- `migrate` - Run database migrations
- `collectstatic` - Collect static files

**Volumes:**
- static (PVC backend-static-pvc)
- media (PVC backend-media-pvc)
- logs (PVC backend-logs-pvc)

**Security:**
- runAsNonRoot: true, runAsUser: 1000
- allowPrivilegeEscalation: false
- readOnlyRootFilesystem: false (needs write for migrations)

---

### 07-frontend-deployment.yaml
Nginx reverse proxy and React SPA server.

**Resources:**
1. Deployment `frontend`
   - Replicas: 3
   - Image: thebot/frontend:latest
   - Strategy: RollingUpdate

2. Service `frontend` (ClusterIP)
3. Service `frontend-lb` (LoadBalancer)
4. HorizontalPodAutoscaler `frontend-hpa`
   - Min replicas: 3, Max replicas: 10
5. PodDisruptionBudget `frontend-pdb` (minAvailable: 2)

**Containers:**
- `frontend` - Nginx
  - Port: 3000
  - Resources: 250m CPU, 256Mi memory (request); 500m CPU, 512Mi (limit)
  - Probes: Liveness, Readiness (/index.html)
  - readOnlyRootFilesystem: true

**Volumes:**
- nginx-config (ConfigMap)
- cache (emptyDir)
- logs (PVC frontend-logs-pvc)

---

### 08-celery-deployment.yaml
Asynchronous task queue workers and scheduler.

**Resources:**
1. Deployment `celery-worker`
   - Replicas: 2
   - Image: thebot/backend:latest
   - Command: celery worker with 4 concurrency

2. Deployment `celery-beat`
   - Replicas: 1 (scheduler must be singleton)
   - Image: thebot/backend:latest
   - Command: celery beat with DatabaseScheduler

3. Service `celery-worker` (headless)
4. ServiceAccount `celery-worker`
5. ServiceAccount `celery-beat`
6. HorizontalPodAutoscaler `celery-worker-hpa`
   - Min: 2, Max: 10
7. PodDisruptionBudget `celery-worker-pdb` (minAvailable: 1)

**Containers:**
- `celery-worker` - Task worker
  - Resources: 500m CPU, 512Mi memory (request); 1000m CPU, 1Gi (limit)
  - Env: Celery broker/backend URLs
  - Probes: Liveness (celery inspect active), Readiness (celery inspect ping)

- `celery-beat` - Task scheduler
  - Resources: 250m CPU, 256Mi memory (request); 500m CPU, 512Mi (limit)

---

### 09-ingress.yaml
HTTP/HTTPS ingress routing and TLS configuration.

**Resources:**
1. Ingress `thebot-ingress`
   - Hosts: the-bot.ru, *.the-bot.ru
   - TLS secret: tls-certificate
   - Annotations: ssl-redirect, rate-limit, CORS, proxy settings

2. Ingress `thebot-api-ingress`
   - Host: api.the-bot.ru
   - Paths: /ws, /api, /admin, /static, /media

3. ClusterIssuer `letsencrypt-prod`
   - ACME solver: HTTP01
   - For automatic certificate generation

4. ClusterIssuer `letsencrypt-staging`
   - For testing certificate generation

**Routing:**
- the-bot.ru → frontend (3000)
- api.the-bot.ru → backend (8000)
- ws.the-bot.ru → backend (8000)
- admin.the-bot.ru → backend (8000)
- www.the-bot.ru → frontend (3000)

---

### 10-monitoring.yaml
Prometheus monitoring and alerting configuration.

**Resources:**
1. ServiceMonitor `backend` - Scrapes /api/system/metrics/prometheus/
2. ServiceMonitor `postgres` - Scrapes pg_exporter metrics
3. ServiceMonitor `redis` - Scrapes redis_exporter metrics

4. PrometheusRule `thebot-alerts` - Alert rules
   - Backend pod restarts
   - High error rates
   - High response times
   - Database connection issues
   - Redis memory usage
   - Kubernetes pod health

5. PrometheusRule `thebot-recording-rules` - Recording rules
   - Request rates
   - Response time percentiles
   - Connection ratios

6. AlertmanagerConfig `thebot-alerts` - Alert routing
   - Routes by severity
   - Email notifications

---

### 11-pod-security.yaml
Security policies and RBAC configuration.

**Resources:**
1. PodSecurityPolicy `thebot-restricted`
   - No privileged mode
   - No privilege escalation
   - Non-root user required
   - Dropped all capabilities

2. NetworkPolicy `thebot-deny-all` - Default deny
3. NetworkPolicy `thebot-allow-dns` - Allow DNS
4. NetworkPolicy `thebot-allow-backend-postgres` - Backend to DB
5. NetworkPolicy `thebot-allow-backend-redis` - Backend to cache
6. NetworkPolicy `thebot-allow-frontend-ingress` - External to frontend
7. NetworkPolicy `thebot-allow-backend-ingress` - External to backend
8. NetworkPolicy `thebot-allow-backend-external` - Backend egress

9. ClusterRole `thebot-monitoring` - Monitoring permissions
10. ClusterRoleBinding `thebot-monitoring`

11. OPA Gatekeeper ConstraintTemplate (optional)
    - Enforces resource requests/limits

---

## Environment Overlays

### overlays/dev/
Development environment with minimal resources.

**Changes:**
- Replicas: 1 for each service (minimal HA)
- Resources: 100m CPU, 128Mi memory (backend requests)
- PVC sizes: 10Gi postgres, 5Gi media
- Images: localhost:5000 registry
- DEBUG=True, LOG_LEVEL=DEBUG
- Storage class: standard (not fast)
- No pod affinity (for smaller clusters)

---

### overlays/staging/
Staging environment for pre-production testing.

**Changes:**
- Replicas: 2 for each service
- Resources: 250m-750m CPU, 256Mi-768Mi memory
- PVC sizes: 50Gi postgres, 20Gi media
- Images: gcr.io registry
- DEBUG=False, LOG_LEVEL=INFO
- HPA limits: max 5 replicas

---

### overlays/production/
Production environment with full HA.

**Changes:**
- Replicas: 3 for each service
- Resources: 750m CPU, 768Mi memory (backend requests); 2000m CPU, 2Gi (limits)
- PVC sizes: 100Gi postgres, 50Gi media
- Images: gcr.io with specific version tags (not latest)
- DEBUG=False, LOG_LEVEL=WARNING
- Storage class: fast-ssd (required)
- HPA limits: max 15 replicas (backend), 10 (frontend)
- Strict pod affinity
- Pod disruption budgets enforced
- Network policies enforced
- Security context enforced

---

## Deployment Workflow

### 1. Development
```bash
./deploy.sh -e dev --wait
```
- Creates thebot-dev namespace
- Deploys minimal resources
- Good for local testing

### 2. Staging
```bash
./deploy.sh -e staging --wait
```
- Creates thebot-staging namespace
- Deploys medium resources
- For pre-production testing

### 3. Production
```bash
./deploy.sh -e production --wait
```
- Creates thebot namespace
- Deploys full HA setup
- For production use

---

## Validation

All manifests can be validated:

```bash
./validate.sh -e production
./test.sh -e production
./test.sh -e production --cluster  # Test against actual cluster
```

---

## File Sizes

| File | Size | Resources |
|------|------|-----------|
| 00-namespace.yaml | ~2.5 KB | 8 |
| 01-configmap.yaml | ~6 KB | 4 |
| 02-secrets.yaml | ~2 KB | 6 |
| 03-pvc.yaml | ~3 KB | 9 |
| 04-postgres-statefulset.yaml | ~8 KB | 4 |
| 05-redis-statefulset.yaml | ~9 KB | 4 |
| 06-backend-deployment.yaml | ~12 KB | 8 |
| 07-frontend-deployment.yaml | ~6 KB | 5 |
| 08-celery-deployment.yaml | ~8 KB | 7 |
| 09-ingress.yaml | ~5 KB | 6 |
| 10-monitoring.yaml | ~12 KB | 6 |
| 11-pod-security.yaml | ~10 KB | 12 |

**Total Base Resources: ~92 manifests across ~83 KB**

---

## Next Steps

1. Customize secrets for your environment
2. Update image registry URLs
3. Configure storage classes
4. Set up certificate management (cert-manager)
5. Deploy monitoring (Prometheus/Grafana)
6. Set up logging (ELK/Loki)
7. Configure GitOps (ArgoCD)
8. Test disaster recovery

See [README.md](./README.md) for detailed deployment instructions.
