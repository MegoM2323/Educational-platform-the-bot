# Compliance & Audit Trail Infrastructure

Comprehensive compliance controls and audit infrastructure for THE_BOT Platform, implementing regulatory requirements for GDPR, SOC 2 Type II, and ISO 27001.

## Overview

This module provides:

- **CloudTrail**: Multi-region audit logging of all AWS API calls
- **CloudWatch Logs**: Centralized log aggregation with real-time processing
- **S3 Audit Storage**: Encrypted, versioned, immutable audit log storage
- **KMS Encryption**: Automatic encryption key rotation and management
- **Monitoring & Alerting**: CloudWatch alarms for security events
- **Compliance Automation**: AWS Config rules for continuous compliance checking
- **GDPR Controls**: Data export, deletion, and anonymization APIs
- **SOC 2 Evidence**: Automated evidence collection for audits

## Features

### Security & Compliance

- ✓ CloudTrail logging (multi-region, log file validation)
- ✓ KMS encryption at rest (AES-256)
- ✓ TLS 1.2+ encryption in transit
- ✓ S3 bucket versioning and Object Lock (WORM)
- ✓ Public access blocked on all buckets
- ✓ MFA delete protection enabled
- ✓ Automatic key rotation (yearly)
- ✓ Audit log integrity validation

### Monitoring & Alerting

- ✓ 5 CloudWatch alarms for security events
- ✓ Log metric filters for pattern detection
- ✓ SNS notifications (email + Slack)
- ✓ CloudWatch dashboard for monitoring
- ✓ Real-time log insights with CloudWatch Logs Insights
- ✓ Monthly compliance reporting

### Data Retention

- ✓ Configurable retention periods
- ✓ Automatic S3 lifecycle policies
- ✓ Transition to Glacier for cost optimization
- ✓ Compliance with GDPR (min 90 days)
- ✓ Compliance with SOC 2 (min 90 days)
- ✓ Long-term archival support

### GDPR & Privacy

- ✓ Right to access (data export)
- ✓ Right to erasure (account deletion)
- ✓ Right to data portability (format conversion)
- ✓ Data anonymization procedures
- ✓ 30-day grace period for deletion
- ✓ Breach notification procedures (72 hours)
- ✓ Privacy notice generation

### SOC 2 Type II

- ✓ Common Criteria (CC6, CC7, CC8, CC9) controls
- ✓ Logging and monitoring (CC7.1, CC7.2)
- ✓ Logical access control (CC6.1, CC6.2)
- ✓ Change management (CC8.1-CC8.4)
- ✓ Incident response (CC9.1, CC9.2)
- ✓ Automated evidence collection
- ✓ Audit trail retention (365+ days)

## Quick Start

### 1. Prerequisites

```bash
# Terraform 1.0+
terraform version

# AWS CLI 2.0+
aws --version

# AWS credentials configured
aws configure
```

### 2. Initialize

```bash
cd infrastructure/compliance

# Copy and customize
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Initialize Terraform
terraform init
terraform validate
```

### 3. Deploy

```bash
# Review changes
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# View outputs
terraform output
```

### 4. Verify

```bash
# Check CloudTrail
aws cloudtrail describe-trails --region us-east-1 | jq '.trailList[0].IsLogging'

# Check logs
aws logs describe-log-groups --log-group-name-prefix "/aws/thebot/compliance"

# List alarms
aws cloudwatch describe-alarms --alarm-name-prefix "TheBot-production"
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed setup instructions.

## File Structure

```
infrastructure/compliance/
├── README.md                          # This file
├── DEPLOYMENT.md                      # Deployment & operational guide
├── compliance-controls.tf             # Main Terraform configuration
├── variables.tf                       # Variable definitions
├── outputs.tf                         # Output definitions
├── terraform.tfvars.example           # Example configuration
├── audit-config.json                  # Audit logging configuration
├── data-retention-policy.json         # Data retention policy
└── ../../docs/
    └── COMPLIANCE_AUDIT.md            # Complete compliance documentation
