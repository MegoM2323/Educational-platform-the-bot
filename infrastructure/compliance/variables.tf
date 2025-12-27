# =============================================================================
# Variables for Compliance Controls Infrastructure
# =============================================================================

variable "aws_region" {
  description = "AWS region for compliance resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "organization_id" {
  description = "AWS Organization ID for multi-account setup"
  type        = string
  default     = ""
}

variable "cloudtrail_enabled" {
  description = "Enable CloudTrail for audit logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days (SOC 2 minimum: 90)"
  type        = number
  default     = 90

  validation {
    condition     = var.log_retention_days >= 30
    error_message = "Log retention must be at least 30 days for compliance."
  }
}

variable "audit_log_retention_days" {
  description = "S3 audit log retention period in days (GDPR minimum: 90)"
  type        = number
  default     = 365

  validation {
    condition     = var.audit_log_retention_days >= 90
    error_message = "Audit log retention must be at least 90 days for GDPR compliance."
  }
}

variable "enable_gdpr_controls" {
  description = "Enable GDPR compliance controls and procedures"
  type        = bool
  default     = true
}

variable "enable_soc2_monitoring" {
  description = "Enable SOC 2 Type II monitoring and evidence collection"
  type        = bool
  default     = true
}

variable "enable_log_file_validation" {
  description = "Enable CloudTrail log file validation (SHA-256 hash chain)"
  type        = bool
  default     = true
}

variable "kms_key_rotation_enabled" {
  description = "Enable automatic KMS key rotation (annual)"
  type        = bool
  default     = true
}

variable "mfa_delete_enabled" {
  description = "Enable MFA delete protection on S3 audit logs"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email address for compliance and security alerts"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.notification_email))
    error_message = "Must be a valid email address."
  }
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for real-time compliance notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "enable_lambda_data_logging" {
  description = "Enable logging of Lambda function data access"
  type        = bool
  default     = true
}

variable "enable_rds_audit_logging" {
  description = "Enable RDS database audit logging"
  type        = bool
  default     = true
}

variable "enable_s3_access_logging" {
  description = "Enable S3 bucket access logging"
  type        = bool
  default     = true
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs for network traffic monitoring"
  type        = bool
  default     = true
}

variable "cloudwatch_alarm_threshold" {
  description = "Number of events to trigger CloudWatch alarm"
  type        = number
  default     = 1

  validation {
    condition     = var.cloudwatch_alarm_threshold >= 1
    error_message = "Threshold must be at least 1."
  }
}

variable "create_compliance_dashboard" {
  description = "Create CloudWatch dashboard for compliance monitoring"
  type        = bool
  default     = true
}

variable "enable_eventbridge_integration" {
  description = "Enable EventBridge for advanced event routing"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default = {
    Compliance = "GDPR_SOC2_ISO27001"
    Scope      = "Production"
    Terraform  = "true"
  }
}

# =============================================================================
# Configuration Variables
# =============================================================================

variable "config_rules_enabled" {
  description = "Enable AWS Config rules for compliance checking"
  type        = bool
  default     = true
}

variable "config_rules_evaluation_frequency" {
  description = "Evaluation frequency for Config rules (One_Hour, Three_Hours, Six_Hours, Twelve_Hours, TwentyFour_Hours)"
  type        = string
  default     = "TwentyFour_Hours"

  validation {
    condition = contains([
      "One_Hour",
      "Three_Hours",
      "Six_Hours",
      "Twelve_Hours",
      "TwentyFour_Hours"
    ], var.config_rules_evaluation_frequency)
    error_message = "Invalid evaluation frequency."
  }
}

variable "enable_security_hub" {
  description = "Enable AWS Security Hub for centralized security findings"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty for threat detection"
  type        = bool
  default     = true
}

# =============================================================================
# Retention & Deletion Variables
# =============================================================================

variable "user_data_retention_days" {
  description = "Days to retain active user data"
  type        = number
  default     = 2555  # 7 years

  validation {
    condition     = var.user_data_retention_days >= 365
    error_message = "User data retention must be at least 1 year."
  }
}

variable "deleted_user_data_retention_days" {
  description = "Days to retain deleted user data before hard deletion"
  type        = number
  default     = 90

  validation {
    condition     = var.deleted_user_data_retention_days >= 30
    error_message = "Deleted user data retention must be at least 30 days."
  }
}

variable "backup_retention_days" {
  description = "Days to retain database backups"
  type        = number
  default     = 90

  validation {
    condition     = var.backup_retention_days >= 7
    error_message = "Backup retention must be at least 7 days."
  }
}

variable "payment_record_retention_days" {
  description = "Days to retain payment records (tax requirement: 7 years)"
  type        = number
  default     = 2555

  validation {
    condition     = var.payment_record_retention_days >= 2555
    error_message = "Payment record retention must be at least 7 years per tax law."
  }
}

# =============================================================================
# Notification Variables
# =============================================================================

variable "alert_critical_email" {
  description = "Email for critical security alerts (escalation)"
  type        = string
  default     = ""

  validation {
    condition     = var.alert_critical_email == "" || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_critical_email))
    error_message = "Must be a valid email address or empty."
  }
}

variable "alert_slack_channel" {
  description = "Slack channel for critical alerts (default: #compliance-alerts)"
  type        = string
  default     = "#compliance-alerts"
}

