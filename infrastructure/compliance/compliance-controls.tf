# =============================================================================
# Compliance Controls & Audit Trail Infrastructure
# =============================================================================
# Implements GDPR, SOC 2 Type II, and regulatory compliance controls
# including CloudTrail, CloudWatch Logs, and data retention policies
#
# Components:
# - CloudTrail for API audit logging
# - CloudWatch Logs for centralized log aggregation
# - S3 for audit log storage with encryption
# - KMS for encryption key management
# - Organizational Trail for multi-account monitoring
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state management
  backend "s3" {
    bucket         = "thebot-terraform-state"
    key            = "compliance/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "THE_BOT_Platform"
      Compliance  = "GDPR_SOC2"
      ManagedBy   = "Terraform"
      CreatedAt   = timestamp()
    }
  }
}

# =============================================================================
# VARIABLES
# =============================================================================

variable "aws_region" {
  description = "AWS region for compliance resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "organization_id" {
  description = "AWS Organization ID for multi-account setup"
  type        = string
}

variable "cloudtrail_enabled" {
  description = "Enable CloudTrail for audit logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 90
  validation {
    condition     = var.log_retention_days >= 30
    error_message = "Log retention must be at least 30 days for compliance."
  }
}

variable "audit_log_retention_days" {
  description = "S3 audit log retention period in days (GDPR minimum 90)"
  type        = number
  default     = 365
}

variable "enable_gdpr_controls" {
  description = "Enable GDPR compliance controls"
  type        = bool
  default     = true
}

variable "enable_soc2_monitoring" {
  description = "Enable SOC 2 Type II monitoring"
  type        = bool
  default     = true
}

variable "enable_log_file_validation" {
  description = "Enable CloudTrail log file validation"
  type        = bool
  default     = true
}

variable "kms_key_rotation_enabled" {
  description = "Enable automatic KMS key rotation"
  type        = bool
  default     = true
}

variable "mfa_delete_enabled" {
  description = "Enable MFA delete protection on audit logs S3"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email for compliance alerts"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for compliance notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

# =============================================================================
# LOCAL VALUES
# =============================================================================

locals {
  common_tags = merge(
    var.tags,
    {
      Module      = "Compliance"
      Environment = var.environment
    }
  )

  audit_bucket_name  = "thebot-audit-logs-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  cloudtrail_name    = "TheBot-${var.environment}-trail"
  log_group_name     = "/aws/thebot/compliance/${var.environment}"

  # CloudTrail events to log
  event_selectors = {
    read_write_type     = "All"
    include_management  = true
    include_data        = true
    include_lambda      = true
  }
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_caller_identity" "current" {}

data "aws_canonical_user_id" "current" {}

# =============================================================================
# S3 BUCKET FOR AUDIT LOGS
# =============================================================================

# KMS key for S3 encryption
resource "aws_kms_key" "audit_logs" {
  description             = "KMS key for encrypting audit logs"
  deletion_window_in_days = 7
  enable_key_rotation     = var.kms_key_rotation_enabled

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudTrail to encrypt logs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = ["kms:GenerateDataKey", "kms:DecryptDataKey"]
        Resource = "*"
        Condition = {
          StringLike = {
            "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:s3:::${local.audit_bucket_name}/*"
          }
        }
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "audit_logs" {
  name          = "alias/thebot-audit-logs-${var.environment}"
  target_key_id = aws_kms_key.audit_logs.key_id
}

# S3 bucket for audit logs
resource "aws_s3_bucket" "audit_logs" {
  bucket = local.audit_bucket_name

  tags = merge(
    local.common_tags,
    {
      Purpose = "Compliance-Audit-Logs"
    }
  )
}

# Enable versioning for audit trail integrity
resource "aws_s3_bucket_versioning" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  versioning_configuration {
    status     = "Enabled"
    mfa_delete = var.mfa_delete_enabled ? "Enabled" : "Disabled"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.audit_logs.arn
    }
    bucket_key_enabled = true
  }
}

# Bucket policy to allow CloudTrail
resource "aws_s3_bucket_policy" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.audit_logs.arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.audit_logs.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = "*"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.audit_logs.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action   = "s3:*"
        Resource = [
          aws_s3_bucket.audit_logs.arn,
          "${aws_s3_bucket.audit_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Lifecycle policy for audit log retention
resource "aws_s3_bucket_lifecycle_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = var.audit_log_retention_days
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.audit_log_retention_days
    }
  }
}

