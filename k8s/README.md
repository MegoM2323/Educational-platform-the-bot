# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for THE_BOT Platform deployment on any Kubernetes cluster.

## Overview

The Kubernetes manifests are organized in a scalable structure using Kustomize:

```
k8s/
├── base/              # Base configuration shared across all environments
├── overlays/
│   ├── dev/          # Development environment
│   ├── staging/      # Staging environment
│   └── production/   # Production environment
└── scripts/          # Deployment and management scripts
```

## Prerequisites

- Kubernetes 1.21+
- kubectl 1.21+
- Helm 3.0+ (for package management)
- Kustomize 4.0+ (included with kubectl)
- cert-manager (for TLS certificates)
- Prometheus Operator (for monitoring, optional)
- Container images built and pushed to registry

## Architecture

### Core Components

1. **Frontend** (3 replicas)
   - Nginx reverse proxy
   - React SPA serving
   - Static asset caching
   - API/WebSocket proxying

2. **Backend** (3 replicas)
   - Django REST Framework API
   - Gunicorn WSGI server
   - Health/readiness probes
   - Metrics endpoint

3. **Celery Workers** (2 replicas)
   - Task queue processing
   - Background jobs
   - Email notifications
   - Report generation

4. **Celery Beat** (1 replica)
   - Scheduled task coordination
   - Database-driven scheduler
   - Task execution triggering

5. **PostgreSQL** (1 primary)
   - Database with WAL archiving
   - Replication support
   - pg_exporter for metrics

6. **Redis** (1 instance)
   - Cache and session store
   - Celery broker
   - WebSocket backend
   - redis_exporter for metrics

### Networking

- **Namespace**: Isolated `thebot` namespace
- **Network Policies**: Strict ingress/egress rules
- **Ingress**: Multi-host routing with TLS
- **Services**: ClusterIP and LoadBalancer

### Storage

- PostgreSQL: 100Gi (production)
- Redis: 20Gi
- Backend media: 50Gi
- Static files: 10Gi
- Logs: 10Gi frontend + 10Gi backend

### Security

- Pod Security Standards (restricted)
- Network policies (namespace isolation)
- RBAC rules
- Non-root containers
- Read-only root filesystems
- Resource limits
- Security context

### Monitoring

- Prometheus scrape targets
- AlertManager rules
- PrometheusRule CRDs
- ServiceMonitor objects
- Grafana dashboards (optional)

## Quick Start

### 1. Prepare Environment

```bash
cd /path/to/THE_BOT_platform/k8s

# Verify kubectl context
kubectl config current-context
kubectl get nodes
```

### 2. Configure Secrets

Edit the secrets for your environment:

```bash
# Development
kubectl create namespace thebot-dev
kubectl apply -k overlays/dev/

# Staging
kubectl create namespace thebot-staging
kubectl apply -k overlays/staging/

# Production
kubectl apply -k overlays/production/
```

### 3. Deploy

```bash
# Dry run (verify)
kubectl apply -k overlays/production/ --dry-run=client -o yaml

# Actual deployment
kubectl apply -k overlays/production/

# Watch deployment
kubectl rollout status deployment/backend -n thebot
kubectl rollout status deployment/frontend -n thebot
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n thebot
kubectl get pods -n thebot -o wide

# Check services
kubectl get svc -n thebot

# Check ingress
kubectl get ingress -n thebot

# Check persistent volumes
kubectl get pvc -n thebot

# View logs
kubectl logs -n thebot deployment/backend --tail=100
kubectl logs -n thebot deployment/frontend --tail=50
```

## Configuration

### ConfigMaps and Secrets

All configuration is managed through:

1. **ConfigMaps** (non-sensitive)
   - Django settings (ENVIRONMENT, DEBUG, ALLOWED_HOSTS)
   - Redis/database hosts
   - API URLs
   - Nginx configuration

