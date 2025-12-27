# THE_BOT Platform - VPC Variables

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
# VPC Configuration
# ==========================================

variable "vpc_cidr" {
  description = "CIDR block for VPC (must be /16)"
  type        = string
  default     = "10.0.0.0/16"
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/16$", var.vpc_cidr))
    error_message = "VPC CIDR must be a valid IPv4 /16 block."
  }
}

variable "availability_zones_count" {
  description = "Number of availability zones (must be 3 for production)"
  type        = number
  default     = 3
  validation {
    condition     = var.availability_zones_count >= 2 && var.availability_zones_count <= 4
    error_message = "Must have between 2 and 4 availability zones."
  }
}

# ==========================================
# Public Subnets (for ALB/NLB)
# ==========================================

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default = [
    "10.0.1.0/24",   # AZ1
    "10.0.2.0/24",   # AZ2
    "10.0.3.0/24"    # AZ3
  ]
}

# ==========================================
# Private Subnets (for application tier)
# ==========================================

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private application subnets"
  type        = list(string)
  default = [
    "10.0.11.0/24",  # AZ1
    "10.0.12.0/24",  # AZ2
    "10.0.13.0/24"   # AZ3
  ]
}

# ==========================================
# Database Subnets (private, no internet)
# ==========================================

variable "database_subnet_cidrs" {
  description = "CIDR blocks for private database subnets"
  type        = list(string)
  default = [
    "10.0.21.0/24",  # AZ1
    "10.0.22.0/24",  # AZ2
    "10.0.23.0/24"   # AZ3
  ]
}

# ==========================================
# Flow Logs Configuration
# ==========================================

variable "flow_logs_retention_days" {
  description = "CloudWatch Logs retention in days for VPC Flow Logs"
  type        = number
  default     = 30
  validation {
    condition     = var.flow_logs_retention_days > 0
    error_message = "Flow logs retention days must be greater than 0."
  }
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

# ==========================================
# Security Configuration
# ==========================================

variable "bastion_allowed_cidr" {
  description = "CIDR block allowed to SSH into Bastion host"
  type        = string
  default     = "0.0.0.0/0"
  sensitive   = true
}

# ==========================================
# Common Tags
# ==========================================

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "THE_BOT"
    ManagedBy   = "Terraform"
    CreatedAt   = "2025-12-27"
  }
}
