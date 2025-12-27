# Budget Alerts and Cost Monitoring Terraform Configuration
#
# This module sets up AWS Budgets, SNS topics, and CloudWatch alarms
# for cost monitoring and anomaly detection across the infrastructure.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "thebot-platform"
}

variable "monthly_budget" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 5000
}

variable "alert_emails" {
  description = "Email addresses for budget alerts"
  type        = list(string)
  default     = []
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# SNS Topic for Budget Alerts
resource "aws_sns_topic" "budget_alerts" {
  name              = "${var.project_name}-budget-alerts"
  display_name      = "Budget Alerts - ${var.project_name}"
  kms_master_key_id = "alias/aws/sns"

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# SNS Topic for Critical Alerts (100% budget)
resource "aws_sns_topic" "budget_critical" {
  name              = "${var.project_name}-budget-critical"
  display_name      = "Budget Critical Alert - ${var.project_name}"
  kms_master_key_id = "alias/aws/sns"

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# SNS Subscriptions for Email Alerts
resource "aws_sns_topic_subscription" "budget_alerts_email" {
  for_each = toset(var.alert_emails)

  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_sns_topic_subscription" "critical_alerts_email" {
  for_each = toset(var.alert_emails)

  topic_arn = aws_sns_topic.budget_critical.arn
  protocol  = "email"
  endpoint  = each.value
}

# AWS Budget - Total Account Spend
resource "aws_budgets_budget" "monthly_total" {
  name              = "${var.project_name}-monthly-total"
  budget_type       = "MONTHLY"
  limit_unit        = "USD"
  limit_amount      = var.monthly_budget
  time_period_start = "2024-01-01_00:00"
  time_period_end   = "2087-12-31_23:59"

  cost_filter {
    name   = "Service"
    values = ["*"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# AWS Budget - EC2 Service Spend
resource "aws_budgets_budget" "ec2_monthly" {
  name              = "${var.project_name}-ec2-monthly"
  budget_type       = "MONTHLY"
  limit_unit        = "USD"
  limit_amount      = var.monthly_budget * 0.3  # 30% of total budget
  time_period_start = "2024-01-01_00:00"
  time_period_end   = "2087-12-31_23:59"

  cost_filter {
    name   = "Service"
    values = ["Amazon Elastic Compute Cloud - Compute"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    service     = "ec2"
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# AWS Budget - RDS Service Spend
resource "aws_budgets_budget" "rds_monthly" {
  name              = "${var.project_name}-rds-monthly"
  budget_type       = "MONTHLY"
  limit_unit        = "USD"
  limit_amount      = var.monthly_budget * 0.25  # 25% of total budget
  time_period_start = "2024-01-01_00:00"
  time_period_end   = "2087-12-31_23:59"

  cost_filter {
    name   = "Service"
    values = ["Amazon Relational Database Service"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    service     = "rds"
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# AWS Budget - Data Transfer Costs
resource "aws_budgets_budget" "data_transfer_monthly" {
  name              = "${var.project_name}-data-transfer-monthly"
  budget_type       = "MONTHLY"
  limit_unit        = "USD"
  limit_amount      = var.monthly_budget * 0.15  # 15% of total budget
  time_period_start = "2024-01-01_00:00"
  time_period_end   = "2087-12-31_23:59"

  cost_filter {
    name   = "Service"
    values = ["AWS Data Transfer"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    service     = "data-transfer"
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# AWS Budget - Development Environment
resource "aws_budgets_budget" "dev_environment" {
  name              = "${var.project_name}-dev-environment"
  budget_type       = "MONTHLY"
  limit_unit        = "USD"
  limit_amount      = var.monthly_budget * 0.1  # 10% of total budget
  time_period_start = "2024-01-01_00:00"
  time_period_end   = "2087-12-31_23:59"

  cost_filter {
    name   = "TagKeyValue"
    values = ["Environment$dev"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_alerts.arn
    treat_missing_data         = "non_zero"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_topic_arn     = aws_sns_topic.budget_critical.arn
    treat_missing_data         = "non_zero"
  }

  tags = {
    project     = var.project_name
    environment = "dev"
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# CloudWatch Alarm - Cost Anomaly Detection
resource "aws_ce_anomaly_monitor" "cost_anomaly" {
  display_name = "${var.project_name}-cost-anomaly-detector"
  monitor_type = "CUSTOM"
  monitor_dimension = "SERVICE"

  monitor_specification {
    dimensions {
      key           = "SERVICE"
      values        = ["*"]
    }
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# Cost Anomaly Alert
resource "aws_ce_anomaly_subscription" "cost_anomaly_alert" {
  display_name      = "${var.project_name}-cost-anomaly-alerts"
  monitor_arn       = aws_ce_anomaly_monitor.cost_anomaly.arn
  threshold         = 100  # Alert on $100+ anomalies
  frequency         = "DAILY"

  subscription_notification_method = "SNS"

  subscription_notification_target {
    address = aws_sns_topic.budget_alerts.arn
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# CloudWatch Metric Alarm - Budget 80% Threshold
resource "aws_cloudwatch_metric_alarm" "budget_warning" {
  alarm_name          = "${var.project_name}-budget-warning"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = var.monthly_budget * 0.8
  alarm_description   = "Alert when spending reaches 80% of monthly budget"
  alarm_actions       = [aws_sns_topic.budget_alerts.arn]
  treat_missing_data  = "notBreaching"

  # This would need a custom metric or use AWS Cost Explorer API
  # For now, we document the metric that should be used
  metric_name = "EstimatedCharges"
  namespace   = "AWS/Billing"
  period      = 300
  statistic   = "Maximum"

  dimensions = {
    Currency = "USD"
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# IAM Role for Cost Analysis Lambda (if used)
resource "aws_iam_role" "cost_analysis_role" {
  name = "${var.project_name}-cost-analysis-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    project     = var.project_name
    environment = var.environment
    cost_center = "infrastructure"
    owner       = "devops-team"
  }
}

# Policy for Cost Exploration
resource "aws_iam_role_policy" "cost_analysis_policy" {
  name = "${var.project_name}-cost-analysis-policy"
  role = aws_iam_role.cost_analysis_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast",
          "ce:GetAnomalyMonitors",
          "ce:GetAnomalySubscriptions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Outputs
output "budget_alerts_topic_arn" {
  description = "ARN of the budget alerts SNS topic"
  value       = aws_sns_topic.budget_alerts.arn
}

output "budget_critical_topic_arn" {
  description = "ARN of the critical budget alerts SNS topic"
  value       = aws_sns_topic.budget_critical.arn
}

output "cost_anomaly_monitor_arn" {
  description = "ARN of the cost anomaly monitor"
  value       = aws_ce_anomaly_monitor.cost_anomaly.arn
}

output "cost_analysis_role_arn" {
  description = "ARN of the cost analysis IAM role"
  value       = aws_iam_role.cost_analysis_role.arn
}
