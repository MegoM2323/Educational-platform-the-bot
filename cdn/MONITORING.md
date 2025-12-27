# CDN Monitoring & Analytics Guide

Complete monitoring and analytics guide for THE_BOT Platform CDN.

## Table of Contents

1. [Cloudflare Dashboard](#cloudflare-dashboard)
2. [Key Metrics](#key-metrics)
3. [Monitoring Alerts](#monitoring-alerts)
4. [Analytics API](#analytics-api)
5. [Logs & Events](#logs--events)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting & Optimization](#troubleshooting--optimization)

## Cloudflare Dashboard

### Overview Dashboard

Navigate to: https://dash.cloudflare.com > Your Domain > Overview

**Key Information Displayed:**
- Traffic status (requests/min)
- Cache status (hits/misses)
- WAF activity
- DDoS mitigation
- DNS status

**Navigation Menu:**
- **Analytics**: Traffic, performance, security data
- **Caching**: Cache status, purge cache, rules
- **Firewall**: WAF, rate limiting, IP filtering
- **Security**: DDoS, bot management, security events
- **Performance**: Core Web Vitals, optimization
- **Workers**: Edge computing scripts
- **Logs**: Real-time HTTP request logs

## Key Metrics

### Cache Metrics

**Cache Hit Ratio**
- **Target**: >80% (indicates healthy caching)
- **Too low** (<60%): Review cache rules, increase TTLs
- **Fluctuating**: May indicate dynamic content or cache misses due to query parameters

```bash
# API to get cache stats (GraphQL)
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { viewer { zones(first: 1) { edges { node { name httpRequests1dGroups(first: 1) { edges { node { cache { cachedRequests uncachedRequests } } } } } } } } }"
  }'
```

### Performance Metrics

**Core Web Vitals**
- **LCP** (Largest Contentful Paint): <2.5s (good)
- **FID** (First Input Delay): <100ms (good)
- **CLS** (Cumulative Layout Shift): <0.1 (good)

**Page Load Performance**
- **First Byte**: <200ms (excellent)
- **Page Load**: <1s for cached, <2s for dynamic
- **Time to Interactive**: <3s

**Available in Dashboard**: Analytics > Performance > Web Vitals

### Security Metrics

**DDoS Attacks**
- Attack count
- Traffic mitigated
- Attack patterns
- Attack timeline

**WAF Activity**
- Rules triggered
- Blocked requests
- Top attack types
- Threat scoring

**Rate Limiting**
- Requests blocked
- By endpoint
- Time-based trends

**Available in Dashboard**: Security > Events

### Bandwidth Metrics

**Cache Impact**
- Total bandwidth
- Cache savings (%)
- Compression reduction (%)
- Bandwidth saved

Formula:
```
Bandwidth Saved = (Bytes Served from Cache) * (1 - Compression Ratio)
Monthly Savings = Cache Savings * Monthly Traffic
```

## Monitoring Alerts

### Setup Cloudflare Alerts

Navigate to: Notifications > Create Alert

**Alert Types Available:**

1. **Cache Performance**
   ```
   Type: Cache Hit Ratio drops below
   Threshold: 70%
   Condition: Over 1 hour
   Action: Email notification
   ```

2. **Error Rate**
   ```
   Type: Error Rate (5xx) exceeds
   Threshold: 1%
   Condition: Over 5 minutes
   Action: Email + PagerDuty
   ```

3. **DDoS Detection**
   ```
   Type: DDoS Attack detected
   Threshold: Any attack
   Condition: Real-time
   Action: Email + Slack + PagerDuty
   ```

4. **WAF Activity**
   ```
   Type: Managed Rules triggered
   Threshold: >10 in 5 minutes
   Condition: 5-minute window
   Action: Email notification
   ```

5. **SSL Certificate**
   ```
   Type: SSL certificate expires in
   Threshold: 30 days
   Condition: Time-based
   Action: Email notification
   ```

6. **Origin Unreachable**
   ```
   Type: Origin is unreachable
   Threshold: Any
   Condition: Real-time
   Action: Email + PagerDuty
   ```

### Integration with Slack

1. Go to Notifications > Webhooks
2. Click "Create Webhook"
3. Enter Slack webhook URL
4. Configure alert rules to use Slack

### Integration with PagerDuty

1. Go to Notifications
2. Click PagerDuty
3. Authorize Cloudflare
4. Create escalation policies
5. Set critical alerts to trigger PagerDuty

## Analytics API

### GraphQL Analytics

Query structure:
```bash
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { ... }"
  }'
```

### Example Queries

**1. Cache Performance (Last 24 hours)**

```graphql
query {
  viewer {
    zones(first: 1) {
      edges {
        node {
          httpRequests1dGroups(first: 1) {
            edges {
              node {
                cache {
                  cachedRequests
                  cachedBytes
                  uncachedRequests
                  uncachedBytes
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**2. Traffic by Country**

```graphql
query {
  viewer {
    zones(first: 1) {
      edges {
        node {
          httpRequests1dGroups(first: 1) {
            edges {
              node {
                uniqCountries
              }
            }
          }
        }
      }
    }
  }
}
```

**3. Request Status Codes**

```graphql
query {
  viewer {
    zones(first: 1) {
      edges {
        node {
          httpRequests1dGroups(first: 1) {
            edges {
              node {
                statusCode {
                  _200
                  _301
                  _302
                  _304
                  _400
                  _401
                  _403
                  _404
                  _500
                  _502
                  _503
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**4. Bandwidth & Data Transfer**

```graphql
query {
  viewer {
    zones(first: 1) {
      edges {
        node {
          httpRequests1dGroups(first: 1) {
            edges {
              node {
                sum {
                  bytes
                  requests
                  cachedBytes
                  cachedRequests
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**5. WAF Activity**

```graphql
query {
  viewer {
    zones(first: 1) {
      edges {
        node {
          firewallEventsAdaptive(first: 10) {
            edges {
              node {
                action
                clientCountry
                clientIP
                clientRequestPath
                ruleId
                timestamp
              }
            }
          }
        }
      }
    }
  }
}
```

### Script: Generate Daily Report

```bash
#!/bin/bash
# generate-cdn-report.sh

API_TOKEN="$CLOUDFLARE_API_TOKEN"
ZONE_ID="$CLOUDFLARE_ZONE_ID"

# Query GraphQL API
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { viewer { zones(first: 1) { edges { node { httpRequests1dGroups(first: 1) { edges { node { cache { cachedRequests cachedBytes uncachedRequests uncachedBytes } sum { bytes requests } } } } } } } }"
  }' | jq '.data.viewer.zones.edges[0].node.httpRequests1dGroups.edges[0].node'
```

## Logs & Events

### Real-Time Logs

Access via: Dashboard > Logs > HTTP Requests

**Log Fields:**
- `ClientIP`: Client IP address
- `ClientCountry`: Geo-location
- `ClientRequestHost`: Domain requested
- `ClientRequestMethod`: HTTP method (GET, POST, etc.)
- `ClientRequestPath`: URL path
- `ClientRequestQuery`: Query string
- `EdgeResponseStatus`: HTTP status code
- `EdgeResponseBytes`: Response size
- `CacheStatus`: HIT/MISS/EXPIRED
- `CacheResponseTime`: Cache lookup time
- `OriginResponseTime`: Origin response time
- `TLSVersion`: TLS version used
- `UserAgent`: Client user agent

### Logpush to S3

Configure in Terraform:

```hcl
enable_logpush = true
log_bucket_name = "thebot-logs"
logpush_frequency = "low"  # or "high"
```

**Fields included in S3 logs:**
- All HTTP request metadata
- Cache statistics
- WAF events
- DDoS mitigation details
- Request/response times

### Query Logs via CLI

```bash
# List recent HTTP requests
curl -X GET "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/logs/received" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result | length'
```

## Performance Optimization

### Cache Hit Ratio Optimization

**1. Identify Low Cache Hit URLs**

```bash
# Via Dashboard:
# Analytics > Cache > Cache Analytics
# Look for low hit ratio items
```

**2. Improve Cache Rules**

```hcl
# Example: Cache PDFs longer
resource "cloudflare_cache_rules" "pdf_documents" {
  zone_id = var.cloudflare_zone_id

  rules {
    description = "Cache PDF documents for 30 days"
    action      = "set"
    action_parameters {
      cache         = true
      browser_ttl   = 86400   # 1 day
      edge_ttl      = 2592000  # 30 days
    }
    expression = "http.request.uri.path matches \".*\\.pdf$\""
  }
}
```

### Compression Optimization

**Check Compression Ratio**

```bash
# Measure gzip compression
curl -s -H "Accept-Encoding: gzip" https://thebot.com/assets/app.js \
  | gzip -c | wc -c

# Measure uncompressed size
curl -s https://thebot.com/assets/app.js | wc -c

# Calculate ratio
# (compressed / uncompressed) * 100
```

**Expected Compression Ratios:**
- JavaScript: 60-75% reduction
- CSS: 70-85% reduction
- JSON/XML: 70-90% reduction
- Images: 5-15% reduction (already compressed)

### Image Optimization

**WebP Conversion Benefits**

```bash
# Original PNG
ls -lh image.png    # e.g., 500KB

# WebP (via Cloudflare Polish)
# Typically 30-50% smaller
# Auto-served to compatible browsers
```

**Enable Polish**

In Dashboard: Performance > Image Optimization > Polish
- Select "Lossless" or "Lossy"
- Cloudflare automatically converts to WebP

### Response Time Optimization

**Identify Slow Requests**

```bash
# Via Dashboard:
# Analytics > Performance > Top 20 Slowest URIs

# Via API:
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -d '{
    "query": "query { viewer { zones(first: 1) { edges { node { httpRequests1dGroups(filter: {datetime_gt: \"2024-01-01T00:00:00Z\"}) { edges { node { requestURI avg { responseTime } } } } } } } }"
  }'
```

**Optimization Steps:**

1. Check origin response time
2. Increase cache TTLs for popular content
3. Enable HTTP/2 Server Push
4. Implement Early Hints
5. Use Cloudflare Workers for dynamic optimization

## Troubleshooting & Optimization

### Low Cache Hit Ratio

**Symptoms:**
- Cache hit ratio < 60%
- High origin traffic
- Slow page loads

**Solutions:**

```bash
# 1. Check cache headers from origin
curl -I https://api.thebot.com/api/data | grep -i cache-control

# 2. Increase TTLs for cacheable content
terraform apply -var="cache_ttl_static=2592000"

# 3. Remove cache-busting parameters
# Check for excessive query parameters

# 4. Enable caching for more content types
# Edit cloudflare.tf and add cache rules
```

### High Error Rate

**Symptoms:**
- Increased 4xx/5xx responses
- User reports errors

**Solutions:**

```bash
# 1. Check origin health
curl -I https://api.thebot.com/health
timeout 10 curl -v https://api.thebot.com/

# 2. Review WAF events
# Dashboard > Security > Events > Managed Rules

# 3. Check rate limiting
# Dashboard > Security > Rate limiting

# 4. Review error logs
curl -X GET "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/logs" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result[] | select(.status >= 500)'
```

### High Bandwidth Usage

**Symptoms:**
- Unexpected bandwidth charges
- Cache hit ratio normal but traffic high

**Solutions:**

```bash
# 1. Identify large files
# Dashboard > Logs > HTTP Requests
# Filter: EdgeResponseBytes > 5000000

# 2. Enable compression
terraform apply -var="enable_compression=true"

# 3. Enable image optimization
terraform apply -var="enable_image_optimization=true"

# 4. Review caching strategy
# May need to cache more aggressively
```

### DDoS Attacks

**Symptoms:**
- Traffic spike
- Origin under stress
- High error rates

**Monitoring:**

```bash
# Check attack timeline
curl -X POST https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -d '{
    "query": "query { viewer { zones(first: 1) { edges { node { ddosAttackEvents(first: 20, orderBy: timestamp_DESC) { edges { node { timestamp action } } } } } } }"
  }'
```

**Response:**

1. Verify attack is being mitigated by Cloudflare
2. Enable stricter security rules if needed
3. Monitor origin health
4. Review attack patterns to adjust rules

### WAF False Positives

**Symptoms:**
- Legitimate requests blocked
- High 403 rate
- User complaints

**Solutions:**

```bash
# 1. Identify blocked URLs
curl -X GET "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/logs" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | \
  jq '.result[] | select(.status == 403)'

# 2. Review triggered rules
# Dashboard > Security > Events > Managed Rules

# 3. Whitelist legitimate requests
# Dashboard > Security > WAF > Managed Rules > Edit rules

# 4. Adjust sensitivity
# May need to use "Challenge" instead of "Block"
```

### Slow Response Times

**Symptoms:**
- Response time > 1s
- Users report slowness

**Solutions:**

```bash
# 1. Check origin performance
time curl -o /dev/null -s https://api.thebot.com

# 2. Check Cloudflare edge location
# Usually <100ms from edge to user

# 3. Check DNS resolution
dig thebot.com

# 4. Enable Early Hints
terraform apply -var="enable_early_hints=true"

# 5. Use Cloudflare Workers for optimization
# Implement caching at edge level
```

## Scheduled Reports

### Daily Report

```bash
#!/bin/bash
# daily-report.sh - Run daily via cron

REPORT_FILE="cdn-report-$(date +%Y-%m-%d).txt"

{
  echo "=== THE_BOT CDN Daily Report ==="
  echo "Generated: $(date)"
  echo

  echo "=== Cache Metrics ==="
  echo "Cache hit ratio: $(curl ... | jq '.cache.hitRatio')"

  echo "=== Traffic ==="
  echo "Total requests: $(curl ... | jq '.sum.requests')"
  echo "Total bytes: $(curl ... | jq '.sum.bytes')"

  echo "=== Errors ==="
  echo "4xx errors: $(curl ... | jq '.status._4xx')"
  echo "5xx errors: $(curl ... | jq '.status._5xx')"

} > "$REPORT_FILE"

# Email report
mail -s "CDN Daily Report $(date +%Y-%m-%d)" admin@thebot.com < "$REPORT_FILE"
```

### Weekly Report

```bash
#!/bin/bash
# weekly-report.sh - Run weekly via cron (Mondays at 8am)

# Generate comprehensive report with:
# - Cache performance trend
# - Top URLs by traffic
# - WAF activity summary
# - DDoS events
# - Bandwidth savings
# - Performance metrics
```

## Best Practices

1. **Monitor regularly**: Check dashboard at least daily
2. **Set up alerts**: Get notified of issues immediately
3. **Analyze trends**: Use GraphQL API for in-depth analysis
4. **Optimize continuously**: Review and adjust cache rules monthly
5. **Document changes**: Keep records of rule updates
6. **Test thoroughly**: Verify changes don't break functionality
7. **Review logs**: Investigate unusual traffic patterns
8. **Backup state**: Keep regular backups of Terraform state

## Next Steps

1. Access Cloudflare Dashboard: https://dash.cloudflare.com
2. Set up alerts in Notifications
3. Review current performance metrics
4. Configure log delivery (Logpush)
5. Create dashboards or reports
6. Set up monitoring tools (Datadog, New Relic, etc.)
7. Schedule regular review meetings
