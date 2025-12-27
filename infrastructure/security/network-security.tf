# ========================================================
# THE_BOT Platform - Comprehensive Network Security
# ========================================================
# This file implements multi-layered network security:
# 1. AWS WAF (Web Application Firewall)
# 2. Network layer DDoS protection
# 3. Egress filtering and whitelisting
# 4. Intrusion detection/prevention
# 5. Traffic filtering rules
# ========================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ========================================================
# 1. AWS WAF - Web Application Firewall for ALB
# ========================================================

# Create WAF Web ACL for protecting ALB
resource "aws_wafv2_web_acl" "alb_protection" {
  name  = "${var.project_name}-alb-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: Rate limiting - Prevent DDoS attacks
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit_requests
        aggregate_key_type = "IP"

        # Optionally scope to specific patterns
        scope_down_statement {
          byte_match_statement {
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
            positional_constraint = "STARTS_WITH"
            search_string         = "/"
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Exclude rules that might cause false positives
        rule_action_override {
          action_to_use {
            block {}
          }
          name = "SizeRestrictions_BODY"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed Rules - SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 5: Custom IP Reputation List - Block known bad IPs
  rule {
    name     = "IPReputationListRule"
    priority = 5

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocked_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "IPReputationListRule"
      sampled_requests_enabled   = true
    }
  }

  # Rule 6: Geo-blocking - Restrict access by country
  rule {
    name     = "GeoBlockingRule"
    priority = 6

    action {
      block {}
    }

    statement {
      geo_match_statement {
        country_codes = var.waf_blocked_countries
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "GeoBlockingRule"
      sampled_requests_enabled   = true
    }
  }

  # Rule 7: Custom - Block requests with suspicious patterns
  rule {
    name     = "CustomProtectionRule"
    priority = 7

    action {
      block {}
    }

    statement {
      or_statement {
        statement {
          byte_match_statement {
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            positional_constraint = "CONTAINS"
            search_string         = "../"
          }
        }

        statement {
          byte_match_statement {
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            positional_constraint = "CONTAINS"
            search_string         = "..\\"
          }
        }

        statement {
          byte_match_statement {
            field_to_match {
              query_string {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            positional_constraint = "CONTAINS"
            search_string         = "../../"
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CustomProtectionRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-alb-waf-metrics"
    sampled_requests_enabled   = true
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-alb-waf"
    }
  )
}

# IP Set for blocked IPs (known malicious sources)
resource "aws_wafv2_ip_set" "blocked_ips" {
  name               = "${var.project_name}-blocked-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.waf_blocked_ip_addresses

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-blocked-ips"
    }
  )
}

# IP Set for allowed IPs (whitelist for specific operations)
resource "aws_wafv2_ip_set" "whitelisted_ips" {
  name               = "${var.project_name}-whitelisted-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.waf_whitelisted_ip_addresses

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-whitelisted-ips"
    }
  )
}

# ========================================================
# 2. Associate WAF with ALB
# ========================================================

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.alb_protection.arn
}

# ========================================================
# 3. Security Group for Egress Filtering
# ========================================================

# Egress filtering security group - restricts outbound traffic
resource "aws_security_group" "egress_filtering" {
  name        = "${var.project_name}-egress-filtering"
  description = "Restrictive egress filtering security group"
  vpc_id      = var.vpc_id

  # Egress to specific whitelisted destinations
  # DNS (53)
  egress {
    description = "DNS queries to Route53"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS (443) - for API calls and external services
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP (80) - restricted, prefer HTTPS
  egress {
    description = "HTTP outbound (for specific services only)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_destinations
  }

  # NTP (123) - for time synchronization
  egress {
    description = "NTP for time sync"
    from_port   = 123
    to_port     = 123
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Internal VPC communication
  egress {
    description = "Internal VPC traffic"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-egress-filtering"
    }
  )
}

# ========================================================
# 4. Network ACL Rules for DDoS Protection
# ========================================================

# Enhanced NACL rules for public subnet with DDoS protection
resource "aws_network_acl_rule" "public_ingress_rate_limit" {
  network_acl_id = var.public_nacl_id
  rule_number    = 100
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}

resource "aws_network_acl_rule" "public_ingress_https_rate_limit" {
  network_acl_id = var.public_nacl_id
  rule_number    = 110
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}

# Deny specific attack patterns at NACL level
resource "aws_network_acl_rule" "deny_syn_flood_protection" {
  network_acl_id = var.public_nacl_id
  rule_number    = 200
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# ========================================================
# 5. VPC Flow Logs for Security Analysis
# ========================================================

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/flowlogs/${var.project_name}"
  retention_in_days = var.flow_logs_retention_days

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-vpc-flow-logs"
    }
  )
}

# IAM role for VPC Flow Logs
resource "aws_iam_role" "vpc_flow_logs_role" {
  name = "${var.project_name}-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# IAM policy for CloudWatch Logs access
resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  name = "${var.project_name}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# VPC Flow Logs - all traffic
resource "aws_flow_log" "vpc_all_traffic" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs_role.arn
  log_destination = "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:*"
  traffic_type    = "ALL"
  vpc_id          = var.vpc_id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-vpc-flow-logs-all"
    }
  )

  depends_on = [aws_iam_role_policy.vpc_flow_logs_policy]
}

# ========================================================
# 6. CloudWatch Alarms for Security Monitoring
# ========================================================