```

## Configuration Files

### compliance-controls.tf

Main Terraform module containing:
- S3 bucket for audit logs with encryption and lifecycle policies
- CloudTrail configuration with multi-region support
- CloudWatch Logs groups and log streams
- KMS key creation and management
- SNS topic for notifications
- 5 CloudWatch alarms for security monitoring
- AWS Config rules for compliance checking
- IAM roles and policies

**Key Resources**: ~25-30
**Estimated Deployment Time**: 3-5 minutes

### variables.tf

Comprehensive variable definitions with validation including:
- AWS region and environment
- Compliance framework selection
- Retention period configuration
- Notification preferences
- Feature flags for different compliance requirements
- Advanced configuration options

**Total Variables**: 50+

### audit-config.json

Audit logging configuration specifying:
- CloudTrail settings
- Event logging preferences
- GDPR compliance requirements
- SOC 2 Type II controls
- Monitoring and alerting configuration
- Data retention schedules
- Incident response procedures

### data-retention-policy.json

Data retention policy covering:
- Data classification levels
- Retention periods for each data type
- Deletion procedures (soft and hard)
- Data anonymization techniques
- Storage tiering strategy
- Compliance exceptions
- Automated cleanup schedules

## Deployment Options

### Production Environment

```hcl
environment                = "production"
cloudtrail_enabled        = true
enable_log_file_validation = true
log_retention_days        = 90
audit_log_retention_days  = 365
enable_gdpr_controls      = true
enable_soc2_monitoring    = true
mfa_delete_enabled        = true
```

### Staging Environment

```hcl
environment                = "staging"
cloudtrail_enabled        = true
enable_log_file_validation = true
log_retention_days        = 30
audit_log_retention_days  = 90
enable_gdpr_controls      = true
enable_soc2_monitoring    = true
```

### Development Environment

```hcl
environment                = "development"
cloudtrail_enabled        = false  # Can be disabled to save costs
enable_log_file_validation = true
log_retention_days        = 7
audit_log_retention_days  = 30
```

## Compliance Frameworks

### GDPR (General Data Protection Regulation)

**Coverage**: Personal data of EU residents

**Implemented Controls**:
- Article 15: Right to access (data export endpoint)
- Article 16: Right to rectification (profile updates)
- Article 17: Right to erasure (account deletion)
- Article 18: Right to restrict processing
- Article 20: Right to data portability (JSON/CSV export)
- Article 21: Right to object (opt-out mechanisms)

**Evidence**:
- Audit logs (retained 365+ days)
- Data processing agreements
- Privacy notices
- Consent records

### SOC 2 Type II

**Audit Period**: 12-month rolling

**Trust Service Criteria**:
- CC6: Logical access control
- CC7: System monitoring
- CC8: Change management
- CC9: Risk mitigation

**Evidence Collected**:
- CloudTrail logs (365 days)
- Access control reviews
- Change management records
- Incident response documentation
- Security training records

### ISO 27001

**Scope**: Information security management

**Key Controls**:
- Asset management
- Access control
- Cryptography
- Incident management
- Continuity management

**Status**: Framework ready, external audit optional

## Monitoring & Alerts

### CloudWatch Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| Unauthorized API Calls | 1+ per 5 min | Email notification |
| Policy Changes | 1+ per 5 min | Email notification |
| CloudTrail Changes | 1+ per 5 min | **Critical alert** |
| Root Account Usage | 1+ per 5 min | **Critical alert** |
| MFA Disabled | 1+ per 5 min | **Critical alert** |

### Notification Channels

- **Email**: Primary notification channel
- **Slack**: Optional real-time alerts (via webhook)
- **SNS**: Topic-based routing for integration with SIEM

### Log Analysis

CloudWatch Logs Insights queries for common investigations:

```sql
-- Failed login attempts
fields @timestamp, userIdentity.userName, sourceIPAddress
| filter eventName = 'ConsoleLogin' and errorCode = 'AuthFailure'
| stats count() as failures by sourceIPAddress

-- Data access audit
fields @timestamp, eventName, requestParameters.bucketName
| filter eventSource = 's3.amazonaws.com'
| filter eventName in ['GetObject', 'PutObject', 'DeleteObject']
| stats count() by eventName

-- Root account usage
fields @timestamp, userIdentity.userName, eventName
| filter userIdentity.type = 'Root'
| filter eventType != 'AwsServiceEvent'

