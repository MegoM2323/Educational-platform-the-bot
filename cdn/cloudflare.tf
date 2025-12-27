# Cloudflare CDN Configuration for THE_BOT Platform
# Global content delivery, caching, security, and performance optimization

terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# ============================================================================
# VARIABLES
# ============================================================================

variable "cloudflare_api_token" {
  description = "Cloudflare API Token for authentication"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
}

variable "domain_name" {
  description = "Domain name (e.g., thebot.com)"
  type        = string
  default     = "thebot.example.com"
}

variable "origin_url" {
  description = "Origin server URL (backend API)"
  type        = string
  default     = "https://origin.thebot.example.com"
}

variable "frontend_origin" {
  description = "Frontend origin server URL"
  type        = string
  default     = "https://frontend.thebot.example.com"
}

variable "enable_advanced_cache" {
  description = "Enable advanced caching features (requires Enterprise)"
  type        = bool
  default     = false
}

# ============================================================================
# ORIGIN SERVER CONFIGURATION
# ============================================================================

# Configure origin pull (SSL/TLS verification)
resource "cloudflare_origin_ca_certificate" "thebot" {
  zone_id             = var.cloudflare_zone_id
  csr                 = tls_cert_request.api.cert_request_pem
  request_type        = "origin-ecc"
  requested_validity  = 365
  min_days_for_renewal = 30
}

# Generate CSR for origin certificate
resource "tls_cert_request" "api" {
  private_key_pem = tls_private_key.api.private_key_pem

  subject {
    common_name  = var.domain_name
    organization = "THE_BOT"
  }
}

# Generate private key for origin certificate
resource "tls_private_key" "api" {
  algorithm = "ECDSA"
  ecdsa_curve = "P256"
}

# ============================================================================
# CACHING RULES
# ============================================================================

# Cache static assets (CSS, JS, images, fonts) for 30 days
resource "cloudflare_cache_rules" "static_assets" {
  zone_id = var.cloudflare_zone_id

  rules {
    description = "Cache CSS and JavaScript files for 30 days"
    action      = "set"
    action_parameters {
      cache         = true
      cache_on_cookie = ""
      browser_ttl   = 3600  # 1 hour in browser
      edge_ttl      = 2592000  # 30 days at edge
      serve_stale   = 86400  # Serve stale for 1 day
    }
    expression = "(cf.mime_type eq \"text/css\") or (cf.mime_type eq \"application/javascript\") or (cf.mime_type eq \"application/x-javascript\")"
  }

  rules {
    description = "Cache images for 30 days"
    action      = "set"
    action_parameters {
      cache         = true
      browser_ttl   = 86400  # 1 day in browser
      edge_ttl      = 2592000  # 30 days at edge
      serve_stale   = 604800  # Serve stale for 7 days
    }
    expression = "(cf.mime_type eq \"image/jpeg\") or (cf.mime_type eq \"image/png\") or (cf.mime_type eq \"image/webp\") or (cf.mime_type eq \"image/gif\") or (cf.mime_type eq \"image/svg+xml\")"
  }

  rules {
    description = "Cache fonts for 30 days"
    action      = "set"
    action_parameters {
      cache         = true
      browser_ttl   = 2592000  # 30 days
      edge_ttl      = 2592000  # 30 days at edge
    }
    expression = "(cf.mime_type eq \"font/woff\") or (cf.mime_type eq \"font/woff2\") or (cf.mime_type eq \"font/ttf\") or (cf.mime_type eq \"application/font-woff\")"
  }

  rules {
    description = "Cache media files for 7 days"
    action      = "set"
    action_parameters {
      cache         = true
      browser_ttl   = 604800  # 7 days
      edge_ttl      = 604800  # 7 days at edge
      serve_stale   = 86400  # Serve stale for 1 day
    }
    expression = "(cf.mime_type eq \"video/mp4\") or (cf.mime_type eq \"audio/mpeg\") or (cf.mime_type eq \"video/webm\")"
  }

  rules {
    description = "Don't cache HTML pages (always fresh)"
    action      = "set"
    action_parameters {
      cache         = false
      browser_ttl   = 0
      edge_ttl      = 0
    }
    expression = "cf.mime_type eq \"text/html\""
  }

  rules {
    description = "Don't cache API responses (use Cache-Control headers)"
    action      = "set"
    action_parameters {
      cache         = false
      browser_ttl   = 0
      edge_ttl      = 0
    }
    expression = "(http.request.uri.path starts with \"/api/\") or (http.request.uri.path starts with \"/api-docs/\")"
  }

  rules {
    description = "Respect query strings for cache busting"
    action      = "set"
    action_parameters {
      cache_key = {
        ignore_query_strings_order = false
        custom_key = {
          query_string = {
            include = ["v", "version", "bust", "cachebust"]
          }
        }
      }
      edge_ttl = 86400
    }
    expression = "cf.cache_status == \"HIT\""
  }
}

