# THE_BOT Platform - Network Security

**Version**: 1.0.0
**Date**: December 27, 2025
**Status**: Production-Ready
**Classification**: Internal Use

## Executive Summary

This document describes the comprehensive network security architecture for the THE_BOT educational platform. The implementation follows AWS best practices and defense-in-depth principles with multiple layers of protection:

1. **AWS WAF** - Web Application Firewall with managed and custom rules
2. **Network Segmentation** - Isolated tiers with restrictive security groups
3. **DDoS Protection** - Rate limiting and traffic analysis
4. **Egress Filtering** - Whitelist-based outbound access
5. **Intrusion Detection** - Threat pattern recognition
6. **Traffic Filtering** - Protocol and port-based restrictions
7. **Monitoring & Audit** - Continuous security monitoring

---

## 1. Architecture Overview

### Security Layers (Defense in Depth)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: AWS WAF (Application-Level Protection)              │
│ - Rate limiting                                               │
│ - OWASP Top 10 protection                                    │
│ - SQL injection prevention                                   │
│ - Geo-blocking                                               │
│ - Custom IP reputation                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Network Segmentation (Security Groups)              │
│ - Public tier (ALB)                                          │
│ - Application tier (ECS/EC2)                                 │
│ - Database tier (RDS)                                        │
│ - Cache tier (Redis)                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Network ACLs (Subnet-Level Filtering)               │
│ - Stateless firewall rules                                   │
│ - Protocol filtering                                         │
│ - Port restrictions                                          │
│ - DDoS attack mitigation                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Egress Filtering (Outbound Whitelist)               │
│ - DNS whitelist                                              │
│ - HTTPS whitelist                                            │
│ - Protocol restrictions                                      │
│ - Port-based access control                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: DDoS & Intrusion Detection                          │
│ - SYN flood protection                                       │
│ - UDP flood detection                                        │
│ - Port scanning detection                                    │
│ - Malformed packet filtering                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Threat Model

### Threat Scenarios Addressed

#### 2.1 DDoS Attacks

**Attacks Mitigated**:
- SYN floods (syn-flood-limit: 1000 packets/sec)
- UDP floods (udp-flood-limit: 5000 packets/sec)
- Volumetric attacks (rate-limit: 2000 req/IP/5min)
- Application-layer attacks (WAF rules)

**Controls**:
- AWS Shield Standard (automatic)
- AWS WAF rate limiting
- Security group connection limits
- Network ACL packet filtering
- ALB connection draining

#### 2.2 SQL Injection & OWASP Top 10

**Attacks Mitigated**:
- SQL injection attacks
- Cross-site scripting (XSS)
- Cross-site request forgery (CSRF)
- Insecure deserialization
- Using components with known vulnerabilities

**Controls**:
- AWS WAF managed rules (Core Rule Set)
- AWS WAF SQL injection rule set
- Input validation at application layer
- Parameterized queries in backend
- Security headers (HSTS, CSP, X-Frame-Options)

#### 2.3 Unauthorized Network Access

**Attacks Mitigated**:
- Port scanning
- Lateral movement
- Unauthorized database access
- Privilege escalation

**Controls**:
- Network segmentation (3-tier architecture)
- Security groups (principle of least privilege)
- NACLs (stateless filtering)
- VPC Flow Logs (audit trail)
- GuardDuty (threat detection)

#### 2.4 Data Exfiltration

**Attacks Mitigated**:
- Unauthorized outbound data transfer
- DNS tunneling
- Data over non-standard protocols

**Controls**:
- Egress filtering (whitelist-based)
- VPC endpoints (prevent internet transit)
- Network ACL restrictions
- VPC Flow Logs analysis
- DNS query monitoring

#### 2.5 Man-in-the-Middle (MITM)

**Attacks Mitigated**:
- Protocol downgrade attacks
- ARP spoofing
- DNS hijacking

**Controls**:
- HTTPS enforcement (TLS 1.2+)
- VPC isolation (no public exposure)
- VPC endpoints (AWS service access)
- DNS query validation
- Security headers

### Threat Sources & Probability

| Threat | Source | Probability | Impact | Mitigation |
|--------|--------|-------------|--------|-----------|
| DDoS | External | High | High | WAF, Shield, Rate limiting |
| SQL Injection | External | High | Critical | WAF, Input validation |
| Unauthorized Access | Internal/External | Medium | High | Segmentation, MFA |
| Data Exfiltration | Internal/External | Medium | Critical | Egress filtering, Logs |
| Malware | External | Medium | High | GuardDuty, File scanning |
| Insider Threat | Internal | Low | High | RBAC, Audit logs |

---

## 3. Network Architecture

### VPC Layout

