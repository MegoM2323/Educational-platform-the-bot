# THE_BOT Platform - Security Groups Reference

**Version**: 1.0.0
**Date**: December 27, 2025
**Status**: Production-Ready
**Last Updated**: December 27, 2025

## Overview

This document provides comprehensive documentation for all security groups in the THE_BOT platform infrastructure on AWS. It includes detailed rule justifications, change management procedures, and troubleshooting guides.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Security Groups Reference](#security-groups-reference)
3. [Rule Justifications](#rule-justifications)
4. [Change Management](#change-management)
5. [Audit Procedures](#audit-procedures)
6. [Validation Scripts](#validation-scripts)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Security Best Practices](#security-best-practices)

---

## Architecture Overview

The THE_BOT platform uses 6 main security groups organized by logical tier:

```
┌─────────────────────────────────────────────────────────────────┐
│                       Internet (0.0.0.0/0)                       │
└─────────────────────────────────────────────────────────────────┘
                               ↓
                        ┌──────────────┐
                        │   IGW        │
                        └──────────────┘
                               ↓
          ┌────────────────────────────────────────┐
          │   Public Subnets (10.0.1-3.0/24)      │
          │   Frontend SG (ALB)                    │
          └────────────────────────────────────────┘
          │ HTTP/HTTPS (80, 443)                   │
          ↓
          ┌────────────────────────────────────────┐
          │   Private App Subnets (10.0.11-13.0/24)│
          │   Backend SG (ECS/EC2)                │
          │   Bastion SG (Jump Host)              │
          │   VPC Endpoints SG                     │
          └────────────────────────────────────────┘
          │ Port 8000, 22, 6379                   │
          ↓
          ┌────────────────────────────────────────┐
          │   Private DB Subnets (10.0.21-23.0/24) │
          │   Database SG (RDS)                    │
          │   Redis SG (ElastiCache)              │
          └────────────────────────────────────────┘
          │ Port 5432, 6379                        │
          ↓
    ┌─────────────────┐  ┌─────────────────┐
    │ PostgreSQL RDS  │  │ Redis ElastiCache│
    └─────────────────┘  └─────────────────┘
```

---

## Security Groups Reference

### 1. Bastion Security Group

**Purpose**: Jump host for administrative access to private resources
**Location**: Public subnets (for SSH access) and private subnets (for system access)
**Terraform Resource**: `aws_security_group.bastion`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| bastion_ssh | 22 | TCP | `var.bastion_allowed_cidr` | SSH access | Admin access from allowed IPs only (e.g., company office, VPN). Should be restricted to specific IP/CIDR, not 0.0.0.0/0 |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| bastion_outbound | 0-65535 | All | 0.0.0.0/0 | Full outbound | Required for: SSH to backend instances, database queries, package updates, external troubleshooting |

#### Rule Justifications

**Inbound SSH (22/TCP)**
- Used for administrative access to the jump host
- Must be restricted to specific IPs/VPNs to prevent unauthorized access
- Default: Restricted via `bastion_allowed_cidr` variable
- Production: Set to your company's IP range or VPN CIDR

**Outbound (All)**
- Enables connectivity to all internal resources (backend, database, Redis)
- Allows for package updates and external tools
- Necessary for troubleshooting and system administration

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: Bastion Host
**Type**: [Add/Modify/Remove] Rule
**Requested By**: [Name]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: [Port number or range]
- **Protocol**: [TCP/UDP/ICMP/All]
- **Source/Destination**: [CIDR or Security Group]
- **Purpose**: [What this rule enables]

### Impact Analysis
- **Services Affected**: [List]
- **Compliance**: [HIPAA/SOC2/etc.]
- **Testing Plan**: [How to verify]

### Approval
- [ ] Security Team
- [ ] DevOps Lead
- [ ] Compliance Officer (if required)
```

---

### 2. Frontend Security Group (ALB)

**Purpose**: Application Load Balancer for distributing traffic
**Location**: Public subnets (10.0.1-3.0/24)
**Terraform Resource**: `aws_security_group.frontend`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| frontend_http | 80 | TCP | 0.0.0.0/0 | HTTP access | Public internet access. ALB redirects to HTTPS |
| frontend_https | 443 | TCP | 0.0.0.0/0 | HTTPS access | Encrypted web traffic (production required) |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| frontend_to_backend | 8000 | TCP | Backend SG | Route to backend | ALB connects to Django backend on port 8000 |
| frontend_outbound | 0-65535 | All | 0.0.0.0/0 | Internet access | DNS queries, health checks, logging |

#### Rule Justifications

**Inbound HTTP (80/TCP)**
- Allows users to access the platform via HTTP
- ALB automatically redirects to HTTPS for security
- Must remain open (0.0.0.0/0) for public accessibility

**Inbound HTTPS (443/TCP)**
- Standard encrypted web traffic
- Required for all sensitive operations
- Uses TLS 1.2+ (enforced by ALB policy)

**Outbound to Backend (8000/TCP)**
- Direct connection from ALB to backend services
- Restricted to Backend SG (not open internet)
- Single-purpose rule for application routing

**Outbound to Internet (All)**
- DNS queries (53/UDP)
- Health check responses
- CloudWatch logging
- SSL/TLS certificate validation

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: ALB Frontend
**Type**: [Add/Modify/Remove] Rule
**Requested By**: [Name]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: [Port number or range]
- **Protocol**: [TCP/UDP]
- **Source/Destination**: [Public or specific SG]
- **Purpose**: [What this rule enables]

### Impact Analysis
- **User Facing**: [Yes/No]
- **Compliance**: [PCI-DSS, etc.]
- **Testing Plan**: [Health check validation]

### Approval
- [ ] Security Team
- [ ] DevOps Lead
```

---

### 3. Backend Security Group (ECS/EC2)

**Purpose**: Application servers running Django and microservices
**Location**: Private app subnets (10.0.11-13.0/24)
**Terraform Resource**: `aws_security_group.backend`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| backend_from_alb | 8000 | TCP | Frontend SG | From ALB | ALB routes traffic to Django application |
| backend_from_bastion | 22 | TCP | Bastion SG | SSH from Bastion | Admin access via jump host (no direct internet SSH) |
| backend_from_redis | 6379 | TCP | Redis SG | Redis cluster | Backend connects to Redis for caching/sessions |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| backend_to_database | 5432 | TCP | Database SG | PostgreSQL connection | Django connects to RDS database |
| backend_to_redis | 6379 | TCP | Redis SG | Redis connection | Cache operations, session storage, message broker |
| backend_outbound | 0-65535 | All | 0.0.0.0/0 | Internet access | Via NAT: External APIs, downloads, updates |

#### Rule Justifications

**Inbound from ALB (8000/TCP)**
- ALB distributes user traffic to backend services
- Restricted to Frontend SG (not open internet)
- Django application listens on port 8000

**Inbound from Bastion (22/TCP)**
- SSH access for administrative tasks
- Restricted to Bastion SG (indirect internet access)
- Enables: debugging, deployments, log collection

**Inbound from Redis (6379/TCP)**
- Bi-directional communication with Redis cluster
- Restricted to Redis SG (not open internet)
- Used for: pub/sub patterns, cross-instance communication

**Outbound to Database (5432/TCP)**
- Django makes queries to RDS database
- Restricted to Database SG
- One-way: Backend → Database (database cannot initiate)

**Outbound to Redis (6379/TCP)**
- Cache operations, session storage
- Restricted to Redis SG
- Message broker for async tasks

**Outbound to Internet (All)**
- External API calls (payment processing, AI services)
- Package downloads, security updates
- CloudWatch metrics, logs
- Routes through NAT Gateway (outbound IP is EIP)

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: Backend Application
**Type**: [Add/Modify/Remove] Rule
**Requested By**: [Name]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: [Port number or range]
- **Protocol**: [TCP/UDP]
- **Source/Destination**: [SG reference or CIDR]
- **Purpose**: [New functionality, security fix, etc.]

### Impact Analysis
- **Services Affected**: [List all microservices]
- **Database Dependencies**: [Yes/No]
- **External Integrations**: [APIs, services]
- **Compliance**: [GDPR, SOC2, PCI-DSS]
- **Testing Plan**: [Unit tests, integration tests]

### Approval
- [ ] Security Team
- [ ] DevOps Lead
- [ ] Application Team Lead
```

---

### 4. Database Security Group (RDS)

**Purpose**: PostgreSQL database server (most restrictive)
**Location**: Private database subnets (10.0.21-23.0/24)
**Terraform Resource**: `aws_security_group.database`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| database_from_backend | 5432 | TCP | Backend SG | App queries | Primary application access to database |
| database_from_bastion | 5432 | TCP | Bastion SG | Maintenance | Backup, restoration, direct queries |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| database_outbound_none | 0-65535 | All | 127.0.0.1/32 | Blocked | Most restrictive: Database cannot initiate outbound |

#### Rule Justifications

**Inbound from Backend (5432/TCP)**
- Production application queries
- Primary data access pattern
- Restricted to Backend SG (no direct access from other sources)

**Inbound from Bastion (5432/TCP)**
- Administrative access for:
  - Backup operations
  - Database maintenance (VACUUM, ANALYZE)
  - Schema migrations
  - Direct troubleshooting queries
- Still restricted to Bastion SG (no public internet access)

**No Outbound Rules**
- Database should NOT initiate connections
- Implements principle of least privilege
- Unreachable destination (127.0.0.1/32) prevents any outbound traffic
- Database is read/write endpoint, not client

#### Security Considerations

1. **Backup & Snapshots**: RDS automated backups use AWS internal networking
2. **Monitoring**: RDS Enhanced Monitoring uses IAM credentials, not network rules
3. **Parameter Updates**: Applied through RDS API, not via network
4. **Encryption**: TLS enabled for all connections (enforced at RDS level)

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: PostgreSQL RDS Database
**Type**: [Add/Modify/Remove] Rule
**Requested By**: [Name]
**Risk Level**: [Critical/High/Medium/Low]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: 5432 (immutable for PostgreSQL)
- **Protocol**: TCP (immutable)
- **Source**: [Backend SG / Bastion SG / Other]
- **Purpose**: [Production traffic / Maintenance / Migration]

### Impact Analysis
- **Data Sensitivity**: [PII/Educational Records/Financial]
- **Compliance**: [FERPA/GDPR/SOC2]
- **Backup Impact**: [Yes/No]
- **High Availability**: [Affects failover? Yes/No]
- **Testing Plan**: [Connection test before/after]

### Approval
- [ ] Security Team (CRITICAL)
- [ ] Database Administrator
- [ ] DevOps Lead
```

---

### 5. Redis Security Group (ElastiCache)

**Purpose**: Redis cache and message broker (highly restrictive)
**Location**: Private database subnets (10.0.21-23.0/24)
**Terraform Resource**: `aws_security_group.redis`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| redis_from_backend | 6379 | TCP | Backend SG | Cache operations | Application reads/writes cache and sessions |
| redis_from_bastion | 6379 | TCP | Bastion SG | Monitoring | Redis CLI for debugging, flushing, stats |
| redis_internal | 16379 | TCP | Redis SG | Cluster comm. | Redis Cluster internal gossip protocol |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| redis_outbound_none | 0-65535 | All | 127.0.0.1/32 | Blocked | Most restrictive: No outbound connections |

#### Rule Justifications

**Inbound from Backend (6379/TCP)**
- Application cache operations:
  - Session storage
  - Rate limiting
  - Caching API responses
  - Message broker (Celery)
- Restricted to Backend SG

**Inbound from Bastion (6379/TCP)**
- Administrative operations:
  - `MONITOR` (observe live commands)
  - `INFO` (cluster statistics)
  - `FLUSHDB` (clear cache during maintenance)
  - `CLIENT LIST` (debugging connections)
- Restricted to Bastion SG (secure access via jump host)

**Inbound Cluster Internal (16379/TCP)**
- Redis Cluster nodes communicate internally
- Same security group reference (self-referential rule)
- Gossip protocol for cluster health

**No Outbound Rules**
- Redis is a data store, not a client
- Should not initiate external connections
- Unreachable destination (127.0.0.1/32) blocks all outbound

#### Use Cases Enabled

```
1. Session Management:
   Backend → Redis (6379) → Store session tokens

2. Cache Layer:
   Backend → Redis (6379) → Check cache
   Cache hit → Return cached data
   Cache miss → Query database

3. Message Queue:
   Backend → Redis (6379) → Enqueue async task
   Celery Worker → Redis (6379) → Dequeue task

4. Rate Limiting:
   Backend → Redis (6379) → Check rate limit counters

5. Pub/Sub (WebSocket):
   Backend → Redis (6379) → Publish message
   Channels Consumer → Redis → Receive message
```

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: Redis ElastiCache
**Type**: [Add/Modify/Remove] Rule
**Requested By**: [Name]
**Risk Level**: [High/Medium/Low]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: [6379/16379]
- **Protocol**: TCP (immutable)
- **Source**: [Backend SG / Bastion SG / Redis SG]
- **Purpose**: [Cache operation / Cluster communication / Monitoring]

### Impact Analysis
- **Affected Features**: [Sessions/Cache/Message Queue/Pub-Sub]
- **Performance Impact**: [Expected latency change]
- **Data Loss Risk**: [Possible? Describe recovery]
- **Testing Plan**: [Cache hit rate validation, latency monitoring]

### Approval
- [ ] Security Team
- [ ] DevOps Lead
- [ ] Application Team Lead
```

---

### 6. VPC Endpoints Security Group

**Purpose**: Interface endpoints for AWS services (most restrictive)
**Location**: Private app subnets (for app tier endpoints), Private DB subnets (for DB-specific)
**Terraform Resource**: `aws_security_group.vpc_endpoints`

#### Inbound Rules

| Rule ID | Port | Protocol | Source | Purpose | Justification |
|---------|------|----------|--------|---------|---------------|
| vpc_endpoints_https | 443 | TCP | 10.0.0.0/16 | HTTPS from VPC | All interface endpoints use HTTPS |
| vpc_endpoints_http | 80 | TCP | 10.0.0.0/16 | HTTP from VPC | S3 redirects (HTTP → HTTPS) |

#### Outbound Rules

| Rule ID | Port | Protocol | Destination | Purpose | Justification |
|---------|------|----------|-------------|---------|---------------|
| (None defined) | - | - | - | (Managed by source SG) | Outbound managed by Backend SG |

#### Rule Justifications

**Inbound HTTPS (443/TCP)**
- All AWS service interface endpoints use HTTPS
- Restricted to VPC CIDR (no external access)
- Services:
  - ECR (Docker image pulls)
  - CloudWatch (metrics, logs)
  - Secrets Manager (credential retrieval)
  - Systems Manager SSM (instance access)
  - EC2 (instance metadata, describe operations)
  - SQS (message queue)
  - SNS (notifications)

**Inbound HTTP (80/TCP)**
- S3 requests can redirect from HTTP to HTTPS
- Restricted to VPC CIDR
- Gateway endpoint S3 uses HTTP initially, then redirects

**No Explicit Outbound**
- Endpoints don't initiate connections
- Backend SG managing outbound to endpoints
- Default VPC SG outbound allows (if not restricted)

#### Gateway vs Interface Endpoints

**Gateway Endpoints** (via route tables, not SG):
- S3 (com.amazonaws.REGION.s3)
- DynamoDB (com.amazonaws.REGION.dynamodb)
- No security group required
- Policy: Restricted to project buckets/tables

**Interface Endpoints** (via this SG):
- ECR API & DKR
- CloudWatch Logs & Monitoring
- RDS Enhanced Monitoring
- Secrets Manager
- Systems Manager (SSM)
- EC2 API
- SQS
- SNS

#### Change Request Template

```markdown
## Security Group Change Request

**Service**: VPC Endpoints
**Type**: [Add/Modify/Remove] Rule or Endpoint
**Requested By**: [Name]
**Justification**: [Detailed explanation]

### Rule Details
- **Port**: 443 (standard for endpoints)
- **Protocol**: TCP
- **Source**: 10.0.0.0/16 (VPC CIDR)
- **Purpose**: [Which AWS service]

### Or Endpoint Details (for new endpoints)
- **Service**: [ECR/Secrets Manager/etc.]
- **Type**: Gateway or Interface
- **Cost Impact**: [$7.20/month + data transfer]
- **Benefits**: [Security/Cost/Performance]

### Impact Analysis
- **Services Affected**: [List]
- **NAT Gateway Savings**: [Reduced data transfer]
- **Performance**: [Improved latency]
- **Testing Plan**: [Connectivity test to endpoint]

### Approval
- [ ] Security Team
- [ ] DevOps Lead
```

---

## Rule Justifications

### Principle of Least Privilege Applied

Each security group follows the principle of least privilege:

1. **Bastion**: Inbound restricted to specific CIDR, outbound unrestricted (admin host)
2. **Frontend**: Inbound public for web traffic, outbound to specific targets
3. **Backend**: Inbound from ALB/Bastion only, outbound to specific services
4. **Database**: Inbound from Backend/Bastion only, outbound completely blocked
5. **Redis**: Inbound from Backend/Bastion/self only, outbound completely blocked
6. **VPC Endpoints**: Inbound from VPC CIDR (443/80), no explicit outbound

### Port Selection Rationale

| Port | Protocol | Service | Restriction | Reason |
|------|----------|---------|-------------|--------|
| 22 | TCP | SSH | Bastion SG only for Backend | Direct SSH from internet prevented |
| 80 | TCP | HTTP | 0.0.0.0/0 for ALB only | Web traffic, redirects to HTTPS |
| 443 | TCP | HTTPS | 0.0.0.0/0 for ALB only | Encrypted web traffic |
| 5432 | TCP | PostgreSQL | Backend + Bastion only | Database access restricted |
| 6379 | TCP | Redis | Backend + Bastion only | Cache/message broker restricted |
| 8000 | TCP | Django | ALB only | Application backend |
| 16379 | TCP | Redis Cluster | Redis SG only | Cluster internal gossip |

---

## Change Management

### Change Control Process

All security group changes follow this process:

```
1. REQUEST
   └─ Use change request template for rule change
   └─ Document business justification
   └─ Identify affected services

2. REVIEW
   └─ Security team verifies compliance
   └─ DevOps validates technical feasibility
   └─ Compliance checks HIPAA/GDPR/SOC2 impact

3. TESTING
   └─ Staging environment validation
   └─ Connection testing before/after
   └─ Performance impact assessment

4. APPROVAL
   └─ Security: Risk assessment
   └─ DevOps: Implementation plan
   └─ Compliance: Regulatory impact (if needed)

5. DEPLOYMENT
   └─ Terraform plan review
   └─ Gradual rollout (if applicable)
   └─ Rollback procedure documented

6. DOCUMENTATION
   └─ Update this reference
   └─ Update Terraform code
   └─ Log change in audit trail
```

### Risk Assessment Matrix

| Change Type | Risk Level | Review Level | Approval |
|-------------|-----------|--------------|----------|
| Add inbound from new source | HIGH | Full review | Security + DevOps + Compliance |
| Add outbound to internet | HIGH | Full review | Security + DevOps |
| Modify database SG | CRITICAL | Full review | DBA + Security + DevOps |
| Add new port to Bastion | MEDIUM | Standard | Security + DevOps |
| Modify frontend SG | LOW | Quick review | Security + DevOps |
| Add VPC endpoint | MEDIUM | Standard | Security + DevOps |

### Terraform Workflow

```bash
# 1. Modify security-groups.tf
vim infrastructure/terraform/vpc/security-groups.tf

# 2. Validate syntax
terraform -chdir=infrastructure/terraform/vpc validate

# 3. Plan changes
terraform -chdir=infrastructure/terraform/vpc plan -out=tfplan

# 4. Review plan
terraform show tfplan

# 5. Apply (after approval)
terraform -chdir=infrastructure/terraform/vpc apply tfplan

# 6. Verify in AWS Console
# Check security group rules in AWS Console
# Test connectivity from affected services

# 7. Update documentation
vim docs/SECURITY_GROUPS_REFERENCE.md
```

### Emergency Change Procedure

For urgent security issues:

1. **Immediate Action**: Issue temporary rule in production
2. **Notification**: Alert security + DevOps teams
3. **Documentation**: Document in change ticket
4. **Review**: Post-incident review within 24 hours
5. **Approval**: Retroactive review required
6. **Monitoring**: Enhanced monitoring for 7 days

---

## Audit Procedures

### Regular Audit Schedule

| Frequency | Task | Owner | Duration |
|-----------|------|-------|----------|
| **Daily** | Automated rule validation script | DevOps | 5 min |
| **Weekly** | VPC Flow Logs analysis | Security | 30 min |
| **Monthly** | Full security group review | Security | 2 hours |
| **Quarterly** | Compliance audit | Compliance | 4 hours |
| **Annually** | Third-party penetration test | External | 1 week |

### Automated Audit Script

Run daily to detect overly permissive rules:

```bash
python3 infrastructure/security/security-groups-audit.py --environment production
```

### Manual Audit Checklist

- [ ] No inbound 0.0.0.0/0 on Database SG
- [ ] No inbound 0.0.0.0/0 on Redis SG
- [ ] Database SG outbound completely blocked
- [ ] Redis SG outbound completely blocked
- [ ] Bastion SSH restricted to specific CIDR
- [ ] Backend SG inbound only from ALB, Bastion, Redis
- [ ] ALB SG outbound to Backend restricted
- [ ] All rules documented with business justification
- [ ] No unused security groups
- [ ] All tags present (Name, Environment, ManagedBy)

### Compliance Checks

**HIPAA Compliance**
- [ ] No open database access (0.0.0.0/0)
- [ ] Encryption in transit enforced (TLS)
- [ ] Access logging enabled
- [ ] Network segmentation implemented

**SOC2 Compliance**
- [ ] Security groups documented
- [ ] Change management process followed
- [ ] Audit trails maintained
- [ ] Access controls enforced

**PCI-DSS (if handling payments)**
- [ ] No public database access
- [ ] Firewall rules documented
- [ ] Cardholder data isolated
- [ ] Regular penetration testing

### Audit Report Template

```markdown
# Security Group Audit Report

**Date**: [Date]
**Auditor**: [Name]
**Period**: [Start - End]
**Status**: [Compliant / Non-Compliant with Issues]

## Summary
- Total Security Groups: 6
- Total Rules: [Count]
- Rules Modified: [Count]
- Non-Compliant Rules: [Count]

## Findings

### Critical Issues
1. [Description]
   - **Rule**: [Rule ID]
   - **Risk**: [Risk description]
   - **Remediation**: [How to fix]
   - **Timeline**: [When to fix]

### Warnings
1. [Description]
   - **Recommendation**: [What to improve]

## Compliance Status
- HIPAA: [Compliant/Non-Compliant]
- SOC2: [Compliant/Non-Compliant]
- PCI-DSS: [Compliant/Non-Compliant]

## Next Review Date
[Date - usually 1 month]
```

---

## Validation Scripts

### Script Purpose

The provided `security-groups-audit.py` script validates security group configuration for:

1. **Overly Permissive Rules**: Detects 0.0.0.0/0 on restricted services
2. **Missing Rules**: Checks for expected rules in each SG
3. **Configuration Consistency**: Validates against documented baseline
4. **Compliance Violations**: Flags HIPAA/SOC2 violations
5. **Tag Validation**: Ensures all resources properly tagged

### Installation

```bash
# Copy script
cp infrastructure/security/security-groups-audit.py ~/scripts/

# Install AWS CLI and boto3
pip install boto3 botocore
```

### Usage

```bash
# Audit production environment
python3 infrastructure/security/security-groups-audit.py --environment production

# Audit staging
python3 infrastructure/security/security-groups-audit.py --environment staging

# Audit specific security group
python3 infrastructure/security/security-groups-audit.py --environment production --sg-name backend-sg

# Generate JSON report
python3 infrastructure/security/security-groups-audit.py --environment production --format json > report.json

# Check for specific violation type
python3 infrastructure/security/security-groups-audit.py --environment production --check permissive-rules
```

### Output Example

```
Security Groups Audit Report
==============================

VPC: vpc-0123456789abcdef0
Environment: production
Timestamp: 2025-12-27T10:30:00Z

Security Groups Found: 6
├── bastion-sg (sg-001)
│   ├── Inbound Rules: 1
│   │   └── SSH (22) from 203.0.113.0/32 ✓ Restricted
│   ├── Outbound Rules: 1
│   │   └── All to 0.0.0.0/0 ✓ Expected
│   └── Status: COMPLIANT
│
├── frontend-sg (sg-002)
│   ├── Inbound Rules: 2
│   │   ├── HTTP (80) from 0.0.0.0/0 ✓ Expected
│   │   └── HTTPS (443) from 0.0.0.0/0 ✓ Expected
│   ├── Outbound Rules: 2
│   │   ├── Port 8000 to backend-sg ✓ Restricted
│   │   └── All to 0.0.0.0/0 ✓ Expected
│   └── Status: COMPLIANT
│
├── backend-sg (sg-003)
│   ├── Inbound Rules: 3
│   │   ├── Port 8000 from frontend-sg ✓ Restricted
│   │   ├── SSH (22) from bastion-sg ✓ Restricted
│   │   └── Port 6379 from redis-sg ✓ Restricted
│   ├── Outbound Rules: 3
│   │   ├── Port 5432 to database-sg ✓ Restricted
│   │   ├── Port 6379 to redis-sg ✓ Restricted
│   │   └── All to 0.0.0.0/0 ✓ Expected
│   └── Status: COMPLIANT
│
├── database-sg (sg-004)
│   ├── Inbound Rules: 2
│   │   ├── PostgreSQL (5432) from backend-sg ✓ Restricted
│   │   └── PostgreSQL (5432) from bastion-sg ✓ Restricted
│   ├── Outbound Rules: 1
│   │   └── No outbound (127.0.0.1/32) ✓ Compliant
│   └── Status: COMPLIANT
│
├── redis-sg (sg-005)
│   ├── Inbound Rules: 3
│   │   ├── Port 6379 from backend-sg ✓ Restricted
│   │   ├── Port 6379 from bastion-sg ✓ Restricted
│   │   └── Port 16379 from redis-sg ✓ Restricted
│   ├── Outbound Rules: 1
│   │   └── No outbound (127.0.0.1/32) ✓ Compliant
│   └── Status: COMPLIANT
│
└── vpc-endpoints-sg (sg-006)
    ├── Inbound Rules: 2
    │   ├── HTTPS (443) from 10.0.0.0/16 ✓ Expected
    │   └── HTTP (80) from 10.0.0.0/16 ✓ Expected
    ├── Outbound Rules: 0
    │   └── (Managed by source SG) ✓ Expected
    └── Status: COMPLIANT

Overall Compliance: COMPLIANT
Scan Duration: 2.34 seconds
```

---

## Troubleshooting Guide

### Connection Issues

#### Problem: Backend Cannot Connect to Database

**Symptoms**:
```
django.db.utils.OperationalError: could not connect to server
psycopg2.OperationalError: (psycopg2.OperationalError) ...
```

**Diagnostic Steps**:
```bash
# 1. Verify Backend SG exists
aws ec2 describe-security-groups --filters Name=group-name,Values=thebot-backend-sg

# 2. Check Database SG inbound rules
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-xxxxx \
  Name=is-egress,Values=false

# 3. Test connectivity from Backend to Database
# SSH into backend instance
aws ssm start-session --target i-xxxxxxxxx

# From backend instance:
nc -zv 10.0.21.10 5432  # Test RDS endpoint
psql -h thebot-db.xxxxx.rds.amazonaws.com -U postgres -d postgres
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| Database SG missing Backend SG inbound | `database_from_backend` rule | Add ingress rule: port 5432 from Backend SG |
| Backend SG missing Database SG outbound | `backend_to_database` rule | Add egress rule: port 5432 to Database SG |
| Wrong RDS security group | Describe RDS instance | Verify RDS is in correct DB tier SG |
| Wrong subnet routing | Route table rules | Verify app subnet routes to NAT, DB subnet has no IGW |
| RDS not running | `aws rds describe-db-instances` | Start RDS instance if stopped |

#### Problem: ALB Cannot Route to Backend

**Symptoms**:
```
HTTP 502 Bad Gateway
Target unhealthy (health check failed)
Connection refused
```

**Diagnostic Steps**:
```bash
# 1. Check ALB target group health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...

# 2. Check security group rules
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-backend \
  Name=group-id,Values=sg-alb \
  Name=is-egress,Values=false

# 3. Test ALB to Backend connectivity
# Get ALB ENI and Backend instance IP
aws ec2 describe-network-interfaces --filters Name=group-name,Values=frontend-sg
aws ec2 describe-instances --filters Name=security-group.id,Values=sg-backend
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| Backend SG missing ALB ingress | `backend_from_alb` rule | Add ingress rule: port 8000 from Frontend SG |
| Frontend SG missing Backend outbound | `frontend_to_backend` rule | Add egress rule: port 8000 to Backend SG |
| Backend not listening | SSH to instance, `sudo netstat -tlnp \| grep 8000` | Start Django service |
| Health check misconfigured | ALB target group | Verify health check path returns 200 |
| Wrong port in ALB | Target group port | Verify port 8000, protocol HTTP |

#### Problem: Redis Connection Refused

**Symptoms**:
```
redis.exceptions.ConnectionError: Error 111 connecting to Redis
Error -3: Name or service not known
```

**Diagnostic Steps**:
```bash
# 1. Check Redis cluster status
aws elasticache describe-cache-clusters --cache-cluster-id thebot-redis

# 2. Verify Redis SG inbound rules
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-redis \
  Name=is-egress,Values=false

# 3. Test connectivity from Backend
# SSH into backend instance
aws ssm start-session --target i-xxxxxxxxx

# From backend instance:
redis-cli -h thebot-redis.xxxxx.cache.amazonaws.com -p 6379 PING
redis-cli -h 10.0.21.15 -p 6379 PING
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| Redis SG missing Backend inbound | `redis_from_backend` rule | Add ingress rule: port 6379 from Backend SG |
| Backend SG missing Redis outbound | `backend_to_redis` rule | Add egress rule: port 6379 to Redis SG |
| Wrong Redis endpoint | Backend config | Verify REDIS_URL in environment |
| Redis cluster not in correct SG | Describe ElastiCache | Move Redis to correct database tier |
| ElastiCache not running | `aws elasticache describe-cache-clusters` | Start Redis cluster |

#### Problem: Bastion SSH Fails

**Symptoms**:
```
ssh: connect to host bastion.example.com port 22: Operation timed out
Permission denied (publickey)
ssh_dispatch_run_fatal: Connection refused
```

**Diagnostic Steps**:
```bash
# 1. Check Bastion SG rules
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-bastion \
  Name=is-egress,Values=false

# 2. Check if bastion_allowed_cidr is set correctly
terraform -chdir=infrastructure/terraform/vpc output bastion_allowed_cidr

# 3. Check your IP
curl https://ifconfig.me

# 4. Test connectivity
nc -zv bastion.example.com 22
ssh -vvv ec2-user@bastion.example.com
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| Your IP not in bastion_allowed_cidr | Terraform variables | Update `bastion_allowed_cidr` to include your IP |
| Bastion instance not running | AWS Console EC2 | Start Bastion instance |
| Security group not attached to instance | Describe instance | Attach bastion-sg to Bastion instance |
| SSH key permissions wrong | `ls -la ~/.ssh/id_rsa` | Set to 600: `chmod 600 ~/.ssh/id_rsa` |
| Wrong username | SSH man page | Try: ec2-user, ubuntu, admin, root |

#### Problem: Cannot Access External APIs (Payment Processing, AI, etc.)

**Symptoms**:
```
requests.exceptions.ConnectionError: Failed to connect
urllib3.exceptions.NewConnectionError: Connection refused
Timeout after 30 seconds
```

**Diagnostic Steps**:
```bash
# 1. Verify Backend SG outbound rule
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-backend \
  Name=is-egress,Values=true

# 2. Check NAT Gateway status
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-xxxxx

# 3. Test from Backend instance
aws ssm start-session --target i-xxxxxxxxx

# From backend:
curl -I https://api.example.com
curl -I https://api.openai.com
nslookup api.example.com  # DNS resolution
traceroute api.example.com
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| Backend SG missing outbound 0.0.0.0/0 | `backend_outbound` rule | Add egress rule: all to 0.0.0.0/0 |
| NAT Gateway not running | `aws ec2 describe-nat-gateways` | Start or recreate NAT Gateway |
| NAT Gateway out of elastic IPs | Check EIP allocation | Allocate new EIP |
| Route table not routing to NAT | `aws ec2 describe-route-tables` | Verify private subnet route table has NAT route |
| DNS not resolving | `nslookup api.example.com` | Check DNS (CloudWatch Logs endpoint) |

#### Problem: VPC Endpoint Connection Failed

**Symptoms**:
```
Error pulling from ECR: AccessDenied
CloudWatch logs not appearing
Cannot retrieve from Secrets Manager
```

**Diagnostic Steps**:
```bash
# 1. Verify VPC Endpoint status
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-xxxxx

# 2. Check VPC Endpoints SG rules
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=sg-vpc-endpoints

# 3. Test DNS resolution
# From backend instance:
nslookup ecr.api.amazonaws.com
nslookup logs.amazonaws.com
nslookup secretsmanager.amazonaws.com

# 4. Check endpoint policy
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-xxxxx --query 'VpcEndpoints[0].PolicyDocument'
```

**Common Causes & Solutions**:

| Cause | Check | Solution |
|-------|-------|----------|
| VPC Endpoints SG missing inbound | `vpc_endpoints_https` rule | Add ingress rule: 443 from VPC CIDR |
| Endpoint not in correct subnet | Describe endpoint | Verify endpoint deployed in private app subnets |
| Endpoint not active | Endpoint state | Wait for endpoint to reach "Available" state |
| Endpoint policy too restrictive | Policy document | Update policy to allow required actions |
| DNS not working | DNS resolution | Enable private DNS for endpoint |

### Port Conflicts

#### Issue: Port 8000 Already in Use

```bash
# Find process using port 8000
lsof -i :8000
netstat -tlnp | grep 8000

# Kill process
kill -9 <PID>

# Or change port in security group and backend config
```

#### Issue: Port 6379 Already in Use

```bash
# Check Redis status
redis-cli ping

# If not Redis, find conflicting process
lsof -i :6379

# Kill or change configuration
```

### VPC Flow Logs Analysis

Analyze rejected traffic to debug connectivity issues:

```bash
# Query VPC Flow Logs
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "REJECT" \
  --query 'events[].message' \
  --output text

# Analyze specific source
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "10.0.11.0 5432 REJECT" \
  --output text
```

### CloudWatch Metrics

Monitor NAT Gateway and ALB health:

```bash
# NAT Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/NatGateway \
  --metric-name ErrorPortAllocation \
  --start-time 2025-12-27T00:00:00Z \
  --end-time 2025-12-27T23:59:59Z \
  --period 3600 \
  --statistics Maximum

# ALB target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...
```

---

## Security Best Practices

### Rule Naming Convention

All rules should follow this naming pattern:

```
[direction]_[service]_[purpose]_[port]

Examples:
- bastion_ssh (clear purpose)
- backend_from_alb (directional, descriptive)
- frontend_to_backend (source-destination)
- database_from_backend (one-way communication)
- redis_internal (cluster communication)
```

### Documentation Standards

Every rule must include:
1. **Description**: What the rule does
2. **Purpose**: Why it exists
3. **Justification**: Business need or security requirement
4. **Review Date**: When last verified

### Change Approval Levels

| Risk Level | Approvers | Timeline |
|-----------|-----------|----------|
| **Critical** | Security + DBA + DevOps Lead | Same day |
| **High** | Security + DevOps Lead | 24 hours |
| **Medium** | Security + DevOps | 48 hours |
| **Low** | DevOps only | Immediate |

### Monitoring & Alerting

Set up alerts for:

```
1. Failed connections (VPC Flow Logs "REJECT" > 100/minute)
2. NAT Gateway errors (ErrorPortAllocation > 0)
3. ALB unhealthy targets (Target status != "healthy")
4. Unexpected security group changes (CloudTrail events)
5. Brute force attempts (CloudWatch metrics)
```

### Incident Response

For security incidents:

1. **Identify**: VPC Flow Logs, CloudWatch alarms
2. **Isolate**: Add temporary deny rule to affected SG
3. **Investigate**: Review logs, check for compromise
4. **Remediate**: Remove malicious rules, apply patches
5. **Document**: Record in incident log
6. **Review**: Post-incident analysis with team

---

## References

- [AWS Security Groups Documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [AWS VPC Security Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/security.html)
- [AWS VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [OWASP Network Security Guidelines](https://owasp.org)
- [THE_BOT NETWORK_ARCHITECTURE.md](NETWORK_ARCHITECTURE.md) - Related documentation
- [THE_BOT SECURITY.md](SECURITY.md) - Overall security architecture

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-27 | DevOps | Initial creation |

**Last Updated**: December 27, 2025
**Status**: Production-Ready
**Reviewers**: Security Team, DevOps Lead