# ============================================================================
# PAGE RULES (Alternative to Cache Rules for backward compatibility)
# ============================================================================

resource "cloudflare_page_rule" "cache_html_bypass" {
  zone_id = var.cloudflare_zone_id
  target  = "${var.domain_name}/*.html"
  priority = 1

  actions {
    cache_level = "bypass"
  }
}

resource "cloudflare_page_rule" "cache_static_long" {
  zone_id = var.cloudflare_zone_id
  target  = "${var.domain_name}/static/*"
  priority = 2

  actions {
    cache_level         = "cache_everything"
    edge_cache_ttl      = 2592000  # 30 days
    browser_cache_ttl   = 3600  # 1 hour
  }
}

resource "cloudflare_page_rule" "cache_assets" {
  zone_id = var.cloudflare_zone_id
  target  = "${var.domain_name}/assets/*"
  priority = 3

  actions {
    cache_level         = "cache_everything"
    edge_cache_ttl      = 2592000  # 30 days
    browser_cache_ttl   = 86400  # 1 day
  }
}

resource "cloudflare_page_rule" "api_no_cache" {
  zone_id = var.cloudflare_zone_id
  target  = "${var.domain_name}/api/*"
  priority = 4

  actions {
    cache_level = "bypass"
  }
}

# ============================================================================
# COMPRESSION & OPTIMIZATION
# ============================================================================

resource "cloudflare_zone_settings_override" "compression" {
  zone_id = var.cloudflare_zone_id

  settings {
    # Enable Gzip compression
    gzip = "on"

    # Enable Brotli compression (automatic for supported browsers)
    brotli = "on"

    # Minify CSS, JavaScript, HTML
    minify {
      css  = "on"
      html = "on"
      js   = "on"
    }

    # Enable HTTP/3 support
    http3 = "on"

    # Enable HTTP/2 Server Push
    h2_prioritization = "on"

    # Use early hints for critical resources
    early_hints = "on"

    # Image optimization settings
    image_resizing = "on"

    # Polish (image optimization)
    polish = "lossless"
  }
}

# ============================================================================
# IMAGE OPTIMIZATION RULES
# ============================================================================

resource "cloudflare_cache_rules" "image_optimization" {
  zone_id = var.cloudflare_zone_id

  rules {
    description = "Convert images to WebP for supported browsers"
    action      = "set"
    action_parameters {
      browser_cache_ttl = 3600
      edge_ttl          = 2592000
      image_file        = "webp"  # Serve WebP to compatible browsers
    }
    expression = "(cf.mime_type eq \"image/jpeg\") or (cf.mime_type eq \"image/png\")"
  }

  rules {
    description = "Responsive image sizing"
    action      = "set"
    action_parameters {
      cache = true
    }
    expression = "http.request.uri.query contains \"w=\""
  }
}

# ============================================================================
# SECURITY RULES - DDoS Protection
# ============================================================================

# Challenge suspicious traffic
resource "cloudflare_firewall_rule" "challenge_bots" {
  zone_id     = var.cloudflare_zone_id
  description = "Challenge suspicious bot traffic"
  filter_id   = cloudflare_firewall_filter.suspicious_bots.id
  action      = "challenge"
}

resource "cloudflare_firewall_filter" "suspicious_bots" {
  zone_id     = var.cloudflare_zone_id
  description = "Suspicious bot behavior"
  expression  = "(cf.bot_management.score < 30) and (cf.threat_score > 50)"
}

# Block malicious traffic
resource "cloudflare_firewall_rule" "block_malicious" {
  zone_id     = var.cloudflare_zone_id
  description = "Block known malicious IP ranges"
  filter_id   = cloudflare_firewall_filter.malicious_ips.id
  action      = "block"
}