-- Policy changes
fields @timestamp, eventName, userIdentity.principalId
| filter eventName like /[Pp]olicy/
| sort @timestamp desc
```

See [COMPLIANCE_AUDIT.md](../../docs/COMPLIANCE_AUDIT.md) for additional queries.

## Cost Estimation

### Monthly Costs (Typical)

| Service | Usage | Cost |
|---------|-------|------|
| CloudTrail | 100GB logs | $20 |
| CloudWatch Logs | 100GB ingested | $50 |
| S3 Standard | 100GB | $2.30 |
| S3 Glacier | 1TB archive | $4.00 |
| KMS | 1 key + ops | $2.00 |
| SNS | 100 notifications | <$1.00 |
| **Total** | | **~$79/month** |

### Cost Optimization

- S3 Intelligent-Tiering: Automatic tier transitions
- Lifecycle policies: Automatic deletion after retention
- Log filtering: Only log necessary events
- Glacier Deep Archive: For long-term storage (<$1/TB/month)

## Security Best Practices

1. **Encryption**
   - All data encrypted at rest (AES-256 KMS)
   - All data encrypted in transit (TLS 1.2+)
   - Automatic key rotation (yearly)

2. **Access Control**
   - S3 bucket policies restrict access
   - IAM roles follow least privilege
   - MFA required for sensitive operations
   - All access logged in CloudTrail

3. **Audit Integrity**
   - CloudTrail log file validation enabled
   - S3 Object Lock (WORM) prevents deletion
   - Versioning enabled for recovery
   - Immutable audit trail

4. **Retention & Deletion**
   - Automatic lifecycle transitions
   - Soft + hard anonymization on deletion
   - 30-day grace period for recovery
   - Permanent deletion after retention

## Maintenance Schedule

### Daily
- Monitor CloudWatch alarms
- Check for security alerts

### Weekly
- Review CloudWatch dashboard
- Verify CloudTrail is logging

### Monthly
- Generate compliance report
- Review failed login attempts
- Check policy changes

### Quarterly
- Access control review
- Disaster recovery test
- Backup validation

### Annual
- SOC 2 Type II audit
- Penetration testing
- Compliance framework review
- Policy updates

## Troubleshooting

### CloudTrail Not Logging

```bash
# Check status
aws cloudtrail get-trail-status --name TheBot-production-trail

# Start logging if stopped
aws cloudtrail start-logging --name TheBot-production-trail
```

### Slow Log Queries

```bash
# Filter early, aggregate late
| filter field = "value"  # Filter first
| stats count() by field  # Then aggregate

# Use recent data
--start-time $(($(date -d '7 days ago' +%s) * 1000))  # Last 7 days

# Limit fields
fields @timestamp, eventName, sourceIPAddress
```

### High Costs

```bash
# Reduce retention
log_retention_days = 30

# Move to Glacier sooner
glacier_transition_days = 15

# Filter unnecessary events
# Disable data event logging for non-critical resources
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed troubleshooting.

## Documentation

### Main References

- **[COMPLIANCE_AUDIT.md](../../docs/COMPLIANCE_AUDIT.md)**
  - Complete compliance framework overview
  - GDPR requirements and implementation
  - SOC 2 Type II controls
  - Incident response procedures
  - FAQ and glossary

- **[DEPLOYMENT.md](./DEPLOYMENT.md)**
  - Step-by-step deployment instructions
  - Configuration and setup
  - Monitoring and maintenance
  - Troubleshooting guide
  - Cost optimization strategies

### Supporting Documents

- **data-retention-policy.json**
  - Detailed retention schedules
  - Deletion procedures
  - Anonymization techniques
  - Compliance exceptions

- **audit-config.json**
  - CloudTrail configuration
  - Event logging setup
  - Monitoring rules
  - Notification channels

## API Integration

### GDPR Data Export

```bash
POST /api/gdpr/data-export
Authorization: Bearer <token>
Content-Type: application/json

Response:
{
  "status": "processing",
  "download_url": "https://...",
  "expires_at": "2025-01-27T10:00:00Z",
  "estimated_size_mb": 42
}
```

### Account Deletion

```bash
DELETE /api/gdpr/account
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "User requested",
  "confirm": true
}

Response:
{
  "status": "pending_deletion",
  "deletion_date": "2025-01-26T10:00:00Z",
  "grace_period_expires": "2025-01-26T10:00:00Z"
}
```

See [API_ENDPOINTS.md](../../docs/API_ENDPOINTS.md) for complete endpoint reference.

## Contributing

To modify this infrastructure:

1. Create feature branch: `git checkout -b feature/compliance-enhancement`
2. Update Terraform files
3. Test in staging: `terraform plan`
4. Review changes: `terraform show tfplan`
5. Submit PR with documentation
6. Require 2 approvals before merge
7. Deploy to production with change management approval

## Support

### Internal Resources

- **Security Team**: security@thebot.com
- **Compliance Officer**: compliance@thebot.com
- **DevOps Team**: devops@thebot.com

### External Resources

- [AWS CloudTrail Documentation](https://docs.aws.amazon.com/awscloudtrail/)
- [GDPR Official Text](https://gdpr-info.eu/)
- [SOC 2 Trust Service Criteria](https://www.aicpa.org/research/topics/audit-assurance/aicpatrustservices)
- [AWS Security Best Practices](https://docs.aws.amazon.com/security/)

## License

This infrastructure is part of THE_BOT Platform and is subject to the same license terms.

---

**Status**: Production Ready
**Last Updated**: December 27, 2025
**Maintenance**: DevOps Team

For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)
For compliance details, see [../../docs/COMPLIANCE_AUDIT.md](../../docs/COMPLIANCE_AUDIT.md)