variable "enable_sns_notifications" {
  description = "Enable SNS notifications for compliance events"
  type        = bool
  default     = true
}

variable "enable_eventbridge_notifications" {
  description = "Enable EventBridge for advanced event routing to multiple targets"
  type        = bool
  default     = true
}

# =============================================================================
# Compliance Framework Variables
# =============================================================================

variable "target_compliance_frameworks" {
  description = "Target compliance frameworks (GDPR, SOC2, ISO27001, HIPAA, CCPA)"
  type        = list(string)
  default     = ["GDPR", "SOC2_TYPE_II", "ISO_27001"]

  validation {
    condition = alltrue([
      for framework in var.target_compliance_frameworks :
      contains(["GDPR", "SOC2_TYPE_II", "ISO_27001", "HIPAA", "CCPA"], framework)
    ])
    error_message = "Invalid compliance framework. Must be one of: GDPR, SOC2_TYPE_II, ISO_27001, HIPAA, CCPA."
  }
}

variable "audit_frequency" {
  description = "Frequency of compliance audits (weekly, monthly, quarterly, annual)"
  type        = string
  default     = "monthly"

  validation {
    condition     = contains(["weekly", "monthly", "quarterly", "annual"], var.audit_frequency)
    error_message = "Must be one of: weekly, monthly, quarterly, annual."
  }
}

variable "evidence_collection_enabled" {
  description = "Enable automatic evidence collection for SOC 2 audits"
  type        = bool
  default     = true
}

variable "evidence_collection_frequency" {
  description = "Frequency of evidence collection (daily, weekly, monthly)"
  type        = string
  default     = "monthly"

  validation {
    condition     = contains(["daily", "weekly", "monthly"], var.evidence_collection_frequency)
    error_message = "Must be one of: daily, weekly, monthly."
  }
}

# =============================================================================
# Cost Optimization Variables
# =============================================================================

variable "enable_cost_optimization" {
  description = "Enable cost optimization (use cheaper storage tiers)"
  type        = bool
  default     = true
}

variable "glacier_transition_days" {
  description = "Days before transitioning to Glacier for cost optimization"
  type        = number
  default     = 30

  validation {
    condition     = var.glacier_transition_days >= 1 && var.glacier_transition_days <= 365
    error_message = "Must be between 1 and 365 days."
  }
}

variable "glacier_deep_archive_days" {
  description = "Days before transitioning to Glacier Deep Archive"
  type        = number
  default     = 90

  validation {
    condition     = var.glacier_deep_archive_days > var.glacier_transition_days
    error_message = "Deep Archive days must be greater than Glacier days."
  }
}

# =============================================================================
# Advanced Configuration Variables
# =============================================================================

variable "insight_events_enabled" {
  description = "Enable CloudTrail Insights for anomaly detection"
  type        = bool
  default     = true
}

variable "multi_account_monitoring" {
  description = "Enable monitoring of multiple AWS accounts (organization trail)"
  type        = bool
  default     = false
}

variable "enable_advanced_threat_protection" {
  description = "Enable advanced threat protection (additional cost)"
  type        = bool
  default     = false
}

variable "log_encryption_algorithm" {
  description = "Encryption algorithm for logs (AES-256 recommended)"
  type        = string
  default     = "aws:kms"

  validation {
    condition     = contains(["AES256", "aws:kms"], var.log_encryption_algorithm)
    error_message = "Must be either AES256 or aws:kms."
  }
}

variable "enable_bucket_versioning" {
  description = "Enable versioning on S3 audit bucket (required for integrity)"
  type        = bool
  default     = true
}

variable "enable_object_lock" {
  description = "Enable S3 Object Lock for WORM (Write Once Read Many) protection"
  type        = bool
  default     = true
}

variable "object_lock_mode" {
  description = "S3 Object Lock mode (GOVERNANCE or COMPLIANCE)"
  type        = string
  default     = "GOVERNANCE"

  validation {
    condition     = contains(["GOVERNANCE", "COMPLIANCE"], var.object_lock_mode)
    error_message = "Must be either GOVERNANCE or COMPLIANCE."
  }
}

variable "object_lock_retention_days" {
  description = "Days to retain objects in Object Lock"
  type        = number
  default     = 365

  validation {
    condition     = var.object_lock_retention_days >= 30
    error_message = "Retention must be at least 30 days."
  }
}

# =============================================================================
# Integration Variables
# =============================================================================

variable "integration_targets" {
  description = "External services to integrate with (e.g., SIEM, ticketing)"
  type        = map(string)
  default     = {}

  # Example:
  # {
  #   "splunk"    = "https://splunk.company.com:8088/services/collector"
  #   "datadog"   = "https://http-intake.logs.datadoghq.com/v1/input"
  #   "jira"      = "https://company.atlassian.net/rest/api/3/issue"
  # }
}

variable "custom_tags" {
  description = "Custom tags for resource identification and cost allocation"
  type        = map(string)
  default     = {}
}

# =============================================================================
# Feature Flags
# =============================================================================

variable "enable_experimental_features" {
  description = "Enable experimental compliance features (not production-ready)"
  type        = bool
  default     = false
}

variable "debug_mode" {
  description = "Enable debug logging (increases costs)"
  type        = bool
  default     = false
}

variable "verbose_logging" {
  description = "Enable verbose logging for troubleshooting"
  type        = bool
  default     = false
}
