# THE_BOT Infrastructure Security Tools

Comprehensive security tools for auditing, validating, and maintaining the THE_BOT platform infrastructure on AWS.

## Tools Overview

### 1. Security Groups Audit Script

**File**: `security-groups-audit.py`

Automated validation tool that checks security group configuration for compliance and security best practices.

#### Features

- Detects overly permissive rules (0.0.0.0/0 on database/Redis)
- Validates expected rules are present in each security group
- Checks for required tags (Name, Environment, ManagedBy)
- Identifies rules missing descriptions
- Verifies restricted services block outbound properly
- Generates compliance reports in multiple formats

#### Installation

```bash
# Ensure AWS credentials are configured
aws sts get-caller-identity

# Install Python dependencies
pip install boto3 botocore

# Make script executable
chmod +x security-groups-audit.py
```

#### Usage

```bash
# Basic audit of production environment
./security-groups-audit.py --environment production

# Audit staging environment
./security-groups-audit.py --environment staging

# Filter to specific security group
./security-groups-audit.py --environment production --sg-name backend

# Generate JSON report
./security-groups-audit.py --environment production --format json

# Save report to file
./security-groups-audit.py --environment production --format json -o report.json

# CSV export for spreadsheet analysis
./security-groups-audit.py --environment production --format csv -o report.csv
```

#### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--environment` | Environment to audit | production |
| `--region` | AWS region | us-east-1 |
| `--sg-name` | Filter security group by name pattern | None |
| `--format` | Output format (text/json/csv) | text |
| `--check` | Specific check to run | all |
| `--output, -o` | Output file path | stdout |

#### Output Example

```
======================================================================
THE_BOT Platform - Security Groups Audit Report
======================================================================
Environment: production
Region: us-east-1
Timestamp: 2025-12-27T19:00:00.000000
======================================================================

VPC ID: vpc-0123456789abcdef0

Auditing: thebot-bastion-sg (sg-001)
----------------------------------------------------------------------
Status: ✓ COMPLIANT

Auditing: thebot-frontend-sg (sg-002)
----------------------------------------------------------------------
Status: ✓ COMPLIANT

Auditing: thebot-backend-sg (sg-003)
----------------------------------------------------------------------
Status: ✓ COMPLIANT

Auditing: thebot-database-sg (sg-004)
----------------------------------------------------------------------
Status: ✓ COMPLIANT

======================================================================
AUDIT SUMMARY
======================================================================
Overall Status: COMPLIANT
Security Groups Audited: 6
Compliant Groups: 6
Non-Compliant Groups: 0
Total Rules Checked: 42
Total Findings: 0

======================================================================
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit completed, all compliant |
| 1 | Audit completed, non-compliance found |
| 2 | Error during audit execution |

#### Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Audit Security Groups
  run: |
    pip install boto3 botocore
    python3 infrastructure/security/security-groups-audit.py \
      --environment staging \
      --format json \
      --output audit-report.json
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_DEFAULT_REGION: us-east-1

- name: Check Audit Results
  run: |
    # Fail if critical findings
    if grep -q '"CRITICAL"' audit-report.json; then
      echo "Critical security issues found!"
      exit 1
    fi
```

### 2. Firewall Rules Configuration

**File**: `firewall-rules.json`

JSON configuration defining all expected firewall rules and their business justifications.

#### Structure

```json
{
  "security_groups": {
    "bastion": {
      "description": "Jump host for administrative access",
      "inbound": [
        {
          "name": "ssh_from_allowed_cidr",
          "port": 22,
          "protocol": "tcp",
          "source": "var.bastion_allowed_cidr",
          "justification": "Admin access from approved locations"
        }
      ],
      "outbound": [
        {
          "name": "all_outbound",
          "port": "0-65535",
          "protocol": "all",
          "destination": "0.0.0.0/0",
          "justification": "Required for admin operations"
        }
      ]
    }
  }
}
```

### 3. Network Security Terraform

**File**: `network-security.tf`

Terraform configuration for network security policies and additional security controls.

#### Contents

- Security group policies
- Network ACL configurations
- VPC Flow Logs setup
- GuardDuty integration
- Security Hub configuration

### 4. Variables and Configuration

**File**: `variables.tf`

Terraform variables for security settings:

```hcl
variable "bastion_allowed_cidr" {
  description = "CIDR block allowed to SSH to Bastion"
  type        = string
  # Example: "203.0.113.0/32" for single IP
  # Example: "203.0.113.0/24" for IP range
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs for monitoring"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable Amazon GuardDuty for threat detection"
  type        = bool
  default     = true
}
```

## Security Group Reference

For detailed information about each security group, see the main reference documentation:

**File**: `../../docs/SECURITY_GROUPS_REFERENCE.md`

### Quick Reference

#### 1. Bastion Security Group
- **Purpose**: Jump host for administrative access
- **Inbound**: SSH (22) from `bastion_allowed_cidr`
- **Outbound**: All traffic
- **Risk Level**: Medium (restricted SSH access)

#### 2. Frontend Security Group (ALB)
- **Purpose**: Application Load Balancer
- **Inbound**: HTTP (80), HTTPS (443) from 0.0.0.0/0
- **Outbound**: Port 8000 to Backend, All to 0.0.0.0/0
- **Risk Level**: Low (public-facing, expected)

#### 3. Backend Security Group (ECS/EC2)
- **Purpose**: Application servers
- **Inbound**: Port 8000 from ALB, SSH from Bastion, Port 6379 from Redis
- **Outbound**: Port 5432 to Database, Port 6379 to Redis, All to 0.0.0.0/0
- **Risk Level**: Low (restricted inbound)

