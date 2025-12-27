# THE_BOT Platform - Network Security Audit Checklist

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Frequency**: Monthly
**Responsible**: DevOps/Security Team

---

## 1. Pre-Audit Preparation

- [ ] Schedule audit window (30-60 minutes)
- [ ] Notify on-call team of audit activity
- [ ] Prepare test environment (non-production if possible)
- [ ] Gather AWS API credentials
- [ ] Review previous audit reports
- [ ] Update audit runbook if needed

**Notes**: _______________________________________________

---

## 2. VPC Configuration Audit

### 2.1 VPC Basic Settings

- [ ] **VPC Exists**: Verify VPC with correct ID (`vpc-xxxxx`)
  - Command: `aws ec2 describe-vpcs --vpc-ids vpc-xxxxx`
  - Expected: VPC found and active

- [ ] **VPC CIDR**: Verify CIDR block is `10.0.0.0/16`
  - Command: `aws ec2 describe-vpcs --vpc-ids vpc-xxxxx --query 'Vpcs[0].CidrBlock'`
  - Expected: `10.0.0.0/16`
  - ⚠️ If different: Document and approve change in ticket

- [ ] **DNS Hostnames**: Verify DNS hostnames enabled
  - Command: `aws ec2 describe-vpc-attribute --vpc-id vpc-xxxxx --attribute enableDnsHostnames`
  - Expected: `"Value": true`

- [ ] **DNS Resolution**: Verify DNS resolution enabled
  - Command: `aws ec2 describe-vpc-attribute --vpc-id vpc-xxxxx --attribute enableDnsSupport`
  - Expected: `"Value": true`

### 2.2 VPC Flow Logs

- [ ] **Flow Logs Active**: Verify Flow Logs enabled
  - Command: `aws ec2 describe-flow-logs --filter Name=resource-id,Values=vpc-xxxxx Name=flow-log-status,Values=ACTIVE`
  - Expected: At least one active flow log

- [ ] **Log Destination**: Verify CloudWatch Logs destination
  - Command: `aws ec2 describe-flow-logs --filter Name=resource-id,Values=vpc-xxxxx --query 'FlowLogs[0].LogDestinationType'`
  - Expected: `CloudWatchLogs`

- [ ] **Log Group Exists**: Verify CloudWatch log group
  - Command: `aws logs describe-log-groups --log-group-name-prefix /aws/vpc/flowlogs`
  - Expected: Log group found with 30-day retention

- [ ] **Traffic Type**: Verify all traffic captured
  - Command: `aws ec2 describe-flow-logs --filter Name=resource-id,Values=vpc-xxxxx --query 'FlowLogs[0].TrafficType'`
  - Expected: `ALL`

**Findings**: _______________________________________________

---

## 3. Subnet Configuration Audit

### 3.1 Public Subnets

