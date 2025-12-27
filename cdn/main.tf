# Main Terraform configuration for THE_BOT Platform CDN

terraform {
  required_version = ">= 1.0"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }

  # Uncomment to use remote state
  # backend "s3" {
  #   bucket         = "thebot-terraform"
  #   key            = "cdn/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}

# Configure Cloudflare provider
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# ============================================================================
# LOCAL VARIABLES
# ============================================================================

locals {
  common_tags = {
    project     = "THE_BOT"
    environment = "production"
    managed_by  = "terraform"
    timestamp   = timestamp()
  }

  cache_rules = {
    static_assets = {
      patterns = ["*.css", "*.js", "*.woff", "*.woff2"]
      ttl      = 2592000
      stale    = 86400
    }
    images = {
      patterns = ["*.jpg", "*.png", "*.gif", "*.webp"]
      ttl      = 2592000
      stale    = 604800
    }
    media = {
      patterns = ["*.mp4", "*.webm", "*.mp3"]
      ttl      = 604800
      stale    = 86400
    }
  }
}

# ============================================================================
# DATA SOURCES
# ============================================================================

# Get current Cloudflare account
data "cloudflare_account" "primary" {
  name = var.cloudflare_account_name
}

# Get zone information
data "cloudflare_zone" "primary" {
  zone_id = var.cloudflare_zone_id
}

# ============================================================================
# MODULES
# ============================================================================

# Include all configuration from cloudflare.tf
# (The configurations from cloudflare.tf are included in the root module)

# ============================================================================
# LOCALS FOR MONITORING
# ============================================================================

locals {
  monitoring = {
    enabled              = true
    cache_metrics        = true
    performance_metrics  = true
    security_events      = true
    ddos_monitoring      = true
    bandwidth_tracking   = true
  }

  cache_strategies = {
    aggressive = {
      ttl_static = 2592000  # 30 days
      ttl_media  = 604800   # 7 days
      stale_ttl  = 86400    # 1 day
    }
    balanced = {
      ttl_static = 604800   # 7 days
      ttl_media  = 259200   # 3 days
      stale_ttl  = 86400    # 1 day
    }
    conservative = {
      ttl_static = 86400    # 1 day
      ttl_media  = 86400    # 1 day
      stale_ttl  = 0        # No stale
    }
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "cloudflare_account_id" {
  description = "Cloudflare account ID"
  value       = data.cloudflare_account.primary.id
}

output "cloudflare_zone_id" {
  description = "Cloudflare zone ID"
  value       = data.cloudflare_zone.primary.id
}

output "cloudflare_zone_status" {
  description = "Cloudflare zone status"
  value       = data.cloudflare_zone.primary.status
}

output "cloudflare_zone_name" {
  description = "Cloudflare zone name"
  value       = data.cloudflare_zone.primary.name
}

output "terraform_state" {
  description = "Terraform state summary"
  value = {
    version   = terraform.version
    timestamp = timestamp()
  }
}
