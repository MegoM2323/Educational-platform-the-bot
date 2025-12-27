# ========================================================
# THE_BOT Platform - AWS WAF Enhanced Rules
# ========================================================
# Comprehensive WAF configuration with:
# - Geo-blocking
# - IP reputation integration
# - Rate limiting by IP reputation
# - Automated rule updates
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
# 1. Enhanced WAF Web ACL with IP Reputation Rules
# ========================================================

resource "aws_wafv2_web_acl" "main" {
  name  = "${var.project_name}-waf-enhanced"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Priority 1: IP Reputation - AbuseIPDB
  rule {
    name     = "IPReputationAbuseIPDB"
    priority = 1

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.abuseipdb_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "IPReputationAbuseIPDB"
      sampled_requests_enabled   = true
    }
  }

  # Priority 2: IP Reputation - Spamhaus
  rule {
    name     = "IPReputationSpamhaus"
    priority = 2

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.spamhaus_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "IPReputationSpamhaus"
      sampled_requests_enabled   = true
    }
  }

  # Priority 3: Custom Blocked IPs
  rule {
    name     = "CustomBlockedIPs"
    priority = 3

    action {
      block {
        custom_response {
          response_code = 403
          custom_response_body_key = "blocked_ip_response"
        }
      }
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.custom_blocked_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CustomBlockedIPs"
      sampled_requests_enabled   = true
    }
  }

  # Priority 4: Geo-Blocking
  rule {
    name     = "GeoBlockingRule"
    priority = 4

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

  # Priority 5: Rate Limiting by IP
  rule {
    name     = "RateLimitingByIP"
    priority = 5

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit_requests
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitingByIP"
      sampled_requests_enabled   = true
    }
  }

  # Priority 6: Rate Limiting by IP Reputation Score
  # (Block IPs that exceed rate limit and have reputation issues)
  rule {
    name     = "RateLimitingByIPReputation"
    priority = 6

    action {
      block {}
    }

    statement {
      and_statement {
        statement {
          rate_based_statement {
            limit              = var.waf_rate_limit_reputation
            aggregate_key_type = "IP"
          }
        }

        statement {
          or_statement {
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.abuseipdb_ips.arn
              }
            }

            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.spamhaus_ips.arn
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitingByIPReputation"
      sampled_requests_enabled   = true
    }
  }

  # Priority 7: AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 7

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          action_to_use {
            block {}
          }
          name = "SizeRestrictions_BODY"
        }

        rule_action_override {
          action_to_use {
            block {}
          }
          name = "GenericRFI_BODY"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Priority 8: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 8

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

  # Priority 9: AWS Managed Rules - SQL Injection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 9

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

  # Priority 10: AWS Managed Rules - Linux Exploits
  rule {
    name     = "AWSManagedRulesLinuxRuleSet"
    priority = 10

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesLinuxRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Priority 11: AWS Managed Rules - Anonymous IP
  rule {
    name     = "AWSManagedRulesAnonymousIPList"
    priority = 11

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIPList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAnonymousIPListMetric"
      sampled_requests_enabled   = true
    }
  }

  # Priority 12: AWS Managed Rules - Amazon IP Reputation
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 12

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAmazonIpReputationListMetric"
      sampled_requests_enabled   = true
    }
  }

  # Priority 13: Custom - Block Suspicious User Agents
  rule {
    name     = "BlockSuspiciousUserAgents"
    priority = 13

    action {
      block {}
    }

    statement {
      or_statement {
        dynamic "statement" {
          for_each = var.blocked_user_agents
          content {
            byte_match_statement {
              field_to_match {
                single_header {
                  name = "user-agent"
                }
              }
              text_transformation {
                priority = 0
                type     = "LOWERCASE"
              }
              positional_constraint = "CONTAINS"
              search_string         = statement.value
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockSuspiciousUserAgents"
      sampled_requests_enabled   = true
    }
  }

  # Priority 14: Custom - Block Directory Traversal
  rule {
    name     = "BlockDirectoryTraversal"
    priority = 14

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
      metric_name                = "BlockDirectoryTraversal"
      sampled_requests_enabled   = true
    }
  }

  # Priority 15: Whitelist - Allow specific trusted IPs
  rule {
    name     = "WhitelistTrustedIPs"
    priority = 15

    action {
      allow {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.whitelisted_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "WhitelistTrustedIPs"
      sampled_requests_enabled   = true
    }
  }

  custom_response_body {
    key          = "blocked_ip_response"
    content      = "Access denied: Your IP has been blocked due to security policy violations."
    content_type = "TEXT_PLAIN"
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf-enhanced-metrics"
    sampled_requests_enabled   = true
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-waf-enhanced"
    }
  )
}

# ========================================================
# 2. IP Sets for Reputation Lists
# ========================================================

# AbuseIPDB - IPs with high abuse scores
resource "aws_wafv2_ip_set" "abuseipdb_ips" {
  name               = "${var.project_name}-abuseipdb-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.abuseipdb_blocked_ips

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-abuseipdb-ips"
    }
  )
}

