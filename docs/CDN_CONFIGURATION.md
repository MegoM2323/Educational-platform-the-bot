# CDN Configuration Guide

CloudFront CDN configuration for THE_BOT Platform providing fast, reliable delivery of static assets and media files with automatic cache invalidation.

## Overview

This guide covers:
- CloudFront distribution setup via Terraform
- Cache policies for different asset types
- Signed URL generation for secure media access
- Cache invalidation strategies
- Cost optimization
- Monitoring and troubleshooting

## Architecture

```
Frontend Build (Vite)
        ↓
   Hashed Assets
  (app-abc123.js)
        ↓
   CloudFront CDN
   ├── Static Cache (1 year for hashed)
   ├── Media Cache (7 days, signed URLs)
   └── Origin (Backend)
        ↓
  User Downloads
 100x faster!
```

## Quick Start

### 1. Deploy CloudFront Distribution

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars with your settings
cat > terraform.tfvars << EOF
origin_domain_name             = "api.thebot.com"
origin_custom_header_value     = "$(openssl rand -base64 32)"
enable_geo_restrictions        = false
EOF

# Review and apply
terraform plan
terraform apply
```

### 2. Capture CloudFront Outputs

After deployment, save these outputs:

```bash
# Get outputs from Terraform
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name)
CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
CLOUDFRONT_KEY_GROUP_ID=$(terraform output -raw cloudfront_key_group_id)

echo "Add to .env:"
echo "CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN"
echo "CLOUDFRONT_DISTRIBUTION_ID=$CLOUDFRONT_DISTRIBUTION_ID"
```

### 3. Configure Environment

Update `.env` file:

```bash
# CDN Settings
CDN_ENABLED=true
CDN_PROVIDER=cloudfront
CLOUDFRONT_DOMAIN=d123456.cloudfront.net
CLOUDFRONT_DISTRIBUTION_ID=E123ABC456
CLOUDFRONT_ORIGIN_VERIFY_TOKEN=your-secret-token-here

# Frontend CDN
VITE_CDN_ENABLED=true
VITE_CDN_DOMAIN=d123456.cloudfront.net
```

### 4. Build and Deploy

```bash
# Frontend - build with CDN URLs
cd frontend
VITE_CDN_ENABLED=true VITE_CDN_DOMAIN=d123456.cloudfront.net npm run build

# Backend - collect static files
cd backend
python manage.py collectstatic --noinput

