# API Gateway Infrastructure

Complete API Gateway setup for THE BOT Platform with Nginx and Kong implementations.

## Files

### Configurations

- **kong.yml** - Kong API Gateway configuration
  - Service definitions (v1, v2, WebSocket)
  - Rate limiting policies
  - Authentication (Key Auth, JWT)
  - CORS and security headers
  - Plugin configuration

- **docker-compose.yml** - Docker Compose for Kong stack
  - Kong API Gateway
  - PostgreSQL database
  - Redis cache
  - Konga admin UI
  - Prometheus metrics
  - Grafana visualization
  - StatsD metrics collector

## Quick Start

### Using Nginx (Recommended for Production)

1. Copy Nginx configuration:
```bash
sudo cp ../nginx/api-gateway.conf /etc/nginx/conf.d/
```

2. Update backends in config:
```bash
# Edit /etc/nginx/conf.d/api-gateway.conf
# Replace backend-*.internal:8000 with actual backend IPs
```

3. Test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

4. Verify health:
```bash
curl https://api.the-bot.ru/health
```

### Using Kong (For Complex Deployments)

1. Start Kong stack:
```bash
docker-compose up -d
```

2. Initialize database:
```bash
docker-compose exec kong kong migrations bootstrap
```

3. Access Konga UI:
```
http://localhost:1337
```

4. Add Kong node in Konga:
- Name: Kong
- URL: http://kong:8001

5. Deploy configuration (optional, using decK):
```bash
# Install decK
brew install deckhq/deckpkg/deck

# Sync configuration
deck sync kong.yml --kong-addr http://localhost:8001
```

6. Verify Kong:
```bash
curl http://localhost:8001/services
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Client Requests                                      │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    ┌───▼────────┐        ┌──────▼──────┐
    │   Nginx    │        │    Kong     │
    │  Gateway   │        │   Gateway   │
    │ (Production)        │ (Optional)  │
    └───┬────────┘        └──────┬──────┘
        │                         │
        │    ┌────────────────────┘
        │    │
    ┌───▼────▼────────────────────┐
    │  Django Middleware Stack     │
    │ - Request ID Injection       │
    │ - API Versioning             │
    │ - Rate Limiting              │
    │ - Request Validation         │
    │ - Response Transform         │
    │ - Circuit Breaker            │
    └───┬────────────────────────┘
        │
    ┌───▼────────────────────────┐
    │  Backend Services           │
    │ - REST API (v1, v2)        │
    │ - WebSocket (Daphne)       │
    │ - Admin Panel              │
    └────────────────────────────┘
```

## Configuration

### Nginx Gateway (api-gateway.conf)

Key features:
- Request ID injection (X-Request-ID)
- API versioning (/api/v1/, /api/v2/)
- Rate limiting per API key
- Request/response logging
- CORS headers
- Security headers
- Circuit breaker pattern

### Kong Configuration (kong.yml)

Key sections:
- **Upstreams**: Backend service definitions
- **Services**: API endpoint definitions
- **Routes**: URL routing rules
- **Consumers**: API users/API keys
- **Plugins**: Global and per-route plugins

### Django Middleware (config/middleware/api_gateway.py)

Middleware stack:
1. **RequestIDMiddleware** - Request ID injection
2. **APIVersioningMiddleware** - API version parsing
3. **RateLimitingMiddleware** - Per-API-key/IP rate limiting
4. **RequestValidationMiddleware** - Content-type, size validation
5. **ResponseTransformationMiddleware** - CORS, security headers
6. **CircuitBreakerMiddleware** - Failure handling
7. **GatewayLoggingMiddleware** - Comprehensive logging

## Rate Limiting

### Configured Limits

| Endpoint | API Key | Per IP | Period |
|----------|---------|--------|--------|
| General API | 100 req/s | 50 req/s | 1s |
| Auth (login) | 5 req/m | 5 req/m | 1m |
| Upload | 10 req/m | 10 req/m | 1m |
| WebSocket | 10 req/s | 10 req/s | 1s |

### Customization

**Nginx (api-gateway.conf)**:
```nginx
limit_req_zone $api_key_hash zone=api_key_limit:50m rate=100r/s;
```

**Kong (kong.yml)**:
```yaml
- name: rate-limiting
  config:
    minute: 6000  # 100 req/s
```

**Django (settings.py)**:
```python
RATE_LIMIT_CONFIG = {
    'default': {'requests': 100, 'period': 1},
    'auth': {'requests': 5, 'period': 60},
}
```

## Monitoring

### Nginx Gateway

View metrics:
```bash
curl https://api.the-bot.ru/metrics
```

Check logs:
```bash
tail -f /var/log/nginx/api-gateway-access.log
tail -f /var/log/nginx/api-gateway-metrics.log
```

### Kong Gateway

Admin API:
```bash
curl http://localhost:8001/services
curl http://localhost:8001/routes
curl http://localhost:8001/plugins
```

Konga UI:
```
http://localhost:1337
```

Prometheus metrics:
```
http://localhost:9090
```

