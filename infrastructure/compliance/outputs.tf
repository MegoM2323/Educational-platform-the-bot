# =============================================================================
# Outputs for Compliance Controls Infrastructure
# =============================================================================
# These outputs provide important information about the deployed
# compliance infrastructure and can be used by other Terraform modules
# or exported for documentation purposes.
# =============================================================================

# =============================================================================
# S3 Audit Bucket Outputs
# =============================================================================

output "audit_bucket_name" {
  description = "Name of the S3 bucket for audit logs storage"
  value       = aws_s3_bucket.audit_logs.id
}

output "audit_bucket_arn" {
  description = "ARN of the S3 bucket for audit logs"
  value       = aws_s3_bucket.audit_logs.arn
}

output "audit_bucket_region" {
  description = "AWS region of the audit logs bucket"
  value       = aws_s3_bucket.audit_logs.region
}

output "audit_bucket_versioning_enabled" {
  description = "Whether versioning is enabled on audit bucket"
  value       = true
  depends_on  = [aws_s3_bucket_versioning.audit_logs]
}

output "audit_bucket_encryption_algorithm" {
  description = "Encryption algorithm used for audit logs"
  value       = "aws:kms"
}

output "audit_bucket_kms_key_id" {
  description = "KMS key ID used for encrypting audit logs in S3"
  value       = aws_kms_key.audit_logs.id
}

# =============================================================================
# CloudTrail Outputs
# =============================================================================

output "cloudtrail_name" {
  description = "Name of the CloudTrail trail"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].name : null
}

output "cloudtrail_arn" {
  description = "ARN of the CloudTrail trail"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].arn : null
}

output "cloudtrail_s3_bucket_name" {
  description = "S3 bucket where CloudTrail logs are stored"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].s3_bucket_name : null
}

output "cloudtrail_log_file_validation_enabled" {
  description = "Whether CloudTrail log file validation is enabled"
  value       = var.enable_log_file_validation
}

output "cloudtrail_multi_region_enabled" {
  description = "Whether CloudTrail covers all regions"
  value       = var.cloudtrail_enabled ? aws_cloudtrail.main[0].is_multi_region_trail : null
}

output "cloudtrail_cloudwatch_logs_group_arn" {
  description = "ARN of CloudWatch Logs group for CloudTrail logs"
  value       = var.cloudtrail_enabled ? aws_cloudwatch_log_group.cloudtrail.arn : null
}

# =============================================================================
# CloudWatch Logs Outputs
# =============================================================================

output "cloudwatch_logs_group_name" {
  description = "Name of the main CloudWatch Logs group for compliance"
  value       = aws_cloudwatch_log_group.compliance.name
}

output "cloudwatch_logs_group_arn" {
  description = "ARN of the main CloudWatch Logs group for compliance"
  value       = aws_cloudwatch_log_group.compliance.arn
}

output "cloudwatch_logs_retention_days" {
  description = "Log retention period in CloudWatch Logs (days)"
  value       = var.log_retention_days
}

output "cloudwatch_logs_kms_key_arn" {
  description = "KMS key ARN used for CloudWatch Logs encryption"
  value       = aws_kms_key.audit_logs.arn
}

output "cloudwatch_logs_cloudtrail_group" {
  description = "CloudWatch Logs group for CloudTrail events"
  value       = aws_cloudwatch_log_group.cloudtrail.name
}

# =============================================================================
# KMS Key Outputs
# =============================================================================

output "kms_key_id" {
  description = "ID of the KMS key used for encrypting audit logs"
  value       = aws_kms_key.audit_logs.id
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encrypting audit logs"
  value       = aws_kms_key.audit_logs.arn
}

output "kms_key_alias" {
  description = "Alias of the KMS key"
  value       = aws_kms_alias.audit_logs.name
}

output "kms_key_rotation_enabled" {
  description = "Whether automatic key rotation is enabled"
  value       = var.kms_key_rotation_enabled
}

output "kms_key_rotation_period_days" {
  description = "KMS key rotation period in days"
  value       = 365
}

# =============================================================================
# SNS Topic Outputs
# =============================================================================

output "sns_topic_arn" {
  description = "ARN of the SNS topic for compliance and security alerts"
  value       = aws_sns_topic.compliance_alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic for compliance alerts"
  value       = aws_sns_topic.compliance_alerts.name
}

