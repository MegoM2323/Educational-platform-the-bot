# HashiCorp Vault Policies for the-bot platform
# Define fine-grained access control for different roles and services

# External Secrets Operator policy
path "secret/data/django/*" {
  capabilities = ["read", "list"]
}

path "secret/data/postgres/*" {
  capabilities = ["read", "list"]
}

path "secret/data/redis/*" {
  capabilities = ["read", "list"]
}

path "secret/data/apis/*" {
  capabilities = ["read", "list"]
}

path "secret/data/email/*" {
  capabilities = ["read", "list"]
}

path "secret/data/jwt/*" {
  capabilities = ["read", "list"]
}

path "secret/data/tls/*" {
  capabilities = ["read", "list"]
}

path "secret/data/docker/*" {
  capabilities = ["read", "list"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# Backend application policy
path "secret/data/django/*" {
  capabilities = ["read"]
}

path "secret/data/postgres/*" {
  capabilities = ["read"]
}

path "secret/data/redis/*" {
  capabilities = ["read"]
}

path "secret/data/apis/*" {
  capabilities = ["read"]
}

path "secret/data/email/*" {
  capabilities = ["read"]
}

path "secret/data/jwt/*" {
  capabilities = ["read"]
}

# Secret rotation policy
path "secret/data/*" {
  capabilities = ["read", "list", "update", "create", "delete"]
}

path "secret/metadata/*" {
  capabilities = ["read", "list", "update"]
}

# Admin policy
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

path "auth/approle/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/audit" {
  capabilities = ["read", "list"]
}

# Health and status
path "sys/health" {
  capabilities = ["read", "sudo"]
}

path "auth/token/self-renew" {
  capabilities = ["update"]
}

path "auth/token/self-lookup" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