```
Internet (0.0.0.0/0)
        |
   +----+----+
   |   IGW   |
   +----+----+
        |
   ┌────┴────────────────────────────┐
   |   Public Tier (10.0.1-3.0/24)    |
   | ┌──────┐  ┌──────┐  ┌──────┐    |
   | │ALB-1 │  │ALB-2 │  │ALB-3 │    |
   | │NAT-1 │  │NAT-2 │  │NAT-3 │    |
   | └──────┘  └──────┘  └──────┘    |
   └────┬────────────────────────────┘
        |
   ┌────┴────────────────────────────┐
   │  App Tier (10.0.11-13.0/24)      │
   │ ┌──────┐  ┌──────┐  ┌──────┐    │
   │ │App-1 │  │App-2 │  │App-3 │    │
   │ │Redis │  │Redis │  │Redis │    │
   │ └──────┘  └──────┘  └──────┘    │
   └────┬────────────────────────────┘
        |
   ┌────┴────────────────────────────┐
   │  DB Tier (10.0.21-23.0/24)       │
   │ ┌──────────────────────────────┐ │
   │ │  RDS PostgreSQL (Multi-AZ)   │ │
   │ │ ┌──────┐ ┌──────┐ ┌──────┐  │ │
   │ │ │DB-1  │ │DB-2  │ │DB-3  │  │ │
   │ │ └──────┘ └──────┘ └──────┘  │ │
   │ └──────────────────────────────┘ │
   └────────────────────────────────┘
```

### CIDR Allocation

| Tier | CIDR | Size | Purpose |
|------|------|------|---------|
| VPC | 10.0.0.0/16 | 65,536 | Main VPC |
| Public-AZ1 | 10.0.1.0/24 | 256 | ALB, NAT |
| Public-AZ2 | 10.0.2.0/24 | 256 | ALB, NAT |
| Public-AZ3 | 10.0.3.0/24 | 256 | ALB, NAT |
| App-AZ1 | 10.0.11.0/24 | 256 | ECS, VPC Endpoints |
| App-AZ2 | 10.0.12.0/24 | 256 | ECS, VPC Endpoints |
| App-AZ3 | 10.0.13.0/24 | 256 | ECS, VPC Endpoints |
| DB-AZ1 | 10.0.21.0/24 | 256 | RDS |
| DB-AZ2 | 10.0.22.0/24 | 256 | RDS |
| DB-AZ3 | 10.0.23.0/24 | 256 | RDS |

---

## 4. Security Groups Configuration

### 4.1 Public Tier - ALB Security Group

**Purpose**: Protect load balancer and route traffic

| Direction | Protocol | Port | Source/Dest | Purpose |
|-----------|----------|------|-------------|---------|
| **Inbound** |
| | TCP | 80 | 0.0.0.0/0 | HTTP |
| | TCP | 443 | 0.0.0.0/0 | HTTPS |
| **Outbound** |
| | TCP | 8000 | Backend SG | Route to backend |
| | TCP | 443 | 0.0.0.0/0 | HTTPS (external) |
| | UDP | 53 | 0.0.0.0/0 | DNS |

### 4.2 Application Tier - ECS/EC2 Security Group

**Purpose**: Protect application servers, prevent lateral movement

| Direction | Protocol | Port | Source/Dest | Purpose |
|-----------|----------|------|-------------|---------|
| **Inbound** |
| | TCP | 8000-8100 | ALB SG | From load balancer |
| | TCP | 22 | Bastion SG | SSH (admin only) |
| **Outbound** |
| | TCP | 5432 | DB SG | PostgreSQL |
| | TCP | 6379 | Cache SG | Redis |
| | TCP | 443 | 0.0.0.0/0 | HTTPS (external APIs) |
| | UDP | 53 | 0.0.0.0/0 | DNS |
| | UDP | 123 | 0.0.0.0/0 | NTP |

### 4.3 Database Tier - RDS Security Group

**Purpose**: Highly restrictive (database receives only, never initiates)

| Direction | Protocol | Port | Source/Dest | Purpose |
|-----------|----------|------|-------------|---------|
| **Inbound** |
| | TCP | 5432 | App SG (all AZs) | From app tier |
| | TCP | 5432 | Bastion SG | Maintenance only |
| **Outbound** |
| | — | — | — | NONE (restricted) |

### 4.4 Cache Tier - Redis Security Group

**Purpose**: Restrict cache to app tier only

| Direction | Protocol | Port | Source/Dest | Purpose |
|-----------|----------|------|-------------|---------|
| **Inbound** |
| | TCP | 6379 | App SG | Redis client |
| | TCP | 16379 | Cache SG | Cluster internal |
| | TCP | 6379 | Bastion SG | Admin monitoring |
| **Outbound** |
| | — | — | — | NONE (restricted) |

---

## 5. AWS WAF Configuration

### 5.1 WAF Rules Priority & Order