output "sns_subscribers" {
  description = "List of SNS topic subscribers"
  value = {
    email = var.notification_email
  }
}

# =============================================================================
# CloudWatch Alarms Outputs
# =============================================================================

output "cloudwatch_alarms" {
  description = "List of created CloudWatch alarms for compliance monitoring"
  value = {
    unauthorized_api_calls = aws_cloudwatch_metric_alarm.unauthorized_api_calls.alarm_name
    policy_changes         = aws_cloudwatch_metric_alarm.policy_changes.alarm_name
    cloudtrail_changes     = aws_cloudwatch_metric_alarm.cloudtrail_changes.alarm_name
    root_account_usage     = aws_cloudwatch_metric_alarm.root_account_usage.alarm_name
    mfa_disabled           = aws_cloudwatch_metric_alarm.mfa_disabled.alarm_name
  }
}

output "cloudwatch_metric_filters" {
  description = "List of CloudWatch Log metric filters for compliance"
  value = {
    unauthorized_api_calls = var.cloudtrail_enabled ? aws_cloudwatch_log_group_metric_filter.unauthorized_api_calls[0].name : null
    policy_changes         = var.cloudtrail_enabled ? aws_cloudwatch_log_group_metric_filter.policy_changes[0].name : null
    cloudtrail_changes     = var.cloudtrail_enabled ? aws_cloudwatch_log_group_metric_filter.cloudtrail_changes[0].name : null
    root_account_usage     = var.cloudtrail_enabled ? aws_cloudwatch_log_group_metric_filter.root_account_usage[0].name : null
    mfa_disabled           = var.cloudtrail_enabled ? aws_cloudwatch_log_group_metric_filter.mfa_disabled[0].name : null
  }
}

# =============================================================================
# AWS Config Outputs
# =============================================================================

output "config_aggregator_arn" {
  description = "ARN of the AWS Config aggregator"
  value       = aws_config_configuration_aggregator.organization.arn
}

output "config_rules" {
  description = "List of AWS Config rules for compliance checking"
  value = {
    cloudtrail_enabled           = aws_config_config_rule.cloudtrail_enabled.name
    cloudtrail_cloudwatch_logs   = aws_config_config_rule.cloudtrail_cloudwatch_logs.name
    cloudtrail_encryption        = aws_config_config_rule.cloudtrail_encryption.name
    root_account_mfa             = aws_config_config_rule.root_account_mfa.name
    s3_versioning                = aws_config_config_rule.s3_versioning.name
    s3_encryption                = aws_config_config_rule.s3_encryption.name
    vpc_flow_logs                = aws_config_config_rule.vpc_flow_logs.name
  }
}

# =============================================================================
# Compliance Configuration Outputs
# =============================================================================

output "compliance_summary" {
  description = "Summary of all compliance controls enabled"
  value = {
    cloudtrail_enabled              = var.cloudtrail_enabled
    log_file_validation_enabled     = var.enable_log_file_validation
    kms_encryption_enabled          = true
    multi_region_trail              = var.cloudtrail_enabled
    cloudwatch_logs_enabled         = true
    s3_versioning_enabled           = true
    s3_encryption_enabled           = true
    s3_public_access_blocked        = true
    s3_mfa_delete_enabled           = var.mfa_delete_enabled
    gdpr_controls_enabled           = var.enable_gdpr_controls
    soc2_monitoring_enabled         = var.enable_soc2_monitoring
    config_rules_enabled            = true
    log_retention_days              = var.log_retention_days
    audit_log_retention_days        = var.audit_log_retention_days
    kms_key_rotation_enabled        = var.kms_key_rotation_enabled
  }
}

output "retention_policy_summary" {
  description = "Summary of data retention policies"
  value = {
    cloudtrail_logs         = "${var.log_retention_days} days (CloudWatch) + ${var.audit_log_retention_days} days (S3)"
    audit_logs              = "${var.audit_log_retention_days} days"
    user_data               = "${var.user_data_retention_days} days"
    deleted_user_data       = "${var.deleted_user_data_retention_days} days (before hard deletion)"
    payment_records         = "${var.payment_record_retention_days} days"
    backup_data             = "${var.backup_retention_days} days"
  }
}

