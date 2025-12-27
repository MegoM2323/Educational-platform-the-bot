# Cloudflare CDN Terraform Variables
# Copy and update with your actual values

cloudflare_zone_id = "your_cloudflare_zone_id_here"
domain_name        = "thebot.com"
origin_url         = "https://api.thebot.com"
frontend_origin    = "https://thebot.com"

# Set via environment variable for security:
# export TF_VAR_cloudflare_api_token="your_api_token_here"