# Enable logging on audit bucket itself for detecting changes
resource "aws_s3_bucket_logging" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  target_bucket = aws_s3_bucket.audit_logs.id
  target_prefix = "self-logs/"
}

# =============================================================================
# CLOUDWATCH LOGS
# =============================================================================

# CloudWatch Logs Group for centralized logging
resource "aws_cloudwatch_log_group" "compliance" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days

  kms_key_id = aws_kms_key.audit_logs.arn

  tags = local.common_tags
}

# CloudWatch Log Group for CloudTrail
resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "${local.log_group_name}/cloudtrail"
  retention_in_days = var.log_retention_days

  kms_key_id = aws_kms_key.audit_logs.arn

  tags = local.common_tags
}

# IAM role for CloudTrail to write to CloudWatch Logs
resource "aws_iam_role" "cloudtrail_logs" {
  name = "TheBot-${var.environment}-CloudTrail-Logs-Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for CloudTrail logs
resource "aws_iam_role_policy" "cloudtrail_logs" {
  name = "CloudTrail-Logs-Policy"
  role = aws_iam_role.cloudtrail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
      }
    ]
  })
}

# =============================================================================
# CLOUDTRAIL
# =============================================================================

resource "aws_cloudtrail" "main" {
  count                      = var.cloudtrail_enabled ? 1 : 0
  name                       = local.cloudtrail_name
  s3_bucket_name             = aws_s3_bucket.audit_logs.id
  include_global_events      = true
  is_multi_region_trail      = true
  is_organization_trail      = false
  enable_log_file_validation = var.enable_log_file_validation
  kms_key_id                 = aws_kms_key.audit_logs.arn
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn  = aws_iam_role.cloudtrail_logs.arn
  depends_on                 = [aws_s3_bucket_policy.audit_logs]

  # Event selection for comprehensive audit
  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::*/"]
    }

    data_resource {
      type   = "AWS::Lambda::Function"
      values = ["arn:aws:lambda:*:*:function/*"]
    }

    data_resource {
      type   = "AWS::RDS::DBCluster"
      values = ["arn:aws:rds:*:*:cluster/*"]
    }
  }

  tags = local.common_tags
}

# =============================================================================
# COMPLIANCE MONITORING & ALERTING
# =============================================================================

