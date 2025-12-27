# CloudFront CDN Terraform Variables

# Project Configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "thebot-platform"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# Origin Configuration
variable "origin_domain_name" {
  description = "Origin domain name (backend API server)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.origin_domain_name))
    error_message = "Origin domain must be a valid domain name."
  }
}

variable "origin_custom_header_name" {
  description = "Custom header name for origin authentication"
  type        = string
  default     = "X-Origin-Verify"

  validation {
    condition     = can(regex("^[A-Z][A-Za-z0-9-]*$", var.origin_custom_header_name))
    error_message = "Header name must be valid HTTP header format."
  }
}

variable "origin_custom_header_value" {
  description = "Custom header value for origin authentication (secret token)"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.origin_custom_header_value) >= 32
    error_message = "Header value must be at least 32 characters for security."
  }
}

# Geo-restriction Configuration
variable "enable_geo_restrictions" {
  description = "Enable geographic restrictions for compliance"
  type        = bool
  default     = false
}

variable "geo_restriction_type" {
  description = "Geo restriction type: none, whitelist, or blacklist"
  type        = string
  default     = "none"

  validation {
    condition     = contains(["none", "whitelist", "blacklist"], var.geo_restriction_type)
    error_message = "Geo restriction type must be none, whitelist, or blacklist."
  }
}

variable "geo_restriction_locations" {
  description = "List of ISO 3166-1 country codes for geo-restriction"
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([
      for code in var.geo_restriction_locations : can(regex("^[A-Z]{2}$", code))
    ])
    error_message = "Geo restriction locations must be valid ISO 3166-1 country codes (e.g., US, CA)."
  }
}

# Cache Configuration
variable "hashed_assets_ttl" {
  description = "TTL for hashed assets in seconds (default: 1 year)"
  type        = number
  default     = 31536000

  validation {
    condition     = var.hashed_assets_ttl >= 0 && var.hashed_assets_ttl <= 31536000
    error_message = "TTL must be between 0 and 1 year (31536000 seconds)."
  }
}

variable "static_files_ttl" {
  description = "TTL for static files in seconds (default: 30 days)"
  type        = number
  default     = 2592000

  validation {
    condition     = var.static_files_ttl >= 0 && var.static_files_ttl <= 31536000
    error_message = "TTL must be between 0 and 1 year (31536000 seconds)."
  }
}

variable "media_files_ttl" {
  description = "TTL for media files in seconds (default: 7 days)"
  type        = number
  default     = 604800

  validation {
    condition     = var.media_files_ttl >= 0 && var.media_files_ttl <= 31536000
    error_message = "TTL must be between 0 and 1 year (31536000 seconds)."
  }
}

# HTTP Configuration
variable "http_version" {
  description = "HTTP version to support"
  type        = string
  default     = "http2and3"

  validation {
    condition     = contains(["http1.1", "http2", "http2and3"], var.http_version)
    error_message = "HTTP version must be http1.1, http2, or http2and3."
  }
}

variable "tls_minimum_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "TLSv1.2_2021"

  validation {
    condition     = contains([
      "SSLv3",
      "TLSv1",
      "TLSv1_2016",
      "TLSv1.1_2016",
      "TLSv1.2_2018",
      "TLSv1.2_2019",
      "TLSv1.2_2021"
    ], var.tls_minimum_version)
    error_message = "Invalid TLS version specified."
  }
}

# Logging Configuration
variable "enable_logging" {
  description = "Enable CloudFront access logging to S3"
  type        = bool
  default     = true
}

variable "logs_retention_days" {
  description = "Number of days to retain CloudFront logs"
  type        = number
  default     = 90

  validation {
    condition     = var.logs_retention_days >= 1 && var.logs_retention_days <= 3650
    error_message = "Log retention must be between 1 and 3650 days."
  }
}

# Tags
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)

  default = {
    Project     = "thebot-platform"
    Component   = "cdn"
    Managed     = "terraform"
    Version     = "1.0.0"
  }

  validation {
    condition     = length(var.tags) >= 2
    error_message = "At least 2 tags must be provided."
  }
}

# Output Configuration
variable "include_private_key_path" {
  description = "Whether to include private key path in outputs"
  type        = bool
  default     = false
  sensitive   = true
}

# Advanced Configuration (optional overrides)
variable "cloudfront_default_root_object" {
  description = "Default root object for CloudFront"
  type        = string
  default     = "index.html"
}

variable "error_document" {
  description = "Error document for 4xx/5xx errors"
  type        = string
  default     = "index.html"
}

variable "price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_100, PriceClass_200)"
  type        = string
  default     = "PriceClass_100"  # Cost optimization

  validation {
    condition     = contains(["PriceClass_All", "PriceClass_100", "PriceClass_200"], var.price_class)
    error_message = "Price class must be PriceClass_All, PriceClass_100, or PriceClass_200."
  }
}

variable "enable_ipv6" {
  description = "Enable IPv6 for CloudFront"
  type        = bool
  default     = true
}

variable "enable_compression" {
  description = "Enable automatic compression (gzip, brotli)"
  type        = bool
  default     = true
}

variable "max_cache_invalidation_paths" {
  description = "Maximum paths per invalidation request (AWS limit: 3000)"
  type        = number
  default     = 3000

  validation {
    condition     = var.max_cache_invalidation_paths > 0 && var.max_cache_invalidation_paths <= 3000
    error_message = "Max paths must be between 1 and 3000 (AWS limit)."
  }
}
