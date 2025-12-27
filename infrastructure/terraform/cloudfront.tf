# CloudFront Distribution for CDN - Static Assets and Media Files
# This configuration provides:
# - 1-year caching for hashed assets (JS, CSS, images with hashes)
# - 30-day caching for other static files
# - Signed URLs for media files (user uploads)
# - HTTPS-only with TLS 1.2+
# - Origin request minimization (cost optimization)
# - Fallback to origin on cache miss

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "thebot-platform"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
}

variable "origin_domain_name" {
  description = "Origin domain (backend API/static files server)"
  type        = string
}

variable "origin_custom_header_name" {
  description = "Custom header name for origin authentication"
  type        = string
  default     = "X-Origin-Verify"
}

variable "origin_custom_header_value" {
  description = "Custom header value for origin authentication"
  type        = string
  sensitive   = true
}

variable "enable_geo_restrictions" {
  description = "Enable geo-restriction for compliance"
  type        = bool
  default     = false
}

variable "geo_restriction_type" {
  description = "Geo restriction type: none, whitelist, or blacklist"
  type        = string
  default     = "none"
}

variable "geo_restriction_locations" {
  description = "List of country codes for geo-restriction"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "thebot-platform"
    Environment = "production"
    Managed     = "terraform"
  }
}

# CloudFront Origin Access Control for S3 (if using S3 as origin)
resource "aws_cloudfront_origin_access_control" "main" {
  name                              = "${var.project_name}-oac"
  description                       = "OAC for ${var.project_name} CloudFront distribution"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Cache Policy - Hashed Assets (1 year, aggressive caching)
resource "aws_cloudfront_cache_policy" "hashed_assets" {
  name            = "${var.project_name}-hashed-assets"
  comment         = "Cache policy for hashed assets (JS, CSS, images) - 1 year TTL"
  default_ttl     = 31536000  # 1 year in seconds
  max_ttl         = 31536000  # 1 year in seconds
  min_ttl         = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true

    query_strings_config {
      query_string_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    cookies_config {
      cookie_behavior = "none"
    }
  }
}

# CloudFront Cache Policy - Static Files (30 days)
resource "aws_cloudfront_cache_policy" "static_files" {
  name            = "${var.project_name}-static-files"
  comment         = "Cache policy for static files - 30 days TTL"
  default_ttl     = 2592000   # 30 days in seconds
  max_ttl         = 2592000   # 30 days in seconds
  min_ttl         = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true

    query_strings_config {
      query_string_behavior = "all"  # Allow query strings for cache busting
    }

    headers_config {
      header_behavior = "none"
    }

    cookies_config {
      cookie_behavior = "none"
    }
  }
}

# CloudFront Cache Policy - Media Files (Signed URLs, 7 days)
resource "aws_cloudfront_cache_policy" "media_files" {
  name            = "${var.project_name}-media-files"
  comment         = "Cache policy for media files with signed URLs - 7 days TTL"
  default_ttl     = 604800    # 7 days in seconds
  max_ttl         = 604800    # 7 days in seconds
  min_ttl         = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true

    query_strings_config {
      query_string_behavior = "all"  # Preserve CloudFront signed URL query strings
    }

    headers_config {
      header_behavior = "none"
    }

    cookies_config {
      cookie_behavior = "none"
    }
  }
}