```
Priority 1: Rate Limiting Rule
   └─ 2000 requests/IP/5 minutes
   └─ Action: BLOCK
   └─ Scope: All requests

Priority 2: AWS Managed Core Rule Set
   └─ OWASP Top 10 protection
   └─ Common vulnerabilities
   └─ Action: BLOCK

Priority 3: Known Bad Inputs Rule Set
   └─ Malicious payloads
   └─ Attack signatures
   └─ Action: BLOCK

Priority 4: SQL Injection Protection
   └─ SQL commands in request
   └─ Database escape attempts
   └─ Action: BLOCK

Priority 5: IP Reputation Rules
   └─ Known malicious IPs
   └─ Custom blocked IP set
   └─ Action: BLOCK

Priority 6: Geo-blocking Rules
   └─ Country-based filtering
   └─ Action: BLOCK (if enabled)

Priority 7: Custom Protection Rules
   └─ Directory traversal (../, ..\)
   └─ Path manipulation
   └─ Action: BLOCK
```

### 5.2 WAF Managed Rules

#### Core Rule Set (CRS)

Protects against OWASP Top 10:

| Rule Group | Description | Enabled | Severity |
|-----------|-------------|---------|----------|
| SQL Injection | SQL command injection | YES | Critical |
| XSS | Cross-site scripting | YES | High |
| Local File Inclusion | LFI attacks | YES | High |
| Remote File Inclusion | RFI attacks | YES | High |
| PHP Injection | PHP code injection | YES | Medium |
| HTTP Protocol Attack | Invalid HTTP | YES | Medium |
| Session Fixation | Session manipulation | YES | High |
| Scanner Detection | Vulnerability scanners | YES | Medium |

#### Known Bad Inputs

- Account takeover attempts
- Bot traffic
- Malware signature detection
- Security testing tools

#### SQL Injection Detection

Blocks requests containing:
- `UNION`, `SELECT`, `INSERT`, `DELETE`, `DROP`
- `EXEC`, `EXECUTE`, `SCRIPT`
- Comment sequences (`--`, `/*`, `*/`)
- Database functions (`xp_`, `sp_`)

### 5.3 Rate Limiting

```
Request Rate Limits (WAF):
├─ Per IP: 2000 requests in 5 minutes
├─ Per endpoint: Analyzed in CloudWatch
├─ Connection limit: 10,000 concurrent connections
└─ Packet rate: 5000 packets/second

DDoS Thresholds:
├─ SYN flood: 1000 SYN packets/second
├─ UDP flood: 5000 packets/second
├─ TCP RST flood: 500 RST packets/second
└─ ICMP flood: 500 packets/second
```

### 5.4 IP Reputation & Geo-blocking

**Blocked IP Set**:
- Auto-updated from AWS threat intelligence
- Custom entries for known attackers
- Regional threat databases

**Geo-blocking** (optional):
- Restrict access by country
- Useful for compliance (GDPR, etc.)
- Default: Disabled (allow all countries)

---

## 6. Network ACL Rules

### 6.1 Public Subnet NACL

**Inbound Rules** (Stateless):

| Rule | Protocol | Port | Source | Action |
|------|----------|------|--------|--------|
| 100 | TCP | 80 | 0.0.0.0/0 | ALLOW |
| 110 | TCP | 443 | 0.0.0.0/0 | ALLOW |
| 120 | TCP | 22 | 0.0.0.0/0 | ALLOW |
| 130 | TCP | 1024-65535 | 0.0.0.0/0 | ALLOW |
| 140 | UDP | 53 | 0.0.0.0/0 | ALLOW |

**Outbound Rules**:

| Rule | Protocol | Port | Destination | Action |
|------|----------|------|-------------|--------|
| 100 | ALL | ALL | 0.0.0.0/0 | ALLOW |

### 6.2 Private Application Subnet NACL

**Inbound Rules**:

| Rule | Protocol | Port | Source | Action |
|------|----------|------|--------|--------|
| 100 | TCP | 8000-8100 | 10.0.0.0/16 | ALLOW |
| 110 | TCP | 22 | 10.0.0.0/16 | ALLOW |
| 120 | TCP | 1024-65535 | 0.0.0.0/0 | ALLOW |

**Outbound Rules**:

| Rule | Protocol | Port | Destination | Action |
|------|----------|------|-------------|--------|
| 100 | ALL | ALL | 0.0.0.0/0 | ALLOW |

### 6.3 Private Database Subnet NACL (Most Restrictive)

**Inbound Rules**:

| Rule | Protocol | Port | Source | Action |
|------|----------|------|--------|--------|
| 100 | TCP | 5432 | 10.0.11.0/24 | ALLOW |
| 110 | TCP | 5432 | 10.0.12.0/24 | ALLOW |
| 120 | TCP | 5432 | 10.0.13.0/24 | ALLOW |
| 130 | TCP | 5432 | 10.0.0.0/16 | ALLOW |
| 140 | TCP | 1024-65535 | 0.0.0.0/0 | ALLOW |

**Outbound Rules**:

| Rule | Protocol | Port | Destination | Action |
|------|----------|------|-------------|--------|
| 100 | UDP | 53 | 0.0.0.0/0 | ALLOW |
| 110 | TCP | 1024-65535 | 0.0.0.0/0 | ALLOW |

---

## 7. Egress Filtering

### 7.1 Whitelisted Outbound Destinations

**DNS (Port 53 - UDP)**
```
Allowed: 0.0.0.0/0
Purpose: Route53 DNS resolution
Restrictions: None
```