# Invalidate cache
../scripts/cdn/invalidate-cache.sh --distribution-id E123ABC456 --all
```

## Cache Configuration

### Asset Types and TTLs

| Asset Type | Pattern | TTL | Cache Policy |
|-----------|---------|-----|--------------|
| Hashed JS | `/js/*-[a-f0-9]*.js` | 1 year | Immutable |
| Hashed CSS | `/css/*-[a-f0-9]*.css` | 1 year | Immutable |
| Hashed Images | `/images/*-[a-f0-9]*.*` | 1 year | Immutable |
| Fonts | `/fonts/*` | 1 year | Immutable |
| Static Files | `/static/*` | 30 days | Must-revalidate |
| Media Files | `/media/*` | 7 days | Signed URLs |
| HTML | `/index.html` | 1 hour | Must-revalidate |

### How Cache Busting Works

**Hashed Assets** (recommended):
```
Vite build output:
  app.js → app-abc12345.js
  styles.css → styles-def67890.css

Browser cache:
  - First visit: Downloads app-abc12345.js (cached 1 year)
  - Update: New hash app-xyz98765.js (different URL, new download)
  - No manual invalidation needed!
```

**Non-hashed Assets**:
```
Query string based:
  /styles.css?v=1.2.3 → Cache miss
  /styles.css?v=1.2.4 → Invalidate, new download
```

## Static Assets Configuration

### Frontend Build Setup

The Vite configuration automatically handles CDN URLs:

```typescript
// vite.config.ts

// CDN is enabled via environment variables
const cdnConfig = {
  enabled: process.env.VITE_CDN_ENABLED === 'true',
  domain: process.env.VITE_CDN_DOMAIN || '',
  basePath: '/static/',
};

// Base URL automatically set for production builds
base: isBuild && cdnConfig.enabled && cdnConfig.domain
  ? `https://${cdnConfig.domain}${cdnConfig.basePath}`
  : '/'
```

### Build Command

```bash
# Build with CDN URLs
VITE_CDN_ENABLED=true \
VITE_CDN_DOMAIN=d123456.cloudfront.net \
npm run build

# Output files have hashes:
# dist/
# ├── js/
# │   ├── app-abc12345.js         (cached 1 year)
# │   ├── vendor-def67890.js       (cached 1 year)
# │   └── ...
# ├── css/
# │   └── app-xyz98765.css         (cached 1 year)
# └── index.html                   (cached 1 hour)
```

### Collecting Static Files

```bash
cd backend

# Collect from frontend build
python manage.py collectstatic --noinput

# Files served via CloudFront
# https://d123456.cloudfront.net/static/js/app-abc12345.js
# https://d123456.cloudfront.net/static/css/app-xyz98765.css
```

## Media Files Configuration

### Signed URLs for Security

Media files (user uploads) require signed URLs to ensure:
- Only authorized users can access files
- Files can't be accessed directly via static URLs
- Downloads are tracked and audited

### Signed URL Generation

**In Django:**

```python
from config.cdn_settings import get_signed_media_url

# Generate signed URL (valid for 1 hour)
user_file_path = 'uploads/user_123/document.pdf'
signed_url = get_signed_media_url(user_file_path)

# URL format:
# https://d123456.cloudfront.net/media/uploads/user_123/document.pdf?
#   Policy=...&Signature=...&Key-Pair-Id=APKAJ7...
```

**In Templates:**

```django
{% load cdn_tags %}

{# Using template filter #}
<a href="{{ 'uploads/user_123/document.pdf'|signed_media_url }}">
  Download Document
</a>

{# Get unsigned URL (requires signed URL separately) #}
<img src="{{ media_file|media_url }}" />
```

**In API Responses:**

```python
# views.py
from config.cdn_settings import get_signed_media_url

class FileDetailView(APIView):
    def get(self, request, pk):
        file_obj = File.objects.get(pk=pk)

        return Response({
            'id': file_obj.id,
            'name': file_obj.name,
            'url': get_signed_media_url(str(file_obj.file)),
            'size': file_obj.file.size,
            'created_at': file_obj.created_at,
        })
```

### Setting TTL for Signed URLs

Configure in `.env`:

```bash
# Signed URL validity (seconds)
SIGNED_URL_TTL_SECONDS=3600  # 1 hour

# Increase for long-lived URLs (e.g., shared links)
SIGNED_URL_TTL_SECONDS=2592000  # 30 days
```

### Programmatic TTL Override

```python
from config.cdn_settings import cdn_config

# Generate URL valid for 24 hours
signed_url = cdn_config.sign_url(url, expires_in=86400)
```

## Cache Invalidation

### Manual Invalidation

Invalidate specific paths:

```bash
# Invalidate static assets after deployment
./scripts/cdn/invalidate-cache.sh \
  --distribution-id E123ABC456 \
  --paths "/static/*" "/assets/*" "/index.html"

# Invalidate media files (rarely needed)
./scripts/cdn/invalidate-cache.sh \
  --distribution-id E123ABC456 \
  --paths "/media/*"
```

### Invalidate All (Full Distribution)

```bash
# Use with caution - costs $0.005 per path!
./scripts/cdn/invalidate-cache.sh \
  --distribution-id E123ABC456 \
  --all
```

### Programmatic Invalidation

```python
from config.cdn_settings import cdn_config

# Invalidate after deployment
cdn_config.invalidate_cache(paths=[
    '/static/js/*',
    '/static/css/*',
    '/index.html'
])

# Or invalidate all
cdn_config.invalidate_cache(all_paths=True)
```

### Invalidation Strategy

**After Frontend Deployment**:
```bash
# Only invalidate changed paths (optimal)
./scripts/cdn/invalidate-cache.sh \
  --paths "/index.html" "/static/*"
```

**After Backend/Media Update**:
```bash
# Invalidate media if needed
./scripts/cdn/invalidate-cache.sh \
  --paths "/media/*"
```

**Emergency/Full Invalidation**:
```bash
# Full distribution (expensive, $0.005 per path)
./scripts/cdn/invalidate-cache.sh --all
```

## Cost Optimization

### Current Configuration

| Metric | Cost | Optimization |
|--------|------|--------------|
| Data transfer | $0.085/GB | Enable compression, CDN hit rate |
| HTTP requests | $0.0075/10k | Combine assets, caching |
| Invalidation | $0.005/path | Batch operations, hash-based busting |

### Cost Reduction Tips

1. **Maximize Cache Hit Rates**
   ```
   Current target: 90%+
   - Use hash-based file names
   - Set appropriate TTLs
   - Monitor CloudWatch metrics
   ```

2. **Enable Compression**
   ```
   Enabled: gzip, brotli
   Reduction: 70% for text assets
   ```

3. **Minimize Invalidations**
   ```
   Before: Invalidate /static/* (1000 paths)
   After: Invalidate only /index.html + /static/app-*.js

   Savings: 95% reduction in invalidation costs
   ```

4. **Batch Operations**
   ```bash
   # Script automatically batches invalidations
   # AWS limit: 3000 paths per request
   # Script handles > 3000 paths automatically
   ```

5. **Optimize Asset Sizes**
   - Minify JS/CSS
   - Compress images
   - Code splitting (done by Vite)

### Cost Monitoring

Check CloudFront costs in AWS Console:
```
AWS Console → CloudFront → Distribution → Monitor
  ├── Data transferred to internet
  ├── Data transferred to origin
  ├── HTTP requests (weighted by method)
  ├── Invalidation requests
  └── Cache hit rate %
```

Set billing alerts:

```bash
# AWS CLI
aws cloudwatch put-metric-alarm \
  --alarm-name cdn-high-cost \
  --alarm-description "CloudFront exceeds $500/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold
```

## Monitoring

### CloudWatch Metrics

Key metrics to monitor:

```
Requests → Bytes Downloaded → Cache Hit Rate
  4xx/5xx → Origin Latency → Edge Location
```

### Check Cache Hit Rate

```bash
# Via AWS CLI
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=E123ABC456 \
  --start-time 2025-12-25T00:00:00Z \
  --end-time 2025-12-27T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Monitor via CloudFront Logs

CloudFront logs are stored in S3:
```
s3://thebot-cloudfront-logs-123456789012/cloudfront/
  └── 2025-12-27/
      └── E123ABC456.*.gz
```

Download and analyze:
```bash
# Download recent logs
aws s3 sync \
  s3://thebot-cloudfront-logs-123456789012/cloudfront/2025-12-27/ \
  ./logs/

# Analyze with tools
gunzip logs/*.gz
tail -100 logs/* | grep "404"  # Check for missing files
```

## Troubleshooting

### Issue: 403 Forbidden from Origin

**Cause**: Origin authentication header missing

**Solution**:
```bash
# Verify header is configured in Terraform
terraform output cloudfront_domain_name

# Check origin is accepting requests
curl -H "X-Origin-Verify: your-token" \
  https://api.thebot.com/static/

# If still failing:
# 1. Verify CLOUDFRONT_ORIGIN_VERIFY_TOKEN matches in backend
# 2. Ensure origin is not blocking CloudFront IPs
# 3. Check security groups and WAF rules
```

### Issue: 404 Not Found

**Cause**: File not on origin or incorrect path

**Solution**:
```bash
# Check file exists on origin
curl https://api.thebot.com/static/js/app-abc123.js -H "X-Origin-Verify: token"

# Verify static files were collected
backend/staticfiles/js/  # Should exist

# Re-collect static files
cd backend
python manage.py collectstatic --noinput

# Invalidate cache
./scripts/cdn/invalidate-cache.sh --all
```

### Issue: Signed URLs Not Working for Media

**Cause**: Missing private key or misconfigured signing

**Solution**:
```bash
# Verify private key exists
ls -la /etc/secrets/cloudfront-private-key.pem

# Check permissions
chmod 600 /etc/secrets/cloudfront-private-key.pem

# Test signing in Python shell
python manage.py shell
>>> from config.cdn_settings import cdn_config
>>> url = cdn_config.sign_url('https://d123456.cloudfront.net/media/test.pdf')
>>> print(url)

# If error, check:
# 1. CLOUDFRONT_PRIVATE_KEY_PATH is set
# 2. CLOUDFRONT_PUBLIC_KEY_ID is set
# 3. Key pair matches in Terraform
```

### Issue: High Error Rates (4xx/5xx)

**Cause**: Origin issues, misconfiguration, or origin overload

**Solution**:
```bash
# Check origin health
curl -I https://api.thebot.com/health/

# Check CloudFront distribution health
aws cloudfront get-distribution \
  --id E123ABC456 \
  --query 'Distribution.Status'

# Monitor origin requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name OriginLatency \
  --dimensions Name=DistributionId,Value=E123ABC456 \
  --start-time 2025-12-25T00:00:00Z \
  --end-time 2025-12-27T00:00:00Z \
  --period 60 \
  --statistics Average,Maximum
```

### Issue: Cache Hit Rate Low (< 80%)

**Cause**: Incorrect cache headers, query strings, or cookies

**Solution**:
```bash
# Check cache headers from origin
curl -I https://api.thebot.com/static/js/app-abc123.js

# Should see:
# Cache-Control: public, max-age=31536000, immutable
# Vary: Accept-Encoding

# If missing headers:
# 1. Update backend CDN middleware
# 2. Configure origin to set correct headers
# 3. Check Terraform functions add-cache-headers.js

# Verify Vite is generating hashes
ls frontend/dist/js/  # Should be: app-abc123.js, not app.js
```

## Integration Examples

### React Component with CDN

```typescript
import { useState, useEffect } from 'react';

const CDNAsset = ({ path, alt }: { path: string; alt: string }) => {
  const cdnDomain = import.meta.env.VITE_CDN_DOMAIN;
  const cdnEnabled = import.meta.env.VITE_CDN_ENABLED === 'true';

  const getAssetUrl = (assetPath: string) => {
    if (!cdnEnabled || !cdnDomain) {
      return `/static/${assetPath}`;
    }
    return `https://${cdnDomain}/static/${assetPath}`;
  };

  return (
    <img
      src={getAssetUrl(path)}
      alt={alt}
      loading="lazy"
      decoding="async"
    />
  );
};

export default CDNAsset;
```

### Django Template Tag

```django
{% load cdn_tags %}

<!-- Static assets (auto-CDN URL) -->
<link rel="stylesheet" href="{% cdn_url 'css/style.css' %}">
<script src="{% cdn_url 'js/app.js' %}"></script>

<!-- Media with signed URL -->
<a href="{% signed_media_url file.path %}">
  Download {{ file.name }}
</a>

<!-- Image with CDN and lazy loading -->
<img src="{% cdn_url 'images/logo.png' %}"
     loading="lazy"
     decoding="async">
```

### API Response with Signed URLs

```python
# serializers.py
from config.cdn_settings import get_signed_media_url

class DocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('id', 'name', 'size', 'created_at', 'download_url')

    def get_download_url(self, obj):
        if obj.file:
            return get_signed_media_url(str(obj.file))
        return None
```

## Security Considerations

### Access Control

1. **Static Assets**: Public, no authentication required
   ```
   Anyone can access via CDN
   ```

2. **Media Files**: Requires signed URL
   ```
   Only users with valid signature can access
   Signature tied to: URL, expiration, key pair
   ```

3. **Origin Protection**: Custom header validation
   ```
   X-Origin-Verify header required
   Prevents direct origin access bypassing CDN
   ```

### HTTPS/TLS Requirements

- All connections use HTTPS
- Minimum TLS 1.2
- CloudFront manages certificates
- Automatic certificate renewal

### Rate Limiting

CloudFront doesn't have built-in rate limiting. Implement in origin:

```python
# Django throttling
from rest_framework.throttling import AnonRateThrottle

class CDNThrottle(AnonRateThrottle):
    scope = 'cdn'
    rate = '1000/hour'  # Per IP address
```

## Next Steps

1. Deploy CloudFront distribution
2. Update environment variables
3. Test static asset delivery
4. Build frontend with CDN URLs
5. Monitor cache metrics
6. Set up billing alerts
7. Implement origin rate limiting
8. Enable CloudFront logs analysis

## References

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [CloudFront Functions Documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html)
- [Vite Build Configuration](https://vitejs.dev/guide/build.html)
- [Django Static Files](https://docs.djangoproject.com/en/5.2/howto/static-files/)
- [Signed URLs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html)

## Support

For CDN configuration issues:
1. Check CloudFront distribution status
2. Review CloudFront logs in S3
3. Monitor CloudWatch metrics
4. Check origin health
5. Verify environment variables
6. Review Terraform configuration
7. Contact AWS support for infrastructure issues