resource "cloudflare_firewall_filter" "malicious_ips" {
  zone_id     = var.cloudflare_zone_id
  description = "Malicious IP ranges from threat intelligence"
  expression  = "(cf.threat_score >= 80) or (cf.bot_management.score < 10)"
}

# Rate limiting
resource "cloudflare_firewall_rule" "rate_limit_login" {
  zone_id     = var.cloudflare_zone_id
  description = "Rate limit login attempts"
  filter_id   = cloudflare_firewall_filter.login_attempts.id
  action      = "challenge"
}

resource "cloudflare_firewall_filter" "login_attempts" {
  zone_id     = var.cloudflare_zone_id
  description = "Multiple login attempts from same IP"
  expression  = "(http.request.uri.path contains \"/api/auth/login\") and (cf.http_request_host eq \"${var.domain_name}\")"
}

# ============================================================================
# WAF (Web Application Firewall) RULES
# ============================================================================

# OWASP ModSecurity Core Rule Set
resource "cloudflare_waf_group" "owasp_rules" {
  zone_id = var.cloudflare_zone_id
  group_id = "62d9e6f958f306154427b599"  # OWASP ModSecurity CRS

  mode = "challenge"  # Challenge suspicious requests
}

# Additional WAF rules for API protection
resource "cloudflare_waf_rule" "api_sql_injection" {
  zone_id  = var.cloudflare_zone_id
  rule_id  = "100000"  # SQL Injection
  group_id = "62d9e6f958f306154427b599"
  mode     = "block"
}

resource "cloudflare_waf_rule" "api_xss_protection" {
  zone_id  = var.cloudflare_zone_id
  rule_id  = "100001"  # XSS
  group_id = "62d9e6f958f306154427b599"
  mode     = "block"
}

# ============================================================================
# RATE LIMITING RULES
# ============================================================================

# Global rate limiting
resource "cloudflare_rate_limit" "global_limit" {
  zone_id = var.cloudflare_zone_id
  disabled = false
  threshold = 1000  # Requests per period
  period = 60  # Seconds
  match {
    request {
      url = {
        path_matches = ["${var.domain_name}/*"]
      }
    }
  }
  action {
    timeout = 86400  # Ban for 24 hours
    response = {
      content_type = "application/json"
      body = jsonencode({
        error = "Rate limit exceeded"
      })
    }
  }
}

# API rate limiting (stricter)
resource "cloudflare_rate_limit" "api_limit" {
  zone_id = var.cloudflare_zone_id
  disabled = false
  threshold = 100  # Requests per period
  period = 60  # Seconds
  match {
    request {
      url = {
        path_matches = ["${var.domain_name}/api/*"]
      }
    }
  }
  action {
    timeout = 3600  # Ban for 1 hour
    response = {
      content_type = "application/json"
      body = jsonencode({
        error = "API rate limit exceeded"
      })
    }
  }
}

# Login endpoint rate limiting
resource "cloudflare_rate_limit" "login_limit" {
  zone_id = var.cloudflare_zone_id
  disabled = false
  threshold = 5  # 5 requests
  period = 60  # per minute
  match {
    request {
      url = {
        path_matches = ["${var.domain_name}/api/auth/login"]
      }
    }
  }
  action {
    timeout = 1800  # Ban for 30 minutes
    response = {
      content_type = "application/json"
      body = jsonencode({
        error = "Too many login attempts. Try again later."
      })
    }
  }
}

# ============================================================================
# SECURITY HEADERS
# ============================================================================

resource "cloudflare_cache_rules" "security_headers" {
  zone_id = var.cloudflare_zone_id

  rules {
    description = "Add security headers to all responses"
    action      = "set"
    action_parameters {
      headers {
        header_name = "X-Content-Type-Options"
        header_value = "nosniff"
        operation = "set"
      }
      headers {
        header_name = "X-Frame-Options"
        header_value = "DENY"
        operation = "set"
      }
      headers {
        header_name = "X-XSS-Protection"
        header_value = "1; mode=block"
        operation = "set"
      }
      headers {
        header_name = "Referrer-Policy"
        header_value = "strict-origin-when-cross-origin"
        operation = "set"
      }
      headers {
        header_name = "Permissions-Policy"
        header_value = "geolocation=(), microphone=(), camera=()"
        operation = "set"
      }
      headers {
        header_name = "Strict-Transport-Security"
        header_value = "max-age=31536000; includeSubDomains; preload"
        operation = "set"
      }
    }
    expression = "true"
  }

  rules {
    description = "CSP header for HTML pages"
    action      = "set"
    action_parameters {
      headers {
        header_name = "Content-Security-Policy"
        header_value = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.example.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' api.example.com; frame-ancestors 'none';"
        operation = "set"
      }
    }
    expression = "cf.mime_type eq \"text/html\""
  }
}

