# THE_BOT Platform - IAM Management Guide

Production-ready Identity and Access Management (IAM) policies, roles, and procedures for the THE_BOT educational platform infrastructure.

## Table of Contents

1. [Overview](#overview)
2. [Role Definitions](#role-definitions)
3. [Permission Boundaries](#permission-boundaries)
4. [Access Control](#access-control)
5. [MFA Requirements](#mfa-requirements)
6. [Access Review Procedures](#access-review-procedures)
7. [CI/CD Service Accounts](#cicd-service-accounts)
8. [Privilege Escalation Prevention](#privilege-escalation-prevention)
9. [Implementation Guide](#implementation-guide)
10. [Troubleshooting](#troubleshooting)

## Overview

This document defines the IAM management strategy for THE_BOT platform, implementing the principle of least privilege across all roles and resources.

### Key Principles

- **Least Privilege**: Users receive only permissions necessary for their role
- **Defense in Depth**: Multiple layers of permission boundaries prevent escalation
- **Audit & Compliance**: All actions logged and regularly reviewed
- **Environment Separation**: Dev/staging/production have different access levels
- **MFA Enforcement**: Multi-factor authentication required for privileged access

### Architecture

```
THE_BOT IAM Architecture
│
├── Human Roles (assume via STS)
│   ├── Developer          [read/write limited]
│   ├── DevOps Engineer    [infrastructure management]
│   ├── Administrator      [full access, MFA required]
│   └── Auditor            [read-only]
│
├── Service Accounts (assumed by services)
│   ├── ECS Task Execution [pull images, write logs]
│   ├── ECS Task App       [application permissions]
│   ├── CI/CD Pipeline     [deploy services]
│   └── Terraform State    [state management]
│
├── Permission Boundaries [prevent escalation]
│   ├── Developer PB       [restricts dangerous actions]
│   ├── DevOps PB          [restricts account changes]
│   ├── Admin PB           [enforces MFA]
│   └── ReadOnly PB        [enforces read-only]
│
└── Resource Policies [object-level control]
    ├── S3 bucket policies
    ├── KMS key policies
    ├── Secrets policies
    └── RDS resource policies
```

## Role Definitions

### 1. Developer Role

**Purpose**: Day-to-day development work on non-production environments

**Access Level**: Read/Write (dev & staging only)

**Key Permissions**:
- ECS: describe, list, update services, run tasks
- S3: get, put, delete objects (dev/staging buckets)
- RDS: database connection
- Secrets Manager: read dev secrets
- Logs: create streams, write events
- CloudWatch: put metrics

**Restrictions**:
- Production environment access denied
- Production secrets blocked
- IAM changes denied
- KMS key deletion denied
- Cannot modify security groups
- Cannot delete databases

**Session Duration**: 3600 seconds (1 hour)

**MFA Required**: No

**Example Commands**:
```bash
# Assume developer role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-developer-role \
  --role-session-name dev-session \
  --duration-seconds 3600 \
  --external-id YOUR_EXTERNAL_ID

# List ECS services
aws ecs list-services --cluster thebot

# Update ECS service with new image
aws ecs update-service \
  --cluster thebot \
  --service api \
  --force-new-deployment

# Read application secrets
aws secretsmanager get-secret-value \
  --secret-id thebot/dev/database-password
```

### 2. DevOps Engineer Role

**Purpose**: Infrastructure management, deployment, and operations

**Access Level**: Infrastructure Management (all environments)

**Key Permissions**:
- EC2: full management
- ECS: full management
- RDS: full management
- S3: full management
- CloudFormation: full management
- IAM: read-only (no modifications)
- Terraform: state management, apply changes
- Route53: DNS management
- KMS: key management (except deletion)

**Restrictions**:
- Cannot delete users or roles
- Cannot create access keys for users
- Cannot delete KMS keys
- Cannot create new users
- Cannot attach/detach user policies

**Session Duration**: 3600 seconds (1 hour)

**IP Restrictions**: Optional (configured in variables)

**MFA Required**: No

**Example Commands**:
```bash
# Assume DevOps role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-devops-role \
  --role-session-name devops-session \
  --duration-seconds 3600 \
  --external-id YOUR_EXTERNAL_ID

# Deploy Terraform changes
terraform apply

# Manage RDS database
aws rds modify-db-instance \
  --db-instance-identifier thebot-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"

# Manage ECS clusters
aws ecs create-service \
  --cluster thebot-prod \
  --service-name api \
  --task-definition thebot-api:1
```

### 3. Administrator Role

**Purpose**: Full infrastructure and account management

**Access Level**: Full Access

**Key Permissions**:
- All AWS services and actions allowed

**Restrictions**:
- MFA REQUIRED for all operations
- IP restrictions apply (if configured)
- Cannot perform dangerous actions without MFA token

**Session Duration**: 900 seconds (15 minutes)

**MFA Required**: Yes, mandatory

**Example Commands**:
```bash
# Assume admin role WITH MFA
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-admin-role \
  --role-session-name admin-session \
  --duration-seconds 900 \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/user@company.com \
  --token-code 123456 \
  --external-id YOUR_EXTERNAL_ID

# Full infrastructure management
aws iam create-user --user-name new-user
aws iam attach-user-policy \
  --user-name new-user \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

### 4. Read-Only Auditor Role

**Purpose**: Compliance auditing and security monitoring

**Access Level**: Read-Only

**Key Permissions**:
- EC2: Describe* operations only
- ECS: Describe* operations only
- RDS: Describe* operations only
- S3: GetObject, ListBucket
- Logs: Get* and Describe* operations
- CloudTrail: View events and logs
- IAM: Get* and List* operations

**Restrictions**:
- Cannot create, modify, or delete any resources
- Cannot make changes to security policies
- Cannot access secrets or encrypted data

**Session Duration**: 3600 seconds (1 hour)

**MFA Required**: No

**Example Commands**:
```bash
# Assume read-only role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-readonly-role \
  --role-session-name audit-session \
  --duration-seconds 3600 \
  --external-id YOUR_EXTERNAL_ID

# View infrastructure state
aws ec2 describe-instances
aws ecs describe-services --cluster thebot
aws rds describe-db-instances

# Check CloudTrail logs
aws cloudtrail lookup-events --max-results 50
```

## Permission Boundaries

Permission boundaries are policies that set the maximum permissions a principal can have. Even if an inline policy grants broader permissions, the boundary limits what can actually be done.

### Boundary Architecture

```
Role Policies          Permission Boundary       Effective Permissions
┌─────────────┐       ┌──────────────────┐     ┌──────────────────┐
│  Allow: *   │  AND  │  Allow: EC2,S3   │ =   │  Allow: EC2,S3   │
│             │       │  Deny: IAM,Org   │     │                  │
└─────────────┘       └──────────────────┘     └──────────────────┘
```

### Developer Permission Boundary

**Policy Name**: `pb-developer`

**Rules**:
1. Allows broad development resource access
2. Denies privilege escalation actions
3. Blocks production secret access

**Denied Actions**:
```
iam:*
organizations:*
account:*
kms:ScheduleKeyDeletion
kms:DisableKey
s3:DeleteBucketPolicy
s3:PutBucketPolicy
rds:ModifyDBInstance
ec2:ModifyInstanceAttribute
logs:DeleteLogGroup
cloudtrail:StopLogging
```

**Denied Resources**:
- `arn:aws:secretsmanager:*:*:secret:prod/*`

### DevOps Permission Boundary

**Policy Name**: `pb-devops`

**Rules**:
1. Allows infrastructure management
2. Denies account-level changes
3. Prevents user and group modifications

**Denied Actions**:
```
organizations:*
account:*
iam:DeleteRole
iam:DeleteRolePolicy
iam:DeleteUser
iam:DeleteGroup
iam:PutUserPolicy
iam:PutGroupPolicy
iam:AttachUserPolicy
iam:AttachGroupPolicy
iam:CreateAccessKey
kms:ScheduleKeyDeletion
kms:DisableKey
```

### Admin Permission Boundary

**Policy Name**: `pb-admin`

**Rules**:
1. Allows all actions
2. Enforces MFA for sensitive actions
3. Prevents KMS key deletion without MFA

**MFA-Protected Actions**:
```
iam:*
organizations:*
account:*
kms:ScheduleKeyDeletion
kms:DisableKey
```

### Read-Only Permission Boundary

**Policy Name**: `pb-readonly`

**Rules**:
1. Allows only read operations
2. Explicitly denies all modifications
3. Blocks IAM access (except Get/List)

**Denied Action Patterns**:
```
*:Create*
*:Delete*
*:Modify*
*:Put*
*:Update*
*:Attach*
*:Detach*
iam:*
```

## Access Control

### Assume Role Prerequisites

To assume any role, you need:

1. **IAM User or Role** in the same AWS account
2. **Assume Role Trust Relationship** configured
3. **External ID** (if configured for security)
4. **MFA Token** (for admin role)
5. **Valid IP Address** (if IP restrictions enabled)

### Trust Relationship Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "EXTERNAL_ID_VALUE"
        },
        "IpAddress": {
          "aws:SourceIp": ["IP1", "IP2"]
        },
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

### Environment-Based Access

| Role | Dev | Staging | Production |
|------|-----|---------|-----------|
| Developer | Yes | Yes | No |
| DevOps | Yes | Yes | Yes |
| Admin | Yes | Yes | Yes |
| Auditor | Yes | Yes | Yes |

### Resource-Based Access Control (RBAC)

Resources are tagged with owner and team information:

```hcl
tags = {
  Project            = "THE_BOT"
  Environment        = "production"
  Owner              = "platform-team"
  DataClassification = "confidential"
  Team               = "backend"
}
```

Access can be granted based on tags:

```json
{
  "Effect": "Allow",
  "Action": ["ec2:TerminateInstances"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "ec2:ResourceTag/Team": "${aws:username}"
    }
  }
}
```

## MFA Requirements

### MFA Setup

**For Admin Users**:

```bash
# Create virtual MFA device
aws iam enable-mfa-device \
  --user-name your-username \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/your-username \
  --authentication-code1 123456 \
  --authentication-code2 654321

# Or use hardware security key
aws iam enable-mfa-device \
  --user-name your-username \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/your-username \
  --authentication-code1 123456 \
  --authentication-code2 654321
```

### MFA-Protected Actions

Actions requiring MFA:

1. **IAM Management**
   - Delete users/roles
   - Attach/detach policies
   - Create access keys
   - Modify permissions

2. **Account Management**
   - Organization changes
   - Account structure modifications
   - Billing modifications

3. **Key Management**
   - KMS key deletion
   - KMS key disablement
   - KMS policy changes

4. **Audit Trail**
   - CloudTrail deletion
   - Log group deletion
   - CloudWatch alarm deletion

### Assume Role with MFA

```bash
# Get temporary credentials with MFA
CREDENTIALS=$(aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-admin-role \
  --role-session-name admin-session \
  --duration-seconds 900 \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/user@company.com \
  --token-code 123456 \
  --external-id YOUR_EXTERNAL_ID)

# Export credentials
export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Credentials.SessionToken')

# Use credentials
aws iam list-users
```

### MFA Best Practices

1. **Use Strong MFA**:
   - Prefer hardware security keys (YubiKey, etc.)
   - Virtual MFA (Google Authenticator, Authy) acceptable
   - SMS-based MFA not recommended

2. **Keep MFA Secure**:
   - Store backup codes securely
   - Never share MFA device
   - Report lost MFA device immediately

3. **MFA Recovery**:
   - Root account can disable MFA
   - Document recovery process
   - Test recovery procedures quarterly

## Access Review Procedures

### Quarterly Access Review (Developer, DevOps, Auditor)

**Schedule**: First Monday of Q1, Q2, Q3, Q4

**Duration**: 2 weeks per quarter

**Process**:

1. **Access Validation**
   ```bash
   # List all users with roles
   aws iam list-users --max-items 100

   # Check attached policies
   aws iam list-attached-user-policies --user-name USERNAME
   ```

2. **Activity Review**
   ```bash
   # Review CloudTrail events
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=Username,AttributeValue=USERNAME \
     --max-results 50 \
     --start-time 2025-09-01T00:00:00Z

   # Check failed authentication attempts
   aws ec2 describe-security-groups \
     --filters "Name=group-name,Values=restricted"
   ```

3. **Validation Checklist**
   - [ ] User still employed and in current role
   - [ ] No unused/excessive permissions
   - [ ] Recent activity aligns with job duties
   - [ ] No policy violations detected
   - [ ] MFA enabled (if required)
   - [ ] No long-inactive sessions

4. **Remediation**
   - Remove unnecessary permissions
   - Update role if responsibilities changed
   - Disable unused access keys
   - Add new permissions if needed
   - Document any changes

5. **Documentation**
   ```json
   {
     "review_date": "2025-12-27",
     "reviewer": "security-team@company.com",
     "period": "Q4 2025",
     "users_reviewed": 25,
     "changes": [
       {
         "user": "john.doe",
         "action": "removed_s3_access",
         "reason": "role_change"
       }
     ],
     "findings": [
       "Access key ABC123 unused for 90 days",
       "3 users without MFA"
     ]
   }
   ```

### Monthly Access Review (Admin, CI/CD)

**Schedule**: First Monday of each month

**Duration**: 1 week per month

**Focus Areas**:

1. **MFA Status** (Admin only)
   ```bash
   # List users with MFA enabled
   aws iam list-mfa-devices --user-name ADMIN_USER

   # Check for unused MFA devices
   aws iam list-virtual-mfa-devices
   ```

2. **Admin Actions Review**
   ```bash
   # Get all admin role assumptions
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=thebot-admin-role \
     --max-results 100

   # Review IAM changes
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=EventName,AttributeValue=CreateUser \
     --max-results 50
   ```

3. **CI/CD Pipeline Review** (CI/CD service account)
   ```bash
   # Check last deployment
   aws ecs describe-services \
     --cluster thebot-prod \
     --services api

   # Review ECR pushes
   aws ecr describe-images \
     --repository-name thebot/api \
     --max-results 10
   ```

4. **Security Incidents**
   - Failed authentication attempts
   - Unauthorized API calls
   - Policy violations
   - Access denied errors

5. **Compliance Status**
   - Are all requirements met?
   - Any policy violations?
   - Recent changes documented?
   - Audit trail complete?

### Annual Access Review

**Schedule**: January (start of fiscal year)

**Scope**: All roles and permissions

**Activities**:

1. **Complete Role Audit**
   ```bash
   # Export all users and roles
   aws iam get-credential-report

   # Review all policies
   aws iam list-policies --scope Local
   ```

2. **Permission Boundary Review**
   - Verify boundaries still appropriate
   - Check for new AWS services
   - Update policies if needed

3. **Service Account Review**
   - Verify service accounts still needed
   - Rotate credentials
   - Update permissions based on usage

4. **Compliance Verification**
   - SOC 2 requirements
   - ISO 27001 controls
   - Industry standards
   - Internal policies

5. **Documentation Update**
   - Update IAM_MANAGEMENT.md
   - Update role descriptions
   - Update runbooks
   - Record changes in git

### Access Review Tools

**CloudTrail for Audit Logging**:
```bash
# Enable CloudTrail for all regions
aws cloudtrail create-trail \
  --name thebot-trail \
  --s3-bucket-name thebot-cloudtrail-logs

# Start logging
aws cloudtrail start-logging --trail-name thebot-trail

# Query events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=USERNAME \
  --start-time 2025-12-01 \
  --max-results 100
```

**AWS Config for Compliance**:
```bash
# Check IAM password policy
aws configservice describe-config-rules \
  --filters Name=ConfigRuleName,Values=iam-password-policy

# Evaluate compliance
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name iam-password-policy
```

**Access Analyzer for Permissions**:
```bash
# Analyze external access
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:REGION:ACCOUNT:analyzer/name
```

## CI/CD Service Accounts

### GitHub Actions Integration

**Setup OIDC Provider**:

```bash
# Create OIDC provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938FD4D98BAB503D5EB2D90C852EBA1
```

**Assume Role in GitHub Actions**:

```yaml
name: Deploy to AWS

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

      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login \
            --username AWS \
            --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

          docker build -t thebot/api:${{ github.sha }} .
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/thebot/api:${{ github.sha }}

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster thebot-prod \
            --service api \
            --force-new-deployment
```

### GitLab CI Integration

**Setup in .gitlab-ci.yml**:

```yaml
deploy:
  stage: deploy
  image: amazon/aws-cli:latest
  script:
    # Assume role using STS
    - |
      CREDENTIALS=$(aws sts assume-role \
        --role-arn arn:aws:iam::ACCOUNT_ID:role/thebot-cicd-role \
        --role-session-name gitlab-ci \
        --duration-seconds 1800 \
        --external-id $EXTERNAL_ID)

    # Export credentials
    - export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r '.Credentials.AccessKeyId')
    - export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r '.Credentials.SecretAccessKey')
    - export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r '.Credentials.SessionToken')

    # Deploy
    - aws ecs update-service --cluster thebot-prod --service api --force-new-deployment
  only:
    - main
```

### Minimal Permissions for CI/CD

The CI/CD service account has minimal permissions to:

1. **Push Docker Images**
   - `ecr:PutImage`
   - `ecr:InitiateLayerUpload`
   - `ecr:UploadLayerPart`
   - `ecr:CompleteLayerUpload`
   - `ecr:GetAuthorizationToken`

2. **Update ECS Services**
   - `ecs:UpdateService`
   - `ecs:DescribeServices`
   - `ecs:RegisterTaskDefinition`

3. **Access Secrets**
   - `secretsmanager:GetSecretValue`
   - `kms:Decrypt`

4. **Write Logs**
   - `logs:CreateLogStream`
   - `logs:PutLogEvents`

**It cannot**:
- Modify IAM policies
- Access other AWS services
- Delete resources
- Access production RDS databases
- Modify security groups

## Privilege Escalation Prevention

### Escalation Vectors and Mitigations

| Vector | Example | Mitigation |
|--------|---------|-----------|
| IAM Policy Attachment | `iam:AttachUserPolicy` | Denied by boundary |
| Inline Policy Creation | `iam:PutUserPolicy` | Denied by boundary |
| Trust Relationship Modification | Modify assume role policy | Denied by boundary |
| PassRole to Admin Role | `iam:PassRole` for admin role | Restricted resource |
| Create Access Key | `iam:CreateAccessKey` | Denied by boundary |
| Assume Higher Role | Assume admin role directly | Trust relationship checks |
| Permissions Boundary Removal | Can't remove boundary | No permission to touch IAM |
| CloudTrail Disabling | `cloudtrail:StopLogging` | Denied by boundary |

### Denied Actions by Role

**Developer - Denied**:
```
iam:* (all IAM actions)
organizations:* (all org actions)
account:* (all account actions)
kms:ScheduleKeyDeletion
kms:DisableKey
s3:DeleteBucketPolicy
s3:PutBucketPolicy
rds:ModifyDBInstance
ec2:ModifyInstanceAttribute
logs:DeleteLogGroup
cloudtrail:StopLogging
cloudtrail:DeleteTrail
```

**DevOps - Denied**:
```
organizations:* (all org actions)
account:* (all account actions)
iam:DeleteRole
iam:DeleteRolePolicy
iam:DeleteUser
iam:DeleteGroup
iam:PutUserPolicy
iam:PutGroupPolicy
iam:AttachUserPolicy
iam:AttachGroupPolicy
iam:CreateAccessKey
kms:ScheduleKeyDeletion
kms:DisableKey
```

**Admin - MFA Required**:
```
iam:* (requires MFA)
organizations:* (requires MFA)
account:* (requires MFA)
kms:ScheduleKeyDeletion (requires MFA)
kms:DisableKey (requires MFA)
```

### Defending Against Common Escalation Attempts

**Attempt**: "Create new admin user"

```bash
aws iam create-user --user-name admin-backdoor
```

**Result**: Denied by permission boundary
```
An error occurred (AccessDenied) when calling the CreateUser operation:
User: arn:aws:iam::ACCOUNT:user/attacker is not authorized to perform:
iam:CreateUser on resource: arn:aws:iam::ACCOUNT:user/admin-backdoor
```

**Attempt**: "Attach admin policy to myself"

```bash
aws iam attach-user-policy \
  --user-name attacker \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

**Result**: Denied
```
An error occurred (AccessDenied) when calling the AttachUserPolicy operation:
User is not authorized to perform: iam:AttachUserPolicy
```

**Attempt**: "Assume higher-privilege role"

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT:role/admin \
  --role-session-name escalation
```

**Result**: Denied by trust relationship
```
An error occurred (AccessDenied) when calling the AssumeRole operation:
User: arn:aws:iam::ACCOUNT:user/attacker is not authorized to perform:
sts:AssumeRole on resource: role/admin
```

## Implementation Guide

### Prerequisites

- Terraform >= 1.0
- AWS CLI v2
- AWS account with appropriate permissions
- External ID for cross-account access (recommended)

### Step 1: Prepare Variables

Create `terraform.tfvars`:

```hcl
project_name = "thebot"
environment  = "production"
aws_region   = "us-east-1"

# Security
external_id = "your-external-id-min-32-chars"
devops_allowed_ips = ["10.0.0.0/8", "203.0.113.0/24"]
admin_allowed_ips  = ["10.0.0.0/8", "203.0.113.0/24"]

# GitHub OIDC (if using GitHub Actions)
oidc_provider_url = "token.actions.githubusercontent.com"
oidc_client_id    = "sts.amazonaws.com"
github_org        = "your-org"
github_repo       = "THE_BOT_platform"

common_tags = {
  Project     = "THE_BOT"
  ManagedBy   = "Terraform"
  CreatedAt   = "2025-12-27"
  Environment = "production"
}
```

### Step 2: Deploy IAM Infrastructure

```bash
cd infrastructure/terraform/iam

# Initialize Terraform
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# Get role ARNs
terraform output iam_summary
```

### Step 3: Configure Access for Users

**Give users trust relationship to assume roles**:

```bash
# Allow John (john@example.com) to assume developer role
aws iam put-user-policy \
  --user-name john \
  --policy-name assume-developer-role \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": "arn:aws:iam::ACCOUNT_ID:role/thebot-developer-role"
      }
    ]
  }'
```

### Step 4: Setup MFA for Admin Users

```bash
# For each admin user
aws iam enable-mfa-device \
  --user-name admin-user \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/admin-user \
  --authentication-code1 123456 \
  --authentication-code2 654321
```

### Step 5: Enable CloudTrail Logging

```bash
# Create S3 bucket for logs
aws s3 mb s3://thebot-cloudtrail-logs-prod

# Create CloudTrail
aws cloudtrail create-trail \
  --name thebot-prod-trail \
  --s3-bucket-name thebot-cloudtrail-logs-prod

# Start logging
aws cloudtrail start-logging --trail-name thebot-prod-trail
```

### Step 6: Configure Access Analyzer

```bash
# Create analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name thebot-prod-analyzer \
  --type ACCOUNT

# Wait for activation
aws accessanalyzer get-analyzer \
  --analyzer-arn arn:aws:access-analyzer:REGION:ACCOUNT:analyzer/thebot-prod-analyzer
```

### Step 7: Setup Automated Reviews

Create scheduled Lambda function:

```python
import boto3
import json
from datetime import datetime

iam = boto3.client('iam')

def lambda_handler(event, context):
    """Quarterly access review reminder"""

    # Get all roles
    roles = iam.list_roles()['Roles']

    # Check for roles without recent activity
    findings = []
    for role in roles:
        if 'thebot' in role['RoleName']:
            # Check last used information
            findings.append({
                'role': role['RoleName'],
                'created': str(role['CreateDate']),
                'status': 'needs_review'
            })

    # Send SNS notification
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:REGION:ACCOUNT:security-reviews',
        Subject='Quarterly Access Review Required',
        Message=json.dumps(findings, indent=2)
    )

    return {
        'statusCode': 200,
        'body': f'Review initiated for {len(findings)} roles'
    }
```

## Troubleshooting

### Common Issues

#### "User is not authorized to perform: sts:AssumeRole"

**Cause**: User doesn't have permission to assume role

**Solution**:
```bash
# Add policy to user
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

#### "InvalidInput: Invalid MFA device serial number"

**Cause**: Wrong MFA device ARN format

**Solution**:
```bash
# Correct format
arn:aws:iam::ACCOUNT_ID:mfa/username

# List MFA devices to verify
aws iam list-mfa-devices --user-name username
```

#### "An error occurred (AccessDenied) when calling the AssumeRole operation"

**Cause**: Permission boundary or trust relationship blocking access

**Solution**:
```bash
# Check role trust relationship
aws iam get-role --role-name role-name

# Check permission boundary
aws iam get-role-policy --role-name role-name --policy-name policy-name

# Verify caller identity
aws sts get-caller-identity
```

#### "The role with name thebot-developer-role cannot be assumed by principal"

**Cause**: External ID mismatch or IP restriction

**Solution**:
```bash
# Verify external ID
echo $EXTERNAL_ID

# Check source IP
curl ifconfig.me

# Assume role with correct parameters
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT:role/thebot-developer-role \
  --role-session-name session-name \
  --external-id $EXTERNAL_ID
```

#### "User: ACCOUNT is not authorized to perform: iam:PassRole"

**Cause**: User can't pass role to services

**Solution**:
```bash
# Grant PassRole permission
aws iam put-user-policy \
  --user-name USERNAME \
  --policy-name pass-role-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "iam:PassRole",
        "Resource": "arn:aws:iam::ACCOUNT:role/thebot-*"
      }
    ]
  }'
```

### Debugging Commands

```bash
# Check current credentials
aws sts get-caller-identity

# List all roles user can assume
aws iam list-roles | grep thebot

# Check user's attached policies
aws iam list-attached-user-policies --user-name USERNAME

# Check user's inline policies
aws iam list-user-policies --user-name USERNAME

# Get policy document
aws iam get-user-policy \
  --user-name USERNAME \
  --policy-name POLICY_NAME

# Check role's trust relationship
aws iam get-role --role-name ROLE_NAME

# Get role's attached policies
aws iam list-attached-role-policies --role-name ROLE_NAME

# Simulate policy
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/role-name \
  --action-names ecs:UpdateService \
  --resource-arns "*"
```

### Security Audit

```bash
# Get credential report
aws iam generate-credential-report
aws iam get-credential-report --query 'Content' --output text | base64 -d

# Check password policy
aws iam get-account-password-policy

# List MFA devices
aws iam list-mfa-devices

# Check access keys age
aws iam list-access-keys --user-name USERNAME

# Get role last used info
aws iam get-role --role-name ROLE_NAME
```

## Monitoring and Alerts

### CloudWatch Alarms

Monitor for suspicious activity:

```bash
# Alert on multiple failed authentication attempts
aws cloudwatch put-metric-alarm \
  --alarm-name thebot-failed-auth-attempts \
  --alarm-description "Alert on multiple failed auth" \
  --metric-name FailedAuthAttempts \
  --namespace AWS/IAM \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### Security Hub Integration

Connect to AWS Security Hub for continuous monitoring:

```bash
# Enable Security Hub
aws securityhub enable-security-hub

# Create automation rule for IAM changes
aws securityhub create-automation-rule \
  --name "Alert on IAM policy changes" \
  --criteria='{...}' \
  --actions='[...]'
```

## Related Documentation

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Permission Boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- THE_BOT CLAUDE.md
- infrastructure/terraform/iam/

## Summary

This IAM management system provides:

✓ **Least-Privilege Access**: Each role has minimum required permissions
✓ **Defense in Depth**: Permission boundaries prevent escalation
✓ **Audit & Compliance**: CloudTrail logs all actions
✓ **Regular Reviews**: Quarterly access audits ensure appropriate access
✓ **MFA Enforcement**: Admin access requires multi-factor authentication
✓ **Environment Separation**: Dev/staging/production have different access levels
✓ **Service Accounts**: CI/CD pipelines with minimal permissions
✓ **Documented Procedures**: Clear processes for access management

For questions or issues, contact the security team at security@company.com
