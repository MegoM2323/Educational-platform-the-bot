# THE_BOT Platform - IAM Variables

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

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# ==========================================
# Security Configuration
# ==========================================

variable "external_id" {
  description = "External ID for cross-account access or federated identity"
  type        = string
  sensitive   = true
  default     = ""
}

variable "devops_allowed_ips" {
  description = "List of IP addresses allowed for DevOps role assumption"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "admin_allowed_ips" {
  description = "List of IP addresses allowed for Admin role assumption"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ==========================================
# OIDC Provider Configuration (for CI/CD)
# ==========================================

variable "oidc_provider_url" {
  description = "OIDC provider URL (e.g., token.actions.githubusercontent.com for GitHub)"
  type        = string
  default     = "token.actions.githubusercontent.com"
}

variable "oidc_client_id" {
  description = "OIDC client ID (audience)"
  type        = string
  default     = "sts.amazonaws.com"
}

# ==========================================
# GitHub Configuration
# ==========================================

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = "your-org"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "THE_BOT_platform"
}

# ==========================================
# Common Tags
# ==========================================

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "THE_BOT"
    ManagedBy = "Terraform"
    CreatedAt = "2025-12-27"
  }
}
