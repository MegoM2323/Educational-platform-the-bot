# ========================================================
# THE_BOT Platform - Security Variables (HARDENED)
# ========================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "thebot"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "vpc_id" {
  description = "ID of the VPC for network security"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "alb_arn" {
  description = "ARN of the Application Load Balancer to protect with WAF"
  type        = string
}

variable "public_nacl_id" {
  description = "ID of the public subnet NACL"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of SNS topic for security alerts"
  type        = string
}

# ========================================================
# WAF Configuration
# ========================================================

variable "waf_rate_limit_requests" {
  description = "Maximum number of requests from an IP address in 5 minutes"
  type        = number
  default     = 2000
  validation {
    condition     = var.waf_rate_limit_requests > 0 && var.waf_rate_limit_requests <= 20000000
    error_message = "Rate limit must be between 1 and 20,000,000."
  }
}

variable "waf_blocked_countries" {
  description = "List of country codes to block (e.g., ['KP', 'IR'])"
  type        = list(string)
  default     = []
}

variable "waf_blocked_ip_addresses" {
  description = "List of IP addresses/CIDR blocks to block"
  type        = list(string)
  default     = []
}

variable "waf_whitelisted_ip_addresses" {
  description = "List of IP addresses/CIDR blocks to whitelist"
  type        = list(string)
  default     = []
}

variable "waf_enabled_rules" {
  description = "Map of WAF rules to enable/disable"
  type = object({
    rate_limiting     = bool
    core_rule_set     = bool
    known_bad_inputs  = bool
    sql_injection     = bool
    ip_reputation     = bool
    geo_blocking      = bool
    custom_protection = bool
  })
  default = {
    rate_limiting     = true
    core_rule_set     = true
    known_bad_inputs  = true
    sql_injection     = true
    ip_reputation     = true
    geo_blocking      = false
    custom_protection = true
  }
}

# ========================================================
# Egress Filtering Configuration
# ========================================================

variable "allowed_http_destinations" {
  description = "CIDR blocks allowed for HTTP egress"
  type        = list(string)
  default     = []
}

variable "allowed_https_destinations" {
  description = "CIDR blocks allowed for HTTPS egress"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_dns_servers" {
  description = "IP addresses of allowed DNS servers"
  type        = list(string)
  default     = ["8.8.8.8/32", "8.8.4.4/32", "1.1.1.1/32"]
}

# ========================================================
# DDoS Protection Configuration
# ========================================================

variable "enable_shield_advanced" {
  description = "Enable AWS Shield Advanced for enhanced DDoS protection"
  type        = bool
  default     = false
}

variable "ddos_protection_level" {
  description = "DDoS protection level (basic, advanced)"
  type        = string
  default     = "basic"
  validation {
    condition     = contains(["basic", "advanced"], var.ddos_protection_level)
    error_message = "DDoS protection level must be 'basic' or 'advanced'."
  }
}

variable "ddos_connection_limit" {
  description = "Maximum number of concurrent connections per source IP"
  type        = number
  default     = 10000
}

variable "ddos_packet_rate_limit" {
  description = "Maximum packet rate per second from a single IP"
  type        = number
  default     = 5000
}

# ========================================================
# Flow Logs Configuration
# ========================================================

variable "flow_logs_retention_days" {
  description = "Retention period for VPC Flow Logs in days"
  type        = number
  default     = 30
  validation {
    condition     = var.flow_logs_retention_days > 0
    error_message = "Flow logs retention must be greater than 0 days."
  }
}

variable "flow_logs_traffic_type" {
  description = "Type of traffic to log (ALL, ACCEPT, REJECT)"
  type        = string
  default     = "ALL"
  validation {
    condition     = contains(["ALL", "ACCEPT", "REJECT"], var.flow_logs_traffic_type)
    error_message = "Traffic type must be ALL, ACCEPT, or REJECT."
  }
}

# ========================================================
# Security Monitoring and Alerting
# ========================================================

variable "security_alarm_rejected_packets_threshold" {
  description = "Threshold for rejected packets alarm"
  type        = number
  default     = 1000
}

variable "security_alarm_waf_blocked_threshold" {
  description = "Threshold for WAF blocked requests alarm"
  type        = number
  default     = 100
}

variable "enable_security_hub" {
  description = "Enable AWS Security Hub for centralized security findings"
  type        = bool
  default     = false
}

variable "enable_guardduty" {
  description = "Enable Amazon GuardDuty for threat detection"
  type        = bool
  default     = true
}

# ========================================================
# Network Segmentation Audit
# ========================================================

variable "expected_subnets" {
  description = "List of expected subnet IDs for audit"
  type        = list(string)
  default     = []
}

variable "expected_nat_gateways" {
  description = "Expected number of NAT Gateways"
  type        = number
  default     = 3
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for audit notifications"
  type        = string
  sensitive   = true
  default     = ""
}

# ========================================================
# Traffic Filtering Rules
# ========================================================

variable "enable_intrusion_detection" {
  description = "Enable intrusion detection rules"
  type        = bool
  default     = true
}

variable "intrusion_detection_sensitivity" {
  description = "Sensitivity level for intrusion detection (low, medium, high)"
  type        = string
  default     = "high"
  validation {
    condition     = contains(["low", "medium", "high"], var.intrusion_detection_sensitivity)
    error_message = "Sensitivity must be low, medium, or high."
  }
}

variable "enable_protocol_filtering" {
  description = "Enable filtering of specific protocols"
  type        = bool
  default     = true
}

variable "blocked_protocols" {
  description = "List of protocols to block"
  type        = list(string)
  default     = ["IGMP", "GRE"]
}

variable "enable_port_filtering" {
  description = "Enable filtering of specific ports"
  type        = bool
  default     = true
}

variable "blocked_ports" {
  description = "List of ports to block"
  type        = list(number)
  default     = [23, 69, 135, 139, 445, 1433, 3306]  # telnet, tftp, RPC, NetBIOS, SMB, MSSQL, MySQL
}

# ========================================================
# Common Tags
# ========================================================

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "THE_BOT"
    ManagedBy   = "Terraform"
    Component   = "NetworkSecurity"
  }
}