# Spamhaus - DROP and EDROP list IPs
resource "aws_wafv2_ip_set" "spamhaus_ips" {
  name               = "${var.project_name}-spamhaus-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.spamhaus_blocked_ips

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-spamhaus-ips"
    }
  )
}

# Custom blocked IPs
resource "aws_wafv2_ip_set" "custom_blocked_ips" {
  name               = "${var.project_name}-custom-blocked-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.custom_blocked_ips

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-custom-blocked-ips"
    }
  )
}

# Whitelisted IPs
resource "aws_wafv2_ip_set" "whitelisted_ips" {
  name               = "${var.project_name}-whitelisted-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.whitelisted_ips

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-whitelisted-ips"
    }
  )
}

# ========================================================
# 3. WAF Association with ALB
# ========================================================

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# ========================================================
# 4. CloudWatch Alarms for WAF Monitoring
# ========================================================

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests_abuseipdb" {
  alarm_name          = "${var.project_name}-waf-blocked-abuseipdb"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.waf_alarm_threshold
  alarm_description   = "Alert when WAF blocks requests from AbuseIPDB IPs"
  treat_missing_data  = "notBreaching"

  dimensions = {
    Rule   = "IPReputationAbuseIPDB"
    WebACL = aws_wafv2_web_acl.main.name
    Region = data.aws_region.current.name
  }

  alarm_actions = [var.sns_topic_arn]

  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests_spamhaus" {
  alarm_name          = "${var.project_name}-waf-blocked-spamhaus"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.waf_alarm_threshold
  alarm_description   = "Alert when WAF blocks requests from Spamhaus IPs"
  treat_missing_data  = "notBreaching"

  dimensions = {
    Rule   = "IPReputationSpamhaus"
    WebACL = aws_wafv2_web_acl.main.name
    Region = data.aws_region.current.name
  }

  alarm_actions = [var.sns_topic_arn]

  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "waf_rate_limit_exceeded" {
  alarm_name          = "${var.project_name}-waf-rate-limit-exceeded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.waf_rate_limit_alarm_threshold
  alarm_description   = "Alert when rate limiting blocks many requests"
  treat_missing_data  = "notBreaching"

  dimensions = {
    Rule   = "RateLimitingByIP"
    WebACL = aws_wafv2_web_acl.main.name
    Region = data.aws_region.current.name
  }

  alarm_actions = [var.sns_topic_arn]

  tags = var.common_tags
}

# ========================================================
# 5. Data Source for Region Information
# ========================================================

data "aws_region" "current" {}

# ========================================================
# Outputs
# ========================================================

output "waf_web_acl_id" {
  description = "ID of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.id
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "abuseipdb_ips_set_arn" {
  description = "ARN of AbuseIPDB IP set"
  value       = aws_wafv2_ip_set.abuseipdb_ips.arn
}

output "spamhaus_ips_set_arn" {
  description = "ARN of Spamhaus IP set"
  value       = aws_wafv2_ip_set.spamhaus_ips.arn
}

output "custom_blocked_ips_set_arn" {
  description = "ARN of custom blocked IPs set"
  value       = aws_wafv2_ip_set.custom_blocked_ips.arn
}

output "whitelisted_ips_set_arn" {
  description = "ARN of whitelisted IPs set"
  value       = aws_wafv2_ip_set.whitelisted_ips.arn
}