- [ ] **Subnet Exists**: Public-AZ1 (10.0.1.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: Public-AZ2 (10.0.2.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: Public-AZ3 (10.0.3.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

### 3.2 Private Application Subnets

- [ ] **Subnet Exists**: App-AZ1 (10.0.11.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: App-AZ2 (10.0.12.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: App-AZ3 (10.0.13.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

### 3.3 Private Database Subnets

- [ ] **Subnet Exists**: DB-AZ1 (10.0.21.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: DB-AZ2 (10.0.22.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

- [ ] **Subnet Exists**: DB-AZ3 (10.0.23.0/24)
  - Status: ☐ Pass ☐ Fail ☐ N/A

### 3.4 Subnet Configuration Verification

- [ ] **Public Subnet Route Table**:
  - Command: `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=subnet-xxxxx`
  - Expected: Route `0.0.0.0/0 -> IGW`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Private App Subnet Route Table**:
  - Expected: Route `0.0.0.0/0 -> NAT Gateway`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Private DB Subnet Route Table**:
  - Expected: No route to internet (local only)
  - ☐ Pass ☐ Fail ☐ Needs Review

**Findings**: _______________________________________________

---

## 4. Security Group Audit

### 4.1 Bastion Security Group

**Name**: `thebot-bastion-sg`

- [ ] **Inbound SSH Rule**:
  - Expected: TCP port 22 from specific CIDR (not 0.0.0.0/0 in production)
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound Rules**:
  - Expected: All traffic allowed (full egress)
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **No Unexpected Rules**:
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 4.2 Frontend/ALB Security Group

**Name**: `thebot-frontend-sg`

- [ ] **Inbound HTTP Rule**:
  - Expected: TCP port 80 from 0.0.0.0/0
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Inbound HTTPS Rule**:
  - Expected: TCP port 443 from 0.0.0.0/0
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound to Backend**:
  - Expected: TCP port 8000 to `thebot-backend-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound DNS**:
  - Expected: UDP port 53 to 0.0.0.0/0
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 4.3 Backend/ECS Security Group

**Name**: `thebot-backend-sg`

- [ ] **Inbound from ALB**:
  - Expected: TCP port 8000-8100 from `thebot-frontend-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Inbound SSH from Bastion**:
  - Expected: TCP port 22 from `thebot-bastion-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound to Database**:
  - Expected: TCP port 5432 to `thebot-database-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound to Redis**:
  - Expected: TCP port 6379 to `thebot-redis-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound HTTPS**:
  - Expected: TCP port 443 to 0.0.0.0/0
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Outbound DNS**:
  - Expected: UDP port 53 to 0.0.0.0/0
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 4.4 Database/RDS Security Group

**Name**: `thebot-database-sg`

- [ ] **Inbound from Backend**:
  - Expected: TCP port 5432 from `thebot-backend-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Inbound from Bastion**:
  - Expected: TCP port 5432 from `thebot-bastion-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **No Outbound Rules**:
  - Expected: Most restrictive (no outbound)
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **No Unexpected Inbound**:
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 4.5 Cache/Redis Security Group

**Name**: `thebot-redis-sg`

- [ ] **Inbound from Backend**:
  - Expected: TCP port 6379 from `thebot-backend-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Inbound from Bastion**:
  - Expected: TCP port 6379 from `thebot-bastion-sg`
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **No Outbound Rules**:
  - Expected: Most restrictive (no outbound)
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 4.6 Overly Permissive Rules

- [ ] **Check for 0.0.0.0/0 on non-public ports**:
  - Command: `aws ec2 describe-security-groups --region us-east-1 --query 'SecurityGroups[?VpcId==`vpc-xxxxx`].[GroupId,IpPermissions]'`
  - ☐ None found ☐ Found (document below)

**Overly Permissive Rules Found**: _______________________________________________

---

## 5. Network ACL Audit

### 5.1 Public Subnet NACL

- [ ] **HTTP Inbound**: Rule 100, TCP port 80, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **HTTPS Inbound**: Rule 110, TCP port 443, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **SSH Inbound**: Rule 120, TCP port 22, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Ephemeral Ports**: Rule 130, TCP 1024-65535, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **DNS Inbound**: Rule 140, UDP port 53, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **All Outbound**: Rule 100, All protocols, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 5.2 Private App Subnet NACL

- [ ] **From ALB**: TCP 8000-8100, 10.0.0.0/16, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **SSH from Bastion**: TCP port 22, 10.0.0.0/16, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Ephemeral Return**: TCP 1024-65535, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **All Outbound**: All protocols, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

### 5.3 Private DB Subnet NACL

- [ ] **PostgreSQL from App-AZ1**: TCP port 5432, 10.0.11.0/24, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **PostgreSQL from App-AZ2**: TCP port 5432, 10.0.12.0/24, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **PostgreSQL from App-AZ3**: TCP port 5432, 10.0.13.0/24, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **PostgreSQL from Bastion**: TCP port 5432, 10.0.0.0/16, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Ephemeral Return**: TCP 1024-65535, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **DNS Outbound**: UDP port 53, 0.0.0.0/0, ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

---

## 6. NAT Gateway Audit

### 6.1 NAT Gateway Count and Status

- [ ] **Total NAT Gateways**: Expected 3 (one per AZ)
  - Command: `aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-xxxxx --query 'length(NatGateways)'`
  - Found: _____ ☐ Pass ☐ Fail

- [ ] **NAT-1 Status** (AZ-a):
  - Expected: Available
  - IP: ___________________
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **NAT-2 Status** (AZ-b):
  - Expected: Available
  - IP: ___________________
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **NAT-3 Status** (AZ-c):
  - Expected: Available
  - IP: ___________________
  - ☐ Pass ☐ Fail ☐ Needs Review

### 6.2 NAT Gateway Configuration

- [ ] **Elastic IPs Assigned**:
  - Expected: All NAT Gateways have elastic IPs
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **One per AZ**:
  - Expected: No single NAT per AZ (no single point of failure)
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Public Subnet Association**:
  - Expected: All NATs in public subnets
  - ☐ Pass ☐ Fail ☐ Needs Review

**Notes**: _______________________________________________

---

## 7. AWS WAF Audit

### 7.1 WAF Web ACL Configuration

- [ ] **Web ACL Exists**:
  - Command: `aws wafv2 list-web-acls --scope REGIONAL`
  - Expected: `thebot-alb-waf` found
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Associated with ALB**:
  - Command: `aws wafv2 list-resources-for-web-acl --web-acl-arn <WAF_ARN> --scope REGIONAL`
  - Expected: ALB ARN found in associations
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Default Action**: ALLOW
  - ☐ Pass ☐ Fail ☐ Needs Review

### 7.2 WAF Rules Configuration

- [ ] **Rate Limiting Rule**:
  - Priority: 1
  - Limit: 2000 requests per 5 minutes per IP
  - Action: BLOCK
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Core Rule Set**:
  - Priority: 2
  - Status: ENABLED
  - Provider: AWS Managed
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Known Bad Inputs**:
  - Priority: 3
  - Status: ENABLED
  - Provider: AWS Managed
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **SQL Injection Protection**:
  - Priority: 4
  - Status: ENABLED
  - Provider: AWS Managed
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **IP Reputation List**:
  - Priority: 5
  - Status: ENABLED
  - ☐ Pass ☐ Fail ☐ Needs Review

### 7.3 WAF Logs and Monitoring

- [ ] **WAF Logs Enabled**:
  - Destination: CloudWatch Logs
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **CloudWatch Metrics**:
  - Namespace: `AWS/WAFV2`
  - Metrics: BlockedRequests, AllowedRequests
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Review Blocked Requests** (last 7 days):
  - Command: `aws logs filter-log-events --log-group-name /aws/wafv2/logs --filter-pattern "action=BLOCK"`
  - Suspicious patterns found: ☐ Yes ☐ No
  - Details: _______________________________________________

**Notes**: _______________________________________________

---

## 8. DDoS Protection Audit

### 8.1 AWS Shield Configuration

- [ ] **Shield Standard Active**:
  - Expected: Automatic (no configuration needed)
  - ☐ Pass ☐ Fail ☐ Needs Review

- [ ] **Shield Advanced** (if applicable):
  - Enabled: ☐ Yes ☐ No ☐ N/A
  - Cost: $3,000/month
  - DRT Access: ☐ Yes ☐ No ☐ N/A

### 8.2 Rate Limiting Review

- [ ] **WAF Rate Limit**: 2000 requests/IP/5min
  - ☐ Appropriate ☐ Too High ☐ Too Low

- [ ] **Connection Limits**: 10,000 concurrent connections
  - ☐ Appropriate ☐ Too High ☐ Too Low

- [ ] **Historical DDoS Attacks**:
  - Attacks detected (last 90 days): ☐ Yes ☐ No
  - If yes, document: _______________________________________________

**Notes**: _______________________________________________

---

## 9. VPC Endpoints Audit

### 9.1 Gateway Endpoints

- [ ] **S3 Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - Policy: ☐ Restricted ☐ Public ☐ Needs Review

- [ ] **DynamoDB Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - Policy: ☐ Restricted ☐ Public ☐ Needs Review

### 9.2 Interface Endpoints

- [ ] **ECR API Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - SGs: ☐ Correct ☐ Needs Review

- [ ] **ECR DKR Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - SGs: ☐ Correct ☐ Needs Review

- [ ] **CloudWatch Logs Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - SGs: ☐ Correct ☐ Needs Review

- [ ] **Secrets Manager Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - SGs: ☐ Correct ☐ Needs Review

- [ ] **Systems Manager Endpoint**:
  - Status: ☐ Active ☐ Missing ☐ Needs Review
  - SGs: ☐ Correct ☐ Needs Review

**Notes**: _______________________________________________

---

## 10. Monitoring & Alerting Audit

### 10.1 CloudWatch Alarms

- [ ] **Rejected Packets Alarm**:
  - Name: `thebot-vpc-rejected-packets`
  - Threshold: 1000 packets in 5 minutes
  - Action: SNS
  - Status: ☐ Active ☐ Disabled ☐ Missing

- [ ] **WAF Blocked Requests Alarm**:
  - Name: `thebot-waf-blocked-requests`
  - Threshold: 100 requests in 5 minutes
  - Action: SNS
  - Status: ☐ Active ☐ Disabled ☐ Missing

- [ ] **NAT Gateway Error Alarm**:
  - Name: `thebot-nat-gateway-errors`
  - Threshold: 5+ errors in 5 minutes
  - Action: SNS
  - Status: ☐ Active ☐ Disabled ☐ Missing

### 10.2 GuardDuty Configuration

- [ ] **GuardDuty Enabled**:
  - Status: ☐ Enabled ☐ Disabled ☐ Not Configured
  - Detection types enabled: _______________________________________________

- [ ] **GuardDuty Findings**:
  - Total findings: _______________
  - High severity: _______________
  - Medium severity: _______________

### 10.3 Security Hub Integration

- [ ] **Security Hub Enabled**:
  - Status: ☐ Enabled ☐ Disabled ☐ Not Configured

- [ ] **Standards Enabled**:
  - AWS Foundational Security Best Practices: ☐ Yes ☐ No
  - CIS AWS Foundations Benchmark: ☐ Yes ☐ No
  - PCI DSS: ☐ Yes ☐ No

**Notes**: _______________________________________________

---

## 11. Traffic Analysis

### 11.1 VPC Flow Logs Analysis

**Query: Find rejected traffic sources**
```bash
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "REJECT" \
  --start-time $(($(date +%s) - 604800))000 \
  --query 'events[*].message'
```

- [ ] **Rejected Traffic Analysis**:
  - Top rejected source IPs: _______________________________________________
  - Action taken: _______________________________________________

**Query: Check for port scanning**
```bash
aws logs insights query:
fields srcaddr, dstport | stats count_distinct(dstport) as ports by srcaddr | filter ports > 10
```

- [ ] **Port Scanning Detected**: ☐ Yes ☐ No
  - If yes, details: _______________________________________________

**Query: Check for data exfiltration patterns**
```bash
fields srcaddr, dstaddr, bytes | filter bytes > 1000000 | sort bytes desc
```

- [ ] **Large Data Transfers**: ☐ Yes ☐ No
  - If yes, legitimate: ☐ Yes ☐ No ☐ Unknown
  - Details: _______________________________________________

### 11.2 Anomalies Detected

- [ ] **Unusual Traffic Patterns**:
  - ☐ None ☐ Minor ☐ Major
  - Details: _______________________________________________

- [ ] **Security Events**:
  - ☐ None ☐ Minor ☐ Major
  - Details: _______________________________________________

---

## 12. Compliance Check

### 12.1 Compliance Standards

- [ ] **PCI-DSS**:
  - Network segmentation: ☐ Pass ☐ Fail
  - Firewall rules: ☐ Pass ☐ Fail
  - Intrusion detection: ☐ Pass ☐ Fail
  - Overall: ☐ Compliant ☐ Non-compliant

- [ ] **HIPAA**:
  - Encryption in transit: ☐ Pass ☐ Fail
  - Encryption at rest: ☐ Pass ☐ Fail
  - Access controls: ☐ Pass ☐ Fail
  - Overall: ☐ Compliant ☐ Non-compliant

- [ ] **SOC2**:
  - Change management: ☐ Pass ☐ Fail
  - Audit logging: ☐ Pass ☐ Fail
  - Incident response: ☐ Pass ☐ Fail
  - Overall: ☐ Compliant ☐ Non-compliant

**Notes**: _______________________________________________

---

## 13. Findings and Remediation

### 13.1 Critical Issues Found

| Issue | Severity | Details | Remediation | Owner | Due Date |
|-------|----------|---------|-------------|-------|----------|
| | CRITICAL | | | | |
| | CRITICAL | | | | |

### 13.2 High Priority Issues

| Issue | Severity | Details | Remediation | Owner | Due Date |
|-------|----------|---------|-------------|-------|----------|
| | HIGH | | | | |

### 13.3 Medium Priority Issues

| Issue | Severity | Details | Remediation | Owner | Due Date |
|-------|----------|---------|-------------|-------|----------|
| | MEDIUM | | | | |

### 13.4 Recommendations

- [ ] 1. _______________________________________________
- [ ] 2. _______________________________________________
- [ ] 3. _______________________________________________

---

## 14. Audit Summary

**Audit Date**: _____________________
**Auditor**: _____________________
**Environment**: ☐ Development ☐ Staging ☐ Production

### 14.1 Overall Assessment

- [ ] **PASS** - All critical checks passed
- [ ] **PASS WITH REMEDIATION** - Minor issues found, remediation planned
- [ ] **FAIL** - Critical issues found, immediate action required

### 14.2 Compliance Status

- [ ] **COMPLIANT** - Meets all requirements
- [ ] **CONDITIONAL** - Compliant with remediation
- [ ] **NON-COMPLIANT** - Does not meet requirements

### 14.3 Risk Rating

**Current Risk Level**: ☐ Low ☐ Medium ☐ High ☐ Critical

**Previous Risk Level**: ☐ Low ☐ Medium ☐ High ☐ Critical

**Trend**: ☐ Improving ☐ Stable ☐ Declining

### 14.4 Executive Summary

_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________

---

## 15. Sign-Off

**Auditor Signature**: _____________________ **Date**: _____________

**Approver Signature**: _____________________ **Date**: _____________

**Next Audit Due**: _____________________

---

## Appendix A: AWS CLI Commands Reference

```bash
# List all VPCs
aws ec2 describe-vpcs

# Describe specific VPC
aws ec2 describe-vpcs --vpc-ids vpc-xxxxx

# List all subnets
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-xxxxx

# List all security groups
aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxxx

# List all NACLs
aws ec2 describe-network-acls --filters Name=vpc-id,Values=vpc-xxxxx

# List NAT Gateways
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-xxxxx

# List VPC Flow Logs
aws ec2 describe-flow-logs --filter Name=resource-id,Values=vpc-xxxxx

# List WAF Web ACLs
aws wafv2 list-web-acls --scope REGIONAL

# List VPC Endpoints
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-xxxxx

# Check GuardDuty status
aws guardduty list-detectors --region us-east-1

# View CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names thebot-vpc-rejected-packets
```

---

**Document Version**: 1.0.0
**Last Updated**: December 27, 2025
**Next Review**: March 27, 2026
