# Compliance Controls Deployment Guide

## Overview

This guide covers the deployment and management of the compliance and audit trail infrastructure for THE_BOT Platform, including CloudTrail, CloudWatch Logs, S3 audit storage, and compliance monitoring.

**Status**: Production Ready
**Last Updated**: December 27, 2025
**Maintenance**: DevOps Team

---

## Prerequisites

### Required Tools

```bash
# Terraform 1.0+
terraform version

# AWS CLI 2.0+
aws --version

# jq (for JSON parsing)
jq --version

# AWS credentials configured
aws configure
```

### AWS Permissions

Your IAM user or role must have permissions for:
- CloudTrail
- S3
- CloudWatch Logs
- KMS
- IAM
- AWS Config
- SNS

**Recommended**: Use the `AdministratorAccess` role for initial setup.

### AWS Account Requirements

- Single AWS account (can expand to organization)
- S3 bucket naming globally unique
- KMS key creation allowed
- CloudTrail service enabled

---

## Deployment Steps

### Step 1: Prepare Configuration

```bash
# Navigate to compliance directory
cd infrastructure/compliance

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars  # or your preferred editor
```

**Required Variables to Update**:

```hcl
# CRITICAL - MUST UPDATE
notification_email = "security@yourcompany.com"  # Your security team email

# Important
environment = "production"                         # or staging/development
aws_region = "us-east-1"                          # Your primary region
organization_id = "o-xxxxxxxxxx"                  # Your AWS Organization ID (if applicable)

# Optional but recommended
alert_critical_email = "ciso@yourcompany.com"    # Escalation email
slack_webhook_url = "https://hooks.slack.com/..." # From Slack (use CI/CD secrets)
```

### Step 2: Initialize Terraform

```bash
# Initialize Terraform (first time only)
terraform init

# Expected output:
# Terraform has been successfully configured!

# Verify configuration
terraform validate

# Expected output:
# Success! The configuration is valid.
```

### Step 3: Plan Deployment

```bash
# Generate execution plan
terraform plan -out=tfplan

# Review the plan carefully
# Expected resources: ~20-30
# Operations: Create

# Key resources created:
# - aws_cloudtrail.main
# - aws_s3_bucket.audit_logs
# - aws_kms_key.audit_logs
# - aws_cloudwatch_log_group.compliance
# - 5x aws_cloudwatch_metric_alarm.*
# - 7x aws_config_config_rule.*
# - SNS topic + subscriptions
```

### Step 4: Apply Configuration

```bash
# Deploy to AWS
terraform apply tfplan

# This will:
# 1. Create S3 bucket for audit logs
# 2. Enable CloudTrail
# 3. Create CloudWatch Logs groups
# 4. Setup KMS encryption
# 5. Configure alarms and notifications
# 6. Enable AWS Config rules

# Estimated time: 3-5 minutes
# Expected cost: ~$50-100/month
```

### Step 5: Verify Deployment

```bash
# Get outputs
terraform output

# Expected outputs:
# - audit_bucket_name
# - cloudtrail_name
# - cloudwatch_logs_group_name
# - kms_key_id
# - sns_topic_arn

# Verify CloudTrail is running
aws cloudtrail describe-trails --region us-east-1 | jq '.trailList[0].IsMultiRegionTrail'
# Should output: true

# Check CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix "/aws/thebot/compliance" | jq '.logGroups[].logGroupName'

# Verify S3 bucket
aws s3 ls | grep thebot-audit-logs
```

### Step 6: Test CloudTrail Logging

```bash
# Make a test API call to trigger CloudTrail logging
aws s3 ls

# Wait 5 minutes for logs to appear
sleep 300

# Query CloudTrail logs
aws logs filter-log-events \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" \
  --start-time $(($(date +%s000) - 600000)) | jq '.events[0]'

# Or check S3 directly
aws s3 ls s3://thebot-audit-logs-ACCOUNT-ID-us-east-1/cloudtrail/ --recursive
```

### Step 7: Configure SNS Email Subscription

```bash
# After deployment, check SNS for confirmation
# User will receive email: "AWS Notification - Subscription Confirmation"

# Click the confirmation link in the email
# This activates email notifications

# Test the notification
aws sns publish \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --subject "Test Notification" \
  --message "This is a test of the compliance alerting system"
```

---

## Post-Deployment Configuration

### 1. Enable Additional Data Event Logging

Edit `compliance-controls.tf` to add more data resources:

```hcl
data_resource {
  type   = "AWS::RDS::DBCluster"
  values = ["arn:aws:rds:*:*:cluster/*"]
}
```