# CloudFront Origin Request Policy - For origin authentication
resource "aws_cloudfront_origin_request_policy" "origin_auth" {
  name            = "${var.project_name}-origin-auth"
  comment         = "Include custom header for origin authentication"

  headers_config {
    header_behavior = "whitelist"
    headers {
      items = [var.origin_custom_header_name]
    }
  }

  cookies_config {
    cookie_behavior = "none"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name} CDN distribution"
  default_root_object = "index.html"
  http_version        = "http2and3"  # HTTP/2 and HTTP/3 (QUIC) support

  # Primary Origin - Backend server/S3 for static and media files
  origin {
    domain_name            = var.origin_domain_name
    origin_id              = "thebot-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id

    custom_header {
      name  = var.origin_custom_header_name
      value = var.origin_custom_header_value
    }
  }

  # Geo-restriction for compliance (optional)
  dynamic "restrictions" {
    for_each = var.enable_geo_restrictions ? [1] : []
    content {
      geo_restriction {
        restriction_type = var.geo_restriction_type
        locations        = var.geo_restriction_locations
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = var.enable_geo_restrictions ? var.geo_restriction_type : "none"
      locations        = var.enable_geo_restrictions ? var.geo_restriction_locations : []
    }
  }

  # HTTPS-only with TLS 1.2+
  viewer_protocol_policy = "redirect-to-https"

  # Default cache behavior - applies to root and non-matching paths
  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods            = ["GET", "HEAD"]
    compress                  = true
    cache_policy_id           = aws_cloudfront_cache_policy.static_files.id
    origin_request_policy_id  = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy    = "redirect-to-https"

    # Forward request headers to origin for proper content negotiation
    function_associations {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.add_cache_headers.arn
    }
  }

  # Cache behavior for hashed assets (JS, CSS, images with hash in filename)
  # Pattern: /js/*.js, /css/*.css, /images/*.png, etc. with hash
  cache_behavior {
    path_pattern             = "/js/*-[a-f0-9]*.js"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods          = ["GET", "HEAD"]
    compress                = true
    cache_policy_id         = aws_cloudfront_cache_policy.hashed_assets.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy  = "redirect-to-https"

    function_associations {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.add_cache_headers.arn
    }
  }

  # Cache behavior for hashed CSS files
  cache_behavior {
    path_pattern             = "/css/*-[a-f0-9]*.css"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods          = ["GET", "HEAD"]
    compress                = true
    cache_policy_id         = aws_cloudfront_cache_policy.hashed_assets.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy  = "redirect-to-https"
  }

  # Cache behavior for hashed images
  cache_behavior {
    path_pattern             = "/images/*-[a-f0-9]*.*"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods          = ["GET", "HEAD"]
    compress                = true
    cache_policy_id         = aws_cloudfront_cache_policy.hashed_assets.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy  = "redirect-to-https"
  }

  # Cache behavior for fonts
  cache_behavior {
    path_pattern             = "/fonts/*"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods          = ["GET", "HEAD"]
    compress                = true
    cache_policy_id         = aws_cloudfront_cache_policy.hashed_assets.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy  = "redirect-to-https"

    function_associations {
      event_type   = "viewer-response"
      function_arn = aws_cloudfront_function.add_cors_headers.arn
    }
  }

  # Cache behavior for media files (user uploads) - requires signed URLs
  cache_behavior {
    path_pattern             = "/media/*"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods          = ["GET", "HEAD"]
    compress                = true
    cache_policy_id         = aws_cloudfront_cache_policy.media_files.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.origin_auth.id
    viewer_protocol_policy  = "redirect-to-https"

    # Trust Auth header for signed URL validation
    function_associations {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.validate_signed_urls.arn
    }
  }

  # Viewer certificate (HTTPS/TLS configuration)
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"  # TLS 1.2 minimum
  }

  # Logging (optional)
  logging_config {
    include_cookies = false
    bucket          = aws_s3_bucket.cloudfront_logs.bucket_domain_name
    prefix          = "cloudfront/"
  }

  # Error responses - serve index.html for SPA 404 errors
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-cdn"
  })

  depends_on = [
    aws_cloudfront_function.add_cache_headers,
    aws_cloudfront_function.add_cors_headers,
    aws_cloudfront_function.validate_signed_urls,
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# CloudFront Function - Add cache headers
resource "aws_cloudfront_function" "add_cache_headers" {
  name    = "${var.project_name}-add-cache-headers"
  runtime = "cloudfront-js-1.0"
  publish = true
  code    = file("${path.module}/functions/add-cache-headers.js")
}

# CloudFront Function - Add CORS headers for fonts
resource "aws_cloudfront_function" "add_cors_headers" {
  name    = "${var.project_name}-add-cors-headers"
  runtime = "cloudfront-js-1.0"
  publish = true
  code    = file("${path.module}/functions/add-cors-headers.js")
}

# CloudFront Function - Validate signed URLs for media files
resource "aws_cloudfront_function" "validate_signed_urls" {
  name    = "${var.project_name}-validate-signed-urls"
  runtime = "cloudfront-js-1.0"
  publish = true
  code    = file("${path.module}/functions/validate-signed-urls.js")
}

# S3 Bucket for CloudFront logs
resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "${var.project_name}-cloudfront-logs-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-cloudfront-logs"
  })
}

# S3 Bucket Versioning for logs
resource "aws_s3_bucket_versioning" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  versioning_configuration {
    status = "Suspended"  # No versioning needed for logs
  }
}

# S3 Bucket Server-side Encryption for logs
resource "aws_s3_bucket_server_side_encryption_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Lifecycle to clean up old logs
resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 90  # Keep logs for 90 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# S3 Bucket Public Access Block for security
resource "aws_s3_bucket_public_access_block" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Key Pair for signing media URLs
resource "aws_cloudfront_public_key" "media_signing" {
  name            = "${var.project_name}-media-key"
  comment         = "Public key for signing media file URLs"
  encoded_key     = file("${path.module}/keys/cloudfront-public-key.pem")
  depends_on      = [aws_cloudfront_distribution.main]

  tags = merge(var.tags, {
    Name = "${var.project_name}-media-signing-key"
  })
}

# CloudFront Key Group for media signing
resource "aws_cloudfront_key_group" "media_signing" {
  name    = "${var.project_name}-media-keys"
  comment = "Key group for signing media file URLs"
  items   = [aws_cloudfront_public_key.media_signing.id]
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# Outputs
output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.main.arn
}

output "cloudfront_key_group_id" {
  description = "CloudFront key group ID for signing media URLs"
  value       = aws_cloudfront_key_group.media_signing.id
}

output "cloudfront_public_key_id" {
  description = "CloudFront public key ID for signing media URLs"
  value       = aws_cloudfront_public_key.media_signing.id
}

output "s3_logs_bucket" {
  description = "S3 bucket for CloudFront logs"
  value       = aws_s3_bucket.cloudfront_logs.bucket
}
