# THE_BOT Platform - IAM Infrastructure

Identity and Access Management infrastructure code and tools for the THE_BOT educational platform.

## Overview

This directory contains:

1. **Terraform Configuration** (`../terraform/iam/`)
   - IAM roles and policies
   - Permission boundaries
   - Service accounts
   - Trust relationships

2. **Configuration Files**
   - `roles.json` - Role definitions and specifications
   - `permission-boundaries.json` - Permission boundary policies

3. **Audit & Validation Tools**
   - `iam-audit.py` - Security audit tool
   - `iam-validator.py` - Policy validation tool

## Quick Start

### 1. Deploy IAM Infrastructure

```bash
cd infrastructure/terraform/iam

# Initialize Terraform
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# Get outputs
terraform output iam_summary
```

### 2. Run Security Audit

```bash
# Full audit
python3 infrastructure/iam/iam-audit.py --audit-all

# Check privilege escalation
python3 infrastructure/iam/iam-audit.py --check-escalation

# Review recent access
python3 infrastructure/iam/iam-audit.py --review-access --days 30

# Export report
python3 infrastructure/iam/iam-audit.py --audit-all --export audit-report.json
```

### 3. Validate Policies

```bash
# Validate all policies
python3 infrastructure/iam/iam-validator.py --validate-policies

# Check permission boundaries
python3 infrastructure/iam/iam-validator.py --validate-boundaries

# Validate principals
python3 infrastructure/iam/iam-validator.py --check-principals

# Export findings
python3 infrastructure/iam/iam-validator.py --validate-policies --export findings.json
```

## File Structure

```
infrastructure/
├── iam/
│   ├── README.md                      # This file
│   ├── roles.json                     # Role definitions
│   ├── permission-boundaries.json     # Permission boundary policies
│   ├── iam-audit.py                   # Security audit tool
│   ├── iam-validator.py               # Policy validation tool
│   └── access-review-template.md      # Access review template
│
└── terraform/
    └── iam/
        ├── iam-policies.tf            # Main IAM resources
        ├── variables.tf               # Variable definitions
        ├── outputs.tf                 # Output values
        └── terraform.tfvars           # Configuration (not in git)
```

## IAM Roles

### Developer Role

- **Purpose**: Day-to-day development work
- **Environment**: Dev and Staging only
- **Session Duration**: 1 hour
- **MFA Required**: No

**Key Permissions**:
- ECS: describe, list, update services
- S3: read/write dev/staging buckets
- RDS: database connection
- Secrets Manager: read dev secrets

**Command to Assume**:
```bash
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-developer-role \
  --role-session-name dev-session \
  --duration-seconds 3600 \
  --external-id YOUR_EXTERNAL_ID
```

### DevOps Engineer Role

- **Purpose**: Infrastructure management
- **Environment**: All (dev, staging, production)
- **Session Duration**: 1 hour
- **MFA Required**: No

**Key Permissions**:
- EC2, ECS, RDS, S3: full management
- Terraform: state management
- CloudFormation: stack management
- IAM: read-only + PassRole

**Command to Assume**:
```bash
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-devops-role \
  --role-session-name devops-session \
  --duration-seconds 3600 \
  --external-id YOUR_EXTERNAL_ID
```

### Admin Role

- **Purpose**: Full infrastructure and account management
- **Environment**: All
- **Session Duration**: 15 minutes
- **MFA Required**: Yes, mandatory

**Command to Assume** (with MFA):
```bash
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-admin-role \
  --role-session-name admin-session \
  --duration-seconds 900 \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/YOUR_USERNAME \
  --token-code 123456 \
  --external-id YOUR_EXTERNAL_ID
```

### Read-Only Auditor Role

- **Purpose**: Compliance auditing and monitoring
- **Environment**: All
- **Session Duration**: 1 hour
- **MFA Required**: No

**Key Permissions**:
- EC2, ECS, RDS, S3: describe/list only
- Logs, CloudTrail: read-only
- IAM: get/list operations only