**HTTPS (Port 443 - TCP)**
```
Allowed: 0.0.0.0/0
Purpose: API calls, external services, software updates
Restrictions: Prefer HTTPS over HTTP
Certificates: TLS 1.2+
```

**HTTP (Port 80 - TCP)**
```
Allowed: Limited destinations only
Purpose: Legacy service compatibility
Restrictions: Discourage use, prefer HTTPS
```

**NTP (Port 123 - UDP)**
```
Allowed: 0.0.0.0/0
Purpose: Time synchronization
Restrictions: CloudWatch verified sources
```

**Internal VPC (All ports)**
```
Allowed: 10.0.0.0/16
Purpose: VPC-internal communication
Restrictions: None
```

### 7.2 Blocked/Restricted Protocols

```
BLOCKED PROTOCOLS:
├─ IGMP (protocol 2) - Used for multicast
├─ GRE (protocol 47) - VPN tunneling
├─ IP-in-IP (protocol 4) - Encapsulation
└─ SCTP (protocol 132) - Rarely used

BLOCKED PORTS:
├─ 23 (Telnet) - Unencrypted remote access
├─ 69 (TFTP) - Unencrypted file transfer
├─ 135-139 (NetBIOS) - Windows file sharing
├─ 445 (SMB) - Windows file sharing
├─ 1433 (MSSQL) - SQL Server
├─ 3306 (MySQL) - MySQL database
├─ 5984 (CouchDB) - NoSQL database
├─ 9042 (Cassandra) - Cassandra database
├─ 27017-27020 (MongoDB) - MongoDB database
└─ 50070 (Hadoop) - Big data processing
```

---

## 8. DDoS Protection

### 8.1 AWS Shield

**Standard (Automatic)**:
- Included with all AWS accounts
- Protects against common DDoS attacks
- L3/L4 protection (IP fragmentation, UDP floods, etc.)
- Automatic attack detection and mitigation
- No additional cost

**Advanced (Optional)**:
- Additional cost: $3,000/month
- 24/7 DDoS Response Team (DRT)
- Real-time attack diagnostics
- Cost protection guarantees
- Recommended for critical applications

### 8.2 Rate Limiting Strategy

```
Layer 1: Application (WAF)
├─ 2000 requests per IP per 5 minutes
└─ Block after threshold exceeded

Layer 2: Network (Security Group)
├─ 10,000 concurrent connections per source
└─ Connection limits enforced

Layer 3: Transport (NACL)
├─ SYN flood detection: 1000 packets/sec
├─ UDP flood detection: 5000 packets/sec
└─ Ephemeral port restrictions

Layer 4: Physical (Network)
└─ AWS Shield Standard automatic mitigation
```

### 8.3 Connection Limits

```
ALB Connection Limits:
├─ Max connections: 100,000
├─ Max new connections/sec: 10,000
└─ Connection timeout: 60 seconds

RDS Connection Limits:
├─ Max connections: 100 (db.t3.micro)
├─ Per-app limit: 20 (connection pool)
└─ Idle connection timeout: 15 min

Redis Connection Limits:
├─ Max connections: 10,000
├─ Client connection timeout: 5 seconds
└─ Max clients: 10,000
```

---

## 9. Intrusion Detection & Prevention

### 9.1 Detection Rules

**Rule IDS_001: Port Scanning Detection**
```
Trigger: 10+ different ports contacted in 60 seconds
Source: Single IP address
Action: Alert + log
Severity: High
Response: Block IP for 1 hour
```

**Rule IDS_002: SYN Flood Detection**
```
Trigger: 1000+ SYN packets per second
Source: Multiple IPs or single IP
Action: Alert + log + rate limit
Severity: Critical
Response: Activate Shield Advanced
```

**Rule IDS_003: UDP Flood Detection**
```
Trigger: 5000+ UDP packets per second
Target: Single port or service
Action: Alert + log + rate limit
Severity: High
Response: Rate limit source IPs
```

**Rule IDS_004: Malformed Packet Detection**
```
Trigger: Invalid protocol headers
Patterns: Zero-length packets, invalid flags
Action: Drop packet + log
Severity: Medium
Response: Log and monitor
```

**Rule IDS_005: Directory Traversal**
```
Patterns: ../, ..\, ....//
Location: URI path, query strings
Action: Block request + log
Severity: High
Response: Block source IP
```

**Rule IDS_006: SQL Injection**
```
Patterns: UNION, SELECT, INSERT, DELETE, exec()
Location: Query strings, POST bodies
Action: Block request + log
Severity: Critical
Response: Block source IP
```

**Rule IDS_007: XSS Attack**
```
Patterns: <script>, javascript:, onerror=
Location: All request fields
Action: Block request + log
Severity: High
Response: Block source IP
```

### 9.2 Detection Tools

**VPC Flow Logs**:
- Captures all network traffic
- Fields: source IP, destination IP, ports, protocol, action
- Storage: CloudWatch Logs (30-day retention)
- Cost: $0.50/GB ingested