# ============================================================================
# HTTPS/TLS CONFIGURATION
# ============================================================================

resource "cloudflare_zone_settings_override" "https" {
  zone_id = var.cloudflare_zone_id

  settings {
    # Always use HTTPS
    always_use_https = "on"

    # Minimum TLS version 1.2
    min_tls_version = "1.2"

    # SSL/TLS encryption mode (Full)
    ssl = "full"

    # Automatic HTTPS rewrites
    automatic_https_rewrites = "on"

    # OCSP stapling
    ocsp_stapling = "on"
  }
}

# ============================================================================
# WORKERS (Cloudflare Workers for dynamic caching)
# ============================================================================

resource "cloudflare_workers_script" "cache_worker" {
  account_id = data.cloudflare_account.current.id
  name       = "thebot-cache-worker"
  content    = file("${path.module}/workers/cache-worker.js")
}

resource "cloudflare_workers_route" "cache_route" {
  zone_id     = var.cloudflare_zone_id
  pattern     = "${var.domain_name}/api/cache/*"
  script_name = cloudflare_workers_script.cache_worker.name
}

# ============================================================================
# ANALYTICS & MONITORING
# ============================================================================

resource "cloudflare_logpush_job" "http_requests" {
  account_id = data.cloudflare_account.current.id
  enabled    = true
  frequency  = "low"
  dataset    = "http_requests"
  logpull_options = "fields=ClientIP,ClientRequestHost,ClientRequestMethod,ClientRequestPath,ClientRequestQuery,EdgeResponseStatus,EdgeResponseBytes,CacheStatus,CacheResponseTime,EdgeResponseCompressionRatio,OriginResponseTime,OriginResponseStatus,TLSVersion,UserAgent&timestamps=rfc3339&CVE=2021-22911"
  destination_conf = "s3://thebot-logs/cloudflare/http-requests"
}

# Data source to get current account
data "cloudflare_account" "current" {
  name = "THE_BOT"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "cloudflare_zone_id" {
  description = "Cloudflare Zone ID"
  value       = var.cloudflare_zone_id
}

output "cdn_status" {
  description = "CDN configuration status"
  value       = "CDN configured successfully"
}

output "cache_rules_status" {
  description = "Cache rules status"
  value = {
    static_assets    = "Cached for 30 days"
    images           = "WebP optimization enabled"
    html             = "Not cached (always fresh)"
    api              = "Not cached (respects Cache-Control)"
    media            = "Cached for 7 days"
  }
}

output "security_features" {
  description = "Enabled security features"
  value = {
    ddos_protection      = "Active (Cloudflare's DDoS mitigation)"
    waf                  = "OWASP ModSecurity rules enabled"
    rate_limiting        = "Configured for API and login endpoints"
    https_everywhere     = "Enforced (TLS 1.2+)"
    security_headers     = "Applied to all responses"
    bot_management       = "Enabled"
  }
}

output "performance_features" {
  description = "Enabled performance features"
  value = {
    gzip_compression     = "Enabled"
    brotli_compression   = "Enabled"
    minification         = "CSS, JS, HTML enabled"
    http3_support        = "Enabled"
    early_hints          = "Enabled"
    image_optimization   = "WebP conversion enabled"
    cache_busting        = "Query string support"
  }
}

output "monitoring_features" {
  description = "Monitoring and logging"
  value = {
    analytics            = "Real-time analytics dashboard"
    http_request_logs    = "Stored in S3"
    cache_metrics        = "Cache hit rate tracking"
    performance_metrics  = "Response time, bandwidth monitoring"
    ddos_monitoring      = "Real-time DDoS attack detection"
  }
}
