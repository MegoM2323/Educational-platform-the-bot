# THE_BOT Platform - Cloudflare CDN Configuration

Comprehensive Cloudflare CDN configuration for global content delivery, caching, security, and performance optimization.

## Features

### Content Delivery
- Global CDN with edge locations worldwide
- Smart caching based on content type
- Cache busting with query parameters
- Stale-while-revalidate support

### Caching Strategy
- **HTML**: Not cached (always fresh)
- **CSS/JS**: 30 days at edge, 1 hour in browser
- **Images**: 30 days at edge, 1 day in browser
- **Media**: 7 days at edge
- **API**: Not cached (respects Cache-Control headers)
- **Fonts**: 30 days at edge

### Performance Optimization
- Gzip and Brotli compression
- CSS, JS, HTML minification
- WebP image optimization with responsive sizing
- HTTP/3 (QUIC) support
- Early Hints for critical resources
- Server Push for preloading

### Security Features
- DDoS protection (Layer 3/4/7)
- Web Application Firewall (WAF) with OWASP ModSecurity rules
- Bot management and detection
- Rate limiting (global, API, login)
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- HTTPS enforcement (TLS 1.2+)

### Monitoring & Analytics
- Real-time analytics dashboard
- Cache hit rate tracking
- Performance metrics (response time, bandwidth)
- DDoS attack monitoring
- HTTP request logging
- Custom alerts

## Installation

### Prerequisites
- Terraform >= 1.0
- Cloudflare account with API token
- Zone ID for your domain
- AWS S3 bucket (optional, for logs)

### Setup Steps

1. **Clone and navigate to cdn directory**
   ```bash
   cd /path/to/THE_BOT_platform/cdn
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your Cloudflare credentials
   ```

3. **Initialize Terraform**
   ```bash
   terraform init
   ```

4. **Validate configuration**
   ```bash
   terraform validate
   terraform plan
   ```

5. **Apply configuration**
   ```bash
   terraform apply
   ```

## Configuration

### Environment Variables

Create `.env` file with your settings:

```bash
# Cloudflare credentials
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_ZONE_ID=your_zone_id_here

# Domain configuration
DOMAIN_NAME=thebot.com
ORIGIN_URL=https://api.thebot.com
FRONTEND_ORIGIN=https://thebot.com

# Feature flags
ENABLE_ADVANCED_CACHE=false
COMPRESSION_ENABLED=true
MINIFICATION_ENABLED=true
HTTP3_ENABLED=true

# Cache TTL (in seconds)
CACHE_TTL_STATIC=2592000    # 30 days
CACHE_TTL_IMAGES=2592000    # 30 days
CACHE_TTL_MEDIA=604800      # 7 days

# Rate limiting
RATE_LIMIT_GLOBAL=1000      # requests per minute
RATE_LIMIT_API=100          # requests per minute
RATE_LIMIT_LOGIN=5          # requests per minute
```

### Terraform Variables

Edit `terraform.tfvars`:

```hcl
cloudflare_zone_id = "your_zone_id"
domain_name        = "thebot.com"
origin_url         = "https://api.thebot.com"
frontend_origin    = "https://thebot.com"

# Optional: set via environment
# export TF_VAR_cloudflare_api_token="your_token"
```

## Deployment

### Full Deployment
```bash
# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# View outputs
terraform output
```

### Partial Deployment
```bash
# Deploy only cache rules
terraform apply -target=cloudflare_cache_rules.static_assets

# Deploy only security rules
terraform apply -target=cloudflare_firewall_rule.challenge_bots
```

### Update Configuration
```bash
# Change cache TTL
terraform apply -var="cache_ttl_static=604800"

# Change rate limits
terraform apply -var="rate_limit_api=200"
```

## Cache Configuration

### Cache Strategies

**Aggressive** (Default)
- Static assets: 30 days
- Media: 7 days
- Stale: 1 day

```bash
terraform apply -var="cache_strategy=aggressive"
```

**Balanced**
- Static assets: 7 days
- Media: 3 days
- Stale: 1 day

```bash
terraform apply -var="cache_strategy=balanced"
```

**Conservative**
- Static assets: 1 day
- Media: 1 day
- Stale: 0 (disabled)

```bash
terraform apply -var="cache_strategy=conservative"
```

### Cache Busting

Add query parameters to bypass cache:
```
https://thebot.com/assets/app.js?v=2.0.1
https://thebot.com/images/logo.png?bust=2024
https://thebot.com/style.css?cachebust=abc123
```