**CloudWatch Logs Insights**:
```
# Find rejected connections
fields srcaddr, dstaddr, dstport, action
| filter action = "REJECT"
| stats count() by srcaddr

# Detect port scanning
fields srcaddr, dstport
| stats count_distinct(dstport) as unique_ports by srcaddr
| filter unique_ports > 10
```

**GuardDuty**:
- Threat detection using machine learning
- Detects compromised instances, cryptomining, malware
- Integration with Security Hub
- Cost: $0.30/million API calls

---

## 10. VPC Flow Logs & Monitoring

### 10.1 Flow Logs Configuration

**CloudWatch Log Group**: `/aws/vpc/flowlogs/thebot`
**Retention**: 30 days
**Traffic Type**: ALL (ACCEPT + REJECT)
**Format**: Version 2 (extended)

### 10.2 Log Fields

```
version account-id interface-id srcaddr dstaddr srcport dstport
protocol packets bytes start end action log-status
tcp-flags substring-fields
```

**Example Log Entry**:
```
2 123456789012 eni-0a1b2c3d 10.0.11.25 10.0.21.10 54932 5432 6 10 720 1634567890 1634567950 ACCEPT OK
```

**Fields Explanation**:
- `version`: 2 (extended format)
- `account-id`: 123456789012
- `interface-id`: eni-0a1b2c3d (ENI of source)
- `srcaddr`: 10.0.11.25 (source IP)
- `dstaddr`: 10.0.21.10 (destination IP)
- `srcport`: 54932 (source port)
- `dstport`: 5432 (destination port - PostgreSQL)
- `protocol`: 6 (TCP)
- `packets`: 10 (packets transferred)
- `bytes`: 720 (bytes transferred)
- `start`: 1634567890 (unix timestamp)
- `end`: 1634567950 (unix timestamp)
- `action`: ACCEPT (packet accepted)
- `log-status`: OK (successfully logged)

### 10.3 CloudWatch Alarms

**Alarm 1: Rejected Packets**
```
Metric: VPC Flow Logs Rejected Packets
Threshold: 1000 packets in 5 minutes
Action: SNS notification
Severity: High
Investigation: Check for network attacks
```

**Alarm 2: WAF Blocked Requests**
```
Metric: WAF Blocked Requests (BlockedRequests)
Threshold: 100 requests in 5 minutes
Action: SNS notification
Severity: Medium
Investigation: Check WAF logs for patterns
```

**Alarm 3: NAT Gateway Errors**
```
Metric: AWS/NatGateway ErrorPortAllocation
Threshold: 5+ errors in 5 minutes
Action: SNS notification
Severity: High
Investigation: May need additional NAT capacity
```

---

## 11. Network Segmentation Verification

### 11.1 Automated Audit Lambda Function

The `network_segmentation_audit` Lambda function runs daily (2 AM UTC) to verify:

**Checks Performed**:

```python
1. VPC Configuration
   ├─ Verify VPC exists with correct CIDR
   ├─ Check Flow Logs enabled
   └─ Validate DHCP option sets

2. Subnet Configuration
   ├─ Verify all expected subnets exist
   ├─ Check CIDR blocks match configuration
   ├─ Validate route tables
   └─ Confirm NAT Gateway associations

3. Security Groups
   ├─ Verify all expected SGs exist
   ├─ Check inbound rules (allow only necessary)
   ├─ Check outbound rules (restrictive)
   └─ Verify no overly permissive rules (0.0.0.0/0)

4. Network ACLs
   ├─ Verify NACL rules match specification
   ├─ Check deny rules are in place
   └─ Validate priority ordering

5. NAT Gateways
   ├─ Verify expected number of NATs
   ├─ Check one per AZ
   └─ Validate elastic IP assignments

6. VPC Endpoints
   ├─ Verify all interface endpoints exist
   ├─ Check security group associations
   └─ Validate route table entries

7. Traffic Flow
   ├─ Test connectivity between tiers
   ├─ Verify blocked routes are blocked
   └─ Confirm VPC Flow Logs are recording
```

**Remediation Actions**:
- Alert via Slack webhook if issues found
- Create AWS Systems Manager runbook
- Auto-remediate simple issues
- Manual review for complex issues

### 11.2 Manual Verification Commands

```bash
# Check VPC configuration
aws ec2 describe-vpcs --vpc-ids vpc-xxxxx

# List all subnets
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-xxxxx

# Verify security groups
aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxxx

# Check NACLs
aws ec2 describe-network-acls --filters Name=vpc-id,Values=vpc-xxxxx

# Validate NAT Gateways
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-xxxxx

# Test connectivity from EC2
nmap -p 5432 10.0.21.10  # PostgreSQL port
curl -v https://api.example.com

# Check Flow Logs
aws logs describe-log-groups --log-group-name-prefix /aws/vpc/flowlogs
```

---

## 12. AWS Security Services Integration

### 12.1 AWS Security Hub

**Purpose**: Centralize security findings across AWS services