Then redeploy:
```bash
terraform apply
```

### 2. Configure Slack Integration (Optional)

```bash
# In Slack: Create Incoming Webhook
# URL format: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX

# Update terraform.tfvars
slack_webhook_url = "https://hooks.slack.com/services/..."

# Redeploy
terraform apply
```

### 3. Setup Email Forwarding Rules

For better email management:

```bash
# Use AWS SES or your email provider to:
# 1. Receive compliance alerts -> compliance-alerts@company.com
# 2. Receive critical alerts -> ciso@company.com
# 3. Archive to compliance folder for audit trail
```

### 4. Create Compliance Dashboard (Manual)

```bash
# CloudWatch → Dashboards → Create dashboard
# Add widgets:
# - CloudTrail logs count (last 24 hours)
# - Failed logins (last 24 hours)
# - Unauthorized API calls (last 24 hours)
# - Root account usage (last 24 hours)
# - MFA disabled events (last 24 hours)
```

Or use CloudWatch automated dashboard:
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "TheBot-Compliance-Production" \
  --dashboard-body file://dashboard.json
```

### 5. Schedule Regular Reviews

```bash
# Create calendar reminders:
# - Weekly: Review CloudWatch alarms
# - Monthly: Generate compliance report
# - Quarterly: Access control review
# - Annual: SOC 2 Type II audit
```

---

## Monitoring & Maintenance

### Daily Tasks

```bash
# Check for alerts
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw sns_topic_arn)

# Review CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "TheBot-production" | jq '.MetricAlarms[].StateValue'
```

### Weekly Tasks

```bash
# Generate weekly compliance summary
aws logs start-query \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" \
  --start-time $(($(date -d '7 days ago' +%s) * 1000)) \
  --end-time $(($(date +%s) * 1000)) \
  --query-string '
    fields @timestamp, eventName
    | filter eventSource = "s3.amazonaws.com"
    | stats count() by eventName
  '
```

### Monthly Tasks

```bash
# Generate compliance report
# 1. Download logs from CloudWatch Logs Insights
# 2. Review for policy changes
# 3. Verify access controls
# 4. Check for security incidents
# 5. Document findings

# Export logs to S3 for analysis
aws logs create-export-task \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" \
  --from $(($(date -d '30 days ago' +%s) * 1000)) \
  --to $(($(date +%s) * 1000)) \
  --destination "thebot-audit-logs-ACCOUNT-ID-us-east-1" \
  --destination-prefix "exports/$(date +%Y-%m)"
```

### Quarterly Tasks

```bash
# Access control review
# 1. List all IAM users
aws iam list-users

# 2. Review CloudTrail logs for each user
aws logs filter-log-events \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" \
  --filter-pattern '{ $.userIdentity.principalId = "AIDAI..." }'

# 3. Approve or revoke access
# 4. Document decisions

# Backup compliance records
aws s3 sync s3://thebot-audit-logs-ACCOUNT-ID-us-east-1/ \
  ./compliance-backup-$(date +%Y-%m-%d) \
  --region us-east-1
```

---

## Updating Compliance Configuration

### Scenario 1: Increase Log Retention

```bash
# Current: 90 days (SOC 2 minimum)
# New: 180 days (double retention)

# Update terraform.tfvars
log_retention_days = 180

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Verify change
aws logs describe-log-groups --log-group-name-prefix "/aws/thebot/compliance" | \
  jq '.logGroups[] | {name: .logGroupName, retention: .retentionInDays}'
```

### Scenario 2: Add New Compliance Framework

```bash
# Add HIPAA compliance
target_compliance_frameworks = [
  "GDPR",
  "SOC2_TYPE_II",
  "ISO_27001",
  "HIPAA"
]

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Update documentation
# Edit COMPLIANCE_AUDIT.md to add HIPAA requirements
```

### Scenario 3: Enable Advanced Threat Detection

```bash
# Update terraform.tfvars
enable_advanced_threat_protection = true
enable_guardduty = true
enable_security_hub = true

# Plan to see new resources
terraform plan -out=tfplan

# Review cost impact
terraform plan -json tfplan | jq '.resource_changes[] | .resource_type'

# Apply
terraform apply tfplan
```

### Scenario 4: Modify Alarm Thresholds

```bash
# Current: Alert on 1 unauthorized API call
# New: Alert on 3 or more within 5 minutes

# Edit compliance-controls.tf
resource "aws_cloudwatch_metric_alarm" "unauthorized_api_calls" {
  threshold = 3  # Changed from 1
  ...
}