2. **Secrets** (sensitive)
   - Database passwords
   - API keys
   - JWT secrets
   - Email credentials

### Customization per Environment

Edit `overlays/{dev,staging,production}/kustomization.yaml`:

```yaml
# Change replicas
replicas:
- name: backend
  count: 5

# Change images
images:
- name: thebot/backend
  newTag: v1.2.3

# Override resource limits
patches:
- target:
    kind: Deployment
    name: backend
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/resources/requests/cpu
      value: 1000m
```

## Deployment Strategies

### Rolling Update (Default)

Safe for production. Gradually replaces pods.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

### Blue-Green Deployment

Requires running two complete environments.

### Canary Deployment

Gradually shift traffic to new version using Istio/Flagger.

## Scaling

### Manual Scaling

```bash
kubectl scale deployment backend --replicas=5 -n thebot
kubectl scale statefulset postgres --replicas=2 -n thebot
```

### Automatic Scaling (HPA)

Enabled by default. Scales based on CPU/memory:

```bash
# View HPA status
kubectl get hpa -n thebot
kubectl describe hpa backend-hpa -n thebot

# Update HPA limits
kubectl patch hpa backend-hpa -p '{"spec":{"maxReplicas":20}}' -n thebot
```

## High Availability

### Database HA

PostgreSQL with replication:

```bash
# Scale PostgreSQL replicas
kubectl scale statefulset postgres --replicas=2 -n thebot

# Check replication status
kubectl exec -it postgres-0 -n thebot -- psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### Redis HA

For production, use Redis Sentinel or Redis Cluster:

```bash
# View current Redis setup
kubectl describe statefulset redis -n thebot

# Scale Redis (note: clustering requires additional configuration)
kubectl scale statefulset redis --replicas=3 -n thebot
```

### Backend/Frontend HA

Already configured with:
- Multiple replicas (3+)
- Pod anti-affinity
- Pod disruption budgets
- Health checks

## Monitoring and Logging

### Prometheus

```bash
# Port forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# View metrics at http://localhost:9090
```

### Grafana

```bash
# Port forward to Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access at http://localhost:3000
```

### Logs

```bash
# Tail backend logs
kubectl logs -f deployment/backend -n thebot

# Tail frontend logs
kubectl logs -f deployment/frontend -n thebot

# Tail celery worker logs
kubectl logs -f deployment/celery-worker -n thebot

# View logs across all containers
kubectl logs -f deployment/backend -n thebot --all-containers=true
```

### Metrics

```bash
# Top resource consumers
kubectl top nodes
kubectl top pods -n thebot

# View resource usage
kubectl describe node <node-name>
```

## Backup and Recovery

### Database Backup

```bash
# Manual backup
kubectl exec -it postgres-0 -n thebot -- pg_dump -U postgres thebot_db > backup.sql

# Restore from backup
kubectl exec -it postgres-0 -n thebot -- psql -U postgres thebot_db < backup.sql

# Use pg_basebackup for replication
kubectl exec -it postgres-0 -n thebot -- pg_basebackup -h postgres.thebot.svc.cluster.local -D /var/lib/postgresql/backup
```

### Volume Snapshots

```bash
# Create snapshot
kubectl apply -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot
  namespace: thebot
spec:
  volumeSnapshotClassName: csi-hostpath-snapshotclass
  source:
    persistentVolumeClaimName: postgres-pvc
EOF

# List snapshots
kubectl get volumesnapshot -n thebot
```

### Velero (cluster-wide backup)

```bash
# Install Velero
velero install --provider aws --bucket thebot-backups --secret-file credentials-velero

# Create backup
velero backup create thebot-backup --include-namespaces thebot

# Restore from backup
velero restore create --from-backup thebot-backup
```

## Network Policies

All network policies are automatically created. Review them:

```bash
kubectl get networkpolicies -n thebot
kubectl describe networkpolicy allow-backend-to-postgres -n thebot
```

To disable network policies temporarily:

```bash
kubectl delete networkpolicies -l app=thebot -n thebot
```

## Ingress Configuration

### Using Nginx Ingress Controller

```bash
# Install nginx-ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace

# Check ingress controller
kubectl get svc -n ingress-nginx
```

### Using AWS ALB

```bash
# Install AWS ALB controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system
```

### TLS Configuration

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace

# Verify ClusterIssuers
kubectl get clusterissuers -n thebot
```

## Troubleshooting

### Pod Won't Start

```bash
# Check pod status
kubectl describe pod <pod-name> -n thebot

# Check logs
kubectl logs <pod-name> -n thebot

# Check events
kubectl get events -n thebot --sort-by='.lastTimestamp'
```

### Pending PVC

```bash
# Check PVC status
kubectl describe pvc postgres-pvc -n thebot

# Check available storage classes
kubectl get storageclass
```

### Service Unreachable

```bash
# Check service endpoints
kubectl get endpoints -n thebot

# Check DNS (from pod)
kubectl run -it debug --image=busybox -n thebot -- nslookup backend.thebot.svc.cluster.local

# Port forward for testing
kubectl port-forward svc/backend 8000:8000 -n thebot
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -l app=postgres -n thebot

# Connect to PostgreSQL
kubectl exec -it postgres-0 -n thebot -- psql -U postgres -d thebot_db

# Check connection from backend
kubectl exec -it deployment/backend -n thebot -- python -c "
import psycopg2
conn = psycopg2.connect('dbname=thebot_db user=postgres host=postgres.thebot.svc.cluster.local')
print('Connected OK')
"
```

### Memory/CPU Issues

```bash
# Check resource usage
kubectl top pods -n thebot

# Check limits
kubectl describe deployment backend -n thebot | grep -A 5 "Limits\|Requests"

# Increase limits
kubectl set resources deployment backend \
  -n thebot \
  --limits=cpu=2000m,memory=2Gi \
  --requests=cpu=500m,memory=512Mi
```

## Performance Tuning

### Database

```yaml
# Edit postgres ConfigMap
kubectl edit cm postgres-config -n thebot

# Apply changes (requires pod restart)
kubectl rollout restart statefulset/postgres -n thebot
```

### Backend

```yaml
# Adjust gunicorn workers
kubectl set env deployment/backend \
  -n thebot \
  GUNICORN_WORKERS=8
```

### Frontend

```yaml
# Adjust nginx worker processes
kubectl edit cm nginx-config -n thebot
```

## Cleanup

### Remove Deployment

```bash
# Development
kubectl delete -k overlays/dev/
kubectl delete namespace thebot-dev

# Staging
kubectl delete -k overlays/staging/
kubectl delete namespace thebot-staging

# Production
kubectl delete -k overlays/production/
kubectl delete namespace thebot
```

### Remove PersistentVolumes

```bash
# WARNING: This deletes all data!
kubectl delete pvc -n thebot --all
```

## Best Practices

1. **Always test in dev first**
   - Test manifests with `--dry-run`
   - Use `kubectl apply -f` with `-n` to preview

2. **Use resource requests/limits**
   - Ensures fair scheduling
   - Prevents resource exhaustion
   - Enables HPA

3. **Monitor everything**
   - Prometheus/Grafana for metrics
   - ELK/Loki for logs
   - Alerts for critical issues

4. **Regular backups**
   - Database dumps
   - Volume snapshots
   - Full cluster backups with Velero

5. **Keep secrets secure**
   - Use sealed-secrets or external-secrets-operator
   - Never commit plain-text secrets
   - Rotate regularly

6. **Use GitOps**
   - ArgoCD for continuous deployment
   - Git as single source of truth
   - Automatic sync

7. **Test disaster recovery**
   - Regularly restore from backups
   - Test failover procedures
   - Document recovery steps

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Guide](https://kustomize.io/)
- [Kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