Supported parameters: `v`, `version`, `bust`, `cachebust`

## Security Configuration

### WAF Rules

Enabled by default:
- OWASP ModSecurity Core Rule Set
- SQL Injection protection
- XSS (Cross-Site Scripting) protection
- Request smuggling protection
- Protocol attack protection

### Rate Limiting

Configured endpoints:
- **Global**: 1000 requests/minute (24h ban)
- **API**: 100 requests/minute (1h ban)
- **Login**: 5 requests/minute (30min ban)

### DDoS Protection

Automatically enabled:
- Layer 3/4 DDoS protection (Cloudflare Always On)
- Layer 7 DDoS protection
- Bot management
- Challenge suspicious traffic
- Block malicious IPs

## Monitoring

### Dashboard Access
- **Cloudflare Dashboard**: https://dash.cloudflare.com
- **Analytics**: Dashboard > Analytics > Performance

### Key Metrics
- Cache hit ratio
- Average response time
- Bandwidth usage
- DDoS attacks blocked
- WAF rules triggered
- Rate limits hit

### Alerts
Configure in Cloudflare Dashboard:
- Cache hit ratio drops below 70%
- Response time exceeds 1 second
- DDoS attack detected
- WAF rule triggered >10x/min

### Logging

Real-time logs available via:
```bash
# Logpush to S3
terraform apply -var="enable_logpush=true"

# GraphQL Analytics API
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -d @query.json
```

## Testing

### Health Checks

**Check CDN Status**
```bash
# Should return 200
curl -i https://thebot.com

# Check cache headers
curl -i https://thebot.com/assets/app.js | grep -i cache

# Check security headers
curl -i https://thebot.com | grep -i "X-"
```

**Verify Caching**
```bash
# First request (cache miss)
curl -i https://thebot.com/images/logo.png | grep X-Cache-Status
# Should show MISS

# Second request (cache hit)
curl -i https://thebot.com/images/logo.png | grep X-Cache-Status
# Should show HIT
```

**Test Compression**
```bash
# Should have Content-Encoding: gzip
curl -i -H "Accept-Encoding: gzip" https://thebot.com | grep Content-Encoding
```

**Verify HTTPS**
```bash
# Should show TLS 1.2+
curl -i https://thebot.com | grep TLS

# Check certificate
echo | openssl s_client -servername thebot.com -connect thebot.com:443 2>/dev/null | openssl x509 -text -noout
```

### Load Testing

```bash
# Using ApacheBench
ab -n 1000 -c 100 https://thebot.com

# Using wrk
wrk -t4 -c100 -d30s https://thebot.com

# Using k6
k6 run performance-test.js
```

### Cache Testing Script

```bash
#!/bin/bash
# test-cache.sh

URL="https://thebot.com/assets/app.js"

echo "=== Cache Testing ==="

# Test 1: Initial request
echo -e "\n1. Initial request (expect MISS):"
curl -s -I "$URL" | grep -i cache-status

# Test 2: Second request
echo -e "\n2. Cached request (expect HIT):"
curl -s -I "$URL" | grep -i cache-status

# Test 3: Cache busting
echo -e "\n3. Cache busted (expect MISS):"
curl -s -I "$URL?v=2" | grep -i cache-status

# Test 4: Compression
echo -e "\n4. Compression check:"
curl -s -I -H "Accept-Encoding: gzip" "$URL" | grep -i content-encoding

# Test 5: Performance
echo -e "\n5. Response time:"
time curl -s "$URL" > /dev/null
```

### Rate Limit Testing

```bash
#!/bin/bash
# test-rate-limit.sh

API_URL="https://thebot.com/api/users"

echo "=== Rate Limit Testing ==="

for i in {1..10}; do
  echo "Request $i:"
  curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" "$API_URL"
  sleep 0.5
done
```

### Security Testing

```bash
# Test WAF - SQL Injection
curl "https://thebot.com/api/search?q='; DROP TABLE users; --"
# Should return 403 Forbidden

# Test Rate Limiting - Login
for i in {1..10}; do
  curl -X POST "https://thebot.com/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}' \
    -w "\nStatus: %{http_code}\n"
done
# After 5 attempts should get 429 Too Many Requests
```

## Troubleshooting

### Cache Not Working

1. **Check cache headers**
   ```bash
   curl -i https://thebot.com/assets/app.js | grep -i cache-control
   ```