# Redeploy
terraform plan -out=tfplan
terraform apply tfplan

# Verify
aws cloudwatch describe-alarms \
  --alarm-names "TheBot-production-Unauthorized-API-Calls" | \
  jq '.MetricAlarms[0].Threshold'
```

---

## Disaster Recovery

### Backup Compliance Configuration

```bash
# Backup Terraform state
aws s3 cp terraform.tfstate s3://thebot-backups/compliance/terraform.tfstate

# Backup audit logs
aws s3 sync \
  s3://thebot-audit-logs-ACCOUNT-ID-us-east-1/ \
  s3://thebot-backups/audit-logs-$(date +%Y-%m-%d) \
  --region us-east-1

# Backup configuration files
tar czf compliance-config-$(date +%Y-%m-%d).tar.gz *.tf *.tfvars

# Upload backup
aws s3 cp compliance-config-*.tar.gz s3://thebot-backups/compliance/
```

### Restore Compliance Configuration

```bash
# If terraform state is lost or corrupted

# 1. Download backup
aws s3 cp s3://thebot-backups/compliance/terraform.tfstate .

# 2. Verify backup
terraform plan  # Should show no changes

# 3. If state was completely lost:
# Generate new state from AWS resources
terraform import aws_cloudtrail.main TheBot-production-trail

# 4. Apply to recreate missing resources
terraform apply
```

### Verify Audit Log Integrity

```bash
# Check S3 bucket
aws s3api head-bucket --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1

# Verify encryption
aws s3api get-bucket-encryption \
  --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1

# Verify versioning
aws s3api get-bucket-versioning \
  --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1

# Verify access is blocked
aws s3api get-bucket-public-access-block \
  --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1
```

---

## Troubleshooting

### Issue 1: CloudTrail Not Logging

**Symptoms**: No events appearing in CloudTrail logs

**Diagnosis**:
```bash
# Check if CloudTrail is running
aws cloudtrail describe-trails --region us-east-1 | jq '.trailList[0].IsLogging'
# Should be: true

# Check S3 bucket
aws s3 ls s3://thebot-audit-logs-ACCOUNT-ID-us-east-1/

# Check CloudWatch Logs
aws logs describe-log-streams \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" | \
  jq '.logStreams[0]'
```

**Fix**:
```bash
# Start CloudTrail logging
aws cloudtrail start-logging --name TheBot-production-trail

# Verify
aws cloudtrail describe-trails --region us-east-1 | jq '.trailList[0].IsLogging'
```

### Issue 2: High Costs

**Symptoms**: Unexpected AWS charges for CloudWatch Logs

**Diagnosis**:
```bash
# Check log volume
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/thebot/compliance" | \
  jq '.logGroups[] | {name: .logGroupName, retentionInDays: .retentionInDays}'

# Estimate cost
# CloudWatch Logs: $0.50 per GB ingested
# S3: $0.023 per GB stored
# KMS: $1 per key + $0.03 per 10,000 operations
```

**Fix**:
```bash
# Reduce retention
log_retention_days = 30  # From 90 days

# Move old logs to Glacier
# (Automatic via lifecycle policy)

# Disable unnecessary data event logging
# Edit event_selector in compliance-controls.tf
```

### Issue 3: SNS Notifications Not Working

**Symptoms**: No email alerts received

**Diagnosis**:
```bash
# Check SNS topic
aws sns get-topic-attributes \
  --topic-arn $(terraform output -raw sns_topic_arn)

# Check subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw sns_topic_arn) | \
  jq '.Subscriptions[] | {Endpoint: .Endpoint, SubscriptionArn: .SubscriptionArn}'

# Check email inbox for confirmation
# (May be in spam folder)
```

**Fix**:
```bash
# Reconfirm email subscription
# 1. Check email for confirmation link
# 2. Click to confirm
# 3. Or subscribe manually:

aws sns subscribe \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --protocol email \
  --notification-endpoint security@company.com
```

### Issue 4: Terraform State Lock

**Symptoms**: Error "Error acquiring the lock"

**Diagnosis**:
```bash
# Check DynamoDB lock table
aws dynamodb list-tables | grep terraform-state-lock

# View locked items
aws dynamodb scan \
  --table-name terraform-state-lock
```

**Fix**:
```bash
# Wait for lock to expire (default 30 minutes)
# Or force unlock (use with caution):

