# Vault & External Secrets Deployment Guide

Step-by-step guide for deploying HashiCorp Vault and External Secrets Operator.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.x
- kubectl admin access
- PostgreSQL 12+
- AWS KMS (for auto-unseal)

## Phase 1: Create Infrastructure

Create PostgreSQL database and AWS KMS key:

```bash
# PostgreSQL
gcloud sql instances create vault-postgres \
  --database-version=POSTGRES_15

# AWS KMS
aws kms create-key --description "Vault Auto-Unseal Key"
```

## Phase 2: Deploy Vault

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  -f secrets/vault/values.yaml \
  -n vault
```

## Phase 3: Initialize Vault

```bash
kubectl exec -n vault vault-0 -- vault operator init \
  -key-shares=5 -key-threshold=3 \
  -format=json > vault-init.json

# Unseal with 3 keys
```

## Phase 4: Configure AppRole

```bash
kubectl exec -n vault vault-0 -- vault auth enable approle

kubectl exec -n vault vault-0 -- \
  vault write auth/approle/role/external-secrets-operator \
  policies="external-secrets"
```

## Phase 5: Deploy External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace
```

## Phase 6: Apply Configuration

```bash
kubectl apply -f k8s/base/12-external-secrets.yaml
```

## Phase 7: Verify

```bash
kubectl get externalsecrets -n thebot
kubectl get secrets -n thebot
```

---

Last Updated: December 27, 2025
