# Variable definitions for Cloudflare CDN Terraform configuration

variable "cloudflare_api_token" {
  description = "Cloudflare API Token with Zone:Read and Cache Purge permissions"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
  validation {
    condition     = length(var.cloudflare_zone_id) > 0
    error_message = "Zone ID must not be empty."
  }
}

variable "cloudflare_account_name" {
  description = "Cloudflare account name"
  type        = string
  default     = "THE_BOT"
}

variable "domain_name" {
  description = "Primary domain name (e.g., thebot.com)"
  type        = string
  default     = "thebot.example.com"
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]?(\\.[a-z0-9][a-z0-9-]{0,61}[a-z0-9]?)*$", var.domain_name))
    error_message = "Must be a valid domain name."
  }
}

variable "origin_url" {
  description = "Origin server URL (backend API)"
  type        = string
  default     = "https://origin.thebot.example.com"
  validation {
    condition     = can(regex("^https?://", var.origin_url))
    error_message = "Must be a valid URL starting with http:// or https://"
  }
}

variable "frontend_origin" {
  description = "Frontend origin server URL"
  type        = string
  default     = "https://frontend.thebot.example.com"
  validation {
    condition     = can(regex("^https?://", var.frontend_origin))
    error_message = "Must be a valid URL starting with http:// or https://"
  }
}

variable "enable_advanced_cache" {
  description = "Enable advanced caching features (requires Enterprise plan)"
  type        = bool
  default     = false
}

variable "enable_image_optimization" {
  description = "Enable image optimization (WebP, responsive sizing)"
  type        = bool
  default     = true
}

variable "enable_minification" {
  description = "Enable minification of CSS, JS, HTML"
  type        = bool
  default     = true
}

variable "enable_compression" {
  description = "Enable Gzip and Brotli compression"
  type        = bool
  default     = true
}

variable "enable_http3" {
  description = "Enable HTTP/3 (QUIC) support"
  type        = bool
  default     = true
}

variable "enable_early_hints" {
  description = "Enable Early Hints for critical resources"
  type        = bool
  default     = true
}

variable "enable_ddos_protection" {
  description = "Enable DDoS protection"
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Enable Web Application Firewall (WAF)"
  type        = bool
  default     = true
}

variable "enable_bot_management" {
  description = "Enable bot management and detection"
  type        = bool
  default     = true
}

variable "enable_rate_limiting" {
  description = "Enable rate limiting"
  type        = bool
  default     = true
}

# Cache TTL Settings (in seconds)

variable "cache_ttl_static" {
  description = "Cache TTL for static assets (CSS, JS, fonts)"
  type        = number
  default     = 2592000  # 30 days
  validation {
    condition     = var.cache_ttl_static >= 0 && var.cache_ttl_static <= 31536000
    error_message = "Cache TTL must be between 0 and 31536000 (1 year)."
  }
}

variable "cache_ttl_images" {
  description = "Cache TTL for images"
  type        = number
  default     = 2592000  # 30 days
  validation {
    condition     = var.cache_ttl_images >= 0 && var.cache_ttl_images <= 31536000
    error_message = "Cache TTL must be between 0 and 31536000 (1 year)."
  }
}

variable "cache_ttl_html" {
  description = "Cache TTL for HTML pages"
  type        = number
  default     = 0  # No cache - always fresh
  validation {
    condition     = var.cache_ttl_html >= 0 && var.cache_ttl_html <= 31536000
    error_message = "Cache TTL must be between 0 and 31536000 (1 year)."
  }
}

variable "cache_ttl_api" {
  description = "Cache TTL for API responses"
  type        = number
  default     = 0  # No cache - respects Cache-Control headers
  validation {
    condition     = var.cache_ttl_api >= 0 && var.cache_ttl_api <= 31536000
    error_message = "Cache TTL must be between 0 and 31536000 (1 year)."
  }
}

variable "cache_ttl_media" {
  description = "Cache TTL for media files"
  type        = number
  default     = 604800  # 7 days
  validation {
    condition     = var.cache_ttl_media >= 0 && var.cache_ttl_media <= 31536000
    error_message = "Cache TTL must be between 0 and 31536000 (1 year)."
  }
}

# Stale-while-revalidate Settings (in seconds)

variable "stale_ttl_static" {
  description = "Serve stale TTL for static assets"
  type        = number
  default     = 86400  # 1 day
}