2. **Verify cache rules**
   ```bash
   terraform show | grep -i cache
   ```

3. **Check browser cache**
   ```bash
   # Clear cache in Cloudflare Dashboard
   # Cache > Purge Cache > Purge Everything
   ```

### Performance Issues

1. **Check response time**
   ```bash
   curl -o /dev/null -s -w "%{time_starttransfer}\n" https://thebot.com
   ```

2. **Monitor bandwidth**
   - Dashboard > Analytics > Bandwidth

3. **Check origin health**
   ```bash
   # Verify origin server responds quickly
   curl -i https://api.thebot.com/health
   ```

### Security Alerts

1. **Check WAF logs**
   - Dashboard > Security > Events

2. **Review rate limiting**
   - Dashboard > Security > Rate limiting

3. **Monitor DDoS**
   - Dashboard > Analytics > DDoS

### API Errors

1. **401 Unauthorized**
   ```bash
   # Check API token
   echo $CLOUDFLARE_API_TOKEN

   # Verify token permissions
   # https://dash.cloudflare.com/profile/api-tokens
   ```

2. **404 Zone not found**
   ```bash
   # Verify zone ID
   echo $CLOUDFLARE_ZONE_ID

   # List zones
   curl -X GET https://api.cloudflare.com/client/v4/zones \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
   ```

3. **Timeout errors**
   ```bash
   # Check network connectivity
   ping api.cloudflare.com

   # Try again with longer timeout
   terraform plan -parallelism=1
   ```

## Maintenance

### Regular Tasks

**Weekly**
- Monitor cache hit rate (target: >80%)
- Check error rates (target: <0.1%)
- Review security events

**Monthly**
- Analyze performance metrics
- Update cache rules if needed
- Review rate limiting effectiveness
- Check for unused rules

**Quarterly**
- Security audit
- Performance optimization
- Update Terraform version
- Backup state files

### Updating Rules

```bash
# Edit terraform files
vi cloudflare.tf

# Plan changes
terraform plan

# Apply changes
terraform apply
```

### Backup and Restore

```bash
# Backup current state
terraform state pull > terraform.tfstate.backup

# Restore from backup
terraform state push terraform.tfstate.backup
```

## Cost Optimization

### Recommendations

1. **Cache aggressively** - Increases cache hit ratio, reduces origin load
2. **Enable compression** - Reduces bandwidth usage (saves 60-80%)
3. **Use image optimization** - Reduces image size (saves 30-50%)
4. **Set appropriate TTLs** - Balance freshness vs. origin load

### Cost Estimation

Monthly costs (approximate):
- **Pro Plan**: $200/month + usage
- **Business Plan**: $200/month + usage
- **Enterprise**: Custom pricing

Bandwidth savings:
- Cache hit ratio 80%: 80% bandwidth reduction
- Compression enabled: 60% size reduction
- Image optimization: 30% size reduction

## Support

### Documentation
- [Cloudflare Documentation](https://developers.cloudflare.com/)
- [Terraform Cloudflare Provider](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs)

### Community
- [Cloudflare Community](https://community.cloudflare.com/)
- [Terraform Community](https://discuss.hashicorp.com/c/terraform/)

### Getting Help

1. Check logs: `terraform logs`
2. Enable debug: `TF_LOG=DEBUG terraform plan`
3. Contact Cloudflare support: https://support.cloudflare.com
4. Review plan documents: `terraform plan -out=tfplan && cat tfplan`

## Files Overview

- `cloudflare.tf` - Main Cloudflare configuration (caching, security, WAF)
- `main.tf` - Terraform configuration and data sources
- `variables.tf` - Variable definitions with validation
- `terraform.tfvars` - Variable values
- `.env.example` - Environment variables template
- `workers/cache-worker.js` - Cloudflare Workers script
- `README.md` - This file

## Next Steps

1. Set up Cloudflare account and domain
2. Configure API token with Zone and Cache Purge permissions
3. Copy `.env.example` to `.env` and fill in values
4. Run `terraform init && terraform plan`
5. Apply configuration: `terraform apply`
6. Monitor dashboard and verify caching/security
7. Run test scripts to verify functionality
8. Set up alerts for monitoring

## Version History

- **v1.0.0** (Dec 2024) - Initial release
  - Caching strategy implementation
  - Security rules and WAF
  - Rate limiting
  - Performance optimization
  - Monitoring setup