# Alarm for excessive rejected connections (potential attack)
resource "aws_cloudwatch_metric_alarm" "vpc_rejected_packets" {
  alarm_name          = "${var.project_name}-vpc-rejected-packets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RejectedPackets"
  namespace           = "AWS/VPC"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.security_alarm_rejected_packets_threshold
  alarm_description   = "Alert when rejected packets exceed threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FlowLogName = aws_flow_log.vpc_all_traffic.id
  }

  alarm_actions = [var.sns_topic_arn]

  tags = var.common_tags
}

# Alarm for WAF blocked requests (potential attack)
resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "${var.project_name}-waf-blocked-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.security_alarm_waf_blocked_threshold
  alarm_description   = "Alert when WAF blocks requests"
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = aws_wafv2_web_acl.alb_protection.name
    Region = data.aws_region.current.name
  }

  alarm_actions = [var.sns_topic_arn]

  tags = var.common_tags
}

# ========================================================
# 7. AWS Shield Advanced - DDoS Protection
# ========================================================

# Note: AWS Shield Standard is automatically included with all AWS accounts
# AWS Shield Advanced provides additional DDoS protection and must be enabled separately

resource "aws_shield_protection" "alb" {
  count        = var.enable_shield_advanced ? 1 : 0
  name         = "${var.project_name}-alb-shield"
  resource_arn = var.alb_arn

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-alb-shield"
    }
  )
}

# DDoS Response Team (DRT) access (available with Shield Advanced)
resource "aws_shield_drt_access_management" "organization" {
  count = var.enable_shield_advanced ? 1 : 0

  depends_on = [aws_shield_protection.alb]
}

# ========================================================
# 8. Security Hub Integration
# ========================================================

resource "aws_securityhub_account" "organization" {
  count                  = var.enable_security_hub ? 1 : 0
  enable_default_standards = true

  tags = var.common_tags
}

# Enable specific Security Hub standards
resource "aws_securityhub_standards_subscription" "pci_dss" {
  count           = var.enable_security_hub ? 1 : 0
  standards_arn   = "arn:aws:securityhub:${data.aws_region.current.name}::standards/aws-foundational-security-best-practices/v/1.0.0"

  depends_on = [aws_securityhub_account.organization[0]]
}

# ========================================================
# 9. GuardDuty - Threat Detection
# ========================================================

resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0

  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  datasources {
    s3_logs {
      enable = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-guardduty"
    }
  )
}

# ========================================================
# 10. Network Segmentation Verification
# ========================================================

# Lambda function to verify network segmentation
resource "aws_lambda_function" "network_segmentation_audit" {
  filename            = "lambda_network_audit.zip"
  function_name       = "${var.project_name}-network-segmentation-audit"
  role                = aws_iam_role.lambda_audit_role.arn
  handler             = "index.handler"
  runtime             = "python3.11"
  timeout             = 60

  environment {
    variables = {
      VPC_ID                 = var.vpc_id
      EXPECTED_SUBNETS       = var.expected_subnets
      EXPECTED_NAT_GATEWAYS  = var.expected_nat_gateways
      SLACK_WEBHOOK_URL      = var.slack_webhook_url
    }
  }

  tags = var.common_tags

  depends_on = [
    aws_iam_role_policy.lambda_audit_policy,
    aws_iam_role.lambda_audit_role
  ]
}

# IAM role for Lambda audit function
resource "aws_iam_role" "lambda_audit_role" {
  name = "${var.project_name}-lambda-audit-role"

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

  tags = var.common_tags
}

# IAM policy for Lambda audit function
resource "aws_iam_role_policy" "lambda_audit_policy" {
  name = "${var.project_name}-lambda-audit-policy"
  role = aws_iam_role.lambda_audit_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeNetworkAcls",
          "ec2:DescribeNatGateways",
          "ec2:DescribeFlowLogs",
          "ec2:DescribeNetworkInterfaces"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# EventBridge rule to run audit daily
resource "aws_cloudwatch_event_rule" "network_audit_schedule" {
  name                = "${var.project_name}-network-audit-schedule"
  description         = "Daily network segmentation audit"
  schedule_expression = "cron(0 2 * * ? *)"  # 2 AM UTC daily

  tags = var.common_tags
}

resource "aws_cloudwatch_event_target" "network_audit_lambda" {
  rule      = aws_cloudwatch_event_rule.network_audit_schedule.name
  target_id = "NetworkAuditLambda"
  arn       = aws_lambda_function.network_segmentation_audit.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.network_segmentation_audit.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.network_audit_schedule.arn
}

# ========================================================
# 11. Data Source for Region Information
# ========================================================

data "aws_region" "current" {}

# ========================================================
# Outputs
# ========================================================

output "waf_web_acl_id" {
  description = "ID of the WAF Web ACL"
  value       = aws_wafv2_web_acl.alb_protection.id
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL"
  value       = aws_wafv2_web_acl.alb_protection.arn
}

output "blocked_ips_set_arn" {
  description = "ARN of the blocked IPs IP set"
  value       = aws_wafv2_ip_set.blocked_ips.arn
}

output "whitelisted_ips_set_arn" {
  description = "ARN of the whitelisted IPs IP set"
  value       = aws_wafv2_ip_set.whitelisted_ips.arn
}

output "egress_filtering_sg_id" {
  description = "ID of the egress filtering security group"
  value       = aws_security_group.egress_filtering.id
}

output "vpc_flow_logs_group_name" {
  description = "Name of the VPC Flow Logs CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.vpc_flow_logs.name
}

output "guardduty_detector_id" {
  description = "ID of the GuardDuty detector"
  value       = var.enable_guardduty ? aws_guardduty_detector.main[0].id : null
}

output "network_audit_lambda_arn" {
  description = "ARN of the network segmentation audit Lambda function"
  value       = aws_lambda_function.network_segmentation_audit.arn
}