**Enabled Standards**:
- AWS Foundational Security Best Practices
- CIS AWS Foundations Benchmark
- PCI DSS

**Integrated Findings**:
- GuardDuty findings
- IAM Access Analyzer
- AWS Config compliance
- AWS Systems Manager Patch Manager
- Macie (data protection)

**Dashboard Metrics**:
- High/Medium/Low severity findings
- Pass/Fail status for standards
- Compliance trend over time

### 12.2 Amazon GuardDuty

**Purpose**: Threat detection using ML/AI

**Detection Types**:
- EC2 findings (compromised instances)
- IAM findings (unusual API usage)
- S3 findings (data exfiltration)
- EKS findings (container attacks)
- RDS findings (database attacks)

**Threat Categories**:
- Trojan malware
- Cryptomining
- Unauthorized access
- Data exfiltration
- Suspicious activity

**Cost**: $0.30 per million API calls (~$10/month for typical platform)

---

## 13. Compliance & Audit Checklist

### 13.1 Security Audit Checklist

- [ ] **Network Segmentation**
  - [ ] VPC has correct CIDR (10.0.0.0/16)
  - [ ] Subnets properly isolated (public/private/db)
  - [ ] Security groups follow least privilege
  - [ ] NACLs have deny-by-default rules

- [ ] **DDoS Protection**
  - [ ] AWS WAF enabled on ALB
  - [ ] Rate limiting configured (2000 req/IP/5min)
  - [ ] AWS Shield Standard active
  - [ ] CloudWatch alarms configured

- [ ] **Firewall Rules**
  - [ ] Public tier: only HTTP(80) + HTTPS(443)
  - [ ] App tier: only from ALB + Bastion SSH
  - [ ] Database tier: only from app tier
  - [ ] Egress filtering active

- [ ] **Intrusion Detection**
  - [ ] VPC Flow Logs enabled
  - [ ] GuardDuty enabled
  - [ ] CloudWatch Logs configured
  - [ ] Log retention set (30 days)

- [ ] **Data Protection**
  - [ ] Database encryption at rest (RDS)
  - [ ] Database encryption in transit (TLS)
  - [ ] Backups encrypted (S3 SSE)
  - [ ] Secrets in AWS Secrets Manager

- [ ] **Access Control**
  - [ ] IAM roles follow least privilege
  - [ ] MFA enabled for console access
  - [ ] Service roles for EC2/ECS
  - [ ] No hardcoded credentials

- [ ] **Monitoring & Alerts**
  - [ ] CloudWatch alarms for security events
  - [ ] SNS notifications enabled
  - [ ] Log aggregation in place
  - [ ] Slack/email alerts configured

- [ ] **Compliance**
  - [ ] Security Hub enabled
  - [ ] Compliance standards verified
  - [ ] Remediation runbooks created
  - [ ] Audit trail maintained

### 13.2 Compliance Standards

**Compliance Mappings**:

| Standard | Requirement | Implementation |
|----------|-------------|-----------------|
| PCI-DSS | Network segmentation | Security groups + NACLs |
| PCI-DSS | Firewall rules | WAF + NACL rules |
| PCI-DSS | Intrusion detection | VPC Flow Logs + GuardDuty |
| HIPAA | Encryption in transit | TLS 1.2+ |
| HIPAA | Encryption at rest | RDS encryption |
| SOC2 | Change management | Terraform + Git |
| SOC2 | Audit logging | VPC Flow Logs (30 days) |
| SOC2 | Access controls | Security groups |
| ISO27001 | Network monitoring | CloudWatch + GuardDuty |
| ISO27001 | Incident response | CloudWatch alarms |

---

## 14. Deployment Instructions

### 14.1 Prerequisites

```bash
# Install Terraform
terraform version  # >= 1.0

# AWS CLI configured
aws sts get-caller-identity

# Verify VPC exists
aws ec2 describe-vpcs --filters Name=cidr,Values=10.0.0.0/16
```

### 14.2 Deploy Network Security

```bash
# Navigate to security directory
cd infrastructure/security

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_name       = "thebot"
environment        = "production"
vpc_id             = "vpc-xxxxx"
alb_arn            = "arn:aws:elasticloadbalancing:..."
public_nacl_id     = "acl-xxxxx"
sns_topic_arn      = "arn:aws:sns:..."
enable_guardduty   = true
enable_security_hub = false
flow_logs_retention_days = 30
EOF

# Plan deployment
terraform plan -var-file=terraform.tfvars

# Apply configuration
terraform apply -var-file=terraform.tfvars
```

### 14.3 Verify Deployment

```bash
# Get WAF Web ACL ID
terraform output waf_web_acl_id

# Get blocked IPs set
terraform output blocked_ips_set_arn

# Verify VPC Flow Logs
aws logs describe-log-groups --log-group-name-prefix /aws/vpc/flowlogs

# Check GuardDuty detector
aws guardduty list-detectors --region us-east-1
```

---

## 15. Troubleshooting

### 15.1 Common Issues

**Issue: WAF Blocking Legitimate Traffic**