Grafana dashboards:
```
http://localhost:3000
```

## Testing

### API Endpoint Tests

```bash
# Health check
curl https://api.the-bot.ru/health

# API versions
curl https://api.the-bot.ru/api/versions

# Request with ID
curl -H "X-Request-ID: test-123" https://api.the-bot.ru/api/v1/users/

# Rate limiting (should be rejected after limit)
for i in {1..150}; do curl https://api.the-bot.ru/api/v1/users/; done

# Content-type validation (should fail)
curl -X POST https://api.the-bot.ru/api/v1/users/ \
  -H "Content-Type: text/xml" \
  -d '<data/>'
```

### Unit Tests

Run gateway tests:
```bash
cd backend
pytest tests/api_gateway/test_gateway.py -v
```

Test specific feature:
```bash
# Test rate limiting
pytest tests/api_gateway/test_gateway.py::TestRateLimitingMiddleware -v

# Test request ID
pytest tests/api_gateway/test_gateway.py::TestRequestIDMiddleware -v
```

## Performance Tuning

### Nginx Optimization

Worker processes:
```nginx
worker_processes auto;
worker_connections 65535;
```

Connection pooling:
```nginx
upstream backend_api {
    keepalive 32;
    keepalive_timeout 60s;
    keepalive_requests 100;
}
```

### Kong Optimization

Database connections:
```
KONG_PG_POOL_SIZE=5
```

Cache settings:
```
KONG_CACHE_DEFAULT_TTL=3600
KONG_CACHE_MAX_SIZE=134217728
```

### Redis Optimization

Memory:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Security

### CORS Configuration

Allowed origins (in Django middleware):
```python
CORS_ALLOW_ORIGINS = [
    'https://the-bot.ru',
    'https://www.the-bot.ru',
]
```

### Security Headers

Added by response transformation middleware:
```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self';
```

### Rate Limiting

Prevents brute force attacks:
- Auth endpoints: 5 req/m
- Upload endpoints: 10 req/m
- Default API: 100 req/s

### Circuit Breaker

Protects backend from cascading failures:
- Threshold: 10 failures in 60s
- Recovery timeout: 30s
- Returns 503 when open

## Troubleshooting

### Rate Limit Not Working

Check Redis:
```bash
redis-cli ping
redis-cli KEYS "ratelimit:*"
```

### Circuit Breaker Always Open

Check backend:
```bash
curl -v http://backend-1:8000/health
```

### CORS Issues

Debug with OPTIONS request:
```bash
curl -X OPTIONS -v https://api.the-bot.ru/api/v1/users/ \
  -H "Origin: http://localhost:8080"
```

### Kong Container Won't Start

Check database:
```bash
docker-compose logs kong
docker-compose exec postgres psql -U kong -d kong -c "SELECT version();"
```

## Maintenance

### Updating Configuration

**Nginx**:
1. Edit `/etc/nginx/conf.d/api-gateway.conf`
2. Test: `sudo nginx -t`
3. Reload: `sudo systemctl reload nginx`

**Kong** (via Konga UI or decK):
1. Add/edit services, routes, plugins
2. Test via Admin API
3. Verify via Konga UI

### Monitoring Uptime

```bash
# Simple health check
watch -n 5 'curl -s https://api.the-bot.ru/health | jq .'

# Monitor errors
tail -f /var/log/nginx/api-gateway-error.log | grep -E "502|503|504"
```

### Log Rotation

For Nginx logs:
```
# Add to /etc/logrotate.d/nginx
/var/log/nginx/api-gateway-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

## Comparison: Nginx vs Kong

| Aspect | Nginx | Kong |
|--------|-------|------|
| Setup time | 5 mins | 15 mins |
| Memory usage | <100MB | 500MB+ |
| Performance | ~10k req/s | ~5k req/s |
| Configuration | Static file | Dynamic API |
| Database | Not needed | PostgreSQL |
| Plugins | Limited | Rich ecosystem |
| UI | None | Konga |
| Production | ✓ | ✓ |
| Development | Good | Better |

## Next Steps

1. **Deploy Nginx gateway** (recommended for production)
2. **Set up monitoring** (Prometheus + Grafana)
3. **Configure alerting** (rate limit violations, circuit breaker)
4. **Load testing** (verify rate limits, performance)
5. **Documentation** (API docs with versioning info)

## Related Documentation

- `/docs/API_GATEWAY.md` - Complete API Gateway documentation
- `/docs/DEPLOYMENT.md` - Production deployment guide
- `/docs/SECURITY.md` - Security architecture
- `/nginx/api-gateway.conf` - Nginx configuration
- `/backend/config/middleware/api_gateway.py` - Django middleware

## Support

For issues:
1. Check logs: `/var/log/nginx/api-gateway-*.log`
2. Test endpoint: `https://api.the-bot.ru/health`
3. Review Kong Admin API: `http://localhost:8001`
4. Check Django middleware settings in `settings.py`
5. Run test suite: `pytest tests/api_gateway/`

## License

See LICENSE file in project root.