#### 4. Database Security Group (RDS)
- **Purpose**: PostgreSQL database server
- **Inbound**: Port 5432 from Backend and Bastion
- **Outbound**: None (completely blocked)
- **Risk Level**: Low (highly restrictive)

#### 5. Redis Security Group (ElastiCache)
- **Purpose**: Cache and message broker
- **Inbound**: Port 6379 from Backend/Bastion, Port 16379 internal cluster
- **Outbound**: None (completely blocked)
- **Risk Level**: Low (highly restrictive)

#### 6. VPC Endpoints Security Group
- **Purpose**: Interface endpoints for AWS services
- **Inbound**: HTTPS (443), HTTP (80) from VPC CIDR
- **Outbound**: Managed by source (Backend SG)
- **Risk Level**: Low (VPC-only)

## Compliance & Audit

### Compliance Standards Supported

- **HIPAA** (Health Insurance Portability and Accountability Act)
- **GDPR** (General Data Protection Regulation)
- **SOC2** (Service Organization Control)
- **PCI-DSS** (Payment Card Industry Data Security Standard)

### Regular Audit Schedule

```
Daily     - Automated validation script
Weekly    - VPC Flow Logs analysis
Monthly   - Full security group review
Quarterly - Compliance audit
Annually  - Third-party penetration test
```

### Running Audits

```bash
# Daily automated check
0 2 * * * /path/to/security-groups-audit.py --environment production --format json -o /var/log/sg-audit.json

# Weekly detailed review
0 3 * * 0 /path/to/security-groups-audit.py --environment production --format json -o /var/log/sg-weekly.json
```

## Change Management

### Change Request Process

1. **Request**: Use change request template in SECURITY_GROUPS_REFERENCE.md
2. **Review**: Security team evaluates risk
3. **Testing**: Validate in staging environment
4. **Approval**: Required approvers sign off
5. **Deployment**: Apply changes via Terraform
6. **Documentation**: Update reference and audit trail

### Terraform Workflow

```bash
# Plan changes
terraform plan -var-file=production.tfvars -out=tfplan

# Review plan
terraform show tfplan

# Apply after approval
terraform apply tfplan

# Verify changes
./security-groups-audit.py --environment production
```

## Troubleshooting

### Common Issues

**Issue**: Audit script fails with AWS credentials error
```bash
# Verify credentials
aws sts get-caller-identity

# Or use AWS profile
export AWS_PROFILE=thebot-prod
./security-groups-audit.py --environment production
```

**Issue**: Cannot detect security groups
```bash
# Verify VPC tags
aws ec2 describe-vpcs --filters Name=tag:Environment,Values=production

# Check for required tags on security groups
aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxxx
```

**Issue**: Permissions denied
```bash
# Required IAM permissions
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSecurityGroupRules",
        "ec2:DescribeVpcs",
        "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    }
  ]
}
```

## Integration Points

### AWS Systems Manager

Use Session Manager to access instances without public SSH:

```bash
# List available instances
aws ssm describe-instance-information --filters "Key=tag:Environment,Values=production"

# Start session
aws ssm start-session --target i-xxxxxxxxx

# From instance: test connectivity
nc -zv 10.0.21.10 5432  # Database
redis-cli -h 10.0.21.15 -p 6379 PING  # Redis
```

### CloudWatch Integration

Monitor security group changes:

```bash
# Query CloudTrail for SG changes
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=thebot-backend-sg \
  --query 'Events[].{Time:EventTime,Name:EventName,Principal:Username}'
```

### VPC Flow Logs

Analyze network traffic:

```bash
# Query rejected traffic
aws logs filter-log-events \
  --log-group-name /aws/vpc/flowlogs/thebot \
  --filter-pattern "REJECT" \
  --query 'events[].message' \
  --output text
```

## Best Practices

### Rule Naming

All rules must use consistent naming:

```
[direction]_[service]_[port_or_purpose]

Examples:
- inbound_alb_8000
- outbound_database_5432
- inbound_bastion_ssh
- internal_redis_cluster
```

### Documentation

Every rule must include:
- Clear description (50 chars max)
- Business justification
- Review date
- Approval signature

### Monitoring

Set up alerts for:
- Failed connection attempts (VPC Flow Logs)
- Unauthorized access attempts (CloudWatch)
- Security group modifications (CloudTrail)
- NAT Gateway errors (CloudWatch metrics)

## Support & References

### Documentation

- [Security Groups Reference](../../docs/SECURITY_GROUPS_REFERENCE.md) - Complete reference
- [Network Architecture](../../docs/NETWORK_ARCHITECTURE.md) - VPC design
- [Security Guide](../../docs/SECURITY.md) - Overall security architecture

### AWS Resources

- [VPC Security Groups](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [Security Group Rules](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

### Compliance Resources

- [HIPAA on AWS](https://aws.amazon.com/compliance/hipaa/)
- [GDPR on AWS](https://aws.amazon.com/compliance/gdpr-center/)
- [SOC2 on AWS](https://aws.amazon.com/compliance/soc/)
- [PCI DSS on AWS](https://aws.amazon.com/compliance/pci-dss/)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-27 | Initial release |

## License

Part of THE_BOT Platform - All rights reserved

## Contact

For questions or issues:
1. Check documentation in `SECURITY_GROUPS_REFERENCE.md`
2. Review troubleshooting guide
3. Contact DevOps team
4. Open GitHub issue (internal)