```
Symptoms:
- 403 Forbidden responses
- Users cannot access API endpoints

Root Cause:
- WAF rule too aggressive
- Rate limit too low
- Custom IP in blocked set

Solution:
1. Check WAF logs in CloudWatch
2. Review blocked request patterns
3. Adjust rules or rate limits
4. Whitelist legitimate IPs if needed

aws wafv2 get-sampled-requests \
  --web-acl-arn <ACL_ARN> \
  --rule-metric-name <RULE_NAME> \
  --scope REGIONAL \
  --time-window StartTime=1634567890,EndTime=1634567950 \
  --max-items 100
```

**Issue: DDoS Attack Not Mitigated**

```
Symptoms:
- High rejected packet count
- Users reporting slow service
- CloudWatch alarms triggering

Root Cause:
- Attack exceeds WAF capacity
- New attack pattern not recognized
- Rate limits need tuning

Solution:
1. Enable AWS Shield Advanced
2. Contact AWS DDoS Response Team
3. Review attack logs in Flow Logs
4. Implement geographic filtering
5. Increase rate limits temporarily

# Contact AWS Support
aws support create-case \
  --issue-type "technical" \
  --service-code "shield" \
  --subject-line "DDoS Attack Mitigation Required"
```

**Issue: VPC Flow Logs Not Recording**

```
Symptoms:
- No logs in /aws/vpc/flowlogs group
- Flow Logs creation failed
- Permission denied errors

Root Cause:
- IAM role missing permissions
- CloudWatch log group deleted
- VPC Flow Logs disabled

Solution:
1. Check IAM role policy
2. Recreate log group
3. Re-enable Flow Logs

# Verify IAM policy
aws iam get-role-policy \
  --role-name thebot-vpc-flow-logs-role \
  --policy-name thebot-vpc-flow-logs-policy

# Recreate log group
aws logs create-log-group \
  --log-group-name /aws/vpc/flowlogs/thebot
```

### 15.2 Debugging Commands

```bash
# Check VPC Flow Logs
aws logs tail /aws/vpc/flowlogs/thebot --follow

# Find rejected traffic
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "REJECT"

# Analyze rejected packets
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "REJECT" \
  --query 'events[*].message'

# Check WAF rules
aws wafv2 list-web-acls --scope REGIONAL

# Get WAF logs
aws wafv2 get-sampled-requests \
  --web-acl-arn <WAF_ARN> \
  --rule-metric-name <RULE_NAME> \
  --scope REGIONAL \
  --time-window StartTime=<TIMESTAMP>,EndTime=<TIMESTAMP> \
  --max-items 100
```

---

## 16. Performance Metrics

### 16.1 Expected Baseline

| Metric | Target | Current |
|--------|--------|---------|
| WAF Processing Latency | <10ms | — |
| Security Group Enforcement | <1ms | — |
| NACL Processing | <1ms | — |
| Flow Logs Ingestion | Real-time | — |
| DDoS Mitigation Time | <5 seconds | — |
| False Positive Rate | <1% | — |

### 16.2 CloudWatch Metrics to Monitor

```
Namespace: AWS/WAFV2
├─ BlockedRequests (sum)
├─ AllowedRequests (sum)
└─ CountedRequests (sum)

Namespace: AWS/NatGateway
├─ BytesOutToDestination (sum)
├─ BytesInFromDestination (sum)
├─ ErrorPortAllocation (sum)
└─ ConnectionCount (sum)

Namespace: AWS/EC2
├─ NetworkPacketsIn (sum)
├─ NetworkPacketsOut (sum)
└─ NetworkIn (bytes)
```

---

## 17. Cost Estimation

### 17.1 Monthly Security Costs

| Service | Item | Unit | Quantity | Cost |
|---------|------|------|----------|------|
| WAF | Request processing | /million | 1 | $0.60 |
| WAF | Rules | per rule | 7 | $1.00 |
| Flow Logs | CloudWatch Logs | /GB | 5 | $2.50 |
| GuardDuty | API calls | /million | 10 | $3.00 |
| **Subtotal** | | | | **$7.10** |
| Shield Advanced* | Monthly | — | 1 | $3,000.00 |
| **Total (Basic)** | | | | **$7.10/month** |
| **Total (Advanced)** | | | | **$3,007.10/month** |

*Shield Advanced is optional and recommended only for critical production systems.

### 17.2 Cost Optimization Tips

1. **WAF**:
   - Evaluate rules quarterly
   - Remove unused custom rules
   - Consolidate related rules

2. **Flow Logs**:
   - Reduce retention from 30 to 14 days (saves 50%)
   - Use sampling (1 in 10 packets)
   - Archive old logs to S3 Glacier

3. **GuardDuty**:
   - Disable if not needed
   - Use with Security Hub (bundle discount)

---

## 18. Best Practices

### 18.1 Security Group Management

✓ **DO**:
- Use descriptive names and descriptions
- Implement principle of least privilege
- Review rules quarterly
- Use security group references (not IPs)
- Document purpose of each rule