terraform force-unlock LOCK_ID
```

---

## Performance Tuning

### Optimize CloudWatch Logs Queries

```bash
# Filter before aggregation (faster)
# ❌ Slow: | stats count() by userIdentity.userName
# ✅ Fast: | filter userIdentity.type = "IAMUser" | stats count() by userName

# Use recent data when possible
# ❌ Slow: Query past 1 year of logs
# ✅ Fast: Query past 30 days

# Limit fields returned
# ❌ Slow: fields *
# ✅ Fast: fields @timestamp, eventName, userIdentity.principalId
```

### Optimize S3 Storage

```bash
# Enable Intelligent-Tiering
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1 \
  --id AutoArchive \
  --intelligent-tiering-configuration '{
    "Id": "AutoArchive",
    "Filter": {"Prefix": ""},
    "Status": "Enabled",
    "Tierings": [
      {"Days": 30, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 90, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'

# Verify
aws s3api get-bucket-intelligent-tiering-configuration \
  --bucket thebot-audit-logs-ACCOUNT-ID-us-east-1 \
  --id AutoArchive
```

---

## Compliance Verification

### Run Compliance Checks

```bash
# Check CloudTrail
aws configservice describe-compliance-by-config-rule \
  --compliance-types COMPLIANT | jq '.ComplianceByConfigRules[]'

# Check specific rule
aws configservice describe-config-rule-compliance-by-config-rule \
  --config-rule-names cloudtrail-enabled-production

# Generate compliance report
aws configservice describe-compliance-by-config-rule \
  --compliance-types NON_COMPLIANT | \
  jq '.ComplianceByConfigRules[] | {ConfigRuleName, Compliance}'
```

### Evidence Collection

```bash
# Collect monthly evidence for SOC 2 audit
aws logs start-query \
  --log-group-name "/aws/thebot/compliance/production/cloudtrail" \
  --start-time $(($(date -d '30 days ago' +%s) * 1000)) \
  --end-time $(($(date +%s) * 1000)) \
  --query-string '
    fields @timestamp, eventName, userIdentity.principalId, sourceIPAddress
    | filter ispresent(errorCode)
    | sort @timestamp desc
  '

# Save results
aws logs get-query-results \
  --query-id QUERY-ID | jq '.results' > evidence-$(date +%Y-%m).json
```

---

## Cost Optimization

### Estimated Monthly Costs

| Service | Usage | Cost |
|---------|-------|------|
| CloudTrail | 100GB logs/month | $20 |
| CloudWatch Logs | 100GB ingested/month | $50 |
| S3 Standard | 100GB stored | $2.30 |
| S3 Glacier | 1TB archived | $4.00 |
| KMS | 1 key + 10k operations | $2.00 |
| SNS | 100 notifications | <$1.00 |
| **Total** | | **~$79/month** |

### Cost Reduction Strategies

```bash
# 1. Reduce log retention
log_retention_days = 30  # From 90

# 2. Filter unnecessary events
# Edit event_selector in compliance-controls.tf
# Remove non-critical data events

# 3. Use S3 Intelligent-Tiering
# Automatically moves old logs to cheaper tiers

# 4. Consolidate multiple accounts
# Use organization trail (multi-account)

# 5. Set up log expiration
# Automatic deletion after retention period
```

---

## Support & Resources

### Getting Help

- **AWS Support**: [AWS Support Console](https://console.aws.amazon.com/support)
- **Terraform Documentation**: [terraform.io](https://www.terraform.io)
- **AWS CloudTrail Docs**: [AWS CloudTrail User Guide](https://docs.aws.amazon.com/awscloudtrail/)
- **GDPR Compliance**: [GDPR Official](https://gdpr-info.eu/)

### Escalation Path

1. Check this guide and FAQ section
2. Review AWS CloudWatch Logs for errors
3. Contact AWS Support (if issue is AWS-related)
4. Contact THE_BOT Security Team
5. Contact Terraform maintainers (if Terraform bug)

---

## Checklist: Initial Deployment

- [ ] AWS credentials configured
- [ ] terraform.tfvars created with correct values
- [ ] `terraform init` executed
- [ ] `terraform validate` passed
- [ ] `terraform plan` reviewed
- [ ] `terraform apply` executed successfully
- [ ] Outputs saved for reference
- [ ] SNS email subscription confirmed
- [ ] CloudTrail verified logging to S3
- [ ] CloudWatch Logs receiving events
- [ ] Alarms tested and working
- [ ] Documentation updated
- [ ] Team trained on procedures
- [ ] Scheduled maintenance tasks created

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
**Maintenance**: DevOps Team
