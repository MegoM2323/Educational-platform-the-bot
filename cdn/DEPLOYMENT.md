# CDN Deployment Guide

Complete deployment guide for THE_BOT Platform Cloudflare CDN configuration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Account Setup](#account-setup)
3. [Terraform Setup](#terraform-setup)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Verification](#verification)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- Terraform >= 1.0
- Curl or similar HTTP client
- Bash shell
- AWS CLI (optional, for S3 logging)

### Required Accounts
- Cloudflare account (pro plan or higher recommended)
- AWS account (if using S3 logging)

### Required Information
- Cloudflare Zone ID
- Cloudflare API token with permissions:
  - Zone:Read
  - Zone:Edit
  - Cache Purge
  - Firewall:Edit
  - WAF:Edit
- Domain name under Cloudflare

## Account Setup

### 1. Create Cloudflare Account

1. Go to https://www.cloudflare.com
2. Sign up or log in
3. Add your domain (nameservers will be updated)
4. Wait for DNS propagation (can take 24 hours)

### 2. Get Zone ID

1. Log in to Cloudflare Dashboard
2. Select your domain
3. Copy Zone ID from the sidebar (right side of Overview tab)

### 3. Create API Token

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use template "Edit Cloudflare Workers" or create custom:
   - **Permissions**:
     - Zone:Read
     - Zone:Edit
     - Cache Purge
     - Firewall:Edit
     - WAF:Edit
   - **Zone Resources**: Include specific zone (your domain)
4. Copy the token (you won't see it again)

### 4. Verify API Token

```bash
export CLOUDFLARE_API_TOKEN="your_token_here"
export CLOUDFLARE_ZONE_ID="your_zone_id_here"

curl -X GET https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json"
```

Should return zone information.

## Terraform Setup

### 1. Initialize Terraform

```bash
cd /path/to/THE_BOT_platform/cdn

# Download provider
terraform init

# Should show:
# Terraform has been successfully configured!
```

### 2. Set Environment Variables

```bash
# Export Cloudflare credentials
export TF_VAR_cloudflare_api_token="your_api_token_here"
export TF_VAR_cloudflare_zone_id="your_zone_id_here"

# Verify
echo $TF_VAR_cloudflare_zone_id
```

### 3. Validate Configuration

```bash
# Syntax check
terraform validate

# Should show:
# Success! The configuration is valid.
```

### 4. Check for Errors

```bash
# Detailed validation
terraform fmt -check

# Should show no changes needed
```

## Configuration

### 1. Set Domain Configuration

Edit `terraform.tfvars`:

```hcl
cloudflare_zone_id = "abcdef1234567890"
domain_name        = "thebot.com"
origin_url         = "https://api.thebot.com"
frontend_origin    = "https://thebot.com"
```

### 2. Configure Cache Settings

Edit `terraform.tfvars` or use command-line variables:

```bash
# Conservative caching (1 day)
terraform plan \
  -var="cache_ttl_static=86400" \
  -var="cache_ttl_images=86400"

# Aggressive caching (30 days)
terraform plan \
  -var="cache_ttl_static=2592000" \
  -var="cache_ttl_images=2592000"
```

### 3. Configure Security

```bash
# Enable all security features
terraform plan \
  -var="enable_ddos_protection=true" \
  -var="enable_waf=true" \
  -var="enable_rate_limiting=true" \
  -var="enable_bot_management=true"
```

### 4. Configure Rate Limits

```bash
# Stricter rate limiting
terraform plan \
  -var="rate_limit_global=500" \
  -var="rate_limit_api=50" \
  -var="rate_limit_login=3"
```

### 5. Create Backend State (Optional)

For production, use remote state:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket thebot-terraform \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket thebot-terraform \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for locks
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

Uncomment backend configuration in `main.tf`:

```hcl
backend "s3" {
  bucket         = "thebot-terraform"
  key            = "cdn/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-locks"
}
```

Then run:

```bash
terraform init
```

## Deployment

### 1. Plan Deployment

```bash
# Review what will be created
terraform plan -out=tfplan

# Should show multiple resources to be created
# Example output:
# cloudflare_cache_rules.static_assets will be created
# cloudflare_firewall_rule.challenge_bots will be created
# cloudflare_rate_limit.login_limit will be created
# ... (30+ resources)
```

### 2. Review Plan

```bash
# Show detailed plan
terraform show tfplan | head -100

# Check resource count
terraform plan -out=tfplan | grep "Plan:"
```

### 3. Apply Configuration

```bash
# Apply the plan
terraform apply tfplan

# Should show:
# Apply complete! Resources: XX added, 0 changed, 0 destroyed.
```

### 4. Verify Deployment

```bash
# Show outputs
terraform output

# Check specific output
terraform output cloudflare_zone_id
terraform output cdn_status
terraform output cache_rules_status
```

### 5. Save State

```bash
# Backup state file
cp terraform.tfstate terraform.tfstate.backup

# Verify state
terraform state list | head -20
```

## Verification

### 1. Test CDN Configuration

```bash
# Run test script
./test-cdn.sh https://thebot.com https://api.thebot.com

# Or with custom domain
./test-cdn.sh https://yourdomain.com https://api.yourdomain.com
```

### 2. Verify Cache Working

```bash
# Check cache headers
curl -I https://thebot.com/assets/app.js | grep Cache-Control

# Expected output:
# Cache-Control: public, max-age=2592000, stale-while-revalidate=86400
```

### 3. Verify HTTPS/TLS

```bash
# Check TLS version
echo | openssl s_client -servername thebot.com -connect thebot.com:443 2>/dev/null | grep TLS

# Expected: TLSv1.2 or TLSv1.3
```

### 4. Verify Security Headers

```bash
# Check all security headers
curl -I https://thebot.com | grep -i "X-\|Strict-Transport-Security\|Content-Security-Policy"

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000
# Content-Security-Policy: ...
```

### 5. Check Dashboard

1. Log in to Cloudflare Dashboard
2. Go to your domain
3. Check sections:
   - **Caching**: Cache rules visible
   - **Firewall**: Rules active
   - **Security**: WAF rules enabled
   - **Performance**: Optimization features on
   - **Analytics**: Traffic data visible

## Monitoring

### 1. Setup Dashboard Alerts

In Cloudflare Dashboard:

1. Go to Notifications
2. Create alerts for:
   - Cache hit ratio drops below 70%
   - Error rate exceeds 1%
   - DDoS attack detected
   - WAF rule triggered 10+ times

### 2. Monitor Cache Performance

```bash
# Check cache hit ratio (via Dashboard API)
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { viewer { zones(first: 1) { edges { node { httpRequests1dGroups(first: 1) { edges { node { cache { cacheStatus count } } } } } } } } }"
  }'
```

### 3. Monitor DDoS Events

In Dashboard:
1. Go to Security > Events
2. Check DDoS Attack Events tab
3. Review blocked requests

### 4. Monitor WAF Events

In Dashboard:
1. Go to Security > Events
2. Check Managed Rules tab
3. Review triggered rules

### 5. Enable Logging

```bash
# Set up S3 logging
terraform apply \
  -var="enable_logpush=true" \
  -var="log_bucket_name=thebot-logs"

# Verify logs in S3
aws s3 ls s3://thebot-logs/cloudflare/http-requests/
```

## Troubleshooting

### Issue: Cache Not Working

```bash
# 1. Check cache rules
terraform show | grep -A5 "cloudflare_cache_rules"

# 2. Verify cache headers
curl -I https://thebot.com/assets/app.js | grep -i cache-control

# 3. Clear cache and retry
# Go to Dashboard > Caching > Purge Cache > Purge Everything

# 4. Check origin server
curl -I https://api.thebot.com/health
```

### Issue: Rate Limiting Not Working

```bash
# 1. Check rate limit rules
terraform show | grep -A5 "cloudflare_rate_limit"

# 2. Verify rule is applied
curl -I https://thebot.com/api/users | grep X-Rate-Limit

# 3. Test rate limit
for i in {1..10}; do curl -I https://thebot.com/api/users; done | grep -i "429\|429"
```

### Issue: WAF Blocking Legitimate Traffic

```bash
# 1. Check WAF events
# Dashboard > Security > Events > Managed Rules

# 2. Temporarily disable WAF
terraform apply -var="enable_waf=false"

# 3. Test application

# 4. Review blocked requests and adjust rules
# Dashboard > Security > WAF > Managed Rules > Edit
```

### Issue: Performance Issues

```bash
# 1. Check response times
curl -w "\nTime: %{time_total}s\n" -o /dev/null -s https://thebot.com

# 2. Check origin health
curl -I https://api.thebot.com/health

# 3. Check cache status
curl -I https://thebot.com/assets/app.js | grep X-Cache-Status

# 4. Review analytics
# Dashboard > Analytics > Performance
```

### Issue: Terraform State Issues

```bash
# Backup current state
cp terraform.tfstate terraform.tfstate.backup

# Show state
terraform state list

# Verify state matches infrastructure
terraform state show 'cloudflare_cache_rules.static_assets'

# Refresh state
terraform refresh

# If corrupted, restore backup
cp terraform.tfstate.backup terraform.tfstate
```

### Issue: API Token Errors

```bash
# Verify token is set
echo $TF_VAR_cloudflare_api_token

# Test token directly
curl -X GET https://api.cloudflare.com/client/v4/zones \
  -H "Authorization: Bearer $TF_VAR_cloudflare_api_token"

# Check token permissions
# https://dash.cloudflare.com/profile/api-tokens > Your Tokens

# Create new token if needed and set:
export TF_VAR_cloudflare_api_token="new_token"
```

## Maintenance

### Regular Tasks

**After Deployment**
- [ ] Run test suite: `./test-cdn.sh`
- [ ] Verify all features in Dashboard
- [ ] Set up monitoring alerts
- [ ] Document any custom settings

**Weekly**
- [ ] Check cache hit ratio (target: >80%)
- [ ] Review security events
- [ ] Monitor error rates

**Monthly**
- [ ] Analyze performance metrics
- [ ] Review and optimize cache rules
- [ ] Update Terraform if new version available
- [ ] Backup state files

**Quarterly**
- [ ] Full security audit
- [ ] Performance optimization review
- [ ] Test disaster recovery
- [ ] Update documentation

### Updating Configuration

```bash
# 1. Edit configuration
vi cloudflare.tf

# 2. Validate changes
terraform validate

# 3. Plan changes
terraform plan -out=tfplan

# 4. Review plan
terraform show tfplan

# 5. Apply changes
terraform apply tfplan

# 6. Verify changes
terraform output
```

### Rolling Back Changes

```bash
# 1. Restore previous state
cp terraform.tfstate.backup terraform.tfstate

# 2. Refresh terraform
terraform refresh

# 3. Apply previous state
terraform apply

# 4. Verify rollback
terraform output
```

## Support & Resources

### Documentation
- [Cloudflare Docs](https://developers.cloudflare.com/)
- [Terraform Cloudflare Provider](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs)

### Useful Links
- [Cloudflare Dashboard](https://dash.cloudflare.com)
- [API Tokens](https://dash.cloudflare.com/profile/api-tokens)
- [Zone Setup](https://dash.cloudflare.com/add-site)
- [Firewall Rules](https://dash.cloudflare.com/) (under Security)

### Contacting Support
- **Cloudflare**: https://support.cloudflare.com
- **Terraform**: https://discuss.hashicorp.com/

## Next Steps

1. Complete prerequisites
2. Create Cloudflare account and add domain
3. Get Zone ID and API token
4. Follow Configuration section
5. Run Deployment
6. Complete Verification
7. Set up Monitoring
8. Schedule maintenance tasks

## Success Checklist

- [ ] Cloudflare account created
- [ ] Domain added and DNS propagated
- [ ] Zone ID and API token obtained
- [ ] Terraform initialized and validated
- [ ] Configuration filled in (domain, URLs)
- [ ] Deployment plan reviewed
- [ ] Configuration applied
- [ ] Tests pass (./test-cdn.sh)
- [ ] Dashboard shows rules active
- [ ] Cache headers present
- [ ] Security headers present
- [ ] Monitoring alerts configured
- [ ] Documentation updated

Congratulations! Your CDN is now live!