variable "stale_ttl_images" {
  description = "Serve stale TTL for images"
  type        = number
  default     = 604800  # 7 days
}

variable "stale_ttl_media" {
  description = "Serve stale TTL for media"
  type        = number
  default     = 86400  # 1 day
}

# Rate Limiting Settings

variable "rate_limit_global" {
  description = "Global rate limit (requests per minute)"
  type        = number
  default     = 1000
  validation {
    condition     = var.rate_limit_global > 0 && var.rate_limit_global <= 10000
    error_message = "Rate limit must be between 1 and 10000."
  }
}

variable "rate_limit_api" {
  description = "API rate limit (requests per minute)"
  type        = number
  default     = 100
  validation {
    condition     = var.rate_limit_api > 0 && var.rate_limit_api <= 10000
    error_message = "Rate limit must be between 1 and 10000."
  }
}

variable "rate_limit_login" {
  description = "Login endpoint rate limit (requests per minute)"
  type        = number
  default     = 5
  validation {
    condition     = var.rate_limit_login > 0 && var.rate_limit_login <= 1000
    error_message = "Rate limit must be between 1 and 1000."
  }
}

variable "ban_duration_global" {
  description = "Global ban duration in seconds"
  type        = number
  default     = 86400  # 24 hours
  validation {
    condition     = var.ban_duration_global > 0 && var.ban_duration_global <= 31536000
    error_message = "Ban duration must be between 1 and 31536000 seconds."
  }
}

variable "ban_duration_api" {
  description = "API ban duration in seconds"
  type        = number
  default     = 3600  # 1 hour
  validation {
    condition     = var.ban_duration_api > 0 && var.ban_duration_api <= 31536000
    error_message = "Ban duration must be between 1 and 31536000 seconds."
  }
}

variable "ban_duration_login" {
  description = "Login ban duration in seconds"
  type        = number
  default     = 1800  # 30 minutes
  validation {
    condition     = var.ban_duration_login > 0 && var.ban_duration_login <= 31536000
    error_message = "Ban duration must be between 1 and 31536000 seconds."
  }
}

# SSL/TLS Settings

variable "ssl_mode" {
  description = "SSL/TLS encryption mode (flexible, full, strict)"
  type        = string
  default     = "full"
  validation {
    condition     = contains(["flexible", "full", "strict"], var.ssl_mode)
    error_message = "SSL mode must be 'flexible', 'full', or 'strict'."
  }
}

variable "min_tls_version" {
  description = "Minimum TLS version (1.0, 1.1, 1.2, 1.3)"
  type        = string
  default     = "1.2"
  validation {
    condition     = contains(["1.0", "1.1", "1.2", "1.3"], var.min_tls_version)
    error_message = "TLS version must be '1.0', '1.1', '1.2', or '1.3'."
  }
}

# Logging and Monitoring

variable "enable_logpush" {
  description = "Enable Logpush to external storage"
  type        = bool
  default     = false
}

variable "logpush_frequency" {
  description = "Logpush frequency (low, high)"
  type        = string
  default     = "low"
  validation {
    condition     = contains(["low", "high"], var.logpush_frequency)
    error_message = "Logpush frequency must be 'low' or 'high'."
  }
}

variable "log_bucket_name" {
  description = "S3 bucket name for logs"
  type        = string
  default     = "thebot-logs"
}

variable "enable_analytics" {
  description = "Enable real-time analytics"
  type        = bool
  default     = true
}

variable "cache_strategy" {
  description = "Caching strategy (aggressive, balanced, conservative)"
  type        = string
  default     = "balanced"
  validation {
    condition     = contains(["aggressive", "balanced", "conservative"], var.cache_strategy)
    error_message = "Cache strategy must be 'aggressive', 'balanced', or 'conservative'."
  }
}

variable "cache_busting_params" {
  description = "Query parameters used for cache busting"
  type        = list(string)
  default     = ["v", "version", "bust", "cachebust"]
}

variable "security_headers_enabled" {
  description = "Enable security headers (CSP, HSTS, etc.)"
  type        = bool
  default     = true
}

variable "custom_csp_policy" {
  description = "Custom Content Security Policy"
  type        = string
  default     = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';"
}

variable "tags" {
  description = "Tags to apply to Cloudflare resources"
  type        = map(string)
  default = {
    project     = "THE_BOT"
    environment = "production"
    managed_by  = "terraform"
  }
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be 'development', 'staging', or 'production'."
  }
}