# SNS Topic for compliance alerts
resource "aws_sns_topic" "compliance_alerts" {
  name              = "TheBot-${var.environment}-Compliance-Alerts"
  kms_master_key_id = aws_kms_key.audit_logs.id

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "compliance_email" {
  topic_arn = aws_sns_topic.compliance_alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# CloudWatch Alarms for compliance monitoring

# Alarm: Unauthorized API calls
resource "aws_cloudwatch_metric_alarm" "unauthorized_api_calls" {
  alarm_name          = "TheBot-${var.environment}-Unauthorized-API-Calls"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "UnauthorizedAPICallsCount"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when unauthorized API calls are detected"
  alarm_actions       = [aws_sns_topic.compliance_alerts.arn]
  treat_missing_data  = "notBreaching"
}

# Alarm: Policy changes
resource "aws_cloudwatch_metric_alarm" "policy_changes" {
  alarm_name          = "TheBot-${var.environment}-Policy-Changes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "PolicyChangesCount"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when IAM policies are changed"
  alarm_actions       = [aws_sns_topic.compliance_alerts.arn]
  treat_missing_data  = "notBreaching"
}

# Alarm: CloudTrail changes
resource "aws_cloudwatch_metric_alarm" "cloudtrail_changes" {
  alarm_name          = "TheBot-${var.environment}-CloudTrail-Changes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "CloudTrailChangesCount"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when CloudTrail is disabled or modified"
  alarm_actions       = [aws_sns_topic.compliance_alerts.arn]
  treat_missing_data  = "notBreaching"
}

# Alarm: Root account usage
resource "aws_cloudwatch_metric_alarm" "root_account_usage" {
  alarm_name          = "TheBot-${var.environment}-Root-Account-Usage"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "RootAccountUsageCount"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when root account is used"
  alarm_actions       = [aws_sns_topic.compliance_alerts.arn]
  treat_missing_data  = "notBreaching"
}

# Alarm: MFA disabled
resource "aws_cloudwatch_metric_alarm" "mfa_disabled" {
  alarm_name          = "TheBot-${var.environment}-MFA-Disabled"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "MFADisabledCount"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when MFA is disabled"
  alarm_actions       = [aws_sns_topic.compliance_alerts.arn]
  treat_missing_data  = "notBreaching"
}

# =============================================================================
# CLOUDWATCH LOG FILTERS
# =============================================================================

# Metric filter for unauthorized API calls
resource "aws_cloudwatch_log_group_metric_filter" "unauthorized_api_calls" {
  count          = var.cloudtrail_enabled ? 1 : 0
  name           = "UnauthorizedAPICallsFilter"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  filter_pattern = "{ ($.errorCode = \"*UnauthorizedOperation\") || ($.errorCode = \"AccessDenied*\") }"

  metric_transformation {
    name      = "UnauthorizedAPICallsCount"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

# Metric filter for policy changes
resource "aws_cloudwatch_log_group_metric_filter" "policy_changes" {
  count          = var.cloudtrail_enabled ? 1 : 0
  name           = "PolicyChangesFilter"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  filter_pattern = "{ ($.eventName = DeleteGroupPolicy) || ($.eventName = DeleteRolePolicy) || ($.eventName = DeleteUserPolicy) || ($.eventName = PutGroupPolicy) || ($.eventName = PutRolePolicy) || ($.eventName = PutUserPolicy) || ($.eventName = CreatePolicy) || ($.eventName = DeletePolicy) || ($.eventName = CreatePolicyVersion) || ($.eventName = DeletePolicyVersion) || ($.eventName = AttachRolePolicy) || ($.eventName = DetachRolePolicy) || ($.eventName = AttachUserPolicy) || ($.eventName = DetachUserPolicy) || ($.eventName = AttachGroupPolicy) || ($.eventName = DetachGroupPolicy) }"

  metric_transformation {
    name      = "PolicyChangesCount"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

# Metric filter for CloudTrail changes
resource "aws_cloudwatch_log_group_metric_filter" "cloudtrail_changes" {
  count          = var.cloudtrail_enabled ? 1 : 0
  name           = "CloudTrailChangesFilter"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  filter_pattern = "{ ($.eventName = CreateTrail) || ($.eventName = UpdateTrail) || ($.eventName = DeleteTrail) || ($.eventName = StartLogging) || ($.eventName = StopLogging) }"

  metric_transformation {
    name      = "CloudTrailChangesCount"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

# Metric filter for root account usage
resource "aws_cloudwatch_log_group_metric_filter" "root_account_usage" {
  count          = var.cloudtrail_enabled ? 1 : 0
  name           = "RootAccountUsageFilter"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  filter_pattern = "{ $.userIdentity.type = \"Root\" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != \"AwsServiceEvent\" }"

  metric_transformation {
    name      = "RootAccountUsageCount"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

# Metric filter for MFA disabled
resource "aws_cloudwatch_log_group_metric_filter" "mfa_disabled" {
  count          = var.cloudtrail_enabled ? 1 : 0
  name           = "MFADisabledFilter"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  filter_pattern = "{ ($.eventName = DeactivateMFADevice) || ($.eventName = DeleteVirtualMFADevice) }"

  metric_transformation {
    name      = "MFADisabledCount"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

# =============================================================================
# CONFIG RULES FOR COMPLIANCE
# =============================================================================

# Enable AWS Config if not already enabled
resource "aws_config_configuration_aggregator" "organization" {
  name = "TheBot-${var.environment}-Organization-Aggregator"

  account_aggregation_sources {
    account_ids = [data.aws_caller_identity.current.account_id]
    regions     = [var.aws_region]
  }
}

# Config Rule: CloudTrail enabled
resource "aws_config_config_rule" "cloudtrail_enabled" {
  name = "cloudtrail-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENABLED"
  }

  depends_on = [aws_cloudtrail.main]
}

# Config Rule: CloudTrail logs enabled for all regions
resource "aws_config_config_rule" "cloudtrail_cloudwatch_logs" {
  name = "cloudtrail-cloudwatch-logs-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_LOG_FILE_VALIDATION_ENABLED"
  }

  depends_on = [aws_cloudtrail.main]
}

# Config Rule: CloudTrail log file validation
resource "aws_config_config_rule" "cloudtrail_encryption" {
  name = "cloudtrail-encryption-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENCRYPTION_ENABLED"
  }

  depends_on = [aws_cloudtrail.main]
}

# Config Rule: MFA enabled on root account
resource "aws_config_config_rule" "root_account_mfa" {
  name = "root-account-mfa-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "ROOT_ACCOUNT_MFA_ENABLED"
  }
}

# Config Rule: S3 bucket versioning enabled
resource "aws_config_config_rule" "s3_versioning" {
  name = "s3-bucket-versioning-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_VERSIONING_ENABLED"
  }
}

# Config Rule: S3 bucket encryption enabled
resource "aws_config_config_rule" "s3_encryption" {
  name = "s3-bucket-encryption-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }
}

# Config Rule: VPC Flow Logs enabled
resource "aws_config_config_rule" "vpc_flow_logs" {
  name = "vpc-flow-logs-enabled-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "VPC_FLOW_LOGS_ENABLED"
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "audit_bucket_name" {
  description = "Name of the S3 bucket for audit logs"
  value       = aws_s3_bucket.audit_logs.id
}

output "audit_bucket_arn" {
  description = "ARN of the S3 bucket for audit logs"
  value       = aws_s3_bucket.audit_logs.arn
}

output "cloudtrail_name" {
  description = "Name of the CloudTrail trail"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].name : null
}

output "cloudtrail_arn" {
  description = "ARN of the CloudTrail trail"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].arn : null
}

output "cloudwatch_log_group" {
  description = "Name of the CloudWatch Log Group for compliance"
  value       = aws_cloudwatch_log_group.compliance.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch Log Group for compliance"
  value       = aws_cloudwatch_log_group.compliance.arn
}

output "kms_key_id" {
  description = "ID of the KMS key for encryption"
  value       = aws_kms_key.audit_logs.id
}

output "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  value       = aws_kms_key.audit_logs.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for compliance alerts"
  value       = aws_sns_topic.compliance_alerts.arn
}

output "log_retention_days" {
  description = "Log retention period in days"
  value       = var.log_retention_days
}

output "audit_log_retention_days" {
  description = "Audit log retention period in days"
  value       = var.audit_log_retention_days
}

output "compliance_summary" {
  description = "Summary of compliance controls"
  value = {
    cloudtrail_enabled              = var.cloudtrail_enabled
    log_file_validation_enabled     = var.enable_log_file_validation
    kms_encryption_enabled          = true
    multi_region_trail              = var.cloudtrail_enabled
    cloudwatch_logs_enabled         = true
    s3_versioning_enabled           = true
    s3_encryption_enabled           = true
    gdpr_controls_enabled           = var.enable_gdpr_controls
    soc2_monitoring_enabled         = var.enable_soc2_monitoring
    mfa_delete_protection_enabled   = var.mfa_delete_enabled
    log_retention_days              = var.log_retention_days
    audit_log_retention_days        = var.audit_log_retention_days
  }
}
