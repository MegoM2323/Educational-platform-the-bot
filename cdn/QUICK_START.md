# CDN Quick Start Guide

Fast setup guide for THE_BOT Platform Cloudflare CDN.

## 5-Minute Setup

### 1. Get Credentials

```bash
# Go to Cloudflare Dashboard
# https://dash.cloudflare.com

# Copy Zone ID (Overview page, bottom right)
# Create API Token (Profile > API Tokens)
# - Permissions: Zone:Read, Zone:Edit, Cache Purge
# - Resources: Include your domain
```

### 2. Set Environment

```bash
# Create environment file
cd /path/to/THE_BOT_platform/cdn
cp .env.example .env

# Edit .env with your values
# CLOUDFLARE_API_TOKEN=your_token
# CLOUDFLARE_ZONE_ID=your_zone_id
# DOMAIN_NAME=yourdomain.com
```

### 3. Deploy

```bash
# Initialize Terraform
terraform init

# Validate
terraform validate

# Deploy
terraform apply

# Done! CDN is live
```

## Verify It Works

```bash
# Test CDN
./test-cdn.sh https://yourdomain.com https://api.yourdomain.com

# Or manual checks
curl -I https://yourdomain.com/assets/app.js | grep Cache-Control
curl -I https://yourdomain.com | grep X-Content-Type-Options
```

## Common Commands

### Update Cache TTL

```bash
# Make CSS cache for 7 days instead of 30
terraform apply -var="cache_ttl_static=604800"
```

### Change Rate Limit

```bash
# Reduce login rate limit to 3 attempts
terraform apply -var="rate_limit_login=3"
```

### Purge Cache

```bash
# Via Dashboard: Caching > Purge Cache > Purge Everything
# Or via API:
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purge_everything": true}'
```

### View Analytics

```bash
# Open Dashboard
https://dash.cloudflare.com

# Go to: Analytics > Performance
# Key metrics: Cache hit ratio, response time, bandwidth
```

## Troubleshooting

**Cache not working?**
```bash
curl -I https://yourdomain.com/assets/app.js | grep X-Cache-Status
# If MISS: content may not be cacheable, check origin headers
```

**Getting 403 errors?**
```bash
# WAF may be blocking
# Check Dashboard > Security > Events > Managed Rules
# Temporarily disable: terraform apply -var="enable_waf=false"
```

**Slow responses?**
```bash
# Check origin: curl https://api.yourdomain.com
# Check cache: curl -I https://yourdomain.com | grep Cache-Control
# Check compression: curl -H "Accept-Encoding: gzip" -I https://yourdomain.com
```

## Next Steps

1. Review [README.md](README.md) for features
2. Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup
3. Setup [MONITORING.md](MONITORING.md) for alerts
4. Run [test-cdn.sh](test-cdn.sh) to verify
5. Configure alerts in Dashboard

## Support

- Docs: https://developers.cloudflare.com/
- Dashboard: https://dash.cloudflare.com
- Support: https://support.cloudflare.com