### CI/CD Service Account Role

- **Purpose**: Automated deployments (GitHub Actions, GitLab CI)
- **Environment**: All (via OIDC)
- **Session Duration**: 30 minutes
- **MFA Required**: N/A

**Key Permissions**:
- ECR: push/pull images
- ECS: update services, register task definitions
- Secrets Manager: read secrets
- CloudWatch Logs: write logs

## Permission Boundaries

Permission boundaries set the maximum permissions a role can have. They prevent privilege escalation even if inline policies grant broader permissions.

### Boundary Policies

| Boundary | Purpose | Prevents |
|----------|---------|----------|
| `pb-developer` | Development access | IAM changes, KMS key deletion, production access |
| `pb-devops` | Infrastructure mgmt | Account changes, user/role deletion, KMS operations |
| `pb-admin` | Full access | MFA-less sensitive operations |
| `pb-readonly` | Auditing | All modifications |

## Access Control

### Prerequisites for Role Assumption

1. **AWS IAM User** in the same AWS account
2. **Trust Relationship** configured on the role
3. **External ID** (if configured)
4. **MFA Token** (for admin role)
5. **Source IP** (if IP restrictions enabled)

### Environment-Based Access

| Role | Dev | Staging | Production |
|------|-----|---------|-----------|
| Developer | ✓ | ✓ | ✗ |
| DevOps | ✓ | ✓ | ✓ |
| Admin | ✓ | ✓ | ✓ |
| Auditor | ✓ | ✓ | ✓ |

## Security Features

### Privilege Escalation Prevention

- Permission boundaries block dangerous IAM actions
- Explicit deny policies prevent workarounds
- Trust relationships restrict who can assume roles
- External IDs add additional security layer

### MFA Enforcement

- Admin role requires MFA for all operations
- Short session duration (15 minutes) for admin
- Automatic session timeout after inactivity

### Audit Logging

- All actions logged to CloudTrail
- Logs retained for 7 years
- Access reviews conducted quarterly
- Automated anomaly detection

## Terraform Deployment

### Prerequisites

```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads.html

# Configure AWS credentials
aws configure
```

### Step 1: Setup Variables

Create `infrastructure/terraform/iam/terraform.tfvars`:

```hcl
project_name = "thebot"
environment  = "production"
aws_region   = "us-east-1"

# Security
external_id = "your-32-char-minimum-external-id"
devops_allowed_ips = ["10.0.0.0/8"]
admin_allowed_ips  = ["10.0.0.0/8"]

# GitHub Actions OIDC (if using)
github_org  = "your-org"
github_repo = "THE_BOT_platform"

common_tags = {
  Project     = "THE_BOT"
  ManagedBy   = "Terraform"
  Environment = "production"
}
```

### Step 2: Initialize and Apply

```bash
cd infrastructure/terraform/iam

# Initialize
terraform init

# Review changes
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Show outputs
terraform output -json
```

### Step 3: Verify Deployment

```bash
# List roles
aws iam list-roles | grep thebot

# Check role trust relationships
aws iam get-role --role-name thebot-developer-role

# Get role summary
terraform output iam_summary
```

## Audit Tools

### iam-audit.py

Comprehensive security audit of IAM configuration.

**Usage**:
```bash
# Full audit
python3 infrastructure/iam/iam-audit.py --audit-all

# Check specific areas
python3 infrastructure/iam/iam-audit.py --check-escalation
python3 infrastructure/iam/iam-audit.py --review-access --days 30
python3 infrastructure/iam/iam-audit.py --unused-access

# Export results
python3 infrastructure/iam/iam-audit.py --audit-all --export audit.json
```

**Checks Performed**:
- Password policy compliance
- MFA usage and configuration
- Role trust relationships
- Permission boundary presence
- Privilege escalation vectors
- Unused roles and credentials
- Inline policy review
- Cross-account access
- Service account security

### iam-validator.py

Policy validation against security best practices.

