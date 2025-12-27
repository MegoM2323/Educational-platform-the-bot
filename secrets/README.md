# Secrets Management for THE_BOT Platform

Comprehensive secrets management solution using HashiCorp Vault and External Secrets Operator.

## Overview

This directory contains configuration for:
- **Vault** - Centralized secret management
- **External Secrets Operator** - Kubernetes integration
- **Secret Rotation** - Automated credential management
- **Audit Logging** - Complete access tracking

## Architecture

Vault (PostgreSQL HA) 
    ↓ (HTTPS/AppRole)
External Secrets Operator
    ↓ (Sync every 1-24h)
Kubernetes Secrets
    ↓ (Mount as env vars)
Application Pods

## Installation

### Prerequisites
- Kubernetes 1.20+
- Helm 3.x
- kubectl configured
- PostgreSQL 12+ (for Vault backend)

### Quick Start

```bash
# 1. Add Helm repositories
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo add external-secrets https://charts.external-secrets.io

# 2. Create namespaces
kubectl create namespace vault
kubectl create namespace external-secrets
kubectl create namespace thebot

# 3. Install Vault
helm install vault hashicorp/vault \
  -f secrets/vault/values.yaml \
  -n vault

# 4. Initialize Vault (see DEPLOYMENT_GUIDE.md)
kubectl exec -n vault vault-0 -- vault operator init \
  -key-shares=5 -key-threshold=3 -format=json > vault-init.json

# 5. Install External Secrets Operator
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --set installCRDs=true

# 6. Apply configuration
kubectl apply -f k8s/base/12-external-secrets.yaml

# 7. Verify secrets sync
kubectl get secrets -n thebot
```

## Configuration Files

### vault/values.yaml
Helm configuration for Vault with:
- HA setup (3 replicas)
- PostgreSQL backend
- AWS KMS auto-unseal
- TLS/HTTPS
- Prometheus metrics

### vault/policies.hcl
Access control policies for:
- external-secrets-operator
- backend-app
- secret-rotation
- admin
- audit-reader

### k8s/base/12-external-secrets.yaml
Kubernetes manifests:
- ClusterSecretStore (Vault connection)
- ExternalSecrets (6 resources)
- AppRole credentials
- Audit logging

## Secret Rotation

### Manual Rotation

```bash
# Dry-run
./scripts/rotate-secrets.sh --dry-run

# Rotate all
./scripts/rotate-secrets.sh

# Rotate specific
./scripts/rotate-secrets.sh django
./scripts/rotate-secrets.sh postgres
```

### Automated with Cron

```bash
# Setup weekly rotation
./scripts/rotate-secrets.sh --setup-cron "0 2 * * 0"

# Or manually add to crontab:
0 2 * * 0 /path/to/rotate-secrets.sh >> /var/log/vault-rotation.log 2>&1
```

See `scripts/cron-examples.md` for more scheduling options.

## Vault Web UI

```bash
# Port-forward
kubectl port-forward -n vault vault-0 8200:8200

# Access
https://localhost:8200
```

## Audit Logging

```bash
# View Vault audit logs
kubectl exec -n vault vault-0 -- tail -f /vault/logs/audit.log

# View rotation logs
tail -f /var/log/vault-rotation.log

# View audit.log from rotation script
tail -f ./audit.log
```

## Security Best Practices

1. **Vault Deployment** - Use HA with auto-unseal
2. **Secret Storage** - Enable versioning and TTLs
3. **Access Control** - Use AppRole for services
4. **Audit Logging** - Monitor all access
5. **Secret Rotation** - Automate with cron jobs

## Troubleshooting

### Vault Not Unsealing
```bash
kubectl exec -n vault vault-0 -- vault status
kubectl logs vault-0 -n vault
```

### External Secrets Not Syncing
```bash
kubectl describe clustersecretstore vault-backend
kubectl describe externalsecret django-secrets -n thebot
kubectl logs -f deployment/external-secrets -n external-secrets
```

### AppRole Authentication Failed
```bash
kubectl describe secret vault-approle -n external-secrets
vault read auth/approle/role/external-secrets-operator
```

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [External Secrets Operator](https://external-secrets.io/)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

## Production Checklist

- [ ] Vault HA deployed
- [ ] PostgreSQL backend configured
- [ ] Auto-unseal enabled
- [ ] AppRole created
- [ ] Policies applied
- [ ] Secrets populated
- [ ] ESO installed
- [ ] ClusterSecretStore verified
- [ ] Secrets syncing
- [ ] Audit logging enabled
- [ ] Rotation script deployed
- [ ] Cron jobs configured
- [ ] Monitoring set up

---

Last Updated: December 27, 2025
Version: 1.0.0
Status: Production Ready