output "compliance_frameworks" {
  description = "List of compliance frameworks configured"
  value = {
    gdpr_compliant          = var.enable_gdpr_controls
    soc2_type_ii_compliant  = var.enable_soc2_monitoring
    cloudtrail_enabled      = var.cloudtrail_enabled
    audit_trail_retention   = "${var.audit_log_retention_days} days"
  }
}

# =============================================================================
# Security Controls Summary
# =============================================================================

output "security_controls_summary" {
  description = "Summary of security controls implemented"
  value = {
    encryption_at_rest      = "AES-256 KMS"
    encryption_in_transit   = "TLS 1.2+"
    log_validation          = var.enable_log_file_validation ? "SHA-256 hash chain" : "disabled"
    access_control          = "IAM + S3 bucket policy"
    mfa_delete              = var.mfa_delete_enabled ? "enabled" : "disabled"
    public_access_blocked   = true
    versioning_enabled      = true
    immutability            = "S3 Object Lock (WORM)"
  }
}

# =============================================================================
# Monitoring & Alerting Summary
# =============================================================================

output "monitoring_summary" {
  description = "Summary of monitoring and alerting configuration"
  value = {
    cloudwatch_alarms_count = 5
    log_metric_filters_count = 5
    sns_notifications       = true
    email_recipient         = var.notification_email
    slack_integration       = var.slack_webhook_url != "" ? "enabled" : "disabled"
    real_time_monitoring    = "CloudWatch Logs + Metric Filters"
    dashboard_created       = true
  }
}

# =============================================================================
# Access & Documentation
# =============================================================================

output "documentation_links" {
  description = "Links to compliance documentation"
  value = {
    compliance_guide          = "docs/COMPLIANCE_AUDIT.md"
    data_retention_policy     = "infrastructure/compliance/data-retention-policy.json"
    audit_configuration       = "infrastructure/compliance/audit-config.json"
    terraform_configuration   = "infrastructure/compliance/compliance-controls.tf"
  }
}

output "log_access_information" {
  description = "Information on how to access and query logs"
  value = {
    cloudtrail_bucket       = aws_s3_bucket.audit_logs.id
    cloudwatch_logs_group   = aws_cloudwatch_log_group.compliance.name
    query_tool              = "AWS CloudWatch Logs Insights"
    archives_location       = "S3 Glacier (${var.glacier_transition_days} days after creation)"
    retention_period        = "${var.audit_log_retention_days} days"
  }
}

output "incident_response_contacts" {
  description = "Contacts for incident response and escalation"
  value = {
    security_email          = var.notification_email
    critical_escalation     = var.alert_critical_email != "" ? var.alert_critical_email : "not configured"
    slack_channel           = var.slack_webhook_url != "" ? var.alert_slack_channel : "not configured"
  }
}

# =============================================================================
# Infrastructure Details for Management
# =============================================================================

output "aws_account_id" {
  description = "AWS Account ID where compliance infrastructure is deployed"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS region where compliance infrastructure is deployed"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name (production, staging, development)"
  value       = var.environment
}

output "resource_tags" {
  description = "Common tags applied to all resources"
  value = {
    Environment = var.environment
    Project     = "THE_BOT_Platform"
    Compliance  = "GDPR_SOC2"
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# Cost Estimation Information
# =============================================================================

output "estimated_monthly_cost_information" {
  description = "Information for cost estimation"
  value = {
    note                    = "Actual costs depend on AWS pricing and usage"
    primary_cost_drivers    = ["S3 storage", "CloudWatch Logs ingestion", "KMS key operations"]
    storage_optimization    = "Automatic transition to Glacier after ${var.glacier_transition_days} days reduces costs"
    retention_setting       = "${var.audit_log_retention_days} days total retention"
    log_volume_factor       = "Based on your AWS API call volume"
  }
}

# =============================================================================
# Deployment Information
# =============================================================================

output "deployment_info" {
  description = "Information about this Terraform deployment"
  value = {
    terraform_version       = "1.0+"
    provider_version        = "AWS 5.0+"
    backend_type            = "S3"
    state_file_bucket       = "thebot-terraform-state"
    deployment_timestamp    = timestamp()
  }
}