**Usage**:
```bash
# Validate all policies
python3 infrastructure/iam/iam-validator.py --validate-policies

# Check specific areas
python3 infrastructure/iam/iam-validator.py --validate-boundaries
python3 infrastructure/iam/iam-validator.py --check-principals

# Export findings
python3 infrastructure/iam/iam-validator.py --validate-policies --export report.json
```

**Validations Performed**:
- Wildcard principal detection
- Dangerous action identification
- Missing condition detection
- Permission boundary verification
- Trust relationship validation
- MFA requirements
- Access key age
- Cross-account access validation

## Access Review Procedures

### Quarterly Review (Q1, Q2, Q3, Q4)

Schedule: First Monday of each quarter

**For**: Developer, DevOps, Auditor roles

**Checklist**:
- [ ] User still employed and in current role
- [ ] No unused permissions
- [ ] Recent activity aligns with responsibilities
- [ ] Policy violations check
- [ ] Documentation updated

**Run Audit**:
```bash
python3 infrastructure/iam/iam-audit.py --audit-all --export q1-audit.json
```

### Monthly Review (Admin, CI/CD)

Schedule: First Monday of each month

**Checklist**:
- [ ] MFA still enabled (admin)
- [ ] Recent admin actions reviewed
- [ ] Failed authentication attempts
- [ ] Credential rotation status
- [ ] Compliance verification

**Run Audit**:
```bash
python3 infrastructure/iam/iam-audit.py --review-access --days 30
```

### Annual Review

Schedule: January (fiscal year start)

**Activities**:
1. Complete credential report export
2. Update permission boundaries
3. Service account credential rotation
4. Compliance verification (SOC 2, ISO 27001, etc.)
5. Documentation update

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v3

      - name: Assume AWS Role
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/thebot-cicd-role
          aws-region: us-east-1

      - name: Deploy
        run: |
          # Your deployment commands
          aws ecs update-service --cluster thebot --service api --force-new-deployment
```

### GitLab CI

```yaml
deploy:
  stage: deploy
  script:
    - |
      CREDENTIALS=$(aws sts assume-role \
        --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-cicd-role \
        --role-session-name gitlab-ci \
        --duration-seconds 1800 \
        --external-id $EXTERNAL_ID)

    - export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.Credentials.AccessKeyId')
    - export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.Credentials.SecretAccessKey')
    - export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Credentials.SessionToken')

    - aws ecs update-service --cluster thebot --service api --force-new-deployment
```

## Troubleshooting

### "User is not authorized to perform: sts:AssumeRole"

**Solution**: User needs assume role policy:

```bash
aws iam put-user-policy \
  --user-name USERNAME \
  --policy-name assume-role-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": "arn:aws:iam::ACCOUNT:role/thebot-*"
      }
    ]
  }'
```

### "Invalid MFA device serial number"

**Solution**: Correct format is `arn:aws:iam::ACCOUNT_ID:mfa/username`

```bash
# List MFA devices
aws iam list-mfa-devices --user-name USERNAME
```

### "Role with name cannot be assumed by principal"

**Solution**: Check trust relationship and external ID:

```bash
# Verify trust relationship
aws iam get-role --role-name ROLE_NAME

# Check caller identity
aws sts get-caller-identity
```

## Related Documentation

- [docs/IAM_MANAGEMENT.md](../../docs/IAM_MANAGEMENT.md) - Complete IAM guide
- [infrastructure/terraform/vpc/](../terraform/vpc/) - VPC infrastructure
- [CLAUDE.md](../../CLAUDE.md) - Project overview
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

## Contributing

When modifying IAM infrastructure:

1. Update Terraform files
2. Run validation: `terraform plan`
3. Run audit tool: `python3 iam-validator.py --validate-policies`
4. Get review from security team
5. Apply and test

## Support

For IAM-related issues:

1. Check troubleshooting section above
2. Review AWS CloudTrail logs
3. Run audit and validation tools
4. Contact security team at security@company.com

---

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Maintained By**: Platform Team