✗ **DON'T**:
- Allow 0.0.0.0/0 (except public tier HTTP/HTTPS)
- Use overly broad port ranges
- Create duplicate rules
- Hardcode IPs (use security group references)
- Forget to remove temporary rules

### 18.2 WAF Best Practices

✓ **DO**:
- Monitor WAF logs regularly
- Adjust rate limits based on usage
- Update managed rules as AWS releases them
- Use IP reputation lists
- Enable geo-blocking if applicable

✗ **DON'T**:
- Disable WAF rules unless necessary
- Set rate limits too high
- Forget to test WAF changes in staging
- Block entire countries without business need
- Use custom rules for OWASP protection (use managed rules)

### 18.3 Network Segmentation Best Practices

✓ **DO**:
- Maintain 3-tier architecture (public/app/db)
- Use NAT Gateways for private tier egress
- Implement restrictive database tier NACL
- Monitor VPC Flow Logs regularly
- Test network connectivity regularly

✗ **DON'T**:
- Route database traffic through public internet
- Expose database directly to public internet
- Disable VPC Flow Logs
- Use single NAT Gateway (single point of failure)
- Allow direct internet access from database tier

### 18.4 DDoS Protection Best Practices

✓ **DO**:
- Start with AWS Shield Standard
- Use AWS WAF for rate limiting
- Monitor CloudWatch alarms
- Have AWS Support plan (for Shield Advanced)
- Test DDoS response procedures

✗ **DON'T**:
- Assume Shield Standard is sufficient for critical services
- Ignore CloudWatch alarms
- Set rate limits too low (causes false positives)
- Use same rate limits for all endpoints
- Skip DDoS response planning

---

## 19. Incident Response

### 19.1 DDoS Attack Response

**Detection Phase** (0-5 minutes):
1. CloudWatch alarm triggers
2. Alert sent to on-call team via SNS
3. Security team reviews Flow Logs
4. Pattern analysis begins

**Response Phase** (5-30 minutes):
1. Activate incident commander
2. Engage AWS Support (if Shield Advanced enabled)
3. Increase rate limiting thresholds
4. Enable geo-blocking if appropriate
5. Scale infrastructure as needed

**Recovery Phase** (30+ minutes):
1. Monitor attack patterns
2. Adjust rules based on observations
3. Prepare post-incident report
4. Update runbooks
5. Conduct post-mortem

### 19.2 WAF Rule Tuning

```bash
# Find most blocked IPs
aws logs filter-log-events \
  --log-group-name /aws/wafv2/logs \
  --filter-pattern "action=BLOCK" \
  --query 'events[*].message' | \
  jq -r '.[] | .httpSourceIp' | \
  sort | uniq -c | sort -rn | head -10

# Find most blocked rules
aws logs filter-log-events \
  --log-group-name /aws/wafv2/logs \
  --filter-pattern "action=BLOCK" \
  --query 'events[*].message' | \
  jq -r '.[] | .ruleGroupList[].ruleList[].ruleId' | \
  sort | uniq -c | sort -rn

# Whitelist legitimate IP
aws wafv2 update-ip-set \
  --name whitelisted-ips \
  --scope REGIONAL \
  --addresses '10.0.0.0/8' '203.0.113.0/24' \
  --id <IP_SET_ID>
```

---

## 20. Additional Resources

### 20.1 AWS Documentation

- [AWS WAF Documentation](https://docs.aws.amazon.com/waf/)
- [AWS Shield Documentation](https://docs.aws.amazon.com/shield/)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [Amazon GuardDuty](https://docs.aws.amazon.com/guardduty/)
- [AWS Security Hub](https://docs.aws.amazon.com/securityhub/)

### 20.2 Related Documentation

- [NETWORK_ARCHITECTURE.md](NETWORK_ARCHITECTURE.md) - VPC design
- [SECURITY.md](SECURITY.md) - Overall security framework
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Pre-launch verification

### 20.3 Tools & Utilities

**AWS CLI**:
```bash
# List all security groups
aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxxx

# Export security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxx --output json > sg-backup.json
```

**Third-party Tools**:
- **CloudMapper**: Visualize AWS network architecture
- **Prowler**: Security scanning and compliance
- **ScoutSuite**: Multi-cloud security auditing

---

## 21. Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-27 | 1.0.0 | Initial release |

---

## 22. Support & Escalation

**For Network Security Issues**:

1. **Level 1 - Operational Team**:
   - Check CloudWatch alarms
   - Review VPC Flow Logs
   - Verify security group rules

2. **Level 2 - Security Team**:
   - Analyze attack patterns
   - Adjust WAF rules
   - Review GuardDuty findings

3. **Level 3 - AWS Support**:
   - DDoS attack mitigation
   - Advanced threat response
   - Compliance requirements

**Contact**:
- Slack: #security-alerts
- Email: security-team@thebot.edu
- PagerDuty: escalation-policy-security

---

**Document Owner**: DevOps Engineer
**Last Updated**: December 27, 2025
**Next Review**: March 27, 2026
